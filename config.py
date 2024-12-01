from contextlib import asynccontextmanager
import logging
from typing import Union
import asyncpg
from fastapi import FastAPI, HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from settings import AUTH_TOKEN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"errors": [exc.detail]}, status_code=exc.status_code)


async def generic_error_handler(
    _: Request,
    exc: Union[Exception],
) -> JSONResponse:
    logger.error(exc, exc_info=True)
    return JSONResponse(
        {"errors": "failed"},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(app)

    yield

    await app.db.close()
    logger.info("database connection closed")


async def init_db(app: FastAPI):
    logger.info("initializing database connection")
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        host=DB_HOST,
        database=DB_NAME,
    )
    app.db = conn


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract the Authorization header
        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # Verify the token
        expected_token = AUTH_TOKEN
        if not expected_token:
            raise HTTPException(status_code=500, detail="Server misconfiguration: AUTH_TOKEN is not set")

        if token != f"Bearer {expected_token}":
            raise HTTPException(status_code=401, detail="Invalid or missing token")

        # Proceed to the next handler if authenticated
        response = await call_next(request)
        return response