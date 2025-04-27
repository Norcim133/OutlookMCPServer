import functools
import logging
from typing import Callable


def requires_graph_auth(func: Callable) -> Callable:
    """Decorator that handles Microsoft Graph authentication before executing the wrapped function"""

    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        logging.info("Checking for graph authentication")

        # Get the settings from the context
        auth_settings = ctx.request_context.lifespan_context.settings

        # Check if we already have a client
        graph_client = auth_settings.get_user_client()

        if graph_client is not None:
            # We're authenticated, proceed with the function
            logging.info("Already authenticated, proceeding with function")
            ctx.request_context.lifespan_context.graph.user_client = graph_client
            return await func(ctx, *args, **kwargs)
        else:
            # We need to authenticate - return instructions
            logging.info("Authentication required, returning instructions")
            try:
                auth_message = auth_settings.get_auth_instructions()
                return auth_message
            except Exception as e:
                logging.error(f"Authentication error: {str(e)}")
                return f"Error during authentication: {str(e)}"

    return wrapper
