from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_efs as efs,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    RemovalPolicy
)

from constructs import Construct

class WordpressFargateAuroraStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(self, "MyVpc", max_azs=2)

        # Create an ECS cluster
        cluster = ecs.Cluster(self, "MyCluster", vpc=vpc)

        # Define an Aurora MySQL database
        aurora_cluster = rds.DatabaseCluster(self, "MyAuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_3_05_1),
            instance_props=rds.InstanceProps(
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                publicly_accessible=False
            ),
            removal_policy=RemovalPolicy.DESTROY,
            default_database_name="wordpress"
        )

        # Assuming the secret with DB credentials is created manually or through another part of the script
        # Reference an existing AWS Secrets Manager secret by ARN (replace 'your-secret-arn-here' with your secret's ARN)
        db_credentials_secret = aurora_cluster.secret

        # Create a security group for EFS
        efs_security_group = ec2.SecurityGroup(
            self, "EfsSecurityGroup",
            vpc=vpc,
            description="Allow NFS traffic to EFS",
            allow_all_outbound=True  # Adjust according to your requirements
        )

        # Allow inbound NFS traffic on port 2049
        efs_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),  # Adjust this to limit access
            connection=ec2.Port.tcp(2049),
            description="Allow NFS traffic from within the VPC"
        )
        
        file_system = efs.FileSystem(
            self, "WebRoot",
            vpc=vpc,
            security_group=efs_security_group,
            removal_policy=RemovalPolicy.DESTROY,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
        )

        access_point = efs.AccessPoint(self, "AccessPoint",
                               file_system=file_system)

        # Define the IAM policy statement with broader EFS permissions
        efs_policy_statement = iam.PolicyStatement(
            actions=[
                "elasticfilesystem:ClientMount",
                "elasticfilesystem:ClientWrite",
                "elasticfilesystem:DescribeMountTargets",
                # Include additional permissions as necessary
            ],
            resources=["*"],  # Best practice is to specify more restrictive resource ARNs
            effect=iam.Effect.ALLOW
        )


       # Create a new Fargate task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "MyTaskDefinition",
            cpu=256,
            memory_limit_mib=512,
        )

        task_definition.add_to_task_role_policy(efs_policy_statement)


        # Add the EFS volume to the task definition
        task_definition.add_volume(
            name="WebRoot",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system.file_system_id,
                transit_encryption='ENABLED',
                authorization_config=ecs.AuthorizationConfig(
                    iam = 'ENABLED',
                    access_point_id=access_point.access_point_id,
                    
                )
            )
        )

        # Add a container to the task definition
        container = task_definition.add_container(
            "WordpressContainer",
            image=ecs.ContainerImage.from_registry("wordpress:latest"),
            environment={
                "WORDPRESS_DB_HOST": aurora_cluster.cluster_endpoint.hostname,
                "WORDPRESS_DB_NAME": "wordpress",
                "WORDPRESS_DB_USER": db_credentials_secret.secret_value_from_json("username").unsafe_unwrap(),
                "WORDPRESS_DB_PASSWORD": db_credentials_secret.secret_value_from_json("password").unsafe_unwrap(),
            }
        )

        # Correctly add the port mapping for the container
        container.add_port_mappings(
            ecs.PortMapping(
                container_port=80,  # WordPress default port
            )
        )

        # Mount the EFS volume to the container
        container.add_mount_points(
            ecs.MountPoint(
                container_path="/var/www/html",
                source_volume="WebRoot",
                read_only=False,
            )
        )

        # Create or identify the security group for your ECS tasks
        ecs_security_group = ec2.SecurityGroup(
            self, "EcsSecurityGroup",
            vpc=vpc,
            description="ECS tasks security group",
            allow_all_outbound=True  # Allows the ECS tasks to communicate with other services
        )

        # Explicitly allow outbound traffic to the EFS security group on port 2049
        ecs_security_group.add_egress_rule(
            peer=efs_security_group,  # Target the EFS security group
            connection=ec2.Port.tcp(2049),
            description="Allow NFS traffic to EFS"
        )

        # Define the WordPress Fargate service with the custom task definition
        wordpress_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "MyWordPressService",
            cluster=cluster,
            desired_count=1,
            task_definition=task_definition,  # Use the custom task definition
            security_groups=[ecs_security_group],
            public_load_balancer=True,
        )

        # Allow the Fargate service to connect to the Aurora cluster
        aurora_cluster.connections.allow_from(wordpress_service.service.connections, ec2.Port.tcp(3306))

        #file_system.connections.allow_from(wordpress_service.service, ec2.Port.tcp(2049))

        
        
        