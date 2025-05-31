from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.fastmcp.prompts import base


from mcpserver.calendar_formatting import format_event_page
from mcpserver.auth_wrapper import requires_graph_auth
from mcpserver.context_manager import app_lifespan
from mcpserver.mail_query import MailQuery
from typing import Any, Optional, List
import json
import logging
import os

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

You also have access to advanced document search and retrieval capabilities through LlamaCloud:

File Management:
- Search Microsoft OneDrive/SharePoint files
- List and navigate SharePoint sites and document libraries
- Important: File IDs differ between systems (SharePoint IDs ≠ LlamaCloud IDs ≠ Pipeline IDs)

LlamaCloud RAG (Retrieval Augmented Generation):
- Search indexed documents using `search_llama_index` for basic search
- Use `direct_multi_pipeline_search` for advanced chunk retrieval with relevance scores
- Retrieval modes:
  - "routing": Auto-selects best pipeline (faster, good for focused search)
  - "full": Searches all pipelines (comprehensive, good for broad search)
- Returns raw text chunks with metadata - no LLM processing, just pure retrieval
- These chunks can be used to answer questions based on document content

When answering questions about document content:
1. First use retrieval tools to find relevant chunks
2. Then synthesize an answer based on the retrieved information
3. Be clear about which documents the information comes from

When taking ingestion or retrieval actions:
1. Check status of pipeline

By default for mail, use html formatting. Do not hallucinate data. Use MCP tools to fetch actual messages or folders.
When unsure which folder an email belongs to, inspect the email body and/or compare the content with other mails already in the folder.

Always be helpful, privacy-conscious, and structured in your reasoning.

IMPORTANT: Always use html formatting for the body of emails and calendar events. Do not hallucinate data.
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
        result += "No messages found in the folder."

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
async def get_folders_and_inbox_mails_for_sort_planning(ctx: Context) -> base.UserMessage:
    """Get the current available folder structure for mails and get mails in the inbox with guidance on how to plan sorting

    Args:
        ctx: FastMCP Context

    Returns:
        String with list of inbox message headers, list of email folder hierarchy, and a prompt for explaining the task
    """
    inbox_messages = await list_inbox_messages(ctx)
    folders = await list_email_folders(ctx)
    return base.UserMessage(f"""
    You are an email organization assistant. Your task is to:

    1. Take all email folders: {folders}
    2. Look at all the headers for inbox messages: {inbox_messages}
    3. Analyze each email's subject, and sender
    4. Suggest which folder each email should be filed into based on your analysis
    5. If the mail header is ambiguous, use the email_id to get_mail_with_mail_id and read content to determine the correct folder.
    6. If a folder is ambiguous get the folder id from the folder_id_dict and get_mail_from_specific_folder to see which emails are in that folder.

    Provide a clear, organized response in a table that lists each email and your folder recommendation.
    """)


@mcp.prompt()
async def sort_inbox(arguments=None):
    """
    Automatically organize your inbox to achieve inbox zero by processing calendar invites,
    filing important emails, and organizing remaining messages.
    """
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": """
Please help me sort my inbox to achieve inbox zero by following these steps:

0. First, get ready for the requests mail and calendar actions:
   - List email folders so you can see the email hierarchy
   - Get folder id dict: So can match folder names to folder ids

1. Next, identify calendar invites and messages with scheduling requests:
   - For calendar invites: Check my calendar for conflicts, then either accept, draft a response, or draft counter-proposals
   - Looking for meeting requests without formal invites: If a mail header is from an individual and the subject looks conversational instead of like marketing, get the full email content to check it for meeting requests
   - If you checked a message content and it did not have a meeting request, file it in the relevant folder as per normal rules below
   - For meeting requests without formal invites: Check my calendar and draft calendar invites with appropriate details

