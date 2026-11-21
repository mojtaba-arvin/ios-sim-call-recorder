terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  name = "${var.project}-${var.environment}"
  common_tags = merge(var.tags, {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
  })
  db_name = "bridge"
  provider_secret_keys = [
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PROVIDER_ACCOUNT_ID",
    "TWILIO_FROM_NUMBER",
    "TWILIO_CONSENT_POLICY_VERSION",
    "TWILIO_CONSENT_DISCLOSURE",
    "PARTICIPANT_ADDRESS_KEY_HEX"
  ]
  api_secrets = concat(
    [
      {
        name      = "DATABASE_HOST"
        valueFrom = "${aws_db_instance.database.master_user_secret[0].secret_arn}:host::"
      },
      {
        name      = "DATABASE_USER"
        valueFrom = "${aws_db_instance.database.master_user_secret[0].secret_arn}:username::"
      },
      {
        name      = "DATABASE_PASSWORD"
        valueFrom = "${aws_db_instance.database.master_user_secret[0].secret_arn}:password::"
      },
      {
        name      = "BRIDGE_API_TOKEN_HASHES"
        valueFrom = "${var.application_secret_arn}:BRIDGE_API_TOKEN_HASHES::"
      }
    ],
    var.enable_live_twilio ? [
      for key in local.provider_secret_keys : {
        name      = key
        valueFrom = "${var.application_secret_arn}:${key}::"
      }
    ] : []
  )
  provider_secrets = concat(
    [
      {
        name      = "DATABASE_HOST"
        valueFrom = "${aws_db_instance.database.master_user_secret[0].secret_arn}:host::"
      },
      {
        name      = "DATABASE_USER"
        valueFrom = "${aws_db_instance.database.master_user_secret[0].secret_arn}:username::"
      },
      {
        name      = "DATABASE_PASSWORD"
        valueFrom = "${aws_db_instance.database.master_user_secret[0].secret_arn}:password::"
      }
    ],
    [
      for key in local.provider_secret_keys : {
        name      = key
        valueFrom = "${var.application_secret_arn}:${key}::"
      }
    ]
  )
}

resource "aws_kms_key" "media" {
  description             = "${local.name} media encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = local.common_tags
}

resource "aws_kms_alias" "media" {
  name          = "alias/${local.name}-media"
  target_key_id = aws_kms_key.media.key_id
}

resource "aws_s3_bucket" "media" {
  bucket        = "${local.name}-media-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.media.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"
    filter {}
    expiration {
      days = 90
    }
  }
}

resource "aws_db_subnet_group" "database" {
  name       = "${local.name}-db"
  subnet_ids = var.private_subnet_ids
  tags       = local.common_tags
}

resource "aws_security_group" "load_balancer" {
  name   = "${local.name}-alb"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.common_tags
}

resource "aws_security_group" "application" {
  name   = "${local.name}-application"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.load_balancer.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.common_tags
}

resource "aws_security_group" "database" {
  name   = "${local.name}-database"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.common_tags
}

resource "aws_db_instance" "database" {
  identifier                 = "${local.name}-postgres"
  engine                     = "postgres"
  instance_class             = "db.t4g.micro"
  allocated_storage          = 20
  max_allocated_storage      = 50
  db_name                    = local.db_name
  username                   = var.db_username
  manage_master_user_password    = true
  master_user_secret_kms_key_id = aws_kms_key.media.arn
  port                       = 5432
  db_subnet_group_name       = aws_db_subnet_group.database.name
  vpc_security_group_ids     = [aws_security_group.database.id]
  publicly_accessible        = false
  storage_encrypted          = true
  kms_key_id                 = aws_kms_key.media.arn
  backup_retention_period    = 1
  deletion_protection        = false
  skip_final_snapshot        = true
  auto_minor_version_upgrade = true
  tags                       = local.common_tags
}

resource "aws_ecr_repository" "backend" {
  name                 = "${local.name}-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.media.arn
  }
  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name}/api"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.name}/worker"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "retention" {
  name              = "/ecs/${local.name}/retention"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_lb" "api" {
  name               = substr("${local.name}-api", 0, 32)
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.load_balancer.id]
  internal           = false
  tags               = local.common_tags
}

resource "aws_lb_target_group" "api" {
  name        = substr("${local.name}-api", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health/ready"
    matcher             = "200"
    interval            = 15
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = local.common_tags
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_ecs_cluster" "main" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = local.common_tags
}

resource "aws_iam_role" "task_execution" {
  name = "${local.name}-task-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "task_secrets" {
  role = aws_iam_role.task_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_db_instance.database.master_user_secret[0].secret_arn, var.application_secret_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.media.arn]
      }
    ]
  })
}

