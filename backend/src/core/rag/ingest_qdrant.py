#!/usr/bin/env python3
"""Backward-compatible entry point for Qdrant ingest."""

import os
import sys

try:
    from src.core.rag.ingest import main
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.core.rag.ingest import main


if __name__ == "__main__":
    main()