2. Next, identify important emails for filing in the Important folder:
   - Look for emails from key contacts (threads I've responded to, clients, team members)
   - Identify emails with urgent subject lines or time-sensitive content or suggesting an action
   - Move these to my "Important" folder using move_email_to_folder

3. For all remaining emails:
   - Analyze the content, sender, and subject
   - Move each email to the most appropriate folder based on its content
   - If the mail header is ambiguous, use the email_id to get_mail_with_mail_id and read content to determine the correct folder
   - Use get_mail_from_specific_folder if needed to see what kinds of emails are in different folders

4. Only pause to ask me questions if:
   - You're truly uncertain which folder is appropriate
   - You've found emails requiring a decision
   - You need clarification on a scheduling conflict

Take action immediately without asking for approval first. Use all available tools including get_folders_and_inbox_mails_for_sort_planning, get_folder_id_dict, get_mail_with_mail_id, and move_email_to_folder. When you're done, provide a summary of what you did, including how many emails you processed, where you moved them, and any draft responses or calendar events you created.
                """
            }
        }
    ]


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
async def get_available_mail_search_properties(ctx: Context) -> str:
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
async def create_top_level_mail_folder(ctx: Context, folder_name: str) -> str:
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
async def create_mail_subfolder(ctx: Context, folder_name: str, parent_folder_id: str) -> str:
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
                            subject: Optional[str] = None,
                            body_with_html_tags: Optional[str] = "None",
                            cc_recipients: Optional[str] = "",
                            bcc_recipients: Optional[str] = "",
                            save_as_draft: Optional[bool] = True) -> str:
    """
    Compose a new email with html formatting and either send it or save as draft

    Args:
        ctx: FastMCP Context
        to_recipients: Comma-separated list of email addresses
        subject: Subject line of the email
        body_with_html_tags: Content of the email (default HTML formatting)
        cc_recipients: Comma-separated list of CC email addresses (optional)
        bcc_recipients: Comma-separated list of BCC email addresses (optional)
        save_as_draft: If true, saves to Drafts folder; if false, sends immediately

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph
    body = body_with_html_tags # Parameter name required to keep Claude reverting to plain text default

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
                         body_with_html_tags: Optional[str],
                         reply_all: Optional[bool] = False,
                         to_recipients: Optional[str] = "",
                         cc_recipients: Optional[str] = "",
                         bcc_recipients: Optional[str] = "",
                         subject: Optional[str] = "") -> str:
    """
    Reply to an existing email with html formatting and send immediately

    Args:
        ctx: FastMCP Context
        message_id: ID of the message to reply to
        body_with_html_tags: Content of the reply (default to HTML formatting)
        reply_all: If true, includes all original recipients; if false, replies only to sender
        to_recipients: Optional comma-separated additional recipients (leave empty to use default recipients)
        cc_recipients: Optional comma-separated CC recipients
        bcc_recipients: Optional comma-separated BCC recipients
        subject: Optional custom subject (leave empty to use "Re: original subject")

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph
    body = body_with_html_tags # Parameter name required to keep Claude reverting to plain text default

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
                             body_with_html_tags: Optional[str] = None,
                             subject: Optional[str] = None,
                             to_recipients: Optional[str] = None,
                             cc_recipients: Optional[str] = None,
                             bcc_recipients: Optional[str] = None) -> str:
    """
    Update an existing draft email with html formatting (Note: anything entered will overwrite existing content so be sure to include old content if needed))

    Args:
        ctx: FastMCP Context
        draft_id: ID of the draft message to update
        body_with_html_tags: New html formatted content for the email (optional); if you want to add html formatted content to existing content, include the original with your edits
        subject: New subject line (optional); if you want to add to existing subject, include the original with your edits
        to_recipients: New comma-separated list of recipients (optional); if you want to add to existing recipients, include the original with your edits
        cc_recipients: New comma-separated list of CC recipients (optional); if you want to add to existing cc_recipients, include the original with your edits
        bcc_recipients: New comma-separated list of BCC recipients (optional); if you want to add to existing bcc_recipients, include the original with your edits

    Returns:
        Status message with result
    """
    graph = ctx.request_context.lifespan_context.graph
    body = body_with_html_tags # Parameter name required to keep Claude reverting to plain text default

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
                                body_with_html_tags: Optional[str] = "",
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
        body_with_html_tags: Body content of the event (default should be HTML); if the event is a meeting, language should make sense for both parties (i.e. instructions should be for everyone from neutral person)
        location: Optional location name
        is_online_meeting: Whether to make this a Teams online meeting
        attendees: Optional comma-separated list of attendee emails

    Returns:
        A confirmation message with the created event details
    """
    graph = ctx.request_context.lifespan_context.graph
    body = body_with_html_tags # Parameter name required to keep Claude reverting to plain text default

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

