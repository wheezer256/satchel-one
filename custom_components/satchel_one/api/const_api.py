"""Satchel One API constants and configuration.

This module contains all HTTP-level API configuration: endpoints, headers,
host, and client credentials. It is the single source of truth for API shape.

All HTTP requests originate from api/client.py, which consumes these constants.
"""

API_HOST = "https://api.satchelone.com/api"

# Default headers for all requests
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "X-Platform": "web",
}

# Endpoints (relative to API_HOST)
ENDPOINT_AUTH = "/oauth/token"
ENDPOINT_STUDENTS = "/students"
ENDPOINT_TODOS = "/todos"
ENDPOINT_STUDENT_PRAISES = "/student_praises"
ENDPOINT_STUDENT_PRAISE_SUMMARY = "/student_praise_summaries/{student_id}"
ENDPOINT_DETENTIONS = "/detentions"

# Query parameter recommendations
# Note: The CDN caches stale 400s, so append a cache-buster to bypass:
#   &_cb=TIMESTAMP
# Example: /todos?student_id=123&_cb=1717485632000
