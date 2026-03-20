from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .. import db
from ..schemas import NoteCreate, NoteRead

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate) -> NoteRead:
    note_id = db.insert_note(payload.content)
    note = db.get_note(note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="note was not persisted correctly",
        )
    return NoteRead(id=note.id, content=note.content, created_at=note.created_at)


@router.get("", response_model=list[NoteRead])
def list_all_notes() -> list[NoteRead]:
    return [
        NoteRead(id=n.id, content=n.content, created_at=n.created_at)
        for n in db.list_notes()
    ]


@router.get("/{note_id}", response_model=NoteRead)
def get_single_note(note_id: int) -> NoteRead:
    row = db.get_note(note_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note not found")
    return NoteRead(id=row.id, content=row.content, created_at=row.created_at)
