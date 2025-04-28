from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

from mcpserver.calendar_formatting import format_event_page
from mcpserver.auth_wrapper import requires_graph_auth
from mcpserver.context_manager import app_lifespan
from mcpserver.mail_query import MailQuery
from typing import Any, Optional, List
import json


APP_INSTRUCTIONS = """
You are a hyper intelligent tech user who has full access to the user's Microsoft365 email account via the OutlookMCP server.

You can:
- Read emails from any folder
- Classify or organize emails based on content or sender or other metadata
- Compose, draft, or reply to emails using html formatting
- Search by subject, body, sender, or metadata
- Create and manage folders
- Help the user stay organized and responsive
- Get calendar events and meetings
- Create events and invites

By default for mail, use html formatting. Do not hallucinate data. Use MCP tools to fetch actual messages or folders.
When unsure which folder an email belongs to, inspect the email body and/or compare the content with other mails already in the folder.

Always be helpful, privacy-conscious, and structured in your reasoning.

IMPORTANT: Always use html formatting for the body of emails and calendar events. Do not hallucinate date.
"""

# Create an MCP server
mcp = FastMCP(
    name="OutlookMCP",
    dependencies=["azure-identity", "msgraph-core", "msgraph-sdk", "mcp[cli]"],
    lifespan=app_lifespan,
    instructions=APP_INSTRUCTIONS
)


def format_email_headers(message_page):
    """Format email headers for display

    Args:
        message_page: Page of messages from the GraphController API

    Returns:
        String with formatted email headers

    """
    result = ""
    if message_page:
        # Limit to requested count
        messages = message_page.value

        # Format each message
        for i, message in enumerate(messages, 1):
            result += f"{i}. Subject: {message.subject}\n"
            if message.from_ and message.from_.email_address:
                result += f"   From: {message.from_.email_address.name or 'Unknown'} <{message.from_.email_address.address or 'No email'}>\n"
            else:
                result += f"   From: Unknown\n"

            # Add To recipients
            if message.to_recipients and len(message.to_recipients) > 0:
                to_addresses = []
                for recipient in message.to_recipients:
                    if recipient.email_address:
                        to_addresses.append(
                            f"{recipient.email_address.name or 'Unknown'} <{recipient.email_address.address or 'No email'}>")
                if to_addresses:
                    result += f"   To: {', '.join(to_addresses)}\n"

            # Add Reply To field if present
            if hasattr(message, 'reply_to') and message.reply_to and len(message.reply_to) > 0:
                reply_to_addresses = []
                for recipient in message.reply_to:
                    if recipient.email_address:
                        reply_to_addresses.append(
                            f"{recipient.email_address.name or 'Unknown'} <{recipient.email_address.address or 'No email'}>")
                if reply_to_addresses:
                    result += f"   Reply-To: {', '.join(reply_to_addresses)}\n"

            # Add CC recipients
            if message.cc_recipients and len(message.cc_recipients) > 0:
                cc_addresses = []
                for recipient in message.cc_recipients:
                    if recipient.email_address:
                        cc_addresses.append(
                            f"{recipient.email_address.name or 'Unknown'} <{recipient.email_address.address or 'No email'}>")
                if cc_addresses:
                    result += f"   CC: {', '.join(cc_addresses)}\n"

            # Add BCC recipients
            if message.bcc_recipients and len(message.bcc_recipients) > 0:
                bcc_addresses = []
                for recipient in message.bcc_recipients:
                    if recipient.email_address:
                        bcc_addresses.append(
                            f"{recipient.email_address.name or 'Unknown'} <{recipient.email_address.address or 'No email'}>")
                if bcc_addresses:
                    result += f"   BCC: {', '.join(bcc_addresses)}\n"

            result += f"   Status: {'Read' if message.is_read else 'Unread'}\n"
            result += f"   Received: {message.received_date_time}\n"
            result += f"   Message ID: {message.id}\n\n"

    else:
        result += "No messages found in the inbox."

    return result


