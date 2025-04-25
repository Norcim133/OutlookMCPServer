from dataclasses import dataclass
from typing import Optional, List, Union
from datetime import datetime

@dataclass
class MailQuery:
    # Search filters
    subject: Optional[str] = None
    body: Optional[str] = None
    from_email: Optional[str] = None  # sender
    to_email: Optional[Union[str, List[str]]] = None
    cc_email: Optional[Union[str, List[str]]] = None
    bcc_email: Optional[Union[str, List[str]]] = None
    participants: Optional[str] = None  # Searches from, to, cc, and bcc
    recipients: Optional[str] = None  # Searches to, cc, and bcc

    # Date filters
    received_after: Optional[datetime] = None
    received_before: Optional[datetime] = None
    sent_after: Optional[datetime] = None
    sent_before: Optional[datetime] = None

    # Attachment filters
    has_attachments: Optional[bool] = None
    attachment_name: Optional[str] = None

    # Other properties
    importance: Optional[str] = None  # "low", "medium", "high"
    is_read: Optional[bool] = None
    size_min: Optional[int] = None  # in bytes
    size_max: Optional[int] = None  # in bytes
    kind: Optional[str] = None  # "email", "meetings", etc.

    # Query configuration
    folder_id: str = "inbox"
    count: int = 50
    include_nested_folders: bool = False
    orderby: List[str] = None  # e.g. ["receivedDateTime DESC"]
    select: List[str] = None  # properties to return

    def __post_init__(self):
        if self.orderby is None:
            self.orderby = ["receivedDateTime DESC"]
        if self.select is None:
            self.select = ["from", "isRead", "receivedDateTime", "subject", "id"]

    def build_search_query(self) -> Optional[str]:
        """Build a $search query string based on the properties set in this query."""
        search_terms = []

        # Map dataclass fields to their corresponding search properties
        field_mappings = {
            'subject': 'subject',
            'body': 'body',
            'from_email': 'from',
            'to_email': 'to',
            'cc_email': 'cc',
            'bcc_email': 'bcc',
            'participants': 'participants',
            'recipients': 'recipients',
            'attachment_name': 'attachment',
            'has_attachments': 'hasAttachments',
            'importance': 'importance',
            'kind': 'kind',
        }

        # Add simple string fields
        for field_name, search_property in field_mappings.items():
            value = getattr(self, field_name)
            if value is not None:
                if field_name == 'has_attachments':
                    search_terms.append(f"{search_property}:{str(value).lower()}")
                elif isinstance(value, str):
                    search_terms.append(f"{search_property}:{value}")
                elif isinstance(value, list):
                    # Handle list of recipients with OR
                    or_terms = [f"{search_property}:{item}" for item in value]
                    search_terms.append(f"({' OR '.join(or_terms)})")

        # Add is_read to search if it's set
        if self.is_read is not None:
            search_terms.append(f"isRead:{str(self.is_read).lower()}")

        # Handle date ranges
        if self.received_after or self.received_before:
            if self.received_after and self.received_before:
                date_from = self.received_after.strftime("%m/%d/%Y")
                date_to = self.received_before.strftime("%m/%d/%Y")
                search_terms.append(f"received:{date_from}..{date_to}")
            elif self.received_after:
                date_from = self.received_after.strftime("%m/%d/%Y")
                search_terms.append(f"received>={date_from}")
            elif self.received_before:
                date_to = self.received_before.strftime("%m/%d/%Y")
                search_terms.append(f"received<={date_to}")

        if self.sent_after or self.sent_before:
            if self.sent_after and self.sent_before:
                date_from = self.sent_after.strftime("%m/%d/%Y")
                date_to = self.sent_before.strftime("%m/%d/%Y")
                search_terms.append(f"sent:{date_from}..{date_to}")
            elif self.sent_after:
                date_from = self.sent_after.strftime("%m/%d/%Y")
                search_terms.append(f"sent>={date_from}")
            elif self.sent_before:
                date_to = self.sent_before.strftime("%m/%d/%Y")
                search_terms.append(f"sent<={date_to}")

        # Handle size range
        if self.size_min or self.size_max:
            if self.size_min and self.size_max:
                search_terms.append(f"size:{self.size_min}..{self.size_max}")
            elif self.size_min:
                search_terms.append(f"size>={self.size_min}")
            elif self.size_max:
                search_terms.append(f"size<={self.size_max}")

        # Combine all search terms with AND
        if search_terms:
            return " AND ".join(search_terms)

        return None

    def is_full_text_query(self) -> bool:
        """Returns True if this query should use $search (e.g. subject/body search only)"""
        return (
                self.subject or self.body or self.from_email or self.to_email or
                self.cc_email or self.bcc_email or self.participants or self.recipients or
                self.attachment_name
        ) is not None and not (
                self.is_read or self.received_after or self.sent_after or self.importance
        )