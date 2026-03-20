from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("content is required")
        return s


class NoteRead(BaseModel):
    id: int
    content: str
    created_at: str


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1)
    save_note: bool = False

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("text is required")
        return s


class ExtractedItem(BaseModel):
    id: int
    text: str


class ExtractResponse(BaseModel):
    note_id: int | None = None
    items: list[ExtractedItem]


class ActionItemRead(BaseModel):
    id: int
    note_id: int | None
    text: str
    done: bool
    created_at: str


class MarkDoneRequest(BaseModel):
    done: bool = True


class MarkDoneResponse(BaseModel):
    id: int
    done: bool
