class WorkflowNotFound(Exception):
    pass


class FileNotFound(Exception):
    pass


class ClientError(Exception):
    pass


class NoAPIKeyError(ClientError):
    pass


class NoBaseURLError(ClientError):
    pass
