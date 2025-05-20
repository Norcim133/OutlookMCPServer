# mcpserver/graph/files_service.py
from msgraph import GraphServiceClient
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.models.drive_item import DriveItem
import json


class FilesService:
    """Service for OneDrive file-related operations using Microsoft Graph API"""

    def __init__(self, user_client: GraphServiceClient):
        self.user_client = user_client

    async def list_followed_sites(self):
        """
        Retrieves a list of SharePoint sites that the current user is following,
        returning their display names, IDs, and web URLs.
        """
        try:

            followed_sites_response = await self.user_client.me.followed_sites.get()

            if not followed_sites_response or not followed_sites_response.value:
                return "No sites are currently being followed by the user."

            sites_info = []
            for site_obj in followed_sites_response.value:

                site_id = getattr(site_obj, 'id', None)
                display_name = getattr(site_obj, 'display_name', 'Unknown Site Name')
                web_url = getattr(site_obj, 'web_url', None)

                if site_id:  # Only include sites that have an ID
                    sites_info.append({
                        "id": site_id,
                        "display_name": display_name,
                        "web_url": web_url
                    })

            if not sites_info:
                return "Followed sites were found, but essential information (like ID) is missing."

            return sites_info
        except Exception as e:
            import traceback  # For server-side logging during development
            traceback.print_exc()
            return f"Error retrieving followed sites: {str(e)}"

    async def get_site_drives(self, site_id: str):
        """
        Retrieves the list of drives (document libraries) for a given SharePoint site ID.

        Args:
            site_id: The ID of the SharePoint site (e.g., 'netorgft16432671.sharepoint.com,d79...').

        Returns:
            A list of drive information (id, name, webUrl) or an error message.
        """
        if not site_id:
            return "Error: A site_id must be provided to get its drives."
        try:
            site_drives_response = await self.user_client.sites.by_site_id(site_id).drives.get()

            if not site_drives_response or not site_drives_response.value:
                return f"No drives (document libraries) found for site ID '{site_id}'."

            drives_info = []
            for drive_obj in site_drives_response.value:
                drive_id = getattr(drive_obj, 'id', None)
                drive_name = getattr(drive_obj, 'name', 'Unknown Drive Name')
                drive_web_url = getattr(drive_obj, 'web_url', None)

                if drive_id:  # Only include drives that have an ID
                    drives_info.append({
                        "id": drive_id,
                        "name": drive_name,
                        "web_url": drive_web_url
                    })

            if not drives_info:
                return f"Drives were found for site ID '{site_id}', but essential information (like ID) is missing."

            return drives_info
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error retrieving drives for site ID '{site_id}': {str(e)}"

    def _get_drive_item_meta_data(self, drive_item_list: DriveItem):
        items_list = []
        for item in drive_item_list.value:
            item_type = "Folder" if getattr(item, 'folder', None) else (
                "File" if getattr(item, 'file', None) else "Unknown")
            items_list.append({
                "id": getattr(item, 'id', None),
                "name": getattr(item, 'name', 'Unknown Item Name'),
                "type": item_type,
                "size": getattr(item, 'size', 0),  # Size in bytes
                "web_url": getattr(item, 'web_url', None),
                "last_modified_date_time": str(getattr(item, 'last_modified_date_time', None))
                # Convert datetime to string
            })

        return items_list

    async def list_drive_root_items(self, drive_id: str):
        """
        Lists files and folders in the root of a specific drive (document library).

        Args:
            drive_id: The ID of the drive.

        Returns:
            A list of item information (id, name, type, size, webUrl, lastModifiedDateTime) or an error message.
        """
        if not drive_id:
            return "Error: A drive_id must be provided to list its root items."
        try:

            root_drive_item = await self.user_client.drives.by_drive_id(drive_id).root.get()

            drive_item_id = getattr(root_drive_item, 'id', None)

            root_items_response = await self.user_client.drives.by_drive_id(drive_id).items.by_drive_item_id(
                drive_item_id).children.get()

            if not root_items_response or not root_items_response.value:
                return f"No items found in the root of drive ID '{drive_id}'."

            return self._get_drive_item_meta_data(root_items_response)
        except Exception as e:
            return f"Error listing root items for drive ID '{drive_id}': {str(e)}"

    async def list_drive_folder_items(self, drive_id: str, folder_item_id: str):
        """
        Lists files and folders within a specific folder in a drive.

        Args:
            drive_id: The ID of the drive.
            folder_item_id: The ID of the folder (which is a DriveItem ID).

        Returns:
            A list of item information (id, name, type, size, webUrl, lastModifiedDateTime) or an error message.
        """
        if not drive_id:
            return "Error: A drive_id must be provided."
        if not folder_item_id:
            return "Error: A folder_item_id must be provided."

        try:

            folder_children_response = await self.user_client.drives.by_drive_id(drive_id).items.by_drive_item_id(
                folder_item_id).children.get()

            if not folder_children_response or not folder_children_response.value:
                # It's normal for a folder to be empty, so this might not be an "error" for the LLM
                return f"No items found in folder ID '{folder_item_id}' within drive ID '{drive_id}'. (Folder might be empty)"

            return self._get_drive_item_meta_data(folder_children_response)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error listing items in folder ID '{folder_item_id}' for drive ID '{drive_id}': {str(e)}"

    async def get_organization_id(self):
        org = await self.user_client.organization.get()
        org_id = org.value[0].id
        return org_id

    async def get_site_id_from_user(self, site_index: int = 0):
        try:

            followed_sites_response = await self.user_client.me.followed_sites.get()

            if not followed_sites_response or not followed_sites_response.value or len(
                    followed_sites_response.value) <= site_index:
                return f"Error: Could not find followed site at index {site_index}."

            return followed_sites_response.value[0].id
        except Exception as e:
            return f"Error retrieving followed sites: {str(e)}"

    async def get_user_drives(self):
        try:
            drive_list = await self.user_client.me.drives.get()
            return drive_list.value
        except Exception as e:
            return f"Error retrieving user drives: {str(e)}"

    async def get_user_drive(self):
        try:
            drive_list = await self.user_client.me.drive.get()
            return drive_list
        except Exception as e:
            return f"Error retrieving user drive: {str(e)}"

    async def get_user_drive_id(self):
        try:
            drive = await self.get_user_drive()
            drive_id = drive.id
            return drive_id
        except Exception as e:
            return f"Error retrieving user drive ID: {str(e)}"

    async def get_root_drive_item(self):
        try:
            drive_id = await self.get_user_drive_id()
            result = await self.user_client.drives.by_drive_id(drive_id).root.get()
            return result
        except Exception as e:
            return f"Error retrieving root drive item: {str(e)}"

    async def get_root_drive_item_id_for_user(self):
        try:
            drive_item = await self.get_root_drive_item()
            drive_item_id = drive_item.id
            return drive_item_id
        except Exception as e:
            return f"Error retrieving root drive item ID: {str(e)}"


    async def get_folders_and_files_from_drive_item(self, drive_id: str, drive_item_id: str):
        try:
            result = await self.user_client.drives.by_drive_id(drive_id).items.by_drive_item_id(
                drive_item_id).children.get()

            # Convert DriveItem objects to dictionaries
            files_info = []
            for item in result.value:
                # Extract only the key information we want to display
                item_info = {
                    "id": item.id,
                    "name": item.name,
                    "type": "Folder" if hasattr(item, "folder") and item.folder else "File",
                    "size": item.size,
                    "web_url": item.web_url,
                    "created_by": item.created_by.user.display_name if item.created_by and item.created_by.user else "Unknown",
                    "created_date": item.created_date_time.isoformat() if item.created_date_time else None,
                    "last_modified_date": item.last_modified_date_time.isoformat() if item.last_modified_date_time else None
                }

                # Add folder-specific properties
                if hasattr(item, "folder") and item.folder:
                    item_info["child_count"] = item.folder.child_count

                # Add file-specific properties
                if hasattr(item, "file") and item.file:
                    item_info["mime_type"] = item.file.mime_type if hasattr(item.file, "mime_type") else None

                files_info.append(item_info)

            # Now convert to JSON
            return json.dumps(files_info, indent=4)
        except Exception as e:
            return f"Error retrieving files: {str(e)}"

    async def search_my_drive(self, query: str, drive_id: str):
        """
        Search for files and folders in the user's OneDrive

        Args:
            query: Search term to find files and folders
            drive_id: Drive ID

        Returns:
            Search results from OneDrive
        """
        try:


            # Create request configuration with query parameters
            from kiota_abstractions.base_request_configuration import RequestConfiguration

            request_config = RequestConfiguration()
            request_config.query_parameters = {
                "$select": "name,id,webUrl,size,file,folder,parentReference"
            }

            # Perform the search
            search_results = await self.user_client.drives.by_drive_id(drive_id).search_with_q("{query}").get()

            # Format the results nicely
            result = f"Search results for '{query}':\n\n"

            if search_results and hasattr(search_results, 'value') and search_results.value:
                for i, item in enumerate(search_results.value, 1):
                    result += f"{i}. {item.name}\n"

                    # Add type info
                    if hasattr(item, 'folder') and item.folder:
                        result += f"   Type: Folder\n"
                        if hasattr(item.folder, 'child_count'):
                            result += f"   Contains: {item.folder.child_count} items\n"
                    elif hasattr(item, 'file') and item.file:
                        result += f"   Type: File\n"
                        if hasattr(item.file, 'mime_type'):
                            result += f"   MIME Type: {item.file.mime_type}\n"

                    # Add size info
                    if hasattr(item, 'size'):
                        size_kb = item.size / 1024
                        if size_kb < 1024:
                            result += f"   Size: {size_kb:.1f} KB\n"
                        else:
                            size_mb = size_kb / 1024
                            result += f"   Size: {size_mb:.1f} MB\n"

                    # Add URL
                    if hasattr(item, 'web_url'):
                        result += f"   URL: {item.web_url}\n"

                    # Add ID
                    if hasattr(item, 'id'):
                        result += f"   ID: {item.id}\n"

                    result += "\n"
            else:
                result += "No results found."

            return result
        except Exception as e:
            return f"Error searching OneDrive: {str(e)}"

    async def get_drive_root_folder_id(self, drive_id: str):
        """
        Gets the ID of the root folder (DriveItem) for a given drive.
        This ID can be used as a folder_id to read from the root of a drive.

        Args:
            drive_id: The ID of the drive.

        Returns:
            The ID of the root DriveItem or an error message.
        """
        if not drive_id:
            return "Error: A drive_id must be provided."
        try:


            # Get the root DriveItem for the drive
            # GET /drives/{drive-id}/root
            root_item = await self.user_client.drives.by_drive_id(drive_id).root.get()

            if not root_item or not getattr(root_item, 'id', None):
                return f"Could not retrieve the root item ID for drive ID '{drive_id}'."

            return getattr(root_item, 'id')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error getting root folder ID for drive '{drive_id}': {str(e)}"

