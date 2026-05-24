"""
AWS Lambda entry point for Tender Engine API (af-south-1 / Cape Town).

This module wraps the FastAPI application with Mangum, the standard adapter
for running ASGI applications (FastAPI, Starlette) inside an AWS Lambda
function via API Gateway (REST API, HTTP API, or Function URL).

How it works:
  - Mangum receives the raw API Gateway event dict from the Lambda runtime.
  - It translates that event into an ASGI scope, feeds it through the
    FastAPI application, and returns the HTTP response.
  - Everything — auth middleware, CORS, error handlers, routes, database
    init — runs exactly as it does under uvicorn.

Usage on Lambda:
  The Lambda function handler must point to this module's `handler`
  function. In your SAM / CDK / Serverless Framework / manual AWS config:

      Handler: api.lambda_handler.handler

  On the first invocation Mangum lazily builds its ASGI adapter. The
  `app` object is imported from `api.main` so all existing startup logic
  (init_db, etc.) is preserved.

Usage locally (unchanged):
  uvicorn api.main:app --reload     # still works exactly as before
"""

from mangum import Mangum
from api.main import app

# ---------------------------------------------------------------------------
# Mangum handler — the single entry point Lambda calls per-request.
#
# API Gateway modes:
#   * "http"   – for API Gateway HTTP API (v2)  ← RECOMMENDED for new APIs
#   * "rest"   – for API Gateway REST API (v1)
#   * None     – auto-detect (ok for most cases, but explicit is clearer)
#
# Cape Town (af-south-1) recommendation:
#   Use API Gateway HTTP API + Lambda Function URL. Both are cheaper and
#   lower-latency than REST API. The "http" mode is the natural fit.
#
# lifespan="off":
#   Lambda does NOT support long-running lifespan contexts. FastAPI's
#   startup/shutdown events still fire on first invocation because Mangum
#   creates a new ASGI instance per cold start. Setting lifespan="off"
#   avoids confusing lifespan protocol interactions in the Lambda environ.
#   The DB init (init_db) runs synchronously via @app.on_event("startup")
#   which Mangum handles correctly on cold start.
# ---------------------------------------------------------------------------
handler = Mangum(app, lifespan="off")