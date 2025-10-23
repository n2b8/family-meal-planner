import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import Base, engine

@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.mark.asyncio
async def test_register_login_me_logout_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register
        r = await ac.post("/auth/register", json={"email": "alice@example.com", "password": "SuperSecret1"})
        assert r.status_code == 200
        uid = r.json()["id"]
        assert uid > 0

        # Login
        r = await ac.post("/auth/login", json={"email": "alice@example.com", "password": "SuperSecret1"})
        assert r.status_code == 200
        assert any(c.startswith("fmp_session=") for c in r.headers.get_list("set-cookie"))

        # Keep cookie
        cookies = r.cookies

        # /me works
        r = await ac.get("/me", cookies=cookies)
        assert r.status_code == 200
        assert r.json()["email"] == "alice@example.com"

        # Logout clears session
        r = await ac.post("/auth/logout", cookies=cookies)
        assert r.status_code == 200

        # Access /me without cookie should fail
        r = await ac.get("/me")
        assert r.status_code == 401
