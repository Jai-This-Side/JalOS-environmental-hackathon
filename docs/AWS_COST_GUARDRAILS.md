# AWS cost guardrails

The scaffold intentionally uses one EC2 instance and does not create NAT Gateway, EKS, ECS/Fargate, load balancer, RDS, cache, warehouse, search service, or GPU resources. AWS charges can still apply for EC2 runtime, EBS storage, public IPv4, S3 storage/requests, CloudWatch logs, and data transfer. Eligibility and pricing vary by account, region, and date; do not assume the deployment is free.

Before applying Terraform, review the current AWS pricing pages and billing dashboard for the selected region and instance type. Set a billing alert in the account. Stop the EC2 instance when idle; stopping compute does not necessarily stop storage or public-IP charges. Delete S3 objects and object versions before destroying the bucket. Use `terraform plan` for both apply and destroy, and confirm no unplanned resources remain in the account afterward.

The default instance type in the example is a small prototype default only. Choose a type that is eligible and suitable for the specific account after checking current AWS terms. This implementation used the configured non-root `JalOS` CLI profile for identity and read-only Terraform planning. It did not apply Terraform or create AWS resources.
