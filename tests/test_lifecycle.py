import pytest

from asas import AsasAsyncClient, AsasClient


class FakeSyncEngine:
    def __init__(self) -> None:
        self.closed = False

    def send(self, request):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def close(self) -> None:
        self.closed = True


class FakeAsyncEngine:
    def __init__(self) -> None:
        self.closed = False

    async def asend(self, request):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def aclose(self) -> None:
        self.closed = True


def test_with_closes_engine() -> None:
    fake = FakeSyncEngine()
    client = AsasClient("http://x", engine=fake)
    with client as c:
        assert c is client
        assert not fake.closed
    assert fake.closed


def test_close_closes_engine() -> None:
    fake = FakeSyncEngine()
    AsasClient("http://x", engine=fake).close()
    assert fake.closed


@pytest.mark.asyncio
async def test_async_with_closes_engine() -> None:
    fake = FakeAsyncEngine()
    client = AsasAsyncClient("http://x", engine=fake)
    async with client as c:
        assert c is client
        assert not fake.closed
    assert fake.closed


@pytest.mark.asyncio
async def test_aclose_closes_engine() -> None:
    fake = FakeAsyncEngine()
    await AsasAsyncClient("http://x", engine=fake).aclose()
    assert fake.closed


def test_engine_closed_even_when_body_raises() -> None:
    fake = FakeSyncEngine()
    with pytest.raises(ValueError):
        with AsasClient("http://x", engine=fake):
            raise ValueError("boom")
    assert fake.closed