resource "aws_iam_role" "task" {
  name = "${local.name}-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "task_media" {
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Resource = ["${aws_s3_bucket.media.arn}/tenants/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.media.arn]
        Condition = {
          StringLike = { "s3:prefix" = ["tenants/*"] }
        }
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = [aws_kms_key.media.arn]
      }
    ]
  })
}

locals {
  api_container = {
    name      = "api"
    image     = "${aws_ecr_repository.backend.repository_url}:staging"
    essential = true
    command   = ["sh", "-c", "python migrate.py && uvicorn asgi:create_app --factory --host 0.0.0.0 --port 8000"]
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "TWILIO_ENABLED", value = tostring(var.enable_live_twilio) },
      { name = "MEDIA_BUCKET", value = aws_s3_bucket.media.bucket },
      { name = "MEDIA_KMS_KEY_ID", value = aws_kms_key.media.arn },
      { name = "TWILIO_PUBLIC_ORIGIN", value = var.public_origin },
      { name = "MEDIA_RETENTION_DAYS", value = "30" },
      { name = "DATABASE_PORT", value = "5432" },
      { name = "DATABASE_NAME", value = local.db_name }
    ]
    secrets = local.api_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "api"
      }
    }
  }
  worker_container = {
    name      = "worker"
    image     = "${aws_ecr_repository.backend.repository_url}:staging"
    essential = true
    command   = ["python", "worker_main.py"]
    environment = [
      { name = "TWILIO_PUBLIC_ORIGIN", value = var.public_origin },
      { name = "DATABASE_PORT", value = "5432" },
      { name = "DATABASE_NAME", value = local.db_name }
    ]
    secrets     = local.provider_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "worker"
      }
    }
  }
  retention_container = {
    name      = "retention"
    image     = "${aws_ecr_repository.backend.repository_url}:staging"
    essential = true
    command   = ["python", "retention_main.py"]
    environment = [
      { name = "MEDIA_BUCKET", value = aws_s3_bucket.media.bucket },
      { name = "MEDIA_KMS_KEY_ID", value = aws_kms_key.media.arn },
      { name = "DATABASE_PORT", value = "5432" },
      { name = "DATABASE_NAME", value = local.db_name }
    ]
    secrets = local.provider_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.retention.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "retention"
      }
    }
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.api_cpu)
  memory                   = tostring(var.api_memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.api_container])
  tags                     = local.common_tags
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.worker_container])
  tags                     = local.common_tags
}

resource "aws_ecs_task_definition" "retention" {
  family                   = "${local.name}-retention"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.retention_container])
  tags                     = local.common_tags
}

resource "aws_ecs_service" "api" {
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  enable_execute_command = false

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.application.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  depends_on = [aws_lb_listener.https]
  tags       = local.common_tags
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.enable_live_twilio ? var.worker_desired_count : 0
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.application.id]
    assign_public_ip = true
  }
  tags = local.common_tags
}

resource "aws_ecs_service" "retention" {
  name            = "${local.name}-retention"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.retention.arn
  desired_count   = var.enable_live_twilio ? var.retention_desired_count : 0
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.application.id]
    assign_public_ip = true
  }
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "api_cpu" {
  alarm_name          = "${local.name}-api-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.api.name
  }
  alarm_description = "API service CPU above 80% for three periods."
  tags              = local.common_tags
}

data "aws_iam_policy_document" "github_deploy_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.github_oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "${local.name}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_deploy_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "github_deploy" {
  role = aws_iam_role.github_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["ecs:DescribeServices", "ecs:DescribeTaskDefinition", "ecs:DescribeTasks", "ecs:RunTask", "ecs:UpdateService", "ecs:RegisterTaskDefinition"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [aws_iam_role.task_execution.arn, aws_iam_role.task.arn]
      }
    ]
  })
}

output "api_url" {
  value = var.public_origin
}
output "alb_dns_name" {
  value = aws_lb.api.dns_name
}
output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}
output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}
output "api_service_name" {
  value = aws_ecs_service.api.name
}
output "api_task_family" {
  value = aws_ecs_task_definition.api.family
}
output "worker_service_name" {
  value = aws_ecs_service.worker.name
}
output "retention_service_name" {
  value = aws_ecs_service.retention.name
}
output "github_deploy_role_arn" {
  value = aws_iam_role.github_deploy.arn
}
output "database_secret_arn" {
  value = aws_db_instance.database.master_user_secret[0].secret_arn
}
output "media_bucket" {
  value = aws_s3_bucket.media.bucket
}
output "media_kms_key_arn" {
  value = aws_kms_key.media.arn
}
