from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class MessageInfo:
    """Simple dataclass to encapsulate important message attributes"""
    id: str
    subject: str
    received_time: Optional[datetime] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    recipients: List[str] = field(default_factory=list)
    cc_recipients: List[str] = field(default_factory=list)
    bcc_recipients: List[str] = field(default_factory=list)
    body: str = ""
    is_read: bool = False
    has_attachments: bool = False
    importance: str = "normal"
    conversation_id: Optional[str] = None

    def __init__(self, message):
        """Initialize from a GraphController API message object"""
        self.id = message.id
        self.subject = message.subject or "(No subject)"
        self.received_time = message.received_date_time if hasattr(message, 'received_date_time') else None

        # Extract sender info
        self.sender_name = None
        self.sender_email = None
        if hasattr(message, 'from') and message.from_ and message.from_.email_address:
            self.sender_name = message.from_.email_address.name
            self.sender_email = message.from_.email_address.address

        # Extract recipients
        self.recipients = []
        self.cc_recipients = []
        self.bcc_recipients = []

        if message.to_recipients:
            for recipient in message.to_recipients:
                if recipient.email_address and recipient.email_address.address:
                    self.recipients.append(f"{recipient.email_address.name or ''} <{recipient.email_address.address}>")

        if hasattr(message, 'cc_recipients') and message.cc_recipients:
            for recipient in message.cc_recipients:
                if recipient.email_address and recipient.email_address.address:
                    self.cc_recipients.append(
                        f"{recipient.email_address.name or ''} <{recipient.email_address.address}>")

        if hasattr(message, 'bcc_recipients') and message.bcc_recipients:
            for recipient in message.bcc_recipients:
                if recipient.email_address and recipient.email_address.address:
                    self.bcc_recipients.append(
                        f"{recipient.email_address.name or ''} <{recipient.email_address.address}>")

        # Extract body
        self.body = ""
        if hasattr(message, 'body') and message.body:
            self.body = message.body.content or ""

        # Other properties
        self.is_read = message.is_read if hasattr(message, 'is_read') else False
        self.has_attachments = message.has_attachments if hasattr(message, 'has_attachments') else False

        # Extract importance
        self.importance = "normal"
        if hasattr(message, 'importance'):
            self.importance = str(message.importance).lower() if message.importance else "normal"

        self.conversation_id = message.conversation_id if hasattr(message, 'conversation_id') else None

    def to_dict(self):
        """Convert to dictionary for easy JSON serialization"""
        return {
            "id": self.id,
            "subject": self.subject,
            "received_time": self.received_time.isoformat() if self.received_time else None,
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email
            },
            "recipients": self.recipients,
            "cc_recipients": self.cc_recipients,
            "bcc_recipients": self.bcc_recipients,
            "body": self.body,
            "is_read": self.is_read,
            "has_attachments": self.has_attachments,
            "importance": self.importance,
            "conversation_id": self.conversation_id
        }

    def to_string(self):
        """Format the message as a readable string"""
        result = f"Subject: {self.subject}\n"
        result += f"From: {self.sender_name} <{self.sender_email}>\n" if self.sender_name and self.sender_email else ""
        result += f"Received: {self.received_time}\n" if self.received_time else ""
        result += f"Status: {'Read' if self.is_read else 'Unread'}\n"
        result += f"Importance: {self.importance.capitalize()}\n"

        if self.recipients:
            result += f"To: {', '.join(self.recipients)}\n"

        if self.cc_recipients:
            result += f"CC: {', '.join(self.cc_recipients)}\n"

        if self.has_attachments:
            result += f"Has Attachments: Yes\n"

        result += f"Body:\n"
        result += self.body

        return result