"""
Storage adapters for Jnkn.

Provides pluggable persistence backends:
- SQLiteStorage: Production-ready local persistence
- MemoryStorage: Fast ephemeral storage for testing
"""

from .base import StorageAdapter
from .memory import MemoryStorage
from .sqlite import SQLiteStorage

__all__ = ["StorageAdapter", "SQLiteStorage", "MemoryStorage"]
