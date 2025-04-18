from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from config import AuthMiddleware, generic_error_handler, http_error_handler, lifespan
from settings import BASE_ROUTE
from routes import api_v1


def get_app() -> FastAPI:
    app = FastAPI(
        docs_url=f"{BASE_ROUTE}/docs",
        redoc_url=f"{BASE_ROUTE}/redocs",
        openapi_url=f"{BASE_ROUTE}/openapi.json",
        title="Events service API documentation",
        version="1.0.0",
        lifespan=lifespan,
    )

    origins = [
        "http://localhost:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthMiddleware)

    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    app.include_router(api_v1, tags=["events"], prefix=BASE_ROUTE)

    return app


app = get_app()
