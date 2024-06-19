import json
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker

vpc = aws.ec2.get_vpc(default=True)
subnets = aws.ec2.get_subnets(
    filters=[aws.ec2.GetSubnetsFilterArgs(name="vpc-id", values=[vpc.id])]
)

ecr_repository = aws.ecr.Repository("enf-repo", name="enf-repo")

auth_token = aws.ecr.get_authorization_token(registry_id=ecr_repository.registry_id)

enf_image = docker.Image(
    f"enf-image",
    build=docker.DockerBuildArgs(
        context=".",
        dockerfile=f"./Dockerfile",
        platform="linux/amd64",
    ),
    image_name=ecr_repository.repository_url.apply(
        lambda repository_url: f"{repository_url}:latest"
    ),
    registry=docker.RegistryArgs(
        username=auth_token.user_name,
        password=pulumi.Output.secret(auth_token.password),
        server=ecr_repository.repository_url
    )
)

security_group = aws.ec2.SecurityGroup(
    "flask-celery-sg",
    vpc_id=vpc.id,
    description="Allow HTTP and Redis",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"]
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=6379,
            to_port=6379,
            cidr_blocks=["0.0.0.0/0"]
        )
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"]
        )
    ]
)

cache_subnet_group = aws.elasticache.SubnetGroup(
    "redis-subnet-group",
    subnet_ids=subnets.ids
)

cache_cluster = aws.elasticache.Cluster(
    "redis-cluster",
    engine="redis",
    node_type="cache.t3.micro",
    num_cache_nodes=1,
    parameter_group_name="default.redis7",
    subnet_group_name=cache_subnet_group.name,
    port=6379,
    security_group_ids=[security_group.id]
)

cluster = aws.ecs.Cluster("flask-celery-cluster")

log_group = aws.cloudwatch.LogGroup("flask-app-log-group")

log_configuration = {
    "logDriver": "awslogs",
    "options": {
        "awslogs-group": log_group.name,
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
    }
}

alb = aws.lb.LoadBalancer(
    "flask-alb",
    internal=False,
    security_groups=[security_group.id],
    subnets=subnets.ids
)

target_group = aws.lb.TargetGroup(
    "flask-tg",
    port=80,
    protocol="HTTP",
    target_type="ip",
    vpc_id=vpc.id
)

listener = aws.lb.Listener(
    "flask-listener",
    load_balancer_arn=alb.arn,
    port=80,
    default_actions=[aws.lb.ListenerDefaultActionArgs(
        type="forward",
        target_group_arn=target_group.arn
    )]
)

redis_url = pulumi.Output.concat("redis://", cache_cluster.cache_nodes[0].address, ":6379/0")

bucket = aws.s3.Bucket("flask-app-bucket")

task_role = aws.iam.Role(
    "task-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    }"""
)

s3_policy = aws.iam.Policy(
    "s3-policy",
    policy=pulumi.Output.all(bucket.arn).apply(lambda bucket_arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:*"
                ],
                "Resource": [
                    f"{bucket_arn[0]}",
                    f"{bucket_arn[0]}/*"
                ]
            }
        ]
    }))
)

aws.iam.RolePolicyAttachment(
    "task-exec-role-s3-policy",
    role=task_role.name,
    policy_arn=s3_policy.arn
)

execution_role = aws.iam.Role(
    "execution-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }"""
)

aws.iam.RolePolicyAttachment(
    "task-exec-role-policy",
    role=execution_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
)

containers_env = [
    {"name": "REDIS_URL", "value": redis_url},
    {"name": "BUCKET_NAME", "value": bucket.bucket},
]

flask_app_container = {
    "name": "flask-app",
    "image": enf_image.image_name,
    "command": ["gunicorn", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:80", "--log-level", "info", "--access-logfile", "-", "make_app:flask_app"],
    "essential": True,
    "portMappings": [{
        "containerPort": 80
    }],
    "logConfiguration": log_configuration,
    "environment": containers_env
}

task_cpu = f"{4 * 1024}"
task_memory = f"{8 * 1024}"

flask_task_definition = aws.ecs.TaskDefinition(
    "flask-app-task",
    family="flask-app-task",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    cpu=task_cpu,
    memory=task_memory,
    execution_role_arn=execution_role.arn,
    task_role_arn=task_role.arn,
    container_definitions=pulumi.Output.all(flask_app_container).apply(
        lambda containers: json.dumps(containers)
    )
)

flask_service = aws.ecs.Service(
    "flask-app-service",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=flask_task_definition.arn,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        subnets=subnets.ids,
        assign_public_ip=True,
        security_groups=[security_group.id]
    ),
    load_balancers=[aws.ecs.ServiceLoadBalancerArgs(
        target_group_arn=target_group.arn,
        container_name=flask_app_container['name'],
        container_port=80
    )]
)

celery_worker_container = {
    "name": "celery-worker",
    "image": enf_image.image_name,
    "command": ["celery", "-A", "make_app:celery_app", "worker", "--loglevel=info", "--concurrency=2"],
    "essential": True,
    "logConfiguration": log_configuration,
    "environment": containers_env
}

celery_task_definition = aws.ecs.TaskDefinition(
    "celery-worker-task",
    family="celery-worker-task",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    cpu=task_cpu,
    memory=task_memory,
    execution_role_arn=execution_role.arn,
    task_role_arn=task_role.arn,
    container_definitions=pulumi.Output.all(celery_worker_container).apply(
        lambda containers: json.dumps(containers)
    )
)

celery_service = aws.ecs.Service(
    "celery-worker-service",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=celery_task_definition.arn,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        subnets=subnets.ids,
        assign_public_ip=True,
        security_groups=[security_group.id]
    )
)

pulumi.export("app_url", alb.dns_name)
