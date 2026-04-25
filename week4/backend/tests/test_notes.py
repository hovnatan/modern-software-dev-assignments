def test_create_and_list_notes(client):
    payload = {"title": "Test", "content": "Hello world"}
    r = client.post("/notes/", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Test"

    r = client.get("/notes/")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1

    r = client.get("/notes/search/")
    assert r.status_code == 200

    r = client.get("/notes/search/", params={"q": "Hello"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1


# ---------------------------------------------------------------------------
# GET single note
# ---------------------------------------------------------------------------


def test_get_note_by_id(client):
    """GET /notes/{id} returns the correct note."""
    payload = {"title": "Specific Note", "content": "Specific content"}
    r = client.post("/notes/", json=payload)
    assert r.status_code == 201
    note_id = r.json()["id"]

    r = client.get(f"/notes/{note_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == note_id
    assert data["title"] == "Specific Note"
    assert data["content"] == "Specific content"


def test_get_note_not_found(client):
    """GET /notes/{id} returns 404 for a non-existent note."""
    r = client.get("/notes/99999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT update note (NOT yet implemented -- these tests should FAIL)
# ---------------------------------------------------------------------------


def test_update_note(client):
    """PUT /notes/{id} updates title and content of an existing note."""
    # Create a note first
    r = client.post("/notes/", json={"title": "Original", "content": "Original body"})
    assert r.status_code == 201
    note_id = r.json()["id"]

    # Update it
    r = client.put(f"/notes/{note_id}", json={"title": "Updated", "content": "Updated body"})
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == note_id
    assert data["title"] == "Updated"
    assert data["content"] == "Updated body"

    # Verify persistence via GET
    r = client.get(f"/notes/{note_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"
    assert r.json()["content"] == "Updated body"


def test_update_note_not_found(client):
    """PUT /notes/{id} returns 404 when the note does not exist."""
    r = client.put("/notes/99999", json={"title": "X", "content": "Y"})
    assert r.status_code == 404


def test_update_note_partial_fields(client):
    """PUT /notes/{id} with only title still requires content (schema validation)."""
    r = client.post("/notes/", json={"title": "A", "content": "B"})
    assert r.status_code == 201
    note_id = r.json()["id"]

    # Missing 'content' -- should be rejected as 422
    r = client.put(f"/notes/{note_id}", json={"title": "Updated only title"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# DELETE note (NOT yet implemented -- these tests should FAIL)
# ---------------------------------------------------------------------------


def test_delete_note(client):
    """DELETE /notes/{id} removes the note and returns 200."""
    r = client.post("/notes/", json={"title": "To Delete", "content": "Goodbye"})
    assert r.status_code == 201
    note_id = r.json()["id"]

    r = client.delete(f"/notes/{note_id}")
    assert r.status_code == 200

    # Confirm the note is gone
    r = client.get(f"/notes/{note_id}")
    assert r.status_code == 404


def test_delete_note_not_found(client):
    """DELETE /notes/{id} returns 404 for a non-existent note."""
    r = client.delete("/notes/99999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Schema / validation tests
# ---------------------------------------------------------------------------


def test_create_note_missing_title(client):
    """POST /notes/ without title should return 422."""
    r = client.post("/notes/", json={"content": "No title here"})
    assert r.status_code == 422


def test_create_note_missing_content(client):
    """POST /notes/ without content should return 422."""
    r = client.post("/notes/", json={"title": "No content here"})
    assert r.status_code == 422


def test_create_note_empty_body(client):
    """POST /notes/ with an empty JSON body should return 422."""
    r = client.post("/notes/", json={})
    assert r.status_code == 422


def test_create_note_response_has_id(client):
    """POST /notes/ response includes an auto-generated integer id."""
    r = client.post("/notes/", json={"title": "ID check", "content": "body"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert isinstance(data["id"], int)


# ---------------------------------------------------------------------------
# Search edge cases
# ---------------------------------------------------------------------------


def test_search_notes_no_match(client):
    """GET /notes/search/?q=... returns empty list when nothing matches."""
    client.post("/notes/", json={"title": "Alpha", "content": "Bravo"})
    r = client.get("/notes/search/", params={"q": "ZZZNOTFOUND"})
    assert r.status_code == 200
    assert r.json() == []


def test_search_notes_matches_content(client):
    """Search finds notes where the query matches content, not just title."""
    client.post("/notes/", json={"title": "Irrelevant title", "content": "UniqueContentToken"})
    r = client.get("/notes/search/", params={"q": "UniqueContentToken"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["content"] == "UniqueContentToken"


# ---------------------------------------------------------------------------
# List notes ordering / multiple notes
# ---------------------------------------------------------------------------


def test_list_notes_returns_all(client):
    """GET /notes/ returns all created notes."""
    client.post("/notes/", json={"title": "Note 1", "content": "Content 1"})
    client.post("/notes/", json={"title": "Note 2", "content": "Content 2"})
    client.post("/notes/", json={"title": "Note 3", "content": "Content 3"})

    r = client.get("/notes/")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3
