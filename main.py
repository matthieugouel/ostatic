import httpx
import os
import typing

from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseSettings
from starlette.applications import Starlette
from starlette.datastructures import Headers, QueryParams
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import (
    FileResponse,
    JSONResponse,
    Response,
)
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette import status
from starlette.types import Scope

PathLike = typing.Union[str, "os.PathLike[str]"]


class NotModifiedResponse(Response):
    NOT_MODIFIED_HEADERS = (
        "cache-control",
        "content-location",
        "date",
        "etag",
        "expires",
        "vary",
    )

    def __init__(self, headers: Headers):
        super().__init__(
            status_code=304,
            headers={
                name: value
                for name, value in headers.items()
                if name in self.NOT_MODIFIED_HEADERS
            },
        )


class Settings(BaseSettings):
    OSTATIC_DIRECTORY: str = "static"
    OSTATIC_TOKEN_EXPIRE: int = 2
    OSTATIC_TOKEN_SECRET_KEY: str = (
        "f3454e667c4ca52d1421832e27749b6a3257a31bbe1978142caabd1c34cfd584"
    )
    OSTATIC_TOKEN_ALGORITHM: str = "HS256"

    OSTATIC_BACKEND_ROUTE: str = "http://localhost:8000/auth"
    OSTATIC_BACKEND_CODE: int = 200

    OSTATIC_CORS_ALLOW_ORIGIN: typing.Optional[str] = None


settings = Settings()


class AuthStaticFiles(StaticFiles):
    async def check_auth(self, scope: Scope) -> bool:
        token = QueryParams(scope["query_string"]).get("token")
        if not token:
            return False
        try:
            payload = jwt.decode(
                token,
                settings.OSTATIC_TOKEN_SECRET_KEY,
                algorithms=[settings.OSTATIC_TOKEN_ALGORITHM],
            )
            username: str = payload.get("sub")
            if username is None:
                return False
        except JWTError:
            return False
        return True

    async def get_response(self, path: str, scope: Scope) -> Response:
        is_authorized = await self.check_auth(scope)
        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )
        return await super().get_response(path, scope)

    def file_response(
        self,
        full_path: PathLike,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        method = scope["method"]
        request_headers = Headers(scope=scope)

        filename = full_path.split("/")[-1]

        response = FileResponse(
            full_path,
            status_code=status_code,
            stat_result=stat_result,
            method=method,
            filename=filename,
        )
        if self.is_not_modified(response.headers, request_headers):
            return NotModifiedResponse(response.headers)
        return response


async def auth_from_backend(auth_header: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                settings.OSTATIC_BACKEND_ROUTE,
                headers={"Authorization": auth_header},
            )
        except Exception:
            return False

    if auth_response.status_code != settings.OSTATIC_BACKEND_CODE:
        return False
    return True


async def create_access_token(
    request: Request, data: dict, expires_delta: typing.Optional[timedelta] = None
):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
    )

    auth_header = request.headers.get("Authorization")
    print(request.headers)
    if not auth_header:
        raise credential_exception

    is_authenticated = await auth_from_backend(auth_header)
    if not is_authenticated:
        raise credential_exception

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=2)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.OSTATIC_TOKEN_SECRET_KEY,
        algorithm=settings.OSTATIC_TOKEN_ALGORITHM,
    )
    return encoded_jwt


async def token(request: Request):
    access_token = await create_access_token(
        request=request,
        data={"sub": "test"},
        expires_delta=timedelta(minutes=settings.OSTATIC_TOKEN_EXPIRE),
    )

    return JSONResponse({"access_token": access_token, "token_type": "bearer"})


routes = [
    Route("/token", token),
    Mount(
        f"/{settings.OSTATIC_DIRECTORY}",
        app=AuthStaticFiles(
            directory=settings.OSTATIC_DIRECTORY,
        ),
        name=settings.OSTATIC_DIRECTORY,
    ),
]

if settings.OSTATIC_CORS_ALLOW_ORIGIN is not None:
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=[settings.OSTATIC_CORS_ALLOW_ORIGIN],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]
else:
    middleware = []


app = Starlette(routes=routes, middleware=middleware)
