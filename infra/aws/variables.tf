variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "project" {
  type    = string
  default = "ios-sim-call-recorder"
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(var.public_subnet_ids) >= 2
    error_message = "Provide public subnets in at least two AZs."
  }
}

variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "Provide private subnets in at least two AZs."
  }
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN for the public API hostname."
}

variable "public_origin" {
  type        = string
  description = "Canonical HTTPS origin, e.g. https://api-staging.example.com"
  validation {
    condition     = startswith(var.public_origin, "https://") && !endswith(var.public_origin, "/")
    error_message = "public_origin must be an HTTPS origin without a trailing slash."
  }
}

variable "application_secret_arn" {
  type        = string
  description = "Secrets Manager JSON secret with BRIDGE_API_TOKEN_HASHES and, when enabled, Twilio and address-vault values."
}

variable "github_oidc_provider_arn" {
  type        = string
  description = "ARN of the GitHub Actions OIDC provider in this AWS account."
}

variable "github_repository" {
  type    = string
  default = "mojtaba-arvin/ios-sim-call-recorder"
}

variable "enable_live_twilio" {
  type        = bool
  default     = false
  description = "Keep false until legal review and live carrier/device validation pass."
}

variable "db_username" {
  type    = string
  default = "bridge_app"
}

variable "api_cpu" {
  type    = number
  default = 256
}

variable "api_memory" {
  type    = number
  default = 512
}

variable "worker_desired_count" {
  type    = number
  default = 1
}

variable "retention_desired_count" {
  type    = number
  default = 1
}

variable "tags" {
  type    = map(string)
  default = {}
}


variable "waf_rate_limit_per_ip" {
  type        = number
  default     = 2000
  description = "Maximum requests per source IP in a rolling five-minute WAF window before blocking."
  validation {
    condition     = var.waf_rate_limit_per_ip >= 100 && var.waf_rate_limit_per_ip <= 20000
    error_message = "waf_rate_limit_per_ip must be between 100 and 20000."
  }
}
