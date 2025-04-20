import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from config import AuthMiddleware, generic_error_handler, http_error_handler, lifespan
from settings import BASE_ROUTE, STATIC_DIR
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
    
    os.makedirs(STATIC_DIR, exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    origins = [
        "http://localhost:3000",
        "https://website-git-main-aakash-s45s-projects.vercel.app/",
        "*"
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
