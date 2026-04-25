import ast
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, select, text
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Note
from ..schemas import NoteCreate, NotePatch, NoteRead

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=list[NoteRead])
def list_notes(
    db: Session = Depends(get_db),
    q: str | None = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    sort: str = Query("-created_at", description="Sort by field, prefix with - for desc"),
) -> list[NoteRead]:
    stmt = select(Note)
    if q:
        stmt = stmt.where((Note.title.contains(q)) | (Note.content.contains(q)))

    sort_field = sort.lstrip("-")
    order_fn = desc if sort.startswith("-") else asc
    if hasattr(Note, sort_field):
        stmt = stmt.order_by(order_fn(getattr(Note, sort_field)))
    else:
        stmt = stmt.order_by(desc(Note.created_at))

    rows = db.execute(stmt.offset(skip).limit(limit)).scalars().all()
    return [NoteRead.model_validate(row) for row in rows]


@router.post("/", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)) -> NoteRead:
    note = Note(title=payload.title, content=payload.content)
    db.add(note)
    db.flush()
    db.refresh(note)
    return NoteRead.model_validate(note)


@router.patch("/{note_id}", response_model=NoteRead)
def patch_note(note_id: int, payload: NotePatch, db: Session = Depends(get_db)) -> NoteRead:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    db.add(note)
    db.flush()
    db.refresh(note)
    return NoteRead.model_validate(note)


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, db: Session = Depends(get_db)) -> NoteRead:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteRead.model_validate(note)


@router.get("/unsafe-search", response_model=list[NoteRead])
def unsafe_search(q: str, db: Session = Depends(get_db)) -> list[NoteRead]:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    sql = text(
        """
        SELECT id, title, content, created_at, updated_at
        FROM notes
        WHERE title LIKE :pattern ESCAPE '\\' OR content LIKE :pattern ESCAPE '\\'
        ORDER BY created_at DESC
        LIMIT 50
        """
    )
    rows = db.execute(sql, {"pattern": pattern}).all()
    results: list[NoteRead] = []
    for r in rows:
        results.append(
            NoteRead(
                id=r.id,
                title=r.title,
                content=r.content,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return results


@router.get("/debug/hash-md5")
def debug_hash_md5(q: str) -> dict[str, str]:
    import hashlib

    return {"algo": "md5", "hex": hashlib.md5(q.encode()).hexdigest()}


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


def _safe_eval_arith(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval_arith(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left = _safe_eval_arith(node.left)
        right = _safe_eval_arith(node.right)
        return {
            ast.Add: lambda: left + right,
            ast.Sub: lambda: left - right,
            ast.Mult: lambda: left * right,
            ast.Div: lambda: left / right,
            ast.Mod: lambda: left % right,
            ast.Pow: lambda: left**right,
            ast.FloorDiv: lambda: left // right,
        }[type(node.op)]()
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARYOPS):
        operand = _safe_eval_arith(node.operand)
        return +operand if isinstance(node.op, ast.UAdd) else -operand
    raise ValueError("unsupported expression")


@router.get("/debug/eval")
def debug_eval(expr: str) -> dict[str, str]:
    if len(expr) > 200:
        raise HTTPException(status_code=400, detail="expression too long")
    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval_arith(tree)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as e:
        raise HTTPException(status_code=400, detail=f"invalid expression: {e}") from e
    return {"result": str(result)}


_ALLOWED_COMMANDS: dict[str, list[str]] = {
    "uptime": ["uptime"],
    "whoami": ["whoami"],
    "date": ["date", "--iso-8601=seconds"],
    "hostname": ["hostname"],
}


@router.get("/debug/run")
def debug_run(cmd: str) -> dict[str, str]:
    import subprocess

    argv = _ALLOWED_COMMANDS.get(cmd)
    if argv is None:
        raise HTTPException(
            status_code=400,
            detail=f"command not allowed; choose one of: {sorted(_ALLOWED_COMMANDS)}",
        )
    try:
        completed = subprocess.run(  # noqa: S603
            argv, shell=False, capture_output=True, text=True, timeout=5
        )
    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=504, detail="command timed out") from e
    return {
        "returncode": str(completed.returncode),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _assert_public_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise HTTPException(status_code=400, detail=f"could not resolve host: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(status_code=400, detail=f"host resolves to non-public IP: {ip}")


@router.get("/debug/fetch")
def debug_fetch(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="only http(s) URLs are allowed")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL must include a hostname")
    _assert_public_host(parsed.hostname)
    try:
        with httpx.Client(follow_redirects=False, timeout=5.0) as client:
            res = client.get(url)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"fetch failed: {e}") from e
    return {"snippet": res.text[:1024]}


@router.get("/debug/read")
def debug_read(path: str) -> dict[str, str]:
    try:
        content = open(path).read(1024)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
    return {"snippet": content}
