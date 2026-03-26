class ServiceError(Exception):
    status_code = 400
    default_detail = "Request could not be processed."
    default_code = "service_error"

    def __init__(self, detail=None, code=None):
        self.detail = detail or self.default_detail
        self.code = code or self.default_code
        super().__init__(self.detail)


class NotFoundError(ServiceError):
    status_code = 404
    default_detail = "Requested resource was not found."
    default_code = "not_found"


class AccessDeniedError(ServiceError):
    status_code = 403
    default_detail = "You do not have access to this resource."
    default_code = "access_denied"


class ConflictError(ServiceError):
    status_code = 409
    default_detail = "Resource conflict."
    default_code = "conflict"
