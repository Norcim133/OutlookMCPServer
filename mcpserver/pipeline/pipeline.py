from llama_cloud.client import LlamaCloud, AsyncLlamaCloud
import os
from typing import Optional
import json
import logging


class PipelineController:
    def __init__(self):
        self.client = AsyncLlamaCloud(token=os.getenv("LLAMA_CLOUD_API_KEY"))
        self.sync_client = LlamaCloud(token=os.getenv("LLAMA_CLOUD_API_KEY"))
        self._organization_id = self._get_org_id()
        self._data_source = None

    def _get_org_id(self):
        org_object = self.sync_client.organizations.get_default_organization()
        org_id = org_object.id
        return org_id

    @property
    def organization_id(self):
        return self._organization_id

    async def list_llama_projects(self):
        if self.organization_id is None:
            return "Must set llama_org_id"
        projects = await self.client.projects.list_projects(organization_id=self.organization_id)
        result = ""

        if projects:
            result += "Existing LlamaCloud Projects:\n"
            project_dict = {}
            for project in projects:
                project_dict[project.name] = project.id
                result += json.dumps(project_dict, indent=4)
        else:
            logging.warning("LIST_LLAMA_PROJECTS: No projects found")
            result += "No projects found.\n"

        return result

    async def list_llama_indices(self, llama_project_id: str) -> str:
        """List existing LlamaCloud indices/pipelines"""

        if llama_project_id is None:
            logging.warning("LIST_LLAMA_INDICES: No llama_project_id")
            return "No llama_project_id given"
        pipelines = await self.client.pipelines.search_pipelines(project_id=llama_project_id)

        result = ""

        if pipelines:
            result += "Existing LlamaCloud indices:\n"
            pipeline_dict = {}
            for pipeline in pipelines:
                pipeline_dict[pipeline.name] = pipeline.id
                result += json.dumps(pipeline_dict, indent=4)
        else:
            logging.warning("LIST_LLAMA_INDICES: No pipelines found")
            result += "No pipelines found.\n"

        return result

    async def get_data_sources(self):
        response = await self.client.data_sources.list_data_sources(organization_id=self.organization_id)
        if len(response) == 0:
            return "No data sources found"

        result = ""

        result += "Existing LlamaCloud data sources:\n"
        source_dict = {}
        for source in response:
            source_dict[source.name] = source.id
            result += json.dumps(source_dict, indent=4)
        return result

    async def create_data_source(self):
        data_sources = await self.get_data_sources()
        if data_sources != "No data sources found":
            return f"Data source already exists. Returning name and id: \n{data_sources}"

        try:
            from llama_cloud.types import CloudSharepointDataSource

            site_name = os.getenv('SHAREPOINT_SITE_NAME')
            client_id = os.getenv('AZURE_CLIENT_ID')
            client_secret = os.getenv('AZURE_CLIENT_SECRET')
            tenant_id = os.getenv('AZURE_TENANT_ID')
            folder_path = os.getenv('TARGET_FOLDER_NAME')
            folder_id = os.getenv('TARGET_FOLDER_ID')
            name = os.getenv('DATA_SOURCE_NAME')

            from llama_cloud.types import CloudSharepointDataSource

            ds = {
                'name': name,
                'source_type': 'MICROSOFT_SHAREPOINT',
                'component': CloudSharepointDataSource(
                    site_name=site_name,
                    folder_path=folder_path,
                    client_id=client_id,
                    client_secret=client_secret,
                    tenant_id=tenant_id,
                    folder_id=folder_id,
                )
            }
            data_source = self.sync_client.data_sources.create_data_source(request=ds)

            return data_source
        except Exception as e:
            return f"Possible .env variables not set with Azure credentials required for data source: {e}"

    async def get_data_source(self, data_source_id: str = os.getenv("DATA_SOURCE_ID")):
        if data_source_id is None:
            return "You must supply data_source_id to get data_source"

        data_source = await self.client.data_sources.get_data_source(data_source_id=data_source_id)

        if data_source is None:
            return "Failed to get data source"

        return data_source

