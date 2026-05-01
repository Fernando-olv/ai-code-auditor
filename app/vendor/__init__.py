"""Concrete adapters for external services (LLM providers, storage backends).

Each subpackage implements one or more ports declared under ``app.ports``.
Services depend only on ports; adapter selection happens in the factories under
``app.services``.
"""