@mcp.tool()
@requires_graph_auth
async def list_followed_sharepoint_sites(ctx: Context):
    """
    Retrieves a list of SharePoint sites that the current user is following,
    returning their display names, IDs, and web URLs.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        sites_info = await files.list_followed_sites()
        return sites_info
    except Exception as e:
        return f"Error retrieving followed sites: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def get_sharepoint_site_drives(ctx: Context, site_id: str = os.environ.get("FULL_SHAREPOINT_SITE_ID")):
    """
    Retrieves the list of drives (document libraries) for a given SharePoint site ID.

    Args:
        ctx: FastMCP Context
        site_id: The ID of the SharePoint site (e.g., 'netorgft16432671.sharepoint.com,d79...').

    Returns:
        A list of drive information (id, name, webUrl) or an error message.
    """
    if not site_id:
        return "Error: A site_id must be provided to get its drives."
    files = ctx.request_context.lifespan_context.graph.files
    try:
        drives_info = await files.get_site_drives(site_id)

        if not drives_info:
            return f"Drives were found for site ID '{site_id}', but essential information (like ID) is missing."

        return drives_info
    except Exception as e:
        return f"Error retrieving drives for site ID '{site_id}': {str(e)}"



@mcp.tool()
@requires_graph_auth
async def list_sharepoint_drive_root_items(ctx: Context, drive_id: str):
    """
    Lists files and folders in the root of a specific drive (document library).

    Args:
        ctx: FastMCP Context
        drive_id: The ID of the drive.

    Returns:
        A list of item information (id, name, type, size, webUrl, lastModifiedDateTime) or an error message.
    """
    if not drive_id:
        return "Error: A drive_id must be provided to list its root items."

    files = ctx.request_context.lifespan_context.graph.files
    try:

        root_drive_item = await files.list_drive_root_items(drive_id)

        return root_drive_item

    except Exception as e:
        return f"Error listing root items for drive ID '{drive_id}': {str(e)}"


@mcp.tool()
@requires_graph_auth
async def list_sharepoint_drive_folder_items(ctx: Context, drive_id: str, folder_item_id: str):
    """
    Lists files and folders within a specific folder in a drive.

    Args:
        ctx: FastMCP Context
        drive_id: The ID of the drive.
        folder_item_id: The ID of the folder (which is a DriveItem ID).

    Returns:
        A list of item information (id, name, type, size, webUrl, lastModifiedDateTime) or an error message.
    """
    if not drive_id:
        return "Error: A drive_id must be provided."
    if not folder_item_id:
        return "Error: A folder_item_id must be provided."

    files = ctx.request_context.lifespan_context.graph.files
    try:
        drive_item_metadata = await files.list_drive_folder_items(drive_id, folder_item_id)
        return drive_item_metadata

    except Exception as e:
        return f"Error listing items in folder ID '{folder_item_id}' for drive ID '{drive_id}': {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_sharepoint_organization_id(ctx: Context):
    """
    Get the organization ID.

    Args:
        ctx: FastMCP Context

    Returns:
        A string with the organization ID.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        org_id = await files.get_organization_id()
        return org_id
    except Exception as e:
        return f"Error retrieving organization ID: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_sharepoint_site_id_from_user(ctx: Context, site_index: int = 0):
    """
    Get the SharePoint site ID for the user's default site.

    Args:
        ctx: FastMCP Context
        site_index: The index of the site to retrieve (default: 0).

    Returns:
        String with the site ID.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        site_id = await files.get_site_id_from_user(site_index)

        return site_id
    except Exception as e:
        return f"Error retrieving followed sites: {str(e)}"


@mcp.tool()
@requires_graph_auth
async def get_user_sharepoint_or_onedrive_drives(ctx: Context):
    """
    Get the list of drives (document libraries) for the user's default site.

    Args:
        ctx: FastMCP Context

    Returns:
        List of drives (document libraries).
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        drives = await files.get_user_drives()
        return drives
    except Exception as e:
        return f"Error retrieving user drives: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_user_main_microsoft_drive(ctx: Context):
    """
    Get the main drive (document library) for the user's default site.

    Args:
        ctx: FastMCP Context

    Returns:
        String object with drive metadata.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        user_drive = await files.get_user_drive()
        return user_drive
    except Exception as e:
        return f"Error retrieving user drive: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_user_microsoft_drive_id(ctx: Context):
    """
    Get the ID of the user's default drive (document library).

    Args:
        ctx: FastMCP Context

    Returns:
        String with the drive ID.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        drive_id = await files.get_user_drive_id()
        return drive_id
    except Exception as e:
        return f"Error retrieving user drive ID: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_msft_root_drive_item_for_user(ctx: Context):
    """
    Get the root drive item (e.g. folder) for the user.

    Args:
        ctx: FastMCP Context

    Returns:
        Object string for the root drive item.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        drive_item = await files.get_root_drive_item()
        return drive_item
    except Exception as e:
        return f"Error retrieving root drive item: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_msft_root_drive_item_id_for_user(ctx: Context):
    """
    Get the ID of the root drive item (e.g. folder) for the user.

    Args:
        ctx: FastMCP Context

    Returns:
        String with the ID of the root drive item.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        root_drive_item_id = await files.get_root_drive_item_id_for_user()
        return root_drive_item_id
    except Exception as e:
        return f"Error retrieving root drive item ID for the current user: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_microsoft_files(ctx: Context, drive_id: str, drive_item_id: str):
    """
    Get the files in a specific folder in a drive.

    Args:
        ctx: FastMCP Context
        drive_id: The ID of the drive.
        drive_item_id: The ID of the folder (which is a DriveItem ID).

    Returns:
        Response object string with the files in the folder.
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        files_info = await files.get_folders_and_files_from_drive_item(drive_id, drive_item_id)
        return files_info
    except Exception as e:
        return f"Error retrieving files for drive ID '{drive_id}' and drive item ID '{drive_item_id}': {str(e)}"

@mcp.tool()
@requires_graph_auth
async def search_microsoft_drive(ctx: Context, query: str, drive_id: str):
    """
    Search for files and folders in the user's OneDrive or SharePoint site drive

    Args:
        ctx: FastMCP Context
        query: Search term to find files and folders
        drive_id: Drive ID

    Returns:
        Search results from OneDrive or Sharepoint files
    """
    files = ctx.request_context.lifespan_context.graph.files
    try:
        search_results = await files.search_my_drive(query, drive_id)
        return search_results
    except Exception as e:
        return f"Error searching my drive: {str(e)}"

@mcp.tool()
@requires_graph_auth
async def get_msft_drive_root_folder_id(ctx: Context, drive_id: str):
    """
    Gets the ID of the root folder (DriveItem) for a given drive.
    This ID can be used as a folder_id to read from when fetching files.

    Args:
        ctx: FastMCP Context
        drive_id: The ID of the drive.

    Returns:
        The ID of the root DriveItem or an error message.
    """
    if not drive_id:
        return "Error: A drive_id must be provided."
    files = ctx.request_context.lifespan_context.graph.files
    try:
        root_drive_id = await files.get_drive_root_folder_id(drive_id)
        return root_drive_id
    except Exception as e:
        return f"Error getting the root folder ID for the drive ID '{drive_id}': {str(e)}"


@mcp.tool()
@requires_graph_auth
async def list_llama_projects(ctx: Context) -> str:
    """List existing LlamaCloud indices/pipelines"""
    pipeline_controller = ctx.request_context.lifespan_context.llama
    projects_list = await pipeline_controller.list_llama_projects()
    return projects_list

@mcp.tool()
@requires_graph_auth
async def list_llama_indices(ctx: Context, llama_project_id: Optional[str] = os.getenv('LLAMA_PROJECT_ID')) -> str:
    """List existing LlamaCloud indices/pipelines"""
    pipeline_controller = ctx.request_context.lifespan_context.llama
    pipeline_list = await pipeline_controller.list_llama_indices(llama_project_id = llama_project_id)
    return pipeline_list

@mcp.tool()
@requires_graph_auth
async def get_llama_index(ctx: Context, index_id: str):
    pipeline_controller = ctx.request_context.lifespan_context.llama
    index = await pipeline_controller.get_pipeline(pipeline_id=index_id)

@mcp.tool()
@requires_graph_auth
async def quick_parse_sharepoint_file(ctx: Context, sharepoint_file_id:str = os.getenv('TEST_FILE_ID'), sharepoint_drive_id: str = os.getenv('TOP_LEVEL_DRIVE_ID')) -> str:
    """Parse a SharePoint file using LlamaParse"""
    from llama_parse import LlamaParse
    import tempfile

    # Get the file from SharePoint
    graph = ctx.request_context.lifespan_context.graph
    file_content = await graph.user_client.drives.by_drive_id(sharepoint_drive_id).items.by_drive_item_id(sharepoint_file_id).content.get()

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
        temp_file.write(file_content)
        temp_path = temp_file.name

    # Parse with LlamaParse
    parser = LlamaParse(api_key=os.getenv("LLAMA_CLOUD_API_KEY"), auto_mode=True)
    result = await parser.aparse(temp_path)

    # Clean up
    os.unlink(temp_path)

    # Get markdown documents from the result
    markdown_documents = result.get_markdown_documents()
    docs = markdown_documents[0].text

    return docs


@mcp.tool()
@requires_graph_auth
async def create_sharepoint_data_source(ctx: Context, folder_path: str, folder_id: str, name_for_source: str) -> str:
    """Create a SharePoint data source in LlamaCloud for document ingestion

    Args:
        ctx: FastMCP Context
        folder_path: SharePoint folder path (e.g., '/sites/MySite/Documents/Folder')
        folder_id: SharePoint folder ID
        name_for_source: Name to give this data source in LlamaCloud

    Returns:
        Data source details or error message
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.create_sharepoint_data_source(
        folder_path=folder_path,
        folder_id=folder_id,
        name_for_source=name_for_source
    )
    return result


