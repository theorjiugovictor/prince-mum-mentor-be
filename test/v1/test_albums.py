import uuid
from datetime import datetime

import pytest


def create_photo(db, image_url: str):
    from api.v1.models.photos import Photos
    photo = Photos(id=uuid.uuid4(), image_url=image_url)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def create_album(db, user_id, name: str = "Test Album"):
    from api.v1.models.albums import Album
    album = Album(id=uuid.uuid4(), name=name, user_id=user_id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(album)
    db.commit()
    db.refresh(album)
    return album


def create_memory(db, album_id, photo_obj, note: str = "A memory"):
    from api.v1.models.memories import Memory
    mem = Memory(id=uuid.uuid4(), album_id=album_id, photo=photo_obj.id, note=note, saved_on=datetime.utcnow())
    # also set relationship if available
    try:
        mem.photo_data = photo_obj
    except Exception:
        pass

    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem


def test_list_albums_returns_thumbnail(client, db, sample_user, auth_headers):
    # Create photo, album and memory
    photo = create_photo(db, "https://example.com/photo1.jpg")
    album = create_album(db, sample_user.id, name="Family")
    _mem = create_memory(db, album.id, photo, note="First memory")

    resp = client.get("/api/v1/albums/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # find our album
    items = [a for a in data if a["id"] == str(album.id)]
    assert len(items) == 1
    item = items[0]
    assert item["last_image"] == photo.image_url


def test_get_album_with_memories_returns_photos(client, db, sample_user, auth_headers):
    photo = create_photo(db, "https://example.com/photo2.jpg")
    album = create_album(db, sample_user.id, name="Trip")
    mem = create_memory(db, album.id, photo, note="On vacation")

    resp = client.get(f"/api/v1/albums/{album.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(album.id)
    # memories should be present
    assert "memories" in data
    assert len(data["memories"]) == 1
    memory = data["memories"][0]
    # photo nested object should include image_url
    assert "photo" in memory
    # Some serializers use nested 'photo' object; ensure image_url matches
    photo_obj = memory["photo"]
    assert photo_obj["image_url"] == photo.image_url
