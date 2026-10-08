"""Compatibility initializer for the app package.

This module mirrors the package-level API for the underscore-named import path so
legacy or typoed imports continue to work without changing the real package.
"""

from app import create_app

__all__ = ["create_app"]
