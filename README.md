
# Wordpress CDK using Fargate and Aurora RDS DB and EFS python Construct

##  EFS is essential for Persistence of Wordpress Themes and Plugins

If wordpress tasks are restarted then without an EFS mount Wordpress loses its configuration around themes and plugins.  Note other stuff such as posts ans users etc is persisted in the DB.


## Fargate and EFS Mount Banana Skin

Note unless you take care of IAM and POSIX permissions in the EFS the Fargate task will not be able to mount the EFS.

See here for explanation https://aws.amazon.com/blogs/containers/developers-guide-to-using-amazon-efs-with-amazon-ecs-and-aws-fargate-part-2/#:%7E:text=POSIX%20permissions

And here for a good example of how to so it right - https://bliskavka.com/2021/10/21/AWS-CDK-Fargate-with-EFS/

Key points are that IAM permmissons need to be set

```
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
```

and IAM needs to be enabled in the configuration for the volume

```
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

```





This uses the latest version of Wordpress in Dockerhub and AuroraMysql 3.05.1 (MySQL 8)

This exposes port 80, you can add /wp-admin to the url to hit the wordpress admin page.

------------------------

This is a blank project for CDK development with Python.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
