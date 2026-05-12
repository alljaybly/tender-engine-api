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
# DATABASE INIT
# -------------------------------
from .services.database import init_db

@app.on_event("startup")
async def on_startup():
    init_db()
    logger.info("[DB] Database initialized on startup")

# -------------------------------
# OPENAPI SECURITY (supports both ApiKey and Bearer JWT)
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
            "name": "x-api-key",
            "description": "Legacy API key authentication (deprecated, use Bearer JWT)"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer token from /api/auth/login"
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}, {"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# -------------------------------
# JWT AUTH HELPERS (for middleware)
# -------------------------------
from .services.auth import decode_access_token
from .services.database import get_user_by_id_sync, get_api_key_sync

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
# AUTH MIDDLEWARE (dual auth: x-api-key OR Bearer JWT)
# -------------------------------
@app.middleware('http')
async def require_api_key(request: Request, call_next):

    path = request.url.path

    # ✅ PUBLIC ROUTES (NO AUTH REQUIRED)
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

    # 🔐 ATTEMPT 1: Bearer JWT authentication
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        payload = decode_access_token(token)
        if payload is not None:
            user_id = payload.get("sub")
            if user_id is not None:
                user = get_user_by_id_sync(user_id)
                if user and user.get("is_active"):
                    request.state.user = {
                        "user_id": user["email"],
                        "id": user["id"],
                        "email": user["email"],
                        "plan": user.get("plan", "free"),
                        "full_name": user.get("full_name", ""),
                        "auth_method": "jwt",
                    }
                    return await call_next(request)

        # Token was provided but invalid — reject immediately
        return error_response('unauthorized', 'Invalid or expired Bearer token', 401)

    # 🔐 ATTEMPT 2: Legacy API key authentication
    if api_key:
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
        user['auth_method'] = 'api_key'
        request.state.user = user
        return await call_next(request)

    # 🔐 NO AUTHENTICATION PROVIDED
    # Auth routes (register/login) are public -> handled below as they start with /api/auth
    if path.startswith("/api/auth"):
        # Allow auth endpoints to pass without authentication
        # (they handle their own auth via the login/register payloads)
        request.state.user = None
        return await call_next(request)

    return error_response('unauthorized', 'Authentication required. Provide x-api-key header or Bearer token.', 401)

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