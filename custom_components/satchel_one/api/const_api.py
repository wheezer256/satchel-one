"""Satchel One API constants and configuration.

This module contains all HTTP-level API configuration: endpoints, headers,
host, and client credentials. It is the single source of truth for API shape.

All HTTP requests originate from api/client.py, which consumes these constants.
"""

API_HOST = "https://api.satchelone.com/api"

# OAuth token endpoint. NOTE: this lives at the domain ROOT, not under /api —
# posting to /api/oauth/token hits a CDN-fronted route that never authenticates
# (verified against a live browser capture, 2026-06-05). Used for both the
# password-grant login and refresh.
OAUTH_TOKEN_URL = "https://api.satchelone.com/oauth/token"

# Web-client credentials. These are NOT user secrets: they are the global
# values Satchel bakes into its public web frontend (and are published openly
# in the smhw-api reference library). The integration must send them as query
# params on every token request.
CLIENT_ID = "55283c8c45d97ffd88eb9f87e13f390675c75d22b4f2085f43b0d7355c1f"  # gitleaks:allow (public Satchel web-client id; see comment above)
CLIENT_SECRET = "c8f7d8fcd0746adc50278bc89ed6f004402acbbf4335d3cb12d6ac6497d3"  # gitleaks:allow (public Satchel web-client secret; see comment above)

# Versioned vendor media type used by EVERY Satchel One API call. Plain
# `application/json` gets some endpoints (e.g. /students) bounced to an HTML
# error page (HTTP 400); the maintained smhw-api client uses this version for
# all requests — authenticated and not. Bump if Satchel rolls the version.
API_ACCEPT = "application/smhw.v2021.5+json"

# Headers for the unauthenticated login + school-search calls (smhw-api style).
BASE_HEADERS = {
    "Accept": API_ACCEPT,
    "Connection": "keep-alive",
}

# Default headers for authenticated (data) requests: same versioned Accept,
# plus X-Platform: web (sent by the real web client).
DEFAULT_HEADERS = {
    "Accept": API_ACCEPT,
    "X-Platform": "web",
}

# Endpoints (relative to API_HOST)
ENDPOINT_SCHOOL_SEARCH = "/public/school_search"
ENDPOINT_STUDENTS = "/students"
ENDPOINT_TODOS = "/todos"
ENDPOINT_STUDENT_PRAISES = "/student_praises"
ENDPOINT_STUDENT_PRAISE_SUMMARY = "/student_praise_summaries/{student_id}"
ENDPOINT_DETENTIONS = "/detentions"

# Query parameter recommendations
# Note: The CDN caches stale 400s, so append a cache-buster to bypass:
#   &_cb=TIMESTAMP
# Example: /todos?student_id=123&_cb=1717485632000
