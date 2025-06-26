"""Pytest configuration for Letrade_v1 tests."""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]