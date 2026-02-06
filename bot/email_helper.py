"""
Email helper for reading verification codes from Outlook
Uses IMAP to fetch recent emails and extract verification codes
"""
import imaplib
import email
from email.header import decode_header
import re
import time
from datetime import datetime, timedelta

# Outlook IMAP settings
IMAP_SERVER = "outlook.office365.com"
IMAP_PORT = 993

def get_verification_code(
    email_address: str,
    password: str,
    sender_contains: str = None,
    subject_contains: str = None,
    max_age_minutes: int = 10,
    code_pattern: str = r'\b(\d{4,8})\b'
) -> str | None:
    """
    Fetch the most recent verification code from email

    Args:
        email_address: Outlook email address
        password: App password (not regular password - need to generate in Microsoft account)
        sender_contains: Filter emails by sender (e.g., "amazon", "workday")
        subject_contains: Filter emails by subject (e.g., "verification", "code")
        max_age_minutes: Only look at emails from the last N minutes
        code_pattern: Regex pattern to extract the code (default: 4-8 digit numbers)

    Returns:
        The verification code as a string, or None if not found
    """
    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email_address, password)
        mail.select("INBOX")

        # Search for recent emails
        # IMAP date format: DD-Mon-YYYY
        since_date = (datetime.now() - timedelta(minutes=max_age_minutes)).strftime("%d-%b-%Y")

        # Build search criteria
        search_criteria = f'(SINCE "{since_date}")'
        if sender_contains:
            search_criteria = f'(SINCE "{since_date}" FROM "{sender_contains}")'

        _, message_numbers = mail.search(None, search_criteria)

        if not message_numbers[0]:
            print(f"  [Email] No recent emails found")
            mail.logout()
            return None

        # Get the most recent emails (last 5)
        email_ids = message_numbers[0].split()[-5:]

        for email_id in reversed(email_ids):  # Start with most recent
            _, msg_data = mail.fetch(email_id, "(RFC822)")

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    # Check subject filter
                    if subject_contains and subject_contains.lower() not in subject.lower():
                        continue

                    # Decode sender
                    sender = msg.get("From", "")

                    # Check sender filter
                    if sender_contains and sender_contains.lower() not in sender.lower():
                        continue

                    print(f"  [Email] Found: {subject[:50]}... from {sender[:30]}")

                    # Get email body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors='ignore')
                                break
                            elif part.get_content_type() == "text/html":
                                body = part.get_payload(decode=True).decode(errors='ignore')
                    else:
                        body = msg.get_payload(decode=True).decode(errors='ignore')

                    # Search for verification code
                    # Common patterns: 6-digit codes, sometimes with dashes
                    patterns = [
                        r'(?:code|verification|verify|confirm)[^\d]*(\d{4,8})',  # "code: 123456"
                        r'(\d{6})',  # Plain 6-digit
                        r'(\d{4})',  # 4-digit
                        r'(\d{3}[- ]?\d{3})',  # 123-456 or 123 456
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, body, re.IGNORECASE)
                        if matches:
                            code = matches[0].replace("-", "").replace(" ", "")
                            print(f"  [Email] Found verification code: {code}")
                            mail.logout()
                            return code

        mail.logout()
        print(f"  [Email] No verification code found in recent emails")
        return None

    except Exception as e:
        print(f"  [Email] Error: {e}")
        return None


def wait_for_verification_code(
    email_address: str,
    password: str,
    sender_contains: str = None,
    subject_contains: str = None,
    timeout_seconds: int = 120,
    poll_interval: int = 10
) -> str | None:
    """
    Wait for a verification code to arrive, polling the inbox

    Args:
        email_address: Outlook email address
        password: App password
        sender_contains: Filter by sender
        subject_contains: Filter by subject
        timeout_seconds: How long to wait before giving up
        poll_interval: How often to check (seconds)

    Returns:
        The verification code, or None if timeout
    """
    print(f"  [Email] Waiting for verification code (timeout: {timeout_seconds}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        code = get_verification_code(
            email_address=email_address,
            password=password,
            sender_contains=sender_contains,
            subject_contains=subject_contains,
            max_age_minutes=5  # Only look at very recent emails
        )

        if code:
            return code

        print(f"  [Email] No code yet, waiting {poll_interval}s...")
        time.sleep(poll_interval)

    print(f"  [Email] Timeout - no verification code received")
    return None


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) >= 3:
        email_addr = sys.argv[1]
        password = sys.argv[2]
        sender = sys.argv[3] if len(sys.argv) > 3 else None

        code = get_verification_code(email_addr, password, sender_contains=sender)
        print(f"Code: {code}")
    else:
        print("Usage: python email_helper.py <email> <app_password> [sender_filter]")
