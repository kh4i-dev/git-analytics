from typing import Any


class AppException(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "An internal error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class ValidationException(AppException):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "The request is invalid."


class AuthenticationException(AppException):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"
    message = "Authentication is required."


class AuthorizationException(AppException):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to access this resource."


class RepositoryNotFoundException(AppException):
    status_code = 404
    code = "REPOSITORY_NOT_FOUND"
    message = "Repository not found."


class ConflictException(AppException):
    status_code = 409
    code = "SYNC_IN_PROGRESS"
    message = "The requested operation conflicts with the current state."


class GitHubAPIException(AppException):
    status_code = 502
    code = "GITHUB_API_ERROR"
    message = "GitHub API request failed."


GitHubAPIError = GitHubAPIException


class GitHubAuthFailed(GitHubAPIException):
    status_code = 401
    code = "GITHUB_AUTH_FAILED"
    message = "GitHub authentication failed."


class GitHubRateLimitExceeded(GitHubAPIException):
    status_code = 429
    code = "GITHUB_RATE_LIMIT_EXCEEDED"
    message = "GitHub API rate limit exceeded."


class GitHubNotFound(GitHubAPIException):
    status_code = 404
    code = "GITHUB_NOT_FOUND"
    message = "GitHub resource not found."


class GitHubServerError(GitHubAPIException):
    status_code = 502
    code = "GITHUB_SERVER_ERROR"
    message = "GitHub API is unavailable."


class SyncFailedException(AppException):
    status_code = 500
    code = "SYNC_FAILED"
    message = "Repository sync failed."


class DatabaseException(AppException):
    status_code = 500
    code = "DATABASE_ERROR"
    message = "Database operation failed."


class DatabaseIntegrityException(AppException):
    status_code = 409
    code = "DATABASE_CONSTRAINT_VIOLATION"
    message = "Database constraint violation."