# Add a tool to list inbox messages
@mcp.tool()
@requires_graph_auth
async def list_inbox_messages(ctx: Context, count: int = 50) -> str:
    """
    Key header details for inbox messages default of 25 messages.

    Args:
        ctx: FastMCP Context
        count: Number of messages to retrieve

    Returns:
        A formatted string with message details including subject, sender, read status, and received date
    """
    graph = ctx.request_context.lifespan_context.graph
    message_page = await graph.mail.get_inbox(count=count)
    result = "Recent emails in your inbox:\n\n"

    result += format_email_headers(message_page)

    return result


@mcp.tool()
@requires_graph_auth
async def list_email_folders(ctx: Context) -> str:
    """
    List all email folders and their structure in your Outlook account

    Args:
        ctx: FastMCP Context

    Returns:
        A formatted string showing the hierarchical folder structure
    """
    graph = ctx.request_context.lifespan_context.graph

    # Get the folder hierarchy
    try:
        folder_hierarchy = await graph.mail.get_mail_folder_hierarchy()

        result = "Your email folder structure:\n\n"

        if folder_hierarchy:
            # Format each folder and its children
            for folder in folder_hierarchy:
                result += f"• {folder['display_name']}\n"

                # Add child folders if any
                if folder['child_folders']:
                    for child in folder['child_folders']:
                        result += f"  ↳ {child['display_name']}\n"

                result += "\n"
        else:
            result += "No folders found."

        return result
    except Exception as e:
        return f"Error listing mail folders: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_mail_folder_name_with_id(ctx: Context, folder_id: str) -> str:
    """Get folder name with specified ID

    Args:
        ctx: FastMCP Context
        folder_id: ID of the folder to retrieve

    Returns:
        Folder name

    """
    if folder_id is None:
        return "Please provide a folder ID"
    graph = ctx.request_context.lifespan_context.graph
    folder = await graph.mail.get_mail_folder_by_id(folder_id)
    return folder

@mcp.tool()
@requires_graph_auth
async def get_folders_and_inbox_mails_for_sort_planning(ctx: Context) -> str:
    """Get the current available folder structure for mails and get mails in the inbox with guidance on how to plan sorting

    Args:
        ctx: FastMCP Context

    Returns:
        String with list of inbox message headers, list of email folder hierarchy, and a prompt for explaining the task
    """
    inbox_messages = await list_inbox_messages(ctx)
    folders = await list_email_folders(ctx)
    return [base.UserMessage(f"""
    You are an email organization assistant. Your task is to:

    1. Take all email folders: {folders}
    2. Look at all the headers for inbox messages: {inbox_messages}
    3. Analyze each email's subject, and sender
    4. Suggest which folder each email should be filed into based on your analysis
    5. If the mail header is ambiguous, use the email_id to get_mail_with_mail_id and read content to determine the correct folder.
    6. If a folder is ambiguous get the folder id from the folder_id_dict and get_mail_from_specific_folder to see which emails are in that folder.

    Provide a clear, organized response in a table that lists each email and your folder recommendation.
    """)]

@mcp.tool()
@requires_graph_auth
async def get_folder_id_dict(ctx: Context) -> str:
    """Get dict that matches folder names to IDs

    Args:
        ctx: FastMCP Context

    Returns:
        Dict pairing folder names and folder_ids
    """
    graph = ctx.request_context.lifespan_context.graph
    folder_id_dict = await graph.mail.get_mail_folder_id_dict()
    return folder_id_dict

@mcp.tool()
@requires_graph_auth
async def move_email_to_folder(ctx: Context, message_id: str=None, folder_id: str=None) -> str:
    """Move an email to a specified folder
    Args:
        ctx: FastMCP Context
        message_id: ID of the email to move
        folder_id: ID of the folder to move the email to. If provided, folder_display_name will be ignored.

    Returns:
        Confirms email was moved
    """

    graph = ctx.request_context.lifespan_context.graph

    if folder_id is not None:
        folder_id = str(folder_id)
        folder_name = await get_mail_folder_name_with_id(ctx, folder_id)
    else:
        return "Please provide either a folder display name or folder ID"

    move_successful = await graph.mail.move_mail_to_folder(message_id=message_id, destination_folder_id=folder_id)

    if move_successful:
        return f"Email {message_id} moved to folder {folder_name}"
    else:
        return f"Error moving email {message_id} to folder {folder_name}"


