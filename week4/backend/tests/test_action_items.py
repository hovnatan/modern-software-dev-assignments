def test_create_and_complete_action_item(client):
    payload = {"description": "Ship it"}
    r = client.post("/action-items/", json=payload)
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["completed"] is False

    r = client.put(f"/action-items/{item['id']}/complete")
    assert r.status_code == 200
    done = r.json()
    assert done["completed"] is True

    r = client.get("/action-items/")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1


# ---------------------------------------------------------------------------
# GET single action item by ID (NOT yet implemented -- should FAIL)
# ---------------------------------------------------------------------------


def test_get_action_item_by_id(client):
    """GET /action-items/{id} returns the correct action item."""
    r = client.post("/action-items/", json={"description": "Find me"})
    assert r.status_code == 201
    item_id = r.json()["id"]

    r = client.get(f"/action-items/{item_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == item_id
    assert data["description"] == "Find me"
    assert data["completed"] is False


def test_get_action_item_not_found(client):
    """GET /action-items/{id} returns 404 with detail message for a non-existent item."""
    r = client.get("/action-items/99999")
    assert r.status_code == 404
    assert "detail" in r.json()


# ---------------------------------------------------------------------------
# DELETE action item (NOT yet implemented -- should FAIL)
# ---------------------------------------------------------------------------


def test_delete_action_item(client):
    """DELETE /action-items/{id} removes the item and returns 200."""
    r = client.post("/action-items/", json={"description": "Delete me"})
    assert r.status_code == 201
    item_id = r.json()["id"]

    r = client.delete(f"/action-items/{item_id}")
    assert r.status_code == 200

    # Confirm it is gone via list
    r = client.get("/action-items/")
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()]
    assert item_id not in ids


def test_delete_action_item_not_found(client):
    """DELETE /action-items/{id} returns 404 with detail message for a non-existent item."""
    r = client.delete("/action-items/99999")
    assert r.status_code == 404
    assert "detail" in r.json()


# ---------------------------------------------------------------------------
# Schema / validation tests
# ---------------------------------------------------------------------------


def test_create_action_item_missing_description(client):
    """POST /action-items/ without description should return 422."""
    r = client.post("/action-items/", json={})
    assert r.status_code == 422


def test_create_action_item_response_has_id(client):
    """POST /action-items/ response includes an auto-generated integer id."""
    r = client.post("/action-items/", json={"description": "Check id"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert isinstance(data["id"], int)


def test_create_action_item_default_completed_false(client):
    """Newly created action items always have completed=False."""
    r = client.post("/action-items/", json={"description": "Defaults test"})
    assert r.status_code == 201
    assert r.json()["completed"] is False


# ---------------------------------------------------------------------------
# Complete item edge cases
# ---------------------------------------------------------------------------


def test_complete_nonexistent_action_item(client):
    """PUT /action-items/{id}/complete returns 404 for non-existent item."""
    r = client.put("/action-items/99999/complete")
    assert r.status_code == 404


def test_complete_already_completed_item(client):
    """Completing an already-completed item should still return 200."""
    r = client.post("/action-items/", json={"description": "Double complete"})
    assert r.status_code == 201
    item_id = r.json()["id"]

    # Complete it once
    r = client.put(f"/action-items/{item_id}/complete")
    assert r.status_code == 200
    assert r.json()["completed"] is True

    # Complete it again -- should still succeed
    r = client.put(f"/action-items/{item_id}/complete")
    assert r.status_code == 200
    assert r.json()["completed"] is True


# ---------------------------------------------------------------------------
# List action items -- multiple items
# ---------------------------------------------------------------------------


def test_list_action_items_returns_all(client):
    """GET /action-items/ returns all created items."""
    client.post("/action-items/", json={"description": "Item 1"})
    client.post("/action-items/", json={"description": "Item 2"})
    client.post("/action-items/", json={"description": "Item 3"})

    r = client.get("/action-items/")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3


def test_list_action_items_empty(client):
    """GET /action-items/ returns empty list when no items exist."""
    r = client.get("/action-items/")
    assert r.status_code == 200
    assert r.json() == []
