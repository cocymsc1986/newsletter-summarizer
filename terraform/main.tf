variable "aws_region" {
  description = "AWS region for SES"
  type        = string
  default     = "us-east-1"
}

variable "sender_email" {
  description = "Email address that will send the digest (must be verified in SES)"
  type        = string
}

variable "destination_email" {
  description = "Email address that will receive the digest (must be verified in SES if in sandbox)"
  type        = string
}

provider "aws" {
  region = var.aws_region
}

# The identity sending the summaries
resource "aws_ses_email_identity" "sender" {
  email = var.sender_email
}

# The recipient identity (Required if in SES Sandbox)
resource "aws_ses_email_identity" "recipient" {
  email = var.destination_email
}

# IAM User for the GitHub Action to send mail
resource "aws_iam_user" "mailer" {
  name = "github-action-mailer"
}

resource "aws_iam_user_policy" "ses_send" {
  name = "SES_Send_Only"
  user = aws_iam_user.mailer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ses:SendRawEmail", "ses:SendEmail"]
      Resource = "*"
    }]
  })
}

# Generate credentials to be stored in GitHub Secrets
resource "aws_iam_access_key" "mailer_key" {
  user = aws_iam_user.mailer.name
}

output "aws_access_key_id" {
  description = "AWS Access Key ID for GitHub Actions (add to GitHub Secrets as AWS_ACCESS_KEY_ID)"
  value       = aws_iam_access_key.mailer_key.id
}

output "aws_secret_access_key" {
  description = "AWS Secret Access Key for GitHub Actions (add to GitHub Secrets as AWS_SECRET_ACCESS_KEY)"
  value       = aws_iam_access_key.mailer_key.secret
  sensitive   = true
}

output "sender_email" {
  description = "Email address verified for sending (add to GitHub Secrets as SOURCE_EMAIL)"
  value       = aws_ses_email_identity.sender.email
}

output "destination_email" {
  description = "Email address verified for receiving (add to GitHub Secrets as DESTINATION_EMAIL)"
  value       = aws_ses_email_identity.recipient.email
}