@mcp.tool()
@requires_graph_auth
async def get_inbox_count(ctx: Context) -> str:
    """Get the number of messages in the inbox

    Args:
        ctx: FastMCP Context

    Returns:
        Number of mails in the inbox
    """

    graph = ctx.request_context.lifespan_context.graph
    inbox_count = await graph.mail.get_inbox_count()
    if inbox_count is not None:
        return inbox_count
    else:
        return "Inbox count not found"

@mcp.tool()
@requires_graph_auth
async def get_mail_with_mail_id(ctx: Context, message_id: str) -> str:
    """Get message with specified message_id

    Args:
        ctx: FastMCP Context
        message_id: ID of the message to retrieve

    Returns:
        The http mail response from which one can grab body with content
    """

    graph = ctx.request_context.lifespan_context.graph
    mail = await graph.mail.get_full_mail_by_id(message_id=message_id)
    if mail is not None:
        return mail
    else:
        return "Mail not found"



@mcp.tool()
@requires_graph_auth
async def get_mail_from_specific_folder(ctx: Context, folder_id: str, count: int=50) -> str:
    """Get all messages from a specific folder"""
    graph = ctx.request_context.lifespan_context.graph
    message_page = await graph.mail.get_mail_from_specific_mail_folder(folder_id=folder_id, count=count)
    result = "Recent emails in your inbox:\n\n"

    result += format_email_headers(message_page)

    return result


@mcp.tool()
@requires_graph_auth
async def search_by_subject(ctx: Context, subject: str, folder_id: str = "inbox") -> str:
    """
    Search for emails by subject

    Args:
        ctx: FastMCP Context
        subject: The subject text to search for
        folder_id: The folder ID to search in (default: inbox)
        count: Maximum number of emails to return

    Returns:
        A list of matching emails
    """
    graph = ctx.request_context.lifespan_context.graph

    query = MailQuery(
        subject=subject,
        folder_id=folder_id
    )

    messages = await graph.mail.search_mail(query)
    return format_email_headers(messages)


@mcp.tool()
@requires_graph_auth
async def search_unread_emails(ctx: Context, folder_id: str = "inbox", count: int = 20) -> str:
    """
    Get unread emails

    Args:
        ctx: FastMCP Context
        folder_id: The folder ID to search in (default: inbox)
        count: Maximum number of emails to return

    Returns:
        A list of unread emails
    """
    graph = ctx.request_context.lifespan_context.graph

    query = MailQuery(
        is_read=False,
        folder_id=folder_id,
        count=count
    )

    messages = await graph.mail.search_mail(query)
    return format_email_headers(messages)


@mcp.tool()
@requires_graph_auth
async def advanced_mail_search(ctx: Context, search_query: Any) -> str:
    """
    Search for emails using advanced criteria in JSON format

    Args:
        ctx: FastMCP Context
        search_query: JSON string with search parameters. Valid fields include:
            subject: Text to match in the subject line
            body: Text to match in the email body
            from_email: Sender's email address or display name
            to_email: Recipient's email address or display name
            cc_email: CC recipient's email address or display name
            has_attachments: Boolean (true/false) whether the email has attachments
            is_read: Boolean (true/false) for read status of the email
            folder_id: ID of the folder to search in (default: inbox)
            count: Maximum number of results to return (default: 50)

    Example: {"subject": "Meeting", "from_email": "john", "is_read": false}

    Returns:
        A list of matching emails
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        # Parse the JSON query
        if isinstance(search_query, dict):
            query_dict = search_query
        else:
            # Try to parse as JSON string

            query_dict = json.loads(search_query)

        # Create the mail query
        query = MailQuery(
            subject=query_dict.get('subject'),
            body=query_dict.get('body'),
            from_email=query_dict.get('from_email'),
            to_email=query_dict.get('to_email'),
            cc_email=query_dict.get('cc_email'),
            has_attachments=query_dict.get('has_attachments'),
            is_read=query_dict.get('is_read'),
            folder_id=query_dict.get('folder_id', 'inbox'),
            count=query_dict.get('count', 20)
        )

        # Execute the search
        messages = await graph.mail.search_mail(query)

        # Format and return results
        return format_email_headers(messages)

    except json.JSONDecodeError:
        return "Error: Invalid JSON format. Please provide a valid JSON object with search criteria."
    except Exception as e:
        return f"Error executing search: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def get_available_search_properties(ctx: Context) -> str:
    """
    Get search guidance and resolve search query errors

    Args:
        ctx: FastMCP Context

    Returns:
        Detailed guidance on mail search properties, valid formats, and troubleshooting tips for search errors
    """
    return """