@mcp.tool()
@requires_graph_auth
async def get_llama_data_sources(ctx: Context) -> str:
    """Get all LlamaCloud data sources configured for your organization

    Args:
        ctx: FastMCP Context

    Returns:
        List of data sources with names and IDs
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.get_data_sources()
    return result


@mcp.tool()
@requires_graph_auth
async def get_llama_data_source(ctx: Context, data_source_id: str) -> str:
    """Get details of a specific LlamaCloud data source

    Args:
        ctx: FastMCP Context
        data_source_id: ID of the data source to retrieve

    Returns:
        Data source details or error message
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.get_data_source(data_source_id=data_source_id)
    return result


@mcp.tool()
@requires_graph_auth
async def get_llama_pipeline_datasources(ctx: Context, pipeline_id: str) -> str:
    """Get all data sources connected to a specific LlamaCloud pipeline

    Args:
        ctx: FastMCP Context
        pipeline_id: ID of the pipeline to check

    Returns:
        List of data sources connected to the pipeline
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.get_pipeline_datasources(pipeline_id=pipeline_id)
    return result


@mcp.tool()
@requires_graph_auth
async def add_data_source_to_llama_pipeline(ctx: Context, pipeline_id: str, data_source_id: str,
                                            sync_interval_hours: float = 12.0) -> str:
    """Connect a data source to a LlamaCloud pipeline for indexing

    Args:
        ctx: FastMCP Context
        pipeline_id: ID of the pipeline to add the data source to
        data_source_id: ID of the data source to add
        sync_interval_hours: How often to re-sync in hours (default: 12)

    Returns:
        Success confirmation or error message
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    # Convert hours to seconds for the API
    sync_interval_seconds = sync_interval_hours * 3600
    result = await pipeline_controller.add_data_source_to_pipeline(
        pipeline_id=pipeline_id,
        data_source_id=data_source_id,
        sync_interval=sync_interval_seconds
    )
    return result


