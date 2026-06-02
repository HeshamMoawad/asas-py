from typing import Any, Dict

from asas import AsasClient, BasicAuth, BearerAuth, Response, get


class ProtectedClient(AsasClient):
    @get("/protected")
    def get_data(self, response: Response) -> Dict[str, Any]:
        return response.json()  # type: ignore[no-any-return]


def main() -> None:
    # Example 1: Basic Auth
    basic_auth = BasicAuth("username", "password")
    client1 = ProtectedClient(base_url="https://httpbin.org", auth=basic_auth)
    # response = client1.get_data() # This would work if the URL was correct
    print(f"Client 1 auth: {type(client1.auth).__name__}")

    # Example 2: Bearer Token
    token_auth = BearerAuth("your-secret-token")
    client2 = ProtectedClient(base_url="https://api.example.com", auth=token_auth)
    print(f"Client 2 auth: {type(client2.auth).__name__}")


if __name__ == "__main__":
    main()
