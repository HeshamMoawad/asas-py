import respx
from httpx import Response as HttpxResponse

from asas import AsasClient, BearerAuth, Response, get


class PublicClient(AsasClient):
    @get("/public", use_auth=False)
    def get_public(self) -> Response:
        raise NotImplementedError

    @get("/private")
    def get_private(self) -> Response:
        raise NotImplementedError


def test_disable_auth_on_endpoint() -> None:
    auth = BearerAuth("secret-token")
    client = PublicClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        public_route = respx_mock.get("/public").mock(return_value=HttpxResponse(200))
        private_route = respx_mock.get("/private").mock(return_value=HttpxResponse(200))

        # Public call should NOT have Authorization header
        assert client.get_public().status_code == 200
        assert "Authorization" not in public_route.calls.last.request.headers

        # Private call SHOULD have Authorization header
        assert client.get_private().status_code == 200
        assert (
            private_route.calls.last.request.headers["Authorization"]
            == "Bearer secret-token"
        )
