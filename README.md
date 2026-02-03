# Auto Email Sender

A simple SMTP-based auto email sender that can send one-off or scheduled emails.

## Setup

Set environment variables for your SMTP provider:

```bash
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USERNAME="you@example.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_SENDER="you@example.com"
export SMTP_USE_TLS="true"  # true for STARTTLS, false for SSL
```

## Usage

Send a single email:

```bash
python auto_email_sender.py \
  --to "recipient@example.com" \
  --subject "Hello" \
  --body "Welcome to Delta Shipping"
```

Send an email with attachments and HTML:

```bash
python auto_email_sender.py \
  --to "recipient@example.com" \
  --subject "Monthly Report" \
  --body @/path/to/body.txt \
  --html @/path/to/body.html \
  --attachment /path/to/report.pdf
```

Send every hour, 5 times:

```bash
python auto_email_sender.py \
  --to "recipient@example.com" \
  --subject "Reminder" \
  --body "Don't forget" \
  --interval-seconds 3600 \
  --count 5
```

Send forever (until stopped):

```bash
python auto_email_sender.py \
  --to "recipient@example.com" \
  --subject "Heartbeat" \
  --body "Still running" \
  --interval-seconds 300 \
  --count 0
```

## Notes

- Use `--body @/path/to/file.txt` to load the email body from a file.
- Use `--html @/path/to/file.html` to include an HTML version.
- Pass `--attachment` multiple times for multiple files.
