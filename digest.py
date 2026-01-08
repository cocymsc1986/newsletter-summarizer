#!/usr/bin/env python3
"""
Newsletter Digest Script
Reads unread emails from Gmail, summarizes them with Gemini AI,
and sends a daily digest via AWS SES.
"""

import os
import sys
import base64
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai


def load_gmail_credentials():
    """Load Gmail OAuth credentials from base64-encoded environment variable."""
    token_b64 = os.environ.get("GMAIL_TOKEN_B64")
    if not token_b64:
        raise ValueError("GMAIL_TOKEN_B64 environment variable not set")

    try:
        token_json = base64.b64decode(token_b64).decode("utf-8")
        token_data = json.loads(token_json)
        return Credentials.from_authorized_user_info(token_data)
    except Exception as e:
        raise ValueError(f"Failed to decode Gmail credentials: {e}")


def get_unread_emails(service, max_results=50):
    """Fetch unread emails from the inbox."""
    try:
        # Search for unread messages
        results = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=max_results
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            print("No unread messages found.")
            return []

        email_data = []
        for msg in messages:
            # Get full message details
            message = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()

            headers = message["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")

            # Extract email body
            body = extract_body(message["payload"])

            email_data.append({
                "id": msg["id"],
                "subject": subject,
                "sender": sender,
                "date": date,
                "body": body[:1000]  # Limit body to 1000 chars for summarization
            })

        return email_data

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def extract_body(payload):
    """Extract the email body from the message payload."""
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                if "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return body


def summarize_emails_with_gemini(emails, api_key):
    """Use Gemini API to summarize the emails."""
    if not emails:
        raise ValueError("No emails to summarize")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Build the prompt
    emails_text = "\n\n".join([
        f"Email {i+1}:\nFrom: {email['sender']}\nSubject: {email['subject']}\nDate: {email['date']}\nPreview: {email['body'][:500]}..."
        for i, email in enumerate(emails)
    ])

    prompt = f"""You are a helpful assistant that summarizes newsletter emails.
Below are {len(emails)} emails from the last 24 hours. Please provide a concise summary of the key information,
organized by topic or theme. Focus on actionable insights and important updates.

{emails_text}

Please provide a well-organized summary with clear sections and bullet points."""

    response = model.generate_content(prompt)
    return response.text


def mark_emails_as_read(service, email_ids):
    """Mark the processed emails as read."""
    if not email_ids:
        return

    try:
        service.users().messages().batchModify(
            userId="me",
            body={
                "ids": email_ids,
                "removeLabelIds": ["UNREAD"]
            }
        ).execute()
        print(f"Marked {len(email_ids)} emails as read.")
    except HttpError as error:
        print(f"Error marking emails as read: {error}")


def send_summary_email(summary, source_email, destination_email, aws_region="us-east-1"):
    """Send the summary via AWS SES."""
    ses_client = boto3.client("ses", region_name=aws_region)

    # Create email
    subject = f"Daily Newsletter Digest - {datetime.now().strftime('%Y-%m-%d')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = source_email
    msg["To"] = destination_email

    # Add HTML version
    html_body = f"""
    <html>
      <head></head>
      <body>
        <h2>{subject}</h2>
        <div style="white-space: pre-wrap; font-family: Arial, sans-serif;">
{summary}
        </div>
        <hr>
        <p style="color: #666; font-size: 12px;">
          This is an automated digest from your newsletter subscriptions.
        </p>
      </body>
    </html>
    """

    text_body = f"{subject}\n\n{summary}\n\n---\nThis is an automated digest from your newsletter subscriptions."

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        response = ses_client.send_raw_email(
            Source=source_email,
            Destinations=[destination_email],
            RawMessage={"Data": msg.as_string()}
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def main():
    """Main execution function."""
    print(f"Starting newsletter digest at {datetime.now()}")

    # Validate required environment variables
    required_vars = [
        "GEMINI_API_KEY",
        "GMAIL_TOKEN_B64",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "SOURCE_EMAIL",
        "DESTINATION_EMAIL"
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # Get configuration from environment
    gemini_api_key = os.environ["GEMINI_API_KEY"]
    source_email = os.environ["SOURCE_EMAIL"]
    destination_email = os.environ["DESTINATION_EMAIL"]
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    try:
        # Load Gmail credentials and build service
        print("Connecting to Gmail...")
        creds = load_gmail_credentials()
        gmail_service = build("gmail", "v1", credentials=creds)

        # Fetch unread emails
        print("Fetching unread emails...")
        emails = get_unread_emails(gmail_service)

        if not emails:
            print("No unread emails found. Nothing to do. Exiting successfully.")
            return

        print(f"Found {len(emails)} unread emails.")

        # Generate summary
        print("Generating summary with Gemini AI...")
        try:
            summary = summarize_emails_with_gemini(emails, gemini_api_key)
            print("Summary generated successfully.")
        except Exception as e:
            print(f"Failed to generate summary: {e}")
            print("Aborting. Emails will remain unread.")
            sys.exit(1)

        # Send summary email
        print("Sending digest email...")
        success = send_summary_email(summary, source_email, destination_email, aws_region)

        if not success:
            print("Failed to send digest email. Aborting. Emails will remain unread.")
            sys.exit(1)

        # Mark emails as read only after successful email send
        print("Marking emails as read...")
        email_ids = [email["id"] for email in emails]
        mark_emails_as_read(gmail_service, email_ids)
        print("Digest completed successfully!")

    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
