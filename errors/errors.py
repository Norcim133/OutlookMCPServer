class CriticalInitializationError(Exception):
    pass

class OrgNotFoundError(Exception):
    pass

class ProjectNotFoundError(Exception):
    pass

class IndexRetrievalError(Exception):
    pass

class MissingValueError(ValueError): # For input validation errors
    pass

class APIError(Exception):
    pass

class LlamaCloudClientInitError(Exception):
    pass

class LlamaOperationFailedError(APIError):
    pass