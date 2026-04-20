"""
conftest.py — shared fixtures and test configuration for YapClean tests.
"""
import os
import sys
import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Suppress logging noise during tests
import logging
logging.disable(logging.CRITICAL)
