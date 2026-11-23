"""
End-to-end integration tests for FastAPI prospect discovery endpoint.
Evaluates the 5 required test cases from the specification.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "gemini_model" in data


@pytest.mark.asyncio
async def test_empty_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/prospect-discovery", json={"query": ""})
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_case_1_football_washington():
    """Test Case 1: Football lovers in Washington DC in USA"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"query": "Football lovers in Washington DC in USA"}
        res = await client.post("/prospect-discovery", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["success"] is True
        assert data["query"] == payload["query"]
        assert data["total_prospects"] >= 1
        assert len(data["prospects"]) == data["total_prospects"]

        # Validate schema of each prospect
        for p in data["prospects"]:
            assert "name" in p and p["name"]
            assert "location" in p
            assert "social_link" in p and isinstance(p["social_link"], list)
            for sl in p["social_link"]:
                assert "platform" in sl and sl["platform"]
                assert "link" in sl and sl["link"]
                # Must be verified URL, not generic search link
                assert "google.com/search" not in sl["link"]


@pytest.mark.asyncio
async def test_case_2_digital_marketing_ny():
    """Test Case 2: Digital marketing agency owners in New York USA"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"query": "Digital marketing agency owners in New York USA"}
        res = await client.post("/prospect-discovery", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["success"] is True
        assert data["total_prospects"] >= 1
        names = [p["name"] for p in data["prospects"]]
        assert any("Vaynerchuk" in n or "Patel" in n for n in names)


@pytest.mark.asyncio
async def test_case_3_startup_founders_london():
    """Test Case 3: Startup founders in London UK"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"query": "Startup founders in London UK"}
        res = await client.post("/prospect-discovery", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["success"] is True
        assert data["total_prospects"] >= 1
        names = [p["name"] for p in data["prospects"]]
        assert any("Hinrikus" in n or "Narula" in n or "Sohoni" in n for n in names)


@pytest.mark.asyncio
async def test_case_4_cricket_ahmedabad():
    """Test Case 4: Cricket lovers in Ahmedabad India"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"query": "Cricket lovers in Ahmedabad India"}
        res = await client.post("/prospect-discovery", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["success"] is True
        assert data["total_prospects"] >= 1
        names = [p["name"] for p in data["prospects"]]
        assert any("Pandya" in n or "Patel" in n for n in names)


@pytest.mark.asyncio
async def test_case_5_restaurant_dubai():
    """Test Case 5: Restaurant owners in Dubai UAE"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"query": "Restaurant owners in Dubai UAE"}
        res = await client.post("/prospect-discovery", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["success"] is True
        assert data["total_prospects"] >= 1
        names = [p["name"] for p in data["prospects"]]
        assert any("Othman" in n or "Bhatia" in n or "Ani" in n for n in names)
