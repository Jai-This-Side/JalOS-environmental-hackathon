variable "aws_region" {
  description = "Region for the single-instance hackathon deployment."
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "Choose after checking current account eligibility and regional pricing."
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Optional existing EC2 key pair name."
  type        = string
  default     = null
  nullable    = true
}

variable "allowed_ssh_cidr" {
  description = "Your current public IPv4 address with /32, for SSH only."
  type        = string
  validation {
    condition     = can(cidrhost(var.allowed_ssh_cidr, 0)) && can(cidrnetmask(var.allowed_ssh_cidr)) && endswith(var.allowed_ssh_cidr, "/32")
    error_message = "allowed_ssh_cidr must be a valid IPv4 /32 address."
  }
}

variable "bucket_name" {
  description = "Globally unique private bucket name for JalOS artifacts."
  type        = string
}

variable "environment" {
  type    = string
  default = "hackathon"
}

variable "github_repository" {
  description = "GitHub repository allowed to deploy, in owner/name form."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be the exact owner/name of the repository."
  }
}

variable "github_branch" {
  description = "Branch allowed to use the GitHub OIDC deployment role."
  type        = string
  default     = "main"
}
