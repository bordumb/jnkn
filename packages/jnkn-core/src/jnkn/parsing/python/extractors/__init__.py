"""
Python Environment Variable Extractors.

This package provides a suite of extractors for detecting environment variable
usage across different Python patterns and frameworks:

- **StdlibExtractor** (100): os.getenv, os.environ patterns
- **PydanticExtractor** (90): Pydantic BaseSettings and Field(env=...)
- **ClickTyperExtractor** (80): Click/Typer envvar option parameters
- **DotenvExtractor** (70): python-dotenv library patterns
- **DjangoExtractor** (60): django-environ patterns
- **AirflowExtractor** (50): Apache Airflow Variable.get()
- **EnvironsExtractor** (40): environs library patterns
- **HeuristicExtractor** (10): Fallback heuristic detection

Extractors are sorted by priority (highest first) when registered.

Usage:
    ```python
    from jnkn.parsing.python.extractors import get_extractors

    extractors = get_extractors()
    for extractor in extractors:
        if extractor.can_extract(ctx):
            yield from extractor.extract(ctx)
    ```
"""

from typing import List

from .airflow import AirflowExtractor
from .base import BaseExtractor
from .click_typer import ClickTyperExtractor
from .django import DjangoExtractor
from .dotenv import DotenvExtractor
from .environs import EnvironsExtractor
from .heuristic import HeuristicExtractor
from .pydantic import PydanticExtractor
from .stdlib import StdlibExtractor

# Registry of extractor classes ordered by priority (highest first)
EXTRACTORS: List[type[BaseExtractor]] = [
    StdlibExtractor,  # 100
    PydanticExtractor,  # 90
    ClickTyperExtractor,  # 80
    DotenvExtractor,  # 70
    DjangoExtractor,  # 60
    AirflowExtractor,  # 50
    EnvironsExtractor,  # 40
    HeuristicExtractor,  # 10
]

__all__ = [
    # Base class
    "BaseExtractor",
    # Individual extractors
    "StdlibExtractor",
    "PydanticExtractor",
    "ClickTyperExtractor",
    "DotenvExtractor",
    "DjangoExtractor",
    "AirflowExtractor",
    "EnvironsExtractor",
    "HeuristicExtractor",
    # Registry
    "EXTRACTORS",
    # Factory function
    "get_extractors",
]


def get_extractors() -> List[BaseExtractor]:
    """
    Factory function to instantiate and sort extractors.

    Creates instances of all registered extractor classes and sorts
    them by priority (highest first).

    Returns:
        List[BaseExtractor]: Sorted list of extractor instances.

    Example:
        ```python
        extractors = get_extractors()
        # Returns: [StdlibExtractor(), PydanticExtractor(), ...]
        # Sorted by priority: 100, 90, 80, 70, 60, 50, 40, 10
        ```
    """
    instances = [cls() for cls in EXTRACTORS]
    return sorted(instances, key=lambda e: -e.priority)
