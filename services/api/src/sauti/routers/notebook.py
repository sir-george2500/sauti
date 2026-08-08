"""Ikaye — the learner's word notebook.

"A place I can take note of words that I have learned": save any word or
phrase (free-form, or snapshotted from a curriculum item) with a personal
note, review them in one place.

Ownership: every query is scoped to the current user; foreign entries answer
404 (indistinguishable from not-existing — no cross-user probing).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from sauti.deps import CurrentUser, DbDep
from sauti.errors import ApiError
from sauti.models import Item, NotebookEntry
from sauti.schemas.notebook import NotebookEntryIn, NotebookEntryOut, NotebookEntryPatch
from sauti.services.audio import audio_urls_for_items

router = APIRouter(tags=["notebook"])


def _out(
    entry: NotebookEntry,
    item: Item | None = None,
    audio_url: str | None = None,
) -> NotebookEntryOut:
    return NotebookEntryOut(
        id=entry.id,
        item_id=entry.item_id,
        text=entry.text,
        gloss=entry.gloss,
        note=entry.note,
        created_at=entry.created_at,
        item_sentence=item.sentence if item else None,
        item_gloss=item.gloss if item else None,
        audio_url=audio_url,
    )


async def _entry_or_404(db, user_id: uuid.UUID, entry_id: uuid.UUID) -> NotebookEntry:
    entry = await db.scalar(
        select(NotebookEntry).where(
            NotebookEntry.id == entry_id, NotebookEntry.user_id == user_id
        )
    )
    if entry is None:
        raise ApiError(404, "NOT_FOUND", "No such notebook entry")
    return entry


async def _linked_item(db, entry: NotebookEntry) -> tuple[Item | None, str | None]:
    """The entry's source item + its cached audio URL (one bulk-resolver call)."""
    if entry.item_id is None:
        return None, None
    item = await db.scalar(select(Item).where(Item.id == entry.item_id))
    if item is None:
        return None, None
    audio_urls = await audio_urls_for_items(db, [item])
    return item, audio_urls.get(item.id)


@router.get("/notebook")
async def list_entries(user: CurrentUser, db: DbDep) -> list[NotebookEntryOut]:
    entries = list(
        await db.scalars(
            select(NotebookEntry)
            .where(NotebookEntry.user_id == user.id)
            .order_by(NotebookEntry.created_at.desc(), NotebookEntry.id.desc())
        )
    )
    item_ids = {e.item_id for e in entries if e.item_id is not None}
    items: dict[uuid.UUID, Item] = {}
    audio_urls: dict[uuid.UUID, str] = {}
    if item_ids:
        items = {
            i.id: i for i in await db.scalars(select(Item).where(Item.id.in_(item_ids)))
        }
        # One bulk tts_cache query for the whole notebook — never per-entry.
        audio_urls = await audio_urls_for_items(db, list(items.values()))
    return [
        _out(
            e,
            items.get(e.item_id) if e.item_id else None,
            audio_urls.get(e.item_id) if e.item_id else None,
        )
        for e in entries
    ]


@router.post("/notebook", status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: NotebookEntryIn, user: CurrentUser, db: DbDep
) -> NotebookEntryOut:
    item: Item | None = None
    if body.item_id is not None:
        item = await db.scalar(select(Item).where(Item.id == body.item_id))
        if item is None:
            raise ApiError(404, "NOT_FOUND", "Unknown item")

    # Snapshot the item's sentence/gloss unless the caller provided their own.
    text = body.text or (item.sentence if item else None)
    if text is None:
        raise ApiError(422, "VALIDATION", "Provide text or item_id")
    gloss = body.gloss or (item.gloss if item else None)

    entry = NotebookEntry(
        user_id=user.id,
        item_id=item.id if item else None,
        text=text,
        gloss=gloss,
        note=body.note,
    )
    db.add(entry)
    await db.commit()

    audio_url = (await audio_urls_for_items(db, [item])).get(item.id) if item else None
    return _out(entry, item, audio_url)


@router.patch("/notebook/{entry_id}")
async def update_entry(
    entry_id: uuid.UUID, body: NotebookEntryPatch, user: CurrentUser, db: DbDep
) -> NotebookEntryOut:
    entry = await _entry_or_404(db, user.id, entry_id)
    changes = body.model_dump(exclude_unset=True)
    if "text" in changes and changes["text"] is None:
        raise ApiError(422, "VALIDATION", "text cannot be empty")
    for field, value in changes.items():
        setattr(entry, field, value)
    await db.commit()
    item, audio_url = await _linked_item(db, entry)
    return _out(entry, item, audio_url)


@router.delete("/notebook/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: uuid.UUID, user: CurrentUser, db: DbDep
) -> Response:
    entry = await _entry_or_404(db, user.id, entry_id)
    await db.delete(entry)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
