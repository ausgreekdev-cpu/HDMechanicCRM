"""Backup route: admin-only SQLite snapshots without same-day clobbering."""
import glob
import os

from app.auth import hash_password
from app.database import DB_PATH, SessionLocal
from app.models import User


def _login_as(client, username, password, role):
    db = SessionLocal()
    db.add(User(username=username, password_hash=hash_password(password),
                role=role, is_active=True))
    db.commit()
    db.close()
    resp = client.post("/login", data={"username": username, "password": password})
    assert resp.status_code == 302, f"login failed: {resp.status_code}"


def _backup_files():
    return sorted(glob.glob(DB_PATH + ".backup-*"))


def test_backup_requires_login(client):
    resp = client.get("/backup")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_backup_requires_admin(client):
    _login_as(client, "worker", "WorkerPass1!", role="user")
    resp = client.get("/backup")
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]
    assert _backup_files() == []


def test_backup_creates_timestamped_file(client):
    _login_as(client, "boss", "BossPass1!", role="admin")
    before = set(_backup_files())

    resp = client.get("/backup")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("Content-Disposition", "")

    created = set(_backup_files()) - before
    assert len(created) == 1
    path = created.pop()
    assert os.path.getsize(path) > 0


def test_backup_does_not_clobber_previous(client):
    _login_as(client, "boss", "BossPass1!", role="admin")
    before = set(_backup_files())

    client.get("/backup")
    client.get("/backup")

    created = set(_backup_files()) - before
    assert len(created) == 2
