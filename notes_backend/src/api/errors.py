from __future__ import annotations

from fastapi import HTTPException, status


class ApiError(HTTPException):
    """Base API error."""


def not_found(detail: str) -> ApiError:
    """Create a 404 error."""
    return ApiError(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def conflict(detail: str) -> ApiError:
    """Create a 409 error."""
    return ApiError(status_code=status.HTTP_409_CONFLICT, detail=detail)


def bad_request(detail: str) -> ApiError:
    """Create a 400 error."""
    return ApiError(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
