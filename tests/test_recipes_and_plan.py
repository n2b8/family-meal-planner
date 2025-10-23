import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import Base, engine

@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

async def register_and_login(ac: AsyncClient, email="me@example.com", pw="SuperSecret1"):
    r = await ac.post("/auth/register", json={"email": email, "password": pw})
    assert r.status_code == 200
    r = await ac.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200
    return r.cookies

@pytest.mark.asyncio
async def test_recipe_crud_and_plan_with_caps_and_toggle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        cookies = await register_and_login(ac)

        # Create recipes (3 Mexican, 2 Asian, 1 Italian)
        async def add_recipe(name, cuisine, items):
            r = await ac.post("/recipes", cookies=cookies, json={"name": name, "cuisine": cuisine, "notes": "", "items": items})
            assert r.status_code == 200

        await add_recipe("Tacos", "Mexican", [{"ingredient_name":"Tortillas","quantity":10,"unit":"pcs"},{"ingredient_name":"Beef","quantity":1.0,"unit":"lb"}])
        await add_recipe("Enchiladas", "Mexican", [{"ingredient_name":"Tortillas","quantity":8,"unit":"pcs"},{"ingredient_name":"Cheese","quantity":0.5,"unit":"lb"}])
        await add_recipe("Pozole", "Mexican", [{"ingredient_name":"Hominy","quantity":2,"unit":"cans"}])
        await add_recipe("Stir Fry", "Asian", [{"ingredient_name":"Soy Sauce","quantity":0.25,"unit":"cup"}])
        await add_recipe("Curry", "Asian", [{"ingredient_name":"Curry Paste","quantity":2,"unit":"tbsp"}])
        await add_recipe("Spaghetti", "Italian", [{"ingredient_name":"Pasta","quantity":1,"unit":"lb"}])

        # Set caps: max 2 Mexican, max 1 Asian
        r = await ac.post("/settings/caps", cookies=cookies, json={"cuisine_caps":{"Mexican":2,"Asian":1}})
        assert r.status_code == 200

        # Generate 5-day plan
        r = await ac.post("/plans", cookies=cookies, json={"days":5})
        assert r.status_code == 200
        pid = r.json()["id"]

        # Read back plan
        r = await ac.get(f"/plans/{pid}", cookies=cookies)
        assert r.status_code == 200
        data = r.json()
        assert data["days"] == 5
        cuisines = [x["cuisine"] for x in data["recipes"]]
        assert cuisines.count("Mexican") <= 2
        assert cuisines.count("Asian")   <= 1

        # Shopping list aggregation checks (case-insensitive by ingredient, unit-aware)
        groceries = data["groceries"]
        names = { (g["name"].lower(), g["unit"]) : g for g in groceries }
        # tortillas pcs should be summed: 10 + 8 = 18
        assert names.get(("tortillas","pcs"))["quantity"] == 18
        # if Mexican exceeded cap, Pozole might not be in plan, so don't assert hominy

        # Toggle a grocery item
        some_id = groceries[0]["id"]
        r = await ac.post(f"/grocery/{some_id}/toggle", cookies=cookies)
        assert r.status_code == 200 and r.json()["checked"] in (True, False)

        # Verify toggle persisted
        r = await ac.get(f"/plans/{pid}", cookies=cookies)
        again = r.json()["groceries"]
        after = next(x for x in again if x["id"] == some_id)
        assert after["checked"] == True
