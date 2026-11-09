"""Parameter markers: Header, Cookie, Form, File and Body(exclude_unset=True).

Runs offline: respx plays the server and echoes back what it received.
"""

from typing import Annotated, Any, Dict, Optional

import httpx
import respx
from pydantic import BaseModel

from asas import AsasClient, Body, Cookie, File, Form, Header, Path, get, patch, post

BASE_URL = "https://api.example.com"


class UserPatch(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None


class User(BaseModel):
    id: int
    name: str
    bio: Optional[str] = None


class UploadResult(BaseModel):
    filename: str
    size: int


class FilesClient(AsasClient):
    @post("/upload")
    def upload(
        self,
        document: Annotated[bytes, File()],
        title: Annotated[str, Form()],
        api_version: Annotated[str, Header()],
    ) -> UploadResult:
        """Multipart upload: a file part, a form field and a header.

        ``api_version`` is sent as the ``Api-Version`` header.
        """
        raise NotImplementedError

    @get("/me")
    def whoami(self, session: Annotated[str, Cookie()]) -> Dict[str, Any]:
        """``session`` is sent as a cookie."""
        raise NotImplementedError

    @patch("/users/{user_id}")
    def update_user(
        self,
        user_id: Annotated[int, Path()],
        changes: Annotated[UserPatch, Body(exclude_unset=True)],
    ) -> User:
        """Only the fields set on ``changes`` are sent (a true partial update)."""
        raise NotImplementedError


def main() -> None:
    with (
        FilesClient(base_url=BASE_URL) as client,
        respx.mock(base_url=BASE_URL) as server,
    ):
        upload_route = server.post("/upload").mock(
            return_value=httpx.Response(200, json={"filename": "notes.txt", "size": 5})
        )
        me_route = server.get("/me").mock(
            return_value=httpx.Response(200, json={"user": "ada"})
        )
        patch_route = server.patch("/users/7").mock(
            return_value=httpx.Response(200, json={"id": 7, "name": "Ada", "bio": "hi"})
        )

        result = client.upload(
            document=b"hello", title="My notes", api_version="2024-01"
        )
        sent = upload_route.calls[0].request
        print(f"upload -> {result}")
        print(f"  Api-Version header: {sent.headers['Api-Version']}")
        print(f"  content type: {sent.headers['Content-Type'].split(';')[0]}")

        print(f"whoami -> {client.whoami(session='abc123')}")
        print(f"  Cookie header: {me_route.calls[0].request.headers['Cookie']}")

        user = client.update_user(user_id=7, changes=UserPatch(bio="hi"))
        print(f"update_user -> {user}")
        print(f"  PATCH body: {patch_route.calls[0].request.content.decode()}")


if __name__ == "__main__":
    main()
