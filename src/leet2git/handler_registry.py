"""Lazy file-handler registry."""

from leet2git.default_handler import DefaultHandler
from leet2git.file_handler import FileHandler
from leet2git.python_handler import PythonHandler


def get_handler_type(language: str) -> type[FileHandler]:
    """Return the file-handler class for a language."""
    handlers: tuple[type[FileHandler], ...] = (PythonHandler,)
    handler_map = {
        handled_language: handler for handler in handlers for handled_language in handler.languages
    }
    return handler_map.get(language.lower(), DefaultHandler)
