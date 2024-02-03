from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
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
        

        # Define the WordPress Fargate service with environment variables for database connection
        wordpress_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "MyWordPressService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("wordpress:latest"),
                container_port=80,
                environment={
                    "WORDPRESS_DB_HOST": aurora_cluster.cluster_endpoint.hostname,
                    "WORDPRESS_DB_NAME": "wordpress",
                    # Retrieve database username and password from the secrets manager
                    "WORDPRESS_DB_USER": db_credentials_secret.secret_value_from_json("username").unsafe_unwrap(),
                    "WORDPRESS_DB_PASSWORD": db_credentials_secret.secret_value_from_json("password").unsafe_unwrap(),
                },
            ),
            public_load_balancer=True
        )

        # Allow the Fargate service to connect to the Aurora cluster
        aurora_cluster.connections.allow_from(wordpress_service.service, ec2.Port.tcp(3306))
