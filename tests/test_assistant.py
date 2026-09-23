"""Tests for the AI Weather & Hazard Assistant."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.assistant_service import (
    resolve_location,
    tool_get_safety_guidelines,
    tool_rank_districts_by_risk,
    tool_get_district_asi,
    generate_assistant_response,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_resolve_location_varieties():
    """Verify LGD district resolution across multiple geographies and synonyms."""
    loc_wayanad = resolve_location("What is the landslide risk in Wayanad?")
    assert loc_wayanad is not None
    assert "wayanad" in (loc_wayanad.get("district") or "").lower() or "wayanad" in loc_wayanad.get("name", "").lower()

    loc_sikkim = resolve_location("Weather in East Sikkim tomorrow")
    assert loc_sikkim is not None
    assert "sikkim" in loc_wayanad.get("state", "").lower() or "sikkim" in loc_sikkim.get("state", "").lower()

    loc_shimla = resolve_location("Rain in Shimla")
    assert loc_shimla is not None
    assert "shimla" in (loc_shimla.get("district") or loc_shimla.get("name") or "").lower()


def test_tool_safety_guidelines():
    """Verify NDMA safety guidelines return authoritative action steps."""
    res_landslide = tool_get_safety_guidelines("landslide")
    assert "actions_during" in res_landslide
    assert "actions_before" in res_landslide
    assert "NDMA" in res_landslide.get("authority", "")

    res_flood = tool_get_safety_guidelines("flood")
    assert "TURN AROUND" in str(res_flood.get("actions_during", []))


def test_tool_rank_districts():
    """Verify cross-district ranking returns sorted susceptibility scores."""
    ranked = tool_rank_districts_by_risk(state="Kerala", limit=5)
    assert len(ranked) <= 5
    assert len(ranked) > 0
    # Check descending sort
    scores = [r["susceptibility_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_tool_district_asi():
    """Verify ASI calculation returns valid saturation status."""
    dummy_loc = {"name": "Test Site", "state": "Kerala", "district": "Wayanad", "rainfall_24h": 35.0}
    asi = tool_get_district_asi(dummy_loc)
    assert asi["antecedent_saturation_index_mm"] > 0
    assert "saturation_status" in asi


@pytest.mark.asyncio
async def test_generate_assistant_response_grounded():
    """Verify end-to-end grounded assistant response contains IST timestamp, sources, and advisory."""
    res = await generate_assistant_response(
        message="Top 5 high landslide risk districts in Kerala",
        current_location={"name": "Wayanad", "state": "Kerala", "district": "Wayanad", "latitude": 11.6854, "longitude": 76.1320},
    )
    assert "reply" in res
    assert "IST" in res["timestamp_ist"]
    assert len(res["sources"]) > 0
    assert "IMD" in res["advisory"]
    assert "NDMA" in res["advisory"]
    assert "NCS" in res["advisory"]


def test_assistant_chat_api_endpoint(client):
    """Verify POST /api/assistant/chat API endpoint contract."""
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "Rain in Wayanad tomorrow?",
            "current_location": {
                "id": 1,
                "name": "Wayanad",
                "state": "Kerala",
                "district": "Wayanad",
                "latitude": 11.6854,
                "longitude": 76.1320,
            },
            "history": [],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "sources" in data
    assert "timestamp_ist" in data
    assert "advisory" in data
    assert "IMD" in data["advisory"]
