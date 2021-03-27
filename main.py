import httpx
import typing

from pydantic import BaseSettings

from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles, PathLike
from starlette.types import Scope


class Settings(BaseSettings):
    OSTATIC_BACKEND_ROUTE: str = "http://localhost:8000/auth"
    OSTATIC_BACKEND_CODE: int = 200
    OSTATIC_DIRECTORY: str = "static"
    OSTATIC_HEADER_KEY: str = "Authorization"


class AuthStaticFiles(StaticFiles):
    def __init__(
        self,
        settings,
        *,
        directory: PathLike = None,
        packages: typing.List[str] = None,
        html: bool = False,
        check_dir: bool = True,
    ) -> None:
        self.settings: str = settings
        super().__init__(
            directory=directory, packages=packages, html=html, check_dir=check_dir
        )

    async def check_auth(self, scope: Scope):
        authorization_header = Headers(scope=scope).get(settings.OSTATIC_HEADER_KEY)
        if not authorization_header:
            return False

        async with httpx.AsyncClient() as client:
            try:
                auth_response = await client.get(
                    self.settings.OSTATIC_BACKEND_ROUTE,
                    headers={settings.OSTATIC_HEADER_KEY: authorization_header},
                )
            except Exception:
                return False

        if auth_response.status_code != settings.OSTATIC_BACKEND_CODE:
            return False
        return True

    async def get_response(self, path: str, scope: Scope) -> Response:
        is_authorized = await self.check_auth(scope)
        if not is_authorized:
            return PlainTextResponse("Unauthorized")
        return await super().get_response(path, scope)


settings = Settings()
routes = [
    Mount(
        f"/{settings.OSTATIC_DIRECTORY}",
        app=AuthStaticFiles(
            settings=settings,
            directory=settings.OSTATIC_DIRECTORY,
        ),
        name=settings.OSTATIC_DIRECTORY,
    ),
]

app = Starlette(routes=routes)
