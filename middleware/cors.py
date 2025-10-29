"""CORS middleware configuration for the FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


class CORSConfig:
    """Configuration for CORS middleware."""

    # Default allowed origins
    DEFAULT_ORIGINS = [
        "http://127.0.0.1:8000",
        "https://demo.odai.chat",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://demo.odai.com",
        "https://odai.com",
        "https://odai.chat",
        "*"
    ]

    @classmethod
    def add_cors_middleware(
        cls,
        app: FastAPI,
        origins: list = None,
        allow_credentials: bool = True,
        allow_methods: list = None,
        allow_headers: list = None
    ) -> None:
        """
        Add CORS middleware to the FastAPI application.

        Args:
            app: The FastAPI application instance
            origins: List of allowed origins (defaults to DEFAULT_ORIGINS)
            allow_credentials: Whether to allow credentials
            allow_methods: List of allowed HTTP methods (defaults to ["*"])
            allow_headers: List of allowed headers (defaults to ["*"])
        """
        if origins is None:
            origins = cls.DEFAULT_ORIGINS

        if allow_methods is None:
            allow_methods = ["*"]

        if allow_headers is None:
            allow_headers = ["*"]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
        )

    @classmethod
    def get_development_origins(cls) -> list:
        """Get origins suitable for development environment.
        
        Returns:
            list: List of allowed origins for development including localhost
        """
        return [
            "http://127.0.0.1:8000",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "https://demo.odai.com",
            "https://odai.com",
            "https://odai.chat",
            "*"
        ]

    @classmethod
    def get_production_origins(cls) -> list:
        """Get origins suitable for production environment.
        
        Returns:
            list: List of allowed origins for production (only official domains)
        """
        return [
            "https://odai.com",
            "https://odai.chat",
        ]
