"""Email reader module supporting Gmail API (OAuth2), IMAP fallback, and Mock reader."""

import os
import base64
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from config import Config
from modules.base import BaseModule
from utils.models import EmailMessage, EmailAttachment
from utils.text_cleaner import clean_html_to_text, decode_mime_words, parse_email_date, sanitize_text
from utils.logger import print_status, print_warning, print_error, print_success


class GmailAPIReader:
    """Gmail API reader using OAuth2 (credentials.json / token.json)."""

    def __init__(self, credentials_path: Path = Config.GMAIL_CREDENTIALS_PATH, token_path: Path = Config.GMAIL_TOKEN_PATH):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate using stored token.json or credentials.json via InstalledAppFlow."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as e:
            print_error(f"Google client libraries not found: {e}")
            return False

        creds = None
        # Check if token.json already exists
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), Config.GMAIL_SCOPES)
            except Exception as e:
                print_warning(f"Failed to load existing token: {e}. Will re-authenticate.")
                creds = None

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print_status("Refreshing expired Gmail OAuth token...")
                    creds.refresh(Request())
                except Exception as e:
                    print_warning(f"Could not refresh token: {e}. Re-authenticating...")
                    creds = None

            if not creds:
                if not self.credentials_path.exists():
                    return False
                try:
                    print_status(f"Authenticating Gmail via OAuth client secret ({self.credentials_path.name})...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), Config.GMAIL_SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print_error(f"OAuth authentication flow failed: {e}")
                    return False

            # Save the credentials for the next run
            try:
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
                print_success(f"Saved OAuth session to {self.token_path.name}")
            except Exception as e:
                print_warning(f"Could not save token file: {e}")

        try:
            self.service = build("gmail", "v1", credentials=creds)
            return True
        except Exception as e:
            print_error(f"Failed to build Gmail service: {e}")
            return False

    def fetch_unread_emails(self, query: str = "is:unread", limit: int = 5) -> List[EmailMessage]:
        """Fetch unread emails from Gmail API."""
        if not self.service:
            if not self.authenticate():
                raise ConnectionError("Gmail API service is not authenticated.")

        results = self.service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
        messages_meta = results.get("messages", [])

        if not messages_meta:
            return []

        emails: List[EmailMessage] = []
        for meta in messages_meta:
            msg_id = meta["id"]
            try:
                full_msg = self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
                email_obj = self._parse_gmail_message(full_msg)
                if email_obj:
                    emails.append(email_obj)
            except Exception as ex:
                print_warning(f"Failed to fetch Gmail message {msg_id}: {ex}")

        return emails

    def mark_as_read(self, message_id: str) -> bool:
        """Remove UNREAD label from a message."""
        if not self.service:
            return False
        try:
            self.service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except Exception as e:
            print_warning(f"Could not mark Gmail message {message_id} as read: {e}")
            return False

    def _parse_gmail_message(self, msg_data: Dict[str, Any]) -> Optional[EmailMessage]:
        """Parse raw Gmail API message dict into EmailMessage model."""
        msg_id = msg_data.get("id", "")
        thread_id = msg_data.get("threadId", "")
        labels = msg_data.get("labelIds", [])
        snippet = msg_data.get("snippet", "")
        payload = msg_data.get("payload", {})
        headers_list = payload.get("headers", [])
        
        headers = {h["name"].lower(): h["value"] for h in headers_list if "name" in h and "value" in h}
        
        sender = decode_mime_words(headers.get("from", "Unknown Sender"))
        recipient = decode_mime_words(headers.get("to", ""))
        subject = decode_mime_words(headers.get("subject", "(No Subject)"))
        date_raw = headers.get("date")
        parsed_date = parse_email_date(date_raw) if date_raw else None

        body_text, body_html, attachments = self._extract_payload_parts(payload)

        # Fallback if plain text was empty
        if not body_text and body_html:
            body_text = clean_html_to_text(body_html)
        elif not body_text and snippet:
            body_text = snippet

        return EmailMessage(
            id=msg_id,
            thread_id=thread_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            date=parsed_date,
            snippet=snippet,
            body_text=sanitize_text(body_text),
            body_html=body_html,
            is_unread="UNREAD" in labels,
            labels=labels,
            attachments=attachments,
            source="gmail",
        )

    def _extract_payload_parts(self, payload: Dict[str, Any]) -> Tuple[str, str, List[EmailAttachment]]:
        """Extract text/plain, text/html, and attachments recursively from Gmail payload."""
        text_parts = []
        html_parts = []
        attachments = []

        def _walk_parts(part: Dict[str, Any]):
            mime_type = part.get("mimeType", "")
            filename = part.get("filename", "")
            body = part.get("body", {})
            data = body.get("data")
            attachment_id = body.get("attachmentId")
            size = body.get("size")

            if filename and (attachment_id or data):
                attachments.append(EmailAttachment(
                    filename=filename,
                    content_type=mime_type,
                    size_bytes=size,
                ))

            if data:
                try:
                    decoded_bytes = base64.urlsafe_b64decode(data.encode("utf-8"))
                    text_content = decoded_bytes.decode("utf-8", errors="replace")
                    if mime_type == "text/plain":
                        text_parts.append(text_content)
                    elif mime_type == "text/html":
                        html_parts.append(text_content)
                except Exception:
                    pass

            for subpart in part.get("parts", []):
                _walk_parts(subpart)

        _walk_parts(payload)
        return "\n".join(text_parts), "\n".join(html_parts), attachments


class IMAPEmailReader:
    """IMAP email reader with SSL support and MIME parser."""

    def __init__(
        self,
        username: Optional[str] = Config.GMAIL_USER,
        password: Optional[str] = Config.GMAIL_APP_PASSWORD,
        server: str = Config.IMAP_SERVER,
        port: int = Config.IMAP_PORT,
        folder: str = Config.IMAP_FOLDER,
    ):
        self.username = username
        self.password = password
        self.server = server
        self.port = port
        self.folder = folder
        self.client: Optional[imaplib.IMAP4_SSL] = None

    def authenticate(self) -> bool:
        """Connect and log in to the IMAP server."""
        if not self.username or not self.password:
            return False
        try:
            print_status(f"Connecting to IMAP server ({self.server}:{self.port}) as {self.username}...")
            self.client = imaplib.IMAP4_SSL(self.server, self.port)
            self.client.login(self.username, self.password)
            return True
        except Exception as e:
            print_error(f"IMAP Authentication failed: {e}")
            self.client = None
            return False

    def fetch_unread_emails(self, query: str = "UNSEEN", limit: int = 5) -> List[EmailMessage]:
        """Fetch unread emails using IMAP."""
        if not self.client:
            if not self.authenticate():
                raise ConnectionError("IMAP client could not be authenticated. Check GMAIL_USER and GMAIL_APP_PASSWORD.")

        assert self.client is not None
        status, _ = self.client.select(self.folder, readonly=False)
        if status != "OK":
            raise ConnectionError(f"Could not open IMAP folder: {self.folder}")

        # Search for unseen messages
        search_criteria = "UNSEEN" if query.lower() in ("unseen", "is:unread") else query
        status, data = self.client.search(None, search_criteria)
        if status != "OK" or not data or not data[0]:
            return []

        message_ids = data[0].split()
        # Get the latest 'limit' messages
        recent_ids = message_ids[-limit:]
        recent_ids.reverse()  # Newest first

        emails: List[EmailMessage] = []
        for msg_num in recent_ids:
            try:
                res, msg_data = self.client.fetch(msg_num, "(RFC822)")
                if res != "OK" or not msg_data:
                    continue

                raw_email_bytes = None
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        raw_email_bytes = response_part[1]
                        break

                if raw_email_bytes:
                    email_msg = self._parse_mime_bytes(str(msg_num.decode()), raw_email_bytes)
                    if email_msg:
                        emails.append(email_msg)
            except Exception as e:
                print_warning(f"Failed to fetch IMAP message #{msg_num}: {e}")

        return emails

    def mark_as_read(self, message_id: str) -> bool:
        """Mark email as seen in IMAP."""
        if not self.client:
            return False
        try:
            self.client.store(message_id, "+FLAGS", "\\Seen")
            return True
        except Exception as e:
            print_warning(f"Could not mark IMAP email {message_id} as read: {e}")
            return False

    def close(self):
        """Safely close and logout from IMAP session."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            try:
                self.client.logout()
            except Exception:
                pass
            self.client = None

    def _parse_mime_bytes(self, msg_id: str, raw_bytes: bytes) -> Optional[EmailMessage]:
        """Parse raw RFC 822 email bytes into EmailMessage."""
        msg = email.message_from_bytes(raw_bytes)

        subject = decode_mime_words(msg.get("Subject", "(No Subject)"))
        sender = decode_mime_words(msg.get("From", "Unknown Sender"))
        recipient = decode_mime_words(msg.get("To", ""))
        date_str = msg.get("Date")
        parsed_date = parse_email_date(date_str) if date_str else None

        body_text_parts = []
        body_html_parts = []
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()

                if filename or "attachment" in content_disposition:
                    decoded_filename = decode_mime_words(filename) if filename else "unnamed_attachment"
                    attachments.append(EmailAttachment(
                        filename=decoded_filename,
                        content_type=content_type,
                    ))

                if "attachment" not in content_disposition:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            text_str = payload.decode(charset, errors="replace")
                        except (LookupError, UnicodeDecodeError):
                            text_str = payload.decode("latin1", errors="replace")

                        if content_type == "text/plain":
                            body_text_parts.append(text_str)
                        elif content_type == "text/html":
                            body_html_parts.append(text_str)
        else:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    text_str = payload.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    text_str = payload.decode("latin1", errors="replace")

                if msg.get_content_type() == "text/html":
                    body_html_parts.append(text_str)
                else:
                    body_text_parts.append(text_str)

        body_text = "\n".join(body_text_parts).strip()
        body_html = "\n".join(body_html_parts).strip() if body_html_parts else None

        if not body_text and body_html:
            body_text = clean_html_to_text(body_html)

        snippet = body_text[:150].replace("\n", " ").strip() if body_text else ""

        return EmailMessage(
            id=msg_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            date=parsed_date,
            snippet=snippet,
            body_text=sanitize_text(body_text),
            body_html=body_html,
            is_unread=True,
            attachments=attachments,
            source="imap",
        )


class MockEmailReader:
    """Mock email generator for testing without credentials."""

    def __init__(self):
        self.mock_db = self._generate_sample_emails()

    def fetch_unread_emails(self, query: str = "is:unread", limit: int = 5) -> List[EmailMessage]:
        """Return simulated realistic unread emails."""
        unreads = [em for em in self.mock_db if em.is_unread]
        return unreads[:limit]

    def mark_as_read(self, message_id: str) -> bool:
        """Mark mock email as read."""
        for em in self.mock_db:
            if em.id == message_id:
                em.is_unread = False
                return True
        return False

    @staticmethod
    def _generate_sample_emails() -> List[EmailMessage]:
        return [
            EmailMessage(
                id="mock-101",
                sender="Pepper Potts <pepper.potts@starkindustries.com>",
                recipient="Tony Stark <tony@starkindustries.com>",
                subject="URGENT: Board Meeting Rescheduled & Q3 Financial Review",
                date=datetime.now(),
                snippet="Tony, the board has moved tomorrow's review to 9:00 AM sharp...",
                body_text="Tony,\n\nThe board of directors has moved tomorrow's quarterly review to 9:00 AM EST in the executive conference room. Please review the attached clean energy pipeline slides and sign off on the Tokyo R&D budget before midnight tonight.\n\nAlso, Rhodey mentioned the Department of Defense contract needs your personal authorization by Friday.\n\nBest,\nPepper",
                is_unread=True,
                attachments=[EmailAttachment(filename="Q3_Financial_Review.pdf", content_type="application/pdf", size_bytes=1048576)],
                source="mock",
            ),
            EmailMessage(
                id="mock-102",
                sender="Col. James Rhodes <rhodey@us.af.mil>",
                recipient="Tony Stark <tony@starkindustries.com>",
                subject="Avionics Telemetry Anomaly in Mark VII",
                date=datetime.now(),
                snippet="Tony, we detected a fluctuating power drop on the starboard repulsor...",
                body_text="Tony,\n\nDuring routine diagnostics this morning, our telemetry sensors logged a 14% transient voltage drop across the starboard repulsor capacitor banks during supersonic transition.\n\nCan JARVIS run a complete micro-diagnostic on the propulsion firmware before our joint flight test on Thursday 14:00?\n\n- Rhodey",
                is_unread=True,
                source="mock",
            ),
            EmailMessage(
                id="mock-103",
                sender="Peter Parker <peter.parker@midtownhigh.edu>",
                recipient="Tony Stark <tony@starkindustries.com>",
                subject="Web-Shooter Fluid Polymer Formula Update",
                date=datetime.now(),
                snippet="Mr. Stark! I tested the new tensile tensile copolymer mix...",
                body_text="Mr. Stark,\n\nI tested the modified copolymer formula you suggested! The tensile strength increased by 300% and it dissolves cleanly after 2 hours with zero residue. Let me know if I can drop by the lab this weekend to recalibrate the pressure nozzles.\n\nThanks!\nPeter",
                is_unread=True,
                source="mock",
            ),
            EmailMessage(
                id="mock-104",
                sender="Security Alert <no-reply@aws.amazon.com>",
                recipient="tony@starkindustries.com",
                subject="AWS Security Notification: IAM Role Policy Modification",
                date=datetime.now(),
                snippet="A critical IAM policy was updated in region us-east-1...",
                body_text="Notification: The IAM policy 'Stark-ArcReactor-Admin' was updated in region us-east-1 at 04:15 UTC. If this change was unauthorized, immediately revoke the associated access keys and review CloudTrail logs.",
                is_unread=True,
                source="mock",
            ),
        ]


class EmailReader(BaseModule):
    """Unified email reader module with intelligent backend selection and fallbacks."""

    def __init__(self, backend: str = "auto"):
        super().__init__(name="EmailReader", description="Fetches and processes unread emails via Gmail API or IMAP")
        self.backend = backend.lower()
        self.gmail_reader = GmailAPIReader()
        self.imap_reader = IMAPEmailReader()
        self.mock_reader = MockEmailReader()
        self.active_backend: Optional[str] = None

    def initialize(self) -> bool:
        """Initialize the appropriate email backend."""
        if self.backend == "mock":
            self.active_backend = "mock"
            self.is_initialized = True
            print_status("Initialized EmailReader in MOCK simulation mode.")
            return True

        if self.backend == "gmail":
            if self.gmail_reader.authenticate():
                self.active_backend = "gmail"
                self.is_initialized = True
                print_success("Connected to Gmail API backend via OAuth.")
                return True
            print_error("Failed to initialize requested Gmail API backend.")
            return False

        if self.backend == "imap":
            if self.imap_reader.authenticate():
                self.active_backend = "imap"
                self.is_initialized = True
                print_success("Connected to IMAP backend.")
                return True
            print_error("Failed to initialize requested IMAP backend.")
            return False

        # AUTO fallback resolution:
        # 1. Try Gmail API if credentials or token exist
        if Config.has_gmail_credentials():
            print_status("Found Gmail OAuth credentials. Attempting Gmail API connection...")
            if self.gmail_reader.authenticate():
                self.active_backend = "gmail"
                self.is_initialized = True
                print_success("Connected to Gmail API successfully.")
                return True
            print_warning("Gmail API authentication failed. Falling back to IMAP...")

        # 2. Try IMAP if username and app password exist
        if Config.has_imap_credentials():
            print_status("Found IMAP credentials in environment. Attempting IMAP connection...")
            if self.imap_reader.authenticate():
                self.active_backend = "imap"
                self.is_initialized = True
                print_success("Connected to IMAP successfully.")
                return True
            print_warning("IMAP connection failed.")

        # 3. Informative notice and fallback to mock if requested or no credentials configured
        print_warning("No active Gmail API (credentials.json) or IMAP (GMAIL_USER/GMAIL_APP_PASSWORD) credentials detected.")
        print_status("Defaulting to simulated Mock Email Reader for demonstration...")
        self.active_backend = "mock"
        self.is_initialized = True
        return True

    def execute(self, query: str = "is:unread", limit: int = 5) -> List[EmailMessage]:
        """Fetch unread emails using active backend."""
        if not self.is_initialized:
            if not self.initialize():
                return []

        if self.active_backend == "gmail":
            return self.gmail_reader.fetch_unread_emails(query=query, limit=limit)
        elif self.active_backend == "imap":
            return self.imap_reader.fetch_unread_emails(query=query, limit=limit)
        elif self.active_backend == "mock":
            return self.mock_reader.fetch_unread_emails(query=query, limit=limit)
        else:
            print_error(f"Unknown email backend: {self.active_backend}")
            return []

    def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read in the active backend."""
        if self.active_backend == "gmail":
            return self.gmail_reader.mark_as_read(message_id)
        elif self.active_backend == "imap":
            return self.imap_reader.mark_as_read(message_id)
        elif self.active_backend == "mock":
            return self.mock_reader.mark_as_read(message_id)
        return False

    def shutdown(self) -> None:
        """Shutdown active connections."""
        if self.imap_reader:
            self.imap_reader.close()
        super().shutdown()
