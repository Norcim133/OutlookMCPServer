from settings import AzureSettings
from mcpserver.graph import Graph
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional, AsyncIterator
from mcp.server.fastmcp import FastMCP


@dataclass
class AppContext:
    graph: Graph


@asynccontextmanager
async def app_lifespan(server: Optional[FastMCP]) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""

    settings = AzureSettings()

    graph = Graph(settings)

    try:
        yield AppContext(graph=graph)
    finally:
        #Add any cleanup if needed
        pass