@mcp.tool()
@requires_graph_auth
async def list_available_llama_files(ctx: Context, organization_id: str, raw_response:bool=False) -> str:
    """List all files available in your LlamaCloud organization

    Args:
        ctx: FastMCP Context
        organization_id: Your LlamaCloud organization ID

    Returns:
        List of files with IDs, paths, and content URLs
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.list_available_llama_files(
        organization_id=organization_id,
        raw_response=raw_response
    )
    return result


@mcp.tool()
@requires_graph_auth
async def list_llama_pipeline_files(ctx: Context, pipeline_id: str, raw_response:bool=False) -> str:
    """List all files indexed by a specific LlamaCloud pipeline

    Args:
        ctx: FastMCP Context
        pipeline_id: ID of the pipeline to check

    Returns:
        List of files with IDs, paths, and content URLs
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.list_pipeline_files(pipeline_id=pipeline_id, raw_response=raw_response)
    return result


@mcp.tool()
@requires_graph_auth
async def search_llama_index(ctx: Context, pipeline_id: str, query: str) -> str:
    """Search for information in a LlamaCloud pipeline's indexed documents

    Args:
        ctx: FastMCP Context
        pipeline_id: ID of the pipeline to search
        query: Search query to find relevant information

    Returns:
        Search results with relevance scores and source information
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.search_index(
        pipeline_id=pipeline_id,
        query=query
    )
    return result


@mcp.tool()
@requires_graph_auth
async def sync_llama_pipeline(ctx: Context, pipeline_id: str) -> str:
    """Trigger a manual sync of a LlamaCloud pipeline to update its index

    Args:
        ctx: FastMCP Context
        pipeline_id: ID of the pipeline to sync

    Returns:
        Sync status or error message
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.sync_pipeline(pipeline_id=pipeline_id)
    return result


