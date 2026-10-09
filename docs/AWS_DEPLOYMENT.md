# AWS deployment

Terraform provisions one EC2 instance, a restricted security group, its instance role, a private S3 bucket, a CloudWatch log group, a private SSM runtime parameter, and a GitHub OIDC deploy role. GitHub Actions builds the release, uploads it to S3, deploys over Systems Manager, and checks `/health`.

The infrastructure and deployment path are implemented but not yet applied to AWS. No AWS resources have been created. Applying the current plan would create 21 resources in `ap-south-1`; review the actual Terraform plan and current account charges first. EC2, EBS, public IPv4, S3, CloudWatch logs, and data transfer can incur charges.

## AWS profile

The configured `aws login --profile jalos` session works with AWS CLI. Terraform uses the AWS SDK credential process, so configure a second local profile that exports the existing CLI session without creating access keys:

```powershell
aws configure set credential_process 'aws configure export-credentials --profile jalos --format process' --profile jalos-terraform
aws configure set region ap-south-1 --profile jalos-terraform
aws sts get-caller-identity --profile jalos-terraform
$env:AWS_PROFILE = "jalos-terraform"
```

Renew the original console login with `aws login --profile jalos` when it expires. The current AWS identity check returned `arn:aws:iam::…:user/JalOS`, not the root user. The identity's attached permissions are still broader than the app needs; before provisioning, use a purpose-scoped Terraform permission policy. Terraform must create IAM roles and an OIDC provider, so a generic `PowerUserAccess` policy is not sufficient. The instance and GitHub deployment roles created by this project are scoped to JalOS.

## Provision the infrastructure

1. Check the AWS billing dashboard and the current price and account eligibility for the selected EC2 type.
2. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars`. Set a globally unique S3 bucket name, your current public IPv4 address with `/32`, and the exact GitHub `owner/repository` that will hold this project. Do not use the example IP or repository values.
3. From PowerShell, select the profile above and inspect the plan:

   ```powershell
   $env:AWS_PROFILE = "jalos-terraform"
   Set-Location terraform
   terraform init
   terraform plan
   ```

4. Review every planned resource and cost. Only then apply the reviewed plan:

   ```powershell
   terraform apply
   ```

Terraform creates random database, JWT, and demo account passwords. The values are stored in a SecureString runtime parameter; Terraform's local state also contains secret values. Keep `terraform.tfstate` and backups private and never commit them. Read the demo login values locally when needed:

```powershell
terraform output -raw demo_admin_email
terraform output -raw demo_admin_password
terraform output -raw demo_resident_email
terraform output -raw demo_resident_password
```

## Enable GitHub OIDC deployment

After `terraform apply`, add these **repository variables** in GitHub Settings → Secrets and variables → Actions → Variables:

| Variable | Value |
|---|---|
| `AWS_ROLE_ARN` | `terraform output -raw github_deploy_role_arn` |
| `AWS_REGION` | `ap-south-1` (or the Terraform region) |
| `JALOS_ENVIRONMENT` | The Terraform `environment`, normally `hackathon` |
| `JALOS_S3_BUCKET` | `terraform output -raw s3_bucket` |
| `JALOS_INSTANCE_ID` | `terraform output -raw instance_id` |
| `JALOS_HEALTH_URL` | `terraform output -raw health_url` |

These are identifiers, not AWS access keys. Do not add long-lived AWS keys to GitHub Secrets. The Terraform OIDC trust allows only the configured repository's configured branch. A push to `main` runs all CI jobs first, then builds and uploads both images, deploys through Systems Manager, and fails if the service health check fails.

The EC2 instance installs Docker, Compose, AWS CLI, and the Systems Manager agent at boot. It reads the runtime SecureString and waits for the first GitHub Actions deployment before starting the application. CI uploads the forecast artifact to both an immutable model-name/version S3 path and the release path. EC2 downloads and validates the release artifact, then mounts it read-only into the backend container. PostgreSQL and uploads use persistent Docker volumes. Database, API, and development ports are not public.

## HTTP and mobile endpoint

The planned EC2 stack serves HTTP on port 80. The security group includes port 443, but there is no TLS certificate or HTTPS listener yet. Use synthetic demo data only while HTTP is enabled. Do not enter real resident data or reuse production passwords. Public Flutter release builds require an HTTPS API endpoint and WSS WebSocket endpoint; HTTP access to the public EC2 IP is only suitable for the temporary synthetic hackathon demo.

## Logs and teardown

- Application, PostgreSQL, and Nginx container logs go to the `/jalos/<environment>` CloudWatch log group with 14-day retention.
- Stop EC2 when it is idle. The root EBS volume remains billable while stopped, and the public IPv4 address can change.
- Before destroying, back up PostgreSQL if needed. Remove S3 objects and versions before Terraform destroy; the bucket intentionally has `force_destroy = false`.
- From `terraform/`, run `terraform plan -destroy`, review it, then `terraform destroy` when ready.
- Check the billing dashboard after teardown for remaining resources or charges.
