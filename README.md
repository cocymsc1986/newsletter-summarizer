# Newsletter Summarizer

An automated daily digest that reads unread emails from Gmail, summarizes them using Google's Gemini AI, and sends a consolidated summary via AWS SES.

## Features

- Fetches unread emails from Gmail inbox
- Generates intelligent summaries using Gemini AI
- Sends formatted digest emails via AWS SES
- Automatically marks processed emails as read
- Runs daily via GitHub Actions

## Prerequisites

- Python 3.12+
- Google Cloud account with Gmail API access
- Google Gemini API key
- AWS account with SES access
- Terraform (for infrastructure setup)
- GitHub account (for automated runs)

## Setup Guide

### 1. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download the credentials and save as `credentials.json` in the project root

### 2. Generate Gmail OAuth Token

Run the auth setup script locally to generate your OAuth token:

```bash
pip install google-auth-oauthlib
python auth_setup.py
```

This will:
- Open your browser for Google OAuth login
- Create a `token.json` file with your credentials

### 3. Prepare GitHub Secret

Convert the token to base64 for GitHub Secrets:

```bash
# macOS
cat token.json | base64 | pbcopy

# Linux
base64 token.json

# Windows (PowerShell)
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content token.json -Raw)))
```

Save this base64 string - you'll add it to GitHub Secrets as `GMAIL_TOKEN_B64`.

### 4. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Save this key - you'll add it to GitHub Secrets as `GEMINI_API_KEY`

### 5. AWS Infrastructure Setup

Configure Terraform variables:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your email addresses
```

Deploy the infrastructure:

```bash
terraform init
terraform plan
terraform apply
```

After successful deployment, note the outputs:
- `aws_access_key_id`
- `aws_secret_access_key` (get with: `terraform output -raw aws_secret_access_key`)
- `sender_email`
- `destination_email`

**Important:** If your AWS SES account is in sandbox mode, you must verify both the sender and recipient email addresses. Check your email for verification links from AWS.

### 6. Configure GitHub Secrets

Go to your GitHub repository > Settings > Secrets and variables > Actions

Add the following secrets:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `GEMINI_API_KEY` | Your Gemini API key | Google AI Studio |
| `GMAIL_TOKEN_B64` | Base64-encoded token.json | Step 3 |
| `AWS_ACCESS_KEY_ID` | AWS access key | Terraform output |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Terraform output |
| `AWS_REGION` | AWS region | Terraform (default: us-east-1) |
| `SOURCE_EMAIL` | Email that sends digest | Terraform output |
| `DESTINATION_EMAIL` | Email that receives digest | Terraform output |

### 7. Test the Workflow

Trigger a manual run:

1. Go to Actions tab in GitHub
2. Select "Daily Newsletter Digest"
3. Click "Run workflow"

## Local Development

Install dependencies:

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

Set environment variables:

```bash
export GEMINI_API_KEY="your-key"
export GMAIL_TOKEN_B64="your-base64-token"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"
export SOURCE_EMAIL="sender@example.com"
export DESTINATION_EMAIL="receiver@example.com"
```

Run the script:

```bash
python digest.py
```

## Scheduled Execution

The GitHub Action runs automatically every day at 8:00 AM UTC (configurable in `.github/workflows/run.yaml`).

To change the schedule, modify the cron expression:
```yaml
schedule:
  - cron: "0 8 * * *"  # minute hour day month weekday
```

## Troubleshooting

### Gmail API Errors

- Ensure OAuth token is valid and base64-encoded correctly
- Check that Gmail API is enabled in Google Cloud Console
- Verify scopes include `gmail.readonly` and `gmail.modify`

### AWS SES Errors

- Verify both sender and recipient emails in SES console
- If in sandbox mode, both emails must be verified
- Request production access if sending to unverified emails
- Check IAM permissions for the GitHub Actions user

### Gemini API Errors

- Verify API key is valid
- Check quota limits in Google AI Studio
- Ensure the model name is correct (currently using `gemini-1.5-flash`)

## Project Structure

```
.
├── digest.py                # Main script
├── auth_setup.py            # OAuth token generator (local use)
├── requirements.txt         # Python dependencies
├── terraform/
│   ├── main.tf              # AWS infrastructure
│   └── terraform.tfvars.example
├── .github/workflows/
│   └── run.yaml             # GitHub Actions workflow
└── README.md
```

## Security Notes

- Never commit `credentials.json`, `token.json`, or `terraform.tfvars`
- These files are gitignored for security
- Store all secrets in GitHub Secrets or environment variables
- Regularly rotate AWS access keys
- Review and limit OAuth scopes to minimum required

## License

MIT
