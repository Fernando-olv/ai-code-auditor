"""Logging bootstrap."""

import logging
import sys


def setup_logging(level: str) -> None:
    """Configure root logger once (stderr, simple format)."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"),
        )
        root.addHandler(handler)
