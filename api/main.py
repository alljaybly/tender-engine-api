from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title='Tender Engine API',
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True
    }
)

# ✅ Serve static files (CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

from .utils import error_response
from .routes import process as process_route
from .routes import status as status_route
from .routes import health as health_route
from .routes import payments as payments_route
from .services.user_store import get_user_by_api_key, reserve_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('tender-engine-api')

# -------------------------------
# OPENAPI SECURITY
# -------------------------------
original_openapi = app.openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = original_openapi()
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key"
        }
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# -------------------------------
# ERROR HANDLERS
# -------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else 'Request failed'
    code = 'http_error'
    if exc.status_code == 404:
        code = 'not_found'
    elif exc.status_code == 401:
        code = 'unauthorized'
    elif exc.status_code == 403:
        code = 'forbidden'
    elif exc.status_code == 429:
        code = 'rate_limit_exceeded'
        message = 'Too many requests'
    return error_response(code, message, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    message = exc.errors()[0].get('msg', 'Invalid request') if exc.errors() else 'Invalid request'
    return error_response('validation_error', message, 422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("[ERROR] Unhandled exception: %s", exc)
    return error_response('internal_server_error', 'Internal server error', 500)

# -------------------------------
# AUTH MIDDLEWARE
# -------------------------------
@app.middleware('http')
async def require_api_key(request: Request, call_next):

    path = request.url.path

    # ✅ PUBLIC ROUTES (NO API KEY)
    if (
        path == "/" or
        path.startswith("/static") or
        path.startswith("/docs") or
        path.startswith("/redoc") or
        path.startswith("/openapi") or
        path.startswith("/health") or
        path.startswith("/favicon")
    ):
        return await call_next(request)

    # 🚀 DEV BYPASS (so YOU are never blocked)
    api_key = request.headers.get('x-api-key')
    if api_key == "test_key_123":
        request.state.user = {"user_id": "dev", "plan": "unlimited"}
        return await call_next(request)

    # 🔐 NORMAL SECURITY
    if not api_key:
        return error_response('unauthorized', 'API key required', 401)

    user = get_user_by_api_key(api_key)
    if not user:
        return error_response('unauthorized', 'Invalid API key', 401)

    reservation = reserve_request(api_key, user.get('plan'))
    if not reservation.get('allowed'):
        code = reservation.get('code', 'request_rejected')
        status_code = 429 if code == 'rate_limit_exceeded' else 403

        if code == 'plan_expired':
            message = 'Plan expired'
        elif code == 'usage_limit_exceeded':
            message = 'Usage limit exceeded'
        elif code == 'rate_limit_exceeded':
            message = 'Too many requests'
        else:
            message = 'Plan invalid'

        return error_response(code, message, status_code)

    user['usage'] = reservation.get('usage', {})
    request.state.user = user

    return await call_next(request)

# -------------------------------
# API ROUTES
# -------------------------------
from .routes import router as api_router
app.include_router(api_router, prefix="/api")

# -------------------------------
# FRONTEND (INDEX.HTML)
# -------------------------------
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")