@mcp.tool()
@requires_graph_auth
async def create_llama_retriever(
        ctx: Context,
        name: str,
        pipeline_ids: str,
        project_id: Optional[str] = None
) -> str:
    """Create a new LlamaCloud retriever for advanced multi-pipeline search

    Args:
        ctx: FastMCP Context
        name: Name for the retriever
        pipeline_ids: Comma-separated list of pipeline IDs to include
        project_id: Optional project ID (defaults to env var)

    Returns:
        Created retriever details
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama

    # Parse pipeline IDs
    pipeline_id_list = [pid.strip() for pid in pipeline_ids.split(',')]

    result = await pipeline_controller.create_retriever(
        name=name,
        pipeline_ids=pipeline_id_list,
        project_id=project_id
    )

    return f"Created retriever '{result.name}' with ID: {result.id}"


@mcp.tool()
@requires_graph_auth
async def list_llama_retrievers(
        ctx: Context,
        project_id: Optional[str] = None
) -> str:
    """List all LlamaCloud retrievers in the project

    Args:
        ctx: FastMCP Context
        project_id: Optional project ID (defaults to env var)

    Returns:
        List of retrievers with their configurations
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.list_retrievers(project_id=project_id)
    return result


@mcp.tool()
@requires_graph_auth
async def search_with_retriever(
        ctx: Context,
        retriever_id: str,
        query: str,
        mode: str = "routing",
        rerank_top_n: Optional[int] = None
) -> str:
    """Search using an existing LlamaCloud retriever for advanced multi-pipeline search

    Args:
        ctx: FastMCP Context
        retriever_id: ID of the retriever to use
        query: Search query
        mode: Retrieval mode - 'routing' (auto-select best pipeline) or 'full' (search all pipelines)
        rerank_top_n: Optional number of results to rerank

    Returns:
        Search results from the retriever
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.retrieve_with_retriever(
        retriever_id=retriever_id,
        query=query,
        mode=mode,
        rerank_top_n=rerank_top_n
    )
    return result


@mcp.tool()
@requires_graph_auth
async def direct_multi_pipeline_search(
        ctx: Context,
        pipeline_ids: str,
        query: str,
        mode: str = "routing",
        rerank_top_n: Optional[int] = None,
        top_k_per_pipeline: int = 10,
        project_id: Optional[str] = None
) -> str:
    """Search across multiple LlamaCloud pipelines without creating a persistent retriever

    Args:
        ctx: FastMCP Context
        pipeline_ids: Comma-separated list of pipeline IDs to search
        query: Search query
        mode: Retrieval mode - 'routing' (auto-select best pipeline) or 'full' (search all pipelines)
        rerank_top_n: Optional number of results to rerank
        top_k_per_pipeline: Number of results per pipeline (default: 10)
        project_id: Optional project ID (defaults to env var)

    Returns:
        Search results across pipelines
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama

    # Parse pipeline IDs
    pipeline_id_list = [pid.strip() for pid in pipeline_ids.split(',')]

    result = await pipeline_controller.direct_retrieve(
        pipeline_ids=pipeline_id_list,
        query=query,
        mode=mode,
        rerank_top_n=rerank_top_n,
        top_k_per_pipeline=top_k_per_pipeline,
        project_id=project_id
    )
    return result


