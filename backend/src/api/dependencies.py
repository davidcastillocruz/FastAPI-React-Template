"""
Shared FastAPI dependencies for the API layer.

This module is a placeholder for cross-cutting dependencies that are
injected into route handlers via `Depends(...)`. Typical examples:

- Authentication and authorization (current user, role checks).
- Rate limiting or throttling.
- Request-scoped context (tenant, locale, correlation id).
- Pagination and sorting defaults.
- Feature flags.

Route-specific dependencies live next to their router. Only put a
dependency here when it is reused by two or more modules, or when it
represents an application-wide concern.
"""