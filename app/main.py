from fastapi import FastAPI

from app.config import Settings
from app.routes import router

settings = Settings()


def get_app() -> FastAPI:
    app = FastAPI(**settings.fastapi_kwargs)

    app.include_router(router)

    return app


app = get_app()
