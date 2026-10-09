resource "random_password" "postgres" {
  length  = 40
  special = false
}

resource "random_password" "jwt" {
  length  = 64
  special = false
}

resource "random_password" "demo_admin" {
  length  = 24
  special = false
}

resource "random_password" "demo_resident" {
  length  = 24
  special = false
}

resource "aws_ssm_parameter" "runtime_environment" {
  name        = "/jalos/${var.environment}/runtime-environment"
  description = "Private runtime environment for the JalOS EC2 Compose deployment."
  type        = "SecureString"
  tier        = "Standard"
  value = templatefile("${path.module}/runtime.env.tftpl", {
    aws_region             = var.aws_region
    cloudwatch_log_group   = aws_cloudwatch_log_group.application.name
    postgres_password      = random_password.postgres.result
    jwt_secret             = random_password.jwt.result
    demo_admin_email       = "admin@jalos.local"
    demo_admin_password    = random_password.demo_admin.result
    demo_resident_email    = "resident@jalos.local"
    demo_resident_password = random_password.demo_resident.result
  })
}

