from settings import AzureSettings
from msgraph import GraphServiceClient
from msgraph.generated.users.item.user_item_request_builder import UserItemRequestBuilder

from kiota_abstractions.base_request_configuration import RequestConfiguration


class GraphController:
    """
    Central controller for Microsoft Graph API interactions.
    Manages the authenticated client and provides access to specialized services.
    """

    def __init__(self, user_client: GraphServiceClient):
        self.user_client = user_client
        self._mail_service = None
        self._calendar_service = None
        self._files_service = None

    @property
    def mail(self):
        """
        Get the mail service instance.
        Lazy-loads the service on first access.
        """
        if self._mail_service is None:
            from mcpserver.graph.mail_service import MailService
            self._mail_service = MailService(self.user_client)
        return self._mail_service

    @property
    def files(self):
        """
        Get the files service instance.
        Lazy-loads the service on first access.
        """
        if self._files_service is None:
            from mcpserver.graph.files_service import FilesService
            self._files_service = FilesService(self.user_client)
        return self._files_service

    @property
    def calendar(self):
        """
        Get the calendar service instance.
        Lazy-loads the service on first access.
        """
        if self._calendar_service is None:
            from mcpserver.graph.calendar_service import CalendarService
            self._calendar_service = CalendarService(self.user_client)
        return self._calendar_service

    async def get_user(self, all_properties: bool = False):
        # Only request specific properties using $select
        if all_properties:
            user = await self.user_client.me.get()
        else:
            query_params = UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
                select=['displayName', 'mail', 'userPrincipalName']
            )

            request_config = RequestConfiguration(
                query_parameters=query_params
            )

            user = await self.user_client.me.get(request_configuration=request_config)
        return user