Available email search properties:

1. subject - The text in the subject line of an email
   Example: {"subject": "meeting"}

2. body - The content in the body of an email
   Example: {"body": "project update"}

3. from_email - The sender of an email (name or address)
   Example: {"from_email": "john.doe@example.com"}

4. to_email - The direct recipient of an email
   Example: {"to_email": "jane"}

5. cc_email - Recipients copied on the email
   Example: {"cc_email": "team"}

6. has_attachments - Whether the email has attachments (true/false)
   Example: {"has_attachments": true}

7. is_read - Whether the email has been read (true/false)
   Example: {"is_read": false}

8. folder_id - The ID of the folder to search in (default: inbox)
   Example: {"folder_id": "AQMkADAwATM0MDAAMS1hM"}

9. count - The maximum number of results to return (default: 20)
   Example: {"count": 50}

You can combine multiple properties in a single search:
Example: {"from_email": "john", "has_attachments": true, "is_read": false, "count": 10}

To use these properties, create a JSON object with your desired search criteria and pass it to the advanced_mail_search tool.
"""


@mcp.tool()
@requires_graph_auth
async def create_top_level_folder(ctx: Context, folder_name: str) -> str:
    """
    Create a new top-level folder in your mailbox

    Args:
        ctx: FastMCP Context
        folder_name: Name for the new folder

    Returns:
        Status message with result and folder ID
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        new_folder = await graph.mail.create_mail_folder(display_name=folder_name)

        return f"Successfully created top-level folder '{folder_name}' with ID: {new_folder.id}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def create_subfolder(ctx: Context, folder_name: str, parent_folder_id: str) -> str:
    """
    Create a subfolder within an existing mail folder

    Args:
        ctx: FastMCP Context
        folder_name: Name for the new subfolder
        parent_folder_id: ID of the parent folder

    Returns:
        Status message with result and folder ID
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        new_folder = await graph.mail.create_mail_folder(
            display_name=folder_name,
            parent_folder_id=parent_folder_id
        )

        return f"Successfully created subfolder '{folder_name}' under folder ID '{parent_folder_id}' with new ID: {new_folder.id}"
    except Exception as e:
        return f"Error creating subfolder: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_user(ctx: Context, all_properties: bool = False) -> str:
    """Get user details

    Args:
        ctx: FastMCP Context
        all_properties: Whether to include all properties in the response (Default: False)

    Returns:
        String containing user information including dozens of properties such as 'displayName', 'mail', 'userPrincipalName', 'givenName', 'jobTitle', 'mobilePhone', 'officeLocation', 'preferredLanguage', 'surname', 'userType'
        If all_properties is False, the response will return t'displayName', 'mail', 'userPrincipalName'

    """
    graph = ctx.request_context.lifespan_context.graph
    try:
        return await graph.get_user(all_properties=all_properties)
    except Exception as e:
        return f"Error getting user: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def compose_new_email(ctx: Context,
                            to_recipients: str,
                            subject: str,
                            body: str,
                            cc_recipients: str = "",
                            bcc_recipients: str = "",
                            save_as_draft: bool = False) -> str:
    """
    Compose a new email with html formatting and either send it or save as draft

    Args:
        ctx: FastMCP Context
        to_recipients: Comma-separated list of email addresses
        subject: Subject line of the email
        body: Content of the email (defaul HTML formatting)
        cc_recipients: Comma-separated list of CC email addresses (optional)
        bcc_recipients: Comma-separated list of BCC email addresses (optional)
        save_as_draft: If true, saves to Drafts folder; if false, sends immediately

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        # Parse recipient lists
        to_list = [email.strip() for email in to_recipients.split(',') if email.strip()]
        cc_list = [email.strip() for email in cc_recipients.split(',') if email.strip()] if cc_recipients else None
        bcc_list = [email.strip() for email in bcc_recipients.split(',') if email.strip()] if bcc_recipients else None

        result = await graph.mail.create_new_email_for_draft_or_send(
            to_recipients=to_list,
            subject=subject,
            body=body,
            cc_recipients=cc_list,
            bcc_recipients=bcc_list,
            save_as_draft=save_as_draft
        )

        if save_as_draft:
            return f"Email saved to Drafts folder with subject: '{subject}'"
        else:
            return f"Email sent successfully to: {to_recipients}"

    except Exception as e:
        return f"Error composing email: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def reply_to_email(ctx: Context,
                         message_id: str,
                         body: str,
                         reply_all: bool = False,
                         to_recipients: str = "",
                         cc_recipients: str = "",
                         bcc_recipients: str = "",
                         subject: str = "") -> str:
    """
    Reply to an existing email with html formatting and send immediately

    Args:
        ctx: FastMCP Context
        message_id: ID of the message to reply to
        body: Content of the reply (default to HTML formatting)
        reply_all: If true, includes all original recipients; if false, replies only to sender
        to_recipients: Optional comma-separated additional recipients (leave empty to use default recipients)
        cc_recipients: Optional comma-separated CC recipients
        bcc_recipients: Optional comma-separated BCC recipients
        subject: Optional custom subject (leave empty to use "Re: original subject")

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        # Parse recipient lists
        to_list = [email.strip() for email in to_recipients.split(',') if email.strip()] if to_recipients else None
        cc_list = [email.strip() for email in cc_recipients.split(',') if email.strip()] if cc_recipients else None
        bcc_list = [email.strip() for email in bcc_recipients.split(',') if email.strip()] if bcc_recipients else None
        subject_param = subject if subject else None

        await graph.mail.reply_to_email(
            message_id=message_id,
            body=body,
            reply_all=reply_all,
            to_recipients=to_list,
            cc_recipients=cc_list,
            bcc_recipients=bcc_list,
            subject=subject_param
        )

        return f"Reply {'(to all)' if reply_all else ''} sent successfully"

    except Exception as e:
        return f"Error replying to email: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def create_draft_reply(ctx: Context, message_id: str) -> str:
    """
    Create a draft reply to an existing email

    Args:
        ctx: FastMCP Context
        message_id: ID of the message to reply to

    Returns:
        Status message with the draft ID
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        draft_reply = await graph.mail.create_draft_reply(message_id=message_id)

        return f"Draft reply created successfully with ID: {draft_reply.id}"

    except Exception as e:
        return f"Error creating draft reply: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def update_draft_email(ctx: Context,
                             draft_id: str,
                             body: Optional[str] = None,
                             subject: Optional[str] = None,
                             to_recipients: Optional[str] = None,
                             cc_recipients: Optional[str] = None,
                             bcc_recipients: Optional[str] = None) -> str:
    """
    Update an existing draft email with html formatting (Note: anything entered will overwrite existing content so be sure to include old content if needed))

    Args:
        ctx: FastMCP Context
        draft_id: ID of the draft message to update
        body: New html formatted content for the email (optional); if you want to add html formatted content to existing content, include the original with your edits
        subject: New subject line (optional); if you want to add to existing subject, include the original with your edits
        to_recipients: New comma-separated list of recipients (optional); if you want to add to existing recipients, include the original with your edits
        cc_recipients: New comma-separated list of CC recipients (optional); if you want to add to existing cc_recipients, include the original with your edits
        bcc_recipients: New comma-separated list of BCC recipients (optional); if you want to add to existing bcc_recipients, include the original with your edits

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        # Parse recipient lists if provided
        to_list = None
        if to_recipients is not None:
            to_list = [email.strip() for email in to_recipients.split(',') if email.strip()]

        cc_list = None
        if cc_recipients is not None:
            cc_list = [email.strip() for email in cc_recipients.split(',') if email.strip()]

        bcc_list = None
        if bcc_recipients is not None:
            bcc_list = [email.strip() for email in bcc_recipients.split(',') if email.strip()]

        await graph.mail.update_draft(
            draft_id=draft_id,
            body=body,
            subject=subject,
            to_recipients=to_list,
            cc_recipients=cc_list,
            bcc_recipients=bcc_list
        )

        return f"Draft email updated successfully"

    except Exception as e:
        return f"Error updating draft: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def send_draft_email(ctx: Context, draft_id: str) -> str:
    """
    Send an existing draft email

    Args:
        ctx: FastMCP Context
        draft_id: ID of the draft message to send

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        success = await graph.mail.send_draft(draft_id=draft_id)

        if success:
            return "Draft email sent successfully"
        else:
            return "Failed to send draft email"

    except Exception as e:
        return f"Error sending draft: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def update_mail_properties(ctx: Context,
                                 message_id: str,
                                 is_read: Optional[bool] = None,
                                 categories: Optional[List[str]] = None,
                                 importance: Optional[str] = None,
                                 inference_classification: Optional[str] = None,
                                 is_delivery_receipt_requested: Optional[bool] = None,
                                 is_read_receipt_requested: Optional[bool] = None) -> str:
    """
    Update mail properties for organization and filing

    Args:
        ctx: FastMCP Context
        message_id: ID of the message to update
        is_read: Mark the message as read or unread
        categories: List of categories to apply to the message
        importance: The importance of the message ('Low', 'Normal', 'High')
        inference_classification: Classification of message ('focused' or 'other')
        is_delivery_receipt_requested: Whether a delivery receipt is requested
        is_read_receipt_requested: Whether a read receipt is requested

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        result = await graph.mail.update_mail_properties(
            message_id=message_id,
            is_read=is_read,
            categories=categories,
            importance=importance,
            inference_classification=inference_classification,
            is_delivery_receipt_requested=is_delivery_receipt_requested,
            is_read_receipt_requested=is_read_receipt_requested
        )

        return f"Email properties successfully updated for message ID: {message_id}"
    except Exception as e:
        return f"Error updating email properties: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def list_available_tools(ctx: Context) -> str:
    """
    Return all registered tools with their descriptions (ideal for Claude to self-discover).
    """
    tools = await ctx.fastmcp.list_tools()
    summaries = []
    for tool in tools:
        args = ", ".join(tool.inputSchema.get("properties", {}).keys())
        summaries.append(f"• {tool.name}({args}): {tool.description or '(No description)'}")
    return "\n".join(sorted(summaries))

@mcp.resource(uri="resource://instructions", name="Instructions", description="Overview of OutlookMCP's capabilities.")
def get_app_instructions() -> str:
    return APP_INSTRUCTIONS


@mcp.tool()
@requires_graph_auth
async def list_calendar_events(ctx: Context, count: int = 10) -> str:
    """
    List upcoming calendar events from the user's default calendar

    Args:
        ctx: FastMCP Context
        count: Maximum number of events to retrieve (default: 10)

    Returns:
        A formatted string with event details including subject, organizer, start/end times, and location
    """
    graph = ctx.request_context.lifespan_context.graph
    events_page = await graph.calendar.list_events(count=count)

    result = "Upcoming calendar events:\n\n"
    result += format_event_page(events_page)

    return result


@mcp.tool()
@requires_graph_auth
async def list_calendar_by_date_range(ctx: Context, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """
    List calendar events within a specific date range

    Args:
        ctx: FastMCP Context
        start_date: Start date in format "YYYY-MM-DD" (default: beginning of current week)
        end_date: End date in format "YYYY-MM-DD" (default: 2 weeks from start_date)

    Returns:
        A formatted string with event details within the specified date range
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        events_page = await graph.calendar.list_events_by_date_range(start_date=start_date, end_date=end_date)

        # Get the actual date range used (for display in result)
        import datetime

        if not start_date:
            today = datetime.datetime.now().date()
            start_of_week = today - datetime.timedelta(days=today.weekday())
            start_date = start_of_week.strftime("%Y-%m-%d")

        if not end_date:
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = start_date_obj + datetime.timedelta(days=14)
            end_date = end_date_obj.strftime("%Y-%m-%d")

        # Format the dates for display
        start_display = datetime.datetime.strptime(start_date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
        end_display = datetime.datetime.strptime(end_date, "%Y-%m-%d").strftime("%A, %B %d, %Y")

        result = f"Calendar events from {start_display} to {end_display}:\n\n"

        # Reuse your existing formatting function
        from mcpserver.calendar_formatting import format_event_page
        result += format_event_page(events_page)

        return result
    except Exception as e:
        return f"Error retrieving calendar events: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def create_calendar_event(ctx: Context,
                                subject: Optional[str],
                                start_datetime: str,
                                end_datetime: str,
                                body: Optional[str] = "",
                                location: Optional[str] = None,
                                is_online_meeting: Optional[bool] = False,
                                attendees: Optional[str] = "") -> str:
    """
    Create a new calendar event with html formatting in body

    Args:
        ctx: FastMCP Context
        subject: Subject of the event
        start_datetime: Start time in format "YYYY-MM-DDTHH:MM:SS"
        end_datetime: End time in format "YYYY-MM-DDTHH:MM:SS"
        body: Body content of the event (default should be HTML); if the event is a meeting, language should make sense for both parties (i.e. instructions should be for everyone from neutral person)
        location: Optional location name
        is_online_meeting: Whether to make this a Teams online meeting
        attendees: Optional comma-separated list of attendee emails

    Returns:
        A confirmation message with the created event details
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        # Parse attendees if provided
        attendee_list = None
        if attendees:
            attendee_list = []
            for email in attendees.split(','):
                email = email.strip()
                if email:
                    attendee_list.append({"email": email})

        # Create the event
        result = await graph.calendar.create_event(
            subject=subject,
            body=body or f"<p>{subject}</p>",  # Default to subject if body is empty
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=location,
            is_online_meeting=is_online_meeting,
            attendees=attendee_list
        )

        # Get formatted event details to return
        from mcpserver.calendar_formatting import format_calendar_event
        formatted_event = format_calendar_event(result)

        return f"Event created successfully:\n\n{formatted_event}"

    except Exception as e:
        return f"Error creating calendar event: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def delete_calendar_event(ctx: Context, event_id: str, notify_attendees: bool = True) -> str:
    """
    Delete a calendar event

    Args:
        ctx: FastMCP Context
        event_id: ID of the event to delete
        notify_attendees: Whether to send cancellation notices to attendees (default: True)

    Returns:
        Confirmation message
    """
    graph = ctx.request_context.lifespan_context.graph

    try:
        # get the event details to provide in the confirmation message
        event = await graph.user_client.me.events.by_event_id(event_id).get()
        event_subject = event.subject if event else "Unknown event"

        # Delete the event
        await graph.calendar.delete_event(event_id, notify_attendees)

        notification_status = "with" if notify_attendees else "without"
        return f"Event successfully deleted {notification_status} attendee notification: '{event_subject}' (ID: {event_id})"
    except Exception as e:
        return f"Error deleting calendar event: {str(e)}"


@mcp.tool()
async def get_current_datetime(ctx: Context) -> str:
    """
    Get the current date and time in various formats

    Args:
        ctx: FastMCP Context

    Returns:
        A string with current date and time information in different formats
    """
    from datetime import datetime, timezone

    # Get current time in UTC
    utc_now = datetime.now(timezone.utc)

    # Get local time
    local_now = datetime.now()

    # Format the times in different ways
    result = "Current Date and Time Information:\n\n"
    result += f"UTC Date and Time: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
    result += f"Local Date and Time: {local_now.strftime('%Y-%m-%d %H:%M:%S')}\n"
    result += f"ISO Format UTC: {utc_now.isoformat()}\n"
    result += f"Calendar-friendly Date: {local_now.strftime('%A, %B %d, %Y')}\n"
    result += f"Time: {local_now.strftime('%I:%M %p')}\n"

    # Add date components that might be useful for calendar operations
    result += "\nDate Components:\n"
    result += f"Year: {local_now.year}\n"
    result += f"Month number: {local_now.month}\n"
    result += f"Month name: {local_now.strftime('%B')}\n"
    result += f"Day: {local_now.day}\n"
    result += f"Hour: {local_now.hour}\n"
    result += f"Minute: {local_now.minute}\n"
    result += f"Second: {local_now.second}\n"
    result += f"Day name: {local_now.strftime('%A')}\n"

    return result

##########################

def run():
    mcp.run()
