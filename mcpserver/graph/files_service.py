# mcpserver/graph/files_service.py
from msgraph import GraphServiceClient
from kiota_abstractions.base_request_configuration import RequestConfiguration


class FilesService:
    """Service for OneDrive file-related operations using Microsoft Graph API"""

    def __init__(self, user_client: GraphServiceClient):
        self.user_client = user_client

    async def search_files(self, query: str, top: int = 10):
        """
        Search for files in OneDrive by filename

        Args:
            query: Search term to find in filenames
            top: Maximum number of results to return

        Returns:
            Collection of matching files
        """
        # Create request configuration with query parameters
        request_config = RequestConfiguration()

        # Add query parameters for search
        request_config.query_parameters = {
            "$search": f'"{query}"',  # Quoted search term
            "$top": top,
            "$select": "id,name,webUrl,createdDateTime,lastModifiedDateTime,size,folder,file"
        }

        # Perform the search in the user's drive
        results = await self.user_client.me.drive.get(request_configuration=request_config)


        return results