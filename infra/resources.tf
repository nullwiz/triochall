provider "aws" {
  region = "us-west-2"
}

data "aws_vpc" "default" {
  default = true
}
// Assumes default vpc 
data "aws_subnet_ids" "all" {
  vpc_id = data.aws_vpc.default.id
}

resource "aws_security_group" "db_sg" {
  name   = "db_sg"
  vpc_id = data.aws_vpc.default.id
}

// Name discovery is necessary for Mailhog
resource "aws_service_discovery_private_dns_namespace" "private_namespace" {
  name        = "services.local"  # You can choose your namespace
  description = "Service Discovery Namespace for internal services"
  vpc         = data.aws_vpc.default.id
}

resource "aws_service_discovery_service" "mailhog_service" {
  name = "mailhog"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.private_namespace.id
    
    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}


// Role for sending emails 
resource "aws_iam_role" "ses_role" {
  name = "SESRole"
  assume_role_policy = <<EOF
{
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
}
EOF
}

resource "aws_iam_role_policy_attachment" "ses_role_policy_attachment" {
  role       = aws_iam_role.ses_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSESFullAccess"
}

resource "aws_db_instance" "postgres" {
  identifier           = "my-postgres"
  engine               = "postgres"
  engine_version       = "13.3"
  instance_class       = "db.t3.micro"
  username             = "postgres"
  password             = "password"
  allocated_storage    = 20
  vpc_security_group_ids = [aws_security_group.db_sg.id]
}

resource "aws_security_group" "redis_sg" {
  name   = "redis_sg"
  vpc_id = data.aws_vpc.default.id
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "my-redis"
  engine               = "redis"
  node_type            = "cache.t2.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis5.0"
  engine_version       = "5.0.6"
  port                 = 6379
  subnet_group_name    = "default"
  vpc_security_group_ids = [aws_security_group.redis_sg.id]
}

resource "aws_ecs_cluster" "cluster" {
  name = "my-cluster"
}

resource "aws_ecs_task_definition" "task" {
  family                   = "service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "0.5GB"

  container_definitions = jsonencode([{
    name  = "triochall-app"
    image = "<docker_image>"
    portMappings = [{
      containerPort = 5000
      hostPort      = 5000
    }]
    environment = [
      // All of these could come off secret management aswell
      { name = "DB_HOST", value = aws_db_instance.postgres.address },
      { name = "DB_PORT", value = tostring(aws_db_instance.postgres.port) },
      { name = "DB_USER", value = aws_db_instance.postgres.username },
      { name = "DB_PASS", value = aws_db_instance.postgres.password },
      { name = "DB_NAME", value = aws_db_instance.postgres.name },
      { name = "REDIS_URL", value = aws_elasticache_cluster.redis.cache_nodes.0.address },
      { name = "REDIS_PORT", value = tostring(aws_elasticache_cluster.redis.cache_nodes.0.port) }
      { name = "NOTIFICATIONS_ENV", value = "prod" },
      { name = "MAILHOG_HOST", value = "mailhog.services.local" },
      { name = "UOW", value = "sqlalchemy" },
      { name = "SECRET_KEY", value = "<Your secret key>" },
      { name = "DB_SYNC_URL", value = f"postgresql+psycopg2://postgres:password@${aws_db_instance.postgres.address}:${tostring(aws_db_instance.postgres.port)}/triochall" },
      { name = "AWS_DEFAULT_REGION", value = "us-west-2" }, 
    ]
  }])
}

// Load Balancer, Listener, Target Group, and related Security Groups follow here (as in the previous example)

resource "aws_ecs_service" "service" {
  name            = "my-service"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.task.arn
  launch_type     = "FARGATE"

  network_configuration {
    subnets = data.aws_subnet_ids.all.ids
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.lb_tg.arn
    container_name   = "triochall-app"
    container_port   = 5000
  }

  desired_count = 1
}
