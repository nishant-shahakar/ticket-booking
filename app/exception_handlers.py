"""
Exception handlers for FastAPI application.
Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import ApplicationException


def register_exception_handlers(app: FastAPI):
    """Register exception handlers for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(ApplicationException)
    async def application_exception_handler(request: Request, exc: ApplicationException):
        """Handle application exceptions.
        
        Args:
            request: HTTP request
            exc: ApplicationException raised
            
        Returns:
            JSON response with error details and appropriate status code
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "code": exc.code,
                    "status": "error",
                }
            },
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle validation errors.
        
        Args:
            request: HTTP request
            exc: ValueError raised
            
        Returns:
            JSON response with 400 status
        """
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": str(exc),
                    "code": "VALIDATION_ERROR",
                    "status": "error",
                }
            },
        )
