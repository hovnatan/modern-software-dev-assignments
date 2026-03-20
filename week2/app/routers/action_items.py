from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .. import db
from ..schemas import (
    ActionItemRead,
    ExtractedItem,
    ExtractRequest,
    ExtractResponse,
    MarkDoneRequest,
    MarkDoneResponse,
)
from ..services.extract import extract_action_items, extract_action_items_llm

router = APIRouter(prefix="/action-items", tags=["action-items"])


@router.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest) -> ExtractResponse:
    note_id: int | None = None
    if payload.save_note:
        note_id = db.insert_note(payload.text)

    items = extract_action_items(payload.text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractResponse(
        note_id=note_id,
        items=[ExtractedItem(id=i, text=t) for i, t in zip(ids, items, strict=True)],
    )


@router.post("/extract-llm", response_model=ExtractResponse)
def extract_llm(payload: ExtractRequest) -> ExtractResponse:
    note_id: int | None = None
    if payload.save_note:
        note_id = db.insert_note(payload.text)

    items = extract_action_items_llm(payload.text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractResponse(
        note_id=note_id,
        items=[ExtractedItem(id=i, text=t) for i, t in zip(ids, items, strict=True)],
    )


@router.get("", response_model=list[ActionItemRead])
def list_all(note_id: int | None = None) -> list[ActionItemRead]:
    rows = db.list_action_items(note_id=note_id)
    return [
        ActionItemRead(
            id=r.id,
            note_id=r.note_id,
            text=r.text,
            done=r.done,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{action_item_id}/done", response_model=MarkDoneResponse)
def mark_done(action_item_id: int, payload: MarkDoneRequest) -> MarkDoneResponse:
    updated = db.mark_action_item_done(action_item_id, payload.done)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="action item not found",
        )
    return MarkDoneResponse(id=action_item_id, done=payload.done)