@mcp.tool()
@requires_graph_auth
async def upload_sharepoint_file_to_llamacloud(
        ctx: Context,
        sharepoint_drive_id: str,
        sharepoint_file_id: str
) -> str:
    """Upload a SharePoint file to LlamaCloud (just upload, no pipeline)

    Args:
        ctx: FastMCP Context
        sharepoint_drive_id: SharePoint drive ID
        sharepoint_file_id: SharePoint file ID

    Returns:
        LlamaCloud file ID after upload
    """
    graph = ctx.request_context.lifespan_context.graph
    pipeline_controller = ctx.request_context.lifespan_context.llama

    result = await pipeline_controller.upload_sharepoint_file_to_llamacloud(
        sharepoint_drive_id=sharepoint_drive_id,
        sharepoint_file_id=sharepoint_file_id,
        graph_client=graph.user_client,
        project_id=None
    )

    return result


@mcp.tool()
@requires_graph_auth
async def list_llama_file_screenshots(
        ctx: Context,
        file_id: str
) -> str:
    """List all page screenshots available for a LlamaCloud file

    Args:
        ctx: FastMCP Context
        file_id: LlamaCloud file ID

    Returns:
        List of available page screenshots with metadata
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    result = await pipeline_controller.list_file_screenshots(file_id=file_id)
    return result


@mcp.tool()
@requires_graph_auth
async def get_llama_file_screenshot(
        ctx: Context,
        file_id: str,
        page_index: int
) -> Image:
    from mcp.server.fastmcp import Image
    """Get a page screenshot from a LlamaCloud file as an image

    Args:
        ctx: FastMCP Context
        file_id: LlamaCloud file ID
        page_index: Page number (0-based index)

    Returns:
        Screenshot image that can be viewed by the LLM
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama

    # Get screenshot data
    screenshot_data = await pipeline_controller.get_file_screenshot(
        file_id=file_id,
        page_index=page_index
    )

    # Detect image format from magic bytes
    if screenshot_data[:4] == b'\xff\xd8\xff\xe0' or screenshot_data[:4] == b'\xff\xd8\xff\xe1':
        fmt = "jpeg"
    elif screenshot_data[:8] == b'\x89PNG\r\n\x1a\n':
        fmt = "png"
    else:
        # Default to jpeg based on what we saw in the error
        fmt = "jpeg"

    # Return as FastMCP Image with correct fmt
    return Image(data=screenshot_data, format=fmt)

