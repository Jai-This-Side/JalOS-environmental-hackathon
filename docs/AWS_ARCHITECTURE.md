# JalOS AWS architecture

The hackathon deployment uses one Ubuntu EC2 instance with Docker Compose. Terraform provisions the instance, a restricted security group, an EC2 instance role, a private encrypted S3 bucket, a CloudWatch log group, an SSM SecureString runtime environment, and a GitHub OIDC deploy role scoped to one repository and branch.

```text
GitHub Actions
  └─ OIDC role → private S3 release objects → Systems Manager Run Command
                                              └─ EC2 Docker Compose
                                                   ├─ Nginx admin web + API/WebSocket proxy
                                                   ├─ FastAPI + simulator + ML artifact
                                                   └─ PostgreSQL on private Docker network
```

GitHub Actions builds the two images after backend, Flutter, React, and Terraform checks pass. It uploads the images and Compose file to S3, stores the forecast model under its model-name/version key and with the release, asks Systems Manager to deploy the commit on EC2, and fails if the application health check fails. The workflow uses short-lived GitHub OIDC credentials; it has no long-lived AWS access keys.

The EC2 role reads only the release and model prefixes and one runtime SSM parameter, writes application logs to the JalOS CloudWatch group, and uses the Systems Manager managed-instance role. GitHub's deploy role can write releases and versioned models and send commands to the one JalOS instance. The database and backend ports are not opened in the security group. S3 is for models, reports, datasets, and release files, not operational telemetry.

The AWS security group allows HTTP 80, HTTPS 443, and SSH 22 from the configured IPv4 `/32`. The production Compose file currently serves HTTP on port 80; port 443 has no TLS listener until a domain and certificate are configured. Use only synthetic demo data while HTTP is enabled. The Flutter production API and WebSocket URLs also need an HTTPS/WSS endpoint before public release.

Terraform generates demo and database secrets, stores the runtime environment as an SSM SecureString, and marks password outputs sensitive. Terraform's local state still contains secret material; keep it private, back it up securely, and never commit it. The AWS-managed SSM KMS key is used to avoid provisioning a separate customer-managed key. The GitHub repository and branch must be set before creating the OIDC trust.

For a larger production system, use the Flutter app over HTTPS, a load balancer, ECS/Fargate, RDS PostgreSQL, private S3, and CloudWatch. That future architecture is documentation only.
