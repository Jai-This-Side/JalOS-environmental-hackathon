output "instance_id" { value = aws_instance.jalos.id }
output "public_ip" { value = aws_instance.jalos.public_ip }
output "health_url" { value = "http://${aws_instance.jalos.public_ip}" }
output "s3_bucket" { value = aws_s3_bucket.artifacts.bucket }
output "ec2_role_name" { value = aws_iam_role.ec2.name }
output "github_deploy_role_arn" { value = aws_iam_role.github_deploy.arn }
output "runtime_environment_parameter" { value = aws_ssm_parameter.runtime_environment.name }
output "demo_admin_email" { value = "admin@jalos.local" }
output "demo_admin_password" {
  value     = random_password.demo_admin.result
  sensitive = true
}
output "demo_resident_email" { value = "resident@jalos.local" }
output "demo_resident_password" {
  value     = random_password.demo_resident.result
  sensitive = true
}