@mcp.tool()
@requires_graph_auth
async def get_llama_file_download_url(
        ctx: Context,
        file_id: str,
        expires_in_seconds: int = 3600
) -> str:
    """Get a temporary download URL for a LlamaCloud file

    Args:
        ctx: FastMCP Context
        file_id: LlamaCloud file ID
        expires_in_seconds: How long the URL should be valid (default: 1 hour)

    Returns:
        Presigned URL for downloading the file
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama
    url = await pipeline_controller.get_file_content_url(
        file_id=file_id,
        expires_in_seconds=expires_in_seconds
    )
    return f"Download URL (expires in {expires_in_seconds} seconds): {url}"


# Add these tools to server.py

@mcp.tool()
@requires_graph_auth
async def create_llama_pipeline(
        ctx: Context,
        name: str,
        pipeline_config: Any,
        project_id: Optional[str] = None
) -> str:
    """Create a new LlamaCloud pipeline with specified configuration

    Args:
        ctx: FastMCP Context
        name: Name for the new pipeline
        pipeline_config: JSON configuration for the pipeline. Example:
            {
                "embedding_config": {
                    "type": "OPENAI_EMBEDDING",
                    "component": {
                        "model_name": "text-embedding-3-small",
                        "api_key": "your-key"
                    }
                },
                "transform_config": {
                    "mode": "auto",
                    "config": {
                        "chunk_size": 1024,
                        "chunk_overlap": 200
                    }
                },
                "preset_retrieval_parameters": {
                    "retrieve_image_nodes": true,
                    "dense_similarity_top_k": 30,
                    "enable_reranking": true
                },
                "llama_parse_parameters": {
                    "take_screenshot": true,
                    "extract_charts": true,
                    "disable_image_extraction": false
                }
            }
        project_id: Optional project ID (defaults to env var)

    Returns:
        Created pipeline details or error message
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama

    # Parse the config if it's a string
    if isinstance(pipeline_config, str):
        try:
            pipeline_config = json.loads(pipeline_config)
        except json.JSONDecodeError:
            return "Error: Invalid JSON in pipeline_config"

    result = await pipeline_controller.create_pipeline(
        name=name,
        project_id=project_id,
        pipeline_config=pipeline_config
    )

    return result


@mcp.tool()
@requires_graph_auth
async def update_llama_pipeline(
        ctx: Context,
        pipeline_id: str,
        update_config: Any
) -> str:
    """Update an existing LlamaCloud pipeline configuration

    Args:
        ctx: FastMCP Context
        pipeline_id: ID of the pipeline to update
        update_config: JSON configuration with updates. Example:
            {
                "preset_retrieval_parameters": {
                    "retrieve_image_nodes": true
                },
                "llama_parse_parameters": {
                    "take_screenshot": true,
                    "extract_charts": true
                }
            }

    Returns:
        Update status or error message
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama

    # Parse the config if it's a string
    if isinstance(update_config, str):
        try:
            update_config = json.loads(update_config)
        except json.JSONDecodeError:
            return "Error: Invalid JSON in update_config"

    result = await pipeline_controller.update_pipeline(
        pipeline_id=pipeline_id,
        update_config=update_config
    )

    return result


# Add this tool to server.py

@mcp.tool()
@requires_graph_auth
async def add_files_to_llama_pipeline(
        ctx: Context,
        pipeline_id: str,
        file_ids: str
) -> str:
    """Add existing LlamaCloud files to a pipeline for processing

    Args:
        ctx: FastMCP Context
        pipeline_id: ID of the pipeline to add files to
        file_ids: Comma-separated list of LlamaCloud file IDs to add

    Returns:
        Success message with added files or error
    """
    pipeline_controller = ctx.request_context.lifespan_context.llama

    # Parse the comma-separated file IDs
    file_id_list = [fid.strip() for fid in file_ids.split(',') if fid.strip()]

    if not file_id_list:
        return "Error: No valid file IDs provided"

    result = await pipeline_controller.add_files_to_pipeline(
        pipeline_id=pipeline_id,
        file_ids=file_id_list
    )

    return result

@mcp.tool()
@requires_graph_auth
async def get_index_status(ctx: Context, pipeline_id) -> str:

    pipeline_controller = ctx.request_context.lifespan_context.llama
    try:
        response = await pipeline_controller.client.pipelines.get_pipeline_status(pipeline_id=pipeline_id)
        return response
    except Exception as e:
        return f"Error getting pipeline status: {str(e)}"

