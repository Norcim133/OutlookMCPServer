# mcpserver/graph/mail_service.py
from msgraph import GraphServiceClient
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.users.item.mail_folders.item.move.move_post_request_body import MovePostRequestBody
from mcpserver.mail_query import MailQuery
from typing import List


class MailService:
    """Service for mail-related operations using Microsoft Graph API"""

    def __init__(self, user_client: GraphServiceClient):
        self.user_client = user_client


    async def get_inbox(self, count: int=50):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            # Only request specific properties
            select=['from', 'isRead', 'receivedDateTime', 'subject', 'id', 'toRecipients', 'ccRecipients', 'bccRecipients', 'replyTo'],

            top=count,
            # Sort by received time, newest first
            orderby=['receivedDateTime DESC']
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters= query_params
        )

        messages = await self.user_client.me.mail_folders.by_mail_folder_id('inbox').messages.get(
                request_configuration=request_config)
        return messages

    async def create_new_email_for_draft_or_send(self,
                                                 to_recipients: List[str],
                                                 subject: str,
                                                 body: str,
                                                 cc_recipients: List[str] = None,
                                                 bcc_recipients: List[str] = None,
                                                 save_as_draft: bool = False):
        """
        Create a new email and either save as draft or send immediately

        Args:
            to_recipients: List of email addresses for To field
            subject: Subject line of the email
            body: Body content of the email
            cc_recipients: List of email addresses for CC field (optional)
            bcc_recipients: List of email addresses for BCC field (optional)
            save_as_draft: If True, saves as draft; if False, sends immediately

        Returns:
            The created or sent message object
        """
        try:
            # Create message object
            message = Message()
            message.subject = subject

            # Set body
            message.body = ItemBody()
            message.body.content_type = BodyType.Html
            message.body.content = body

            # Set recipients
            message.to_recipients = []
            for recipient in to_recipients:
                to_recipient = Recipient()
                to_recipient.email_address = EmailAddress()
                to_recipient.email_address.address = recipient
                message.to_recipients.append(to_recipient)

            # Set CC recipients if provided
            if cc_recipients:
                message.cc_recipients = []
                for recipient in cc_recipients:
                    cc_recipient = Recipient()
                    cc_recipient.email_address = EmailAddress()
                    cc_recipient.email_address.address = recipient
                    message.cc_recipients.append(cc_recipient)

            # Set BCC recipients if provided
            if bcc_recipients:
                message.bcc_recipients = []
                for recipient in bcc_recipients:
                    bcc_recipient = Recipient()
                    bcc_recipient.email_address = EmailAddress()
                    bcc_recipient.email_address.address = recipient
                    message.bcc_recipients.append(bcc_recipient)

            if save_as_draft:
                # Save as draft
                result = await self.user_client.me.messages.post(message)
                return result
            else:
                # Send immediately
                request_body = SendMailPostRequestBody()
                request_body.message = message
                await self.user_client.me.send_mail.post(body=request_body)
                return message

        except Exception as e:
            raise Exception(f"Error creating or sending email: {str(e)}")

    async def reply_to_email(self,
                             message_id: str,
                             body: str,
                             reply_all: bool = False,
                             to_recipients: List[str] = None,
                             cc_recipients: List[str] = None,
                             bcc_recipients: List[str] = None,
                             subject: str = None):
        """
        Reply to an existing email and send immediately

        Args:
            message_id: ID of the message to reply to
            body: Body content of the reply
            reply_all: If True, includes all original recipients; if False, replies only to sender
            to_recipients: Optional list of email addresses to override recipients
            cc_recipients: Optional list of email addresses for CC field
            bcc_recipients: Optional list of email addresses for BCC field
            subject: Optional custom subject (default: Re: original subject)

        Returns:
            The sent message object
        """
        try:
            # Get the original message
            original_message = await self.user_client.me.messages.by_message_id(message_id).get()
            if not original_message:
                raise Exception(f"Original message with ID {message_id} not found")

            # Handle subject
            if subject is None:
                # Check if the original subject already starts with any form of "RE:"
                original_subject = original_message.subject or ""
                if original_subject.upper().startswith("RE:") or original_subject.upper().startswith("RE "):
                    subject = original_subject
                else:
                    subject = f"Re: {original_subject}"

            # Create a new message to send as reply
            message = Message()
            message.subject = subject

            # Set body
            message.body = ItemBody()
            message.body.content_type = BodyType.Html
            message.body.content = body

            # Set recipients based on reply_all flag and any explicitly provided recipients
            if to_recipients is None:
                if reply_all and original_message.to_recipients:
                    # Include all original recipients
                    to_recipients = []
                    # Add original sender (for completeness)
                    if original_message.from_ and original_message.from_.email_address:
                        to_recipients.append(original_message.from_.email_address.address)

                    # Add all original To recipients except self
                    user_info = await self.user_client.me.get()
                    my_email = user_info.mail

                    for recipient in original_message.to_recipients:
                        if recipient.email_address and recipient.email_address.address and recipient.email_address.address != my_email:
                            to_recipients.append(recipient.email_address.address)
                else:
                    # Reply only to sender
                    to_recipients = [original_message.from_.email_address.address]

            # Set CC recipients based on reply_all flag and any explicitly provided CC recipients
            if cc_recipients is None and reply_all and original_message.cc_recipients:
                # Include original CC recipients
                cc_recipients = []
                for recipient in original_message.cc_recipients:
                    if recipient.email_address and recipient.email_address.address:
                        cc_recipients.append(recipient.email_address.address)

            # Set recipients
            message.to_recipients = []
            for recipient in to_recipients:
                to_recipient = Recipient()
                to_recipient.email_address = EmailAddress()
                to_recipient.email_address.address = recipient
                message.to_recipients.append(to_recipient)

            # Set CC recipients if provided
            if cc_recipients:
                message.cc_recipients = []
                for recipient in cc_recipients:
                    cc_recipient = Recipient()
                    cc_recipient.email_address = EmailAddress()
                    cc_recipient.email_address.address = recipient
                    message.cc_recipients.append(cc_recipient)

            # Set BCC recipients if provided
            if bcc_recipients:
                message.bcc_recipients = []
                for recipient in bcc_recipients:
                    bcc_recipient = Recipient()
                    bcc_recipient.email_address = EmailAddress()
                    bcc_recipient.email_address.address = recipient
                    message.bcc_recipients.append(bcc_recipient)

            # Send the reply
            request_body = SendMailPostRequestBody()
            request_body.message = message
            await self.user_client.me.send_mail.post(body=request_body)
            return message

        except Exception as e:
            raise Exception(f"Error replying to email: {str(e)}")

    async def create_draft_reply(self, message_id: str):
        """
        Create a draft reply to an existing email

        Args:
            message_id: ID of the message to reply to

        Returns:
            The created draft reply message
        """
        try:
            # Use createReply endpoint to create a draft reply
            empty_body = {}
            draft_reply = await self.user_client.me.messages.by_message_id(message_id).create_reply.post(empty_body)
            return draft_reply
        except Exception as e:
            raise Exception(f"Error creating draft reply: {str(e)}")

    async def update_draft(self,
                           draft_id: str,
                           body: str = None,
                           subject: str = None,
                           to_recipients: List[str] = None,
                           cc_recipients: List[str] = None,
                           bcc_recipients: List[str] = None):
        """
        Update an existing draft email

        Args:
            draft_id: ID of the draft message to update
            body: New body content (optional)
            subject: New subject line (optional)
            to_recipients: New list of To recipients (optional)
            cc_recipients: New list of CC recipients (optional)
            bcc_recipients: New list of BCC recipients (optional)

        Returns:
            The updated draft message
        """
        try:
            # Create an update message object
            update_message = Message()

            # Set provided fields
            if body is not None:
                update_message.body = ItemBody()
                update_message.body.content_type = BodyType.Html
                update_message.body.content = body

            if subject is not None:
                update_message.subject = subject

            if to_recipients is not None:
                update_message.to_recipients = []
                for recipient in to_recipients:
                    to_recipient = Recipient()
                    to_recipient.email_address = EmailAddress()
                    to_recipient.email_address.address = recipient
                    update_message.to_recipients.append(to_recipient)

            if cc_recipients is not None:
                update_message.cc_recipients = []
                for recipient in cc_recipients:
                    cc_recipient = Recipient()
                    cc_recipient.email_address = EmailAddress()
                    cc_recipient.email_address.address = recipient
                    update_message.cc_recipients.append(cc_recipient)

            if bcc_recipients is not None:
                update_message.bcc_recipients = []
                for recipient in bcc_recipients:
                    bcc_recipient = Recipient()
                    bcc_recipient.email_address = EmailAddress()
                    bcc_recipient.email_address.address = recipient
                    update_message.bcc_recipients.append(bcc_recipient)

            # Update the draft message
            result = await self.user_client.me.messages.by_message_id(draft_id).patch(update_message)
            return result
        except Exception as e:
            raise Exception(f"Error updating draft: {str(e)}")

    async def send_draft(self, draft_id: str):
        """
        Send an existing draft email

        Args:
            draft_id: ID of the draft message to send

        Returns:
            True if successful
        """
        try:
            # Send the draft message
            await self.user_client.me.messages.by_message_id(draft_id).send.post()
            return True
        except Exception as e:
            raise Exception(f"Error sending draft: {str(e)}")

    async def move_mail_to_folder(self, message_id: str=None, destination_folder_id: str=None):
        """Moves a message to a specified folder"""
        request_body = MovePostRequestBody(destination_id=destination_folder_id)

        response = await self.user_client.me.messages.by_message_id(message_id).move.post(request_body)
        if response is not None:
            return True
        else:
            return False

    async def get_folders(self):
        folder_count = await self.user_client.me.mail_folders.count.get()

        if folder_count > 10:
            data = await self.user_client.me.mail_folders.get()
            all_data = []
            all_data.extend(data.value)
            url = data.odata_next_link
            while url:
                response = await self.user_client.me.mail_folders.with_url(url).get()
                data = response.value
                all_data.extend(data)
                url = response.odata_next_link

        else:
            data = await self.user_client.me.mail_folders.get()
            all_data = []
            all_data.extend(data.value)

        return all_data

    async def get_mail_folder_id_dict(self):
        """Gets the ID of the Inbox folder"""
        all_data = await self.get_folders()
        folder_id_dict = {}
        for folder in all_data:
            folder_id_dict[folder.display_name] = folder.id
            try:
                child_folders = await self.user_client.me.mail_folders.by_mail_folder_id(folder.id).child_folders.get()
                if child_folders and child_folders.value:
                    for child in child_folders.value:
                        folder_id_dict[child.display_name] = child.id
            except Exception as e:
                # Some folders might not support child folder operations
                print("Error getting mail folders: ", e)
        return folder_id_dict

    async def get_mail_folder_hierarchy(self):
        """Gets all mail folders with their hierarchical structure"""
        # Get top-level folders first
        all_data = await self.get_folders()

        # For each folder, get its child folders
        result = []
        if all_data:
            for folder in all_data:
                folder_info = {
                    "id": folder.id,
                    "display_name": folder.display_name,
                    "parent_folder_id": folder.parent_folder_id,
                    "child_folders": []
                }

                # Get child folders if they exist
                try:
                    child_folders = await self.user_client.me.mail_folders.by_mail_folder_id(folder.id).child_folders.get()
                    if child_folders and child_folders.value:
                        for child in child_folders.value:
                            child_info = {
                                "id": child.id,
                                "display_name": child.display_name,
                                "parent_folder_id": child.parent_folder_id
                            }
                            folder_info["child_folders"].append(child_info)
                except Exception as e:
                    # Some folders might not support child folder operations
                    print("Error getting mail folders: ", e)

                result.append(folder_info)

        return result

    async def get_mail_folder_by_id(self, folder_id: str):
        """Get folder with specified ID

        Args:
            folder_id: ID of the folder to retrieve

        Returns:
            Folder details with ID and display name

        """
        response = await self.user_client.me.mail_folders.by_mail_folder_id(folder_id).get()

        if response is not None:
            return response.display_name
        else:
            return "Folder not found"

    async def get_inbox_count(self):
        response = await self.user_client.me.mail_folders.by_mail_folder_id('inbox').messages.count.get()
        if response is not None:
            response = int(response)
        return response

    async def get_full_mail_by_id(self, message_id: str):
        """Get http email message response with specified message_id

        Args:
            message_id: ID of the message to retrieve

        Returns:
            The http response from which one can grab the body with content of the mail message
        """
        response = await self.user_client.me.messages.by_message_id(message_id).get()
        if response is not None:
            response = response
        return response

    async def get_mail_from_specific_mail_folder(self, folder_id: str='inbox', count: int=50):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            # Only request specific properties
            select=['from', 'isRead', 'receivedDateTime', 'subject', 'id', 'toRecipients', 'ccRecipients', 'bccRecipients', 'replyTo'],
            # Get at most 25 results
            top=count,
            # Sort by received time, newest first
            orderby=['receivedDateTime DESC']
        )
        request_config = RequestConfiguration(
            query_parameters= query_params
        )

        messages = await self.user_client.me.mail_folders.by_mail_folder_id(folder_id).messages.get(
                request_configuration=request_config)
        return messages

    async def search_mail(self, query: MailQuery):
        """
        Search for emails based on the provided query parameters

        Args:
            query: A MailQuery object containing search parameters

        Returns:
            A collection of messages matching the search criteria
        """

        # Build query parameters
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=query.select,
            top=query.count
        )

        if query.is_full_text_query():
            search_string = query.build_search_query()
            if search_string:
                query_params.search = f"\"{search_string}\""
        else:
            query_params.orderby = query.orderby
            if query.is_read is not None:
                query_params.filter = f"isRead eq {str(query.is_read).lower()}"

        request_config = RequestConfiguration(
            query_parameters=query_params
        )

        # Determine the target folder
        if query.include_nested_folders:
            # Search across all folders
            messages = await self.user_client.me.messages.get(
                request_configuration=request_config)
        else:
            # Search in specific folder
            messages = await self.user_client.me.mail_folders.by_mail_folder_id(query.folder_id).messages.get(
                request_configuration=request_config)

        return messages


    async def create_mail_folder(self, display_name: str, parent_folder_id: str = None, is_hidden: bool = False):
        """
        Create a new mail folder

        Args:
            display_name: Name of the folder to create
            parent_folder_id: ID of the parent folder (if None, creates a top-level folder)
            is_hidden: Whether the folder should be hidden

        Returns:
            The created mail folder object
        """
        from msgraph.generated.models.mail_folder import MailFolder

        # Create folder object
        request_body = MailFolder(
            display_name=display_name,
            is_hidden=is_hidden,
        )

        try:
            # Create as child folder if parent_folder_id is provided
            if parent_folder_id:
                result = await self.user_client.me.mail_folders.by_mail_folder_id(parent_folder_id).child_folders.post(
                    request_body)
            else:
                # Create as top-level folder
                result = await self.user_client.me.mail_folders.post(request_body)

            return result
        except Exception as e:
            raise Exception(f"Error creating mail folder: {str(e)}")

    async def update_mail_properties(self,
                                     message_id: str,
                                     is_read: bool = None,
                                     categories: List[str] = None,
                                     importance: str = None,
                                     inference_classification: str = None,
                                     is_delivery_receipt_requested: bool = None,
                                     is_read_receipt_requested: bool = None):
        """
        Update mail properties for organization and filing

        Args:
            message_id: ID of the message to update
            is_read: Mark the message as read or unread
            categories: List of categories to apply to the message
            importance: The importance of the message ('Low', 'Normal', 'High')
            inference_classification: Classification of message ('focused' or 'other')
            is_delivery_receipt_requested: Whether a delivery receipt is requested
            is_read_receipt_requested: Whether a read receipt is requested

        Returns:
            The updated message
        """
        try:
            # Create an update message object
            update_message = Message()

            # Set provided fields
            if is_read is not None:
                update_message.is_read = is_read

            if categories is not None:
                update_message.categories = categories

            if importance is not None:
                # Validate importance value
                valid_importance = ["low", "normal", "high"]
                if importance.lower() not in valid_importance:
                    raise ValueError(f"Importance must be one of: {', '.join(valid_importance)}")
                update_message.importance = importance

            if inference_classification is not None:
                # Validate inference classification value
                valid_classification = ["focused", "other"]
                if inference_classification.lower() not in valid_classification:
                    raise ValueError(f"Inference classification must be one of: {', '.join(valid_classification)}")
                update_message.inference_classification = inference_classification

            if is_delivery_receipt_requested is not None:
                update_message.is_delivery_receipt_requested = is_delivery_receipt_requested

            if is_read_receipt_requested is not None:
                update_message.is_read_receipt_requested = is_read_receipt_requested

            # Update the message
            result = await self.user_client.me.messages.by_message_id(message_id).patch(update_message)
            return result
        except Exception as e:
            raise Exception(f"Error updating mail properties: {str(e)}")