"""Input-validation hardening tests for Golem asset encryption and the
air-gapped controller. These exercise the rejection paths added to harden
public entry points against malformed or hostile inputs.
"""
import base64
import json
import os

import pytest


# --------------------------------------------------------------------------
# GolemAssetEncryption
# --------------------------------------------------------------------------
from encryption.asset_encryption import GolemAssetEncryption


def test_master_key_must_be_non_empty_string():
    with pytest.raises(ValueError):
        GolemAssetEncryption("")
    with pytest.raises(TypeError):
        GolemAssetEncryption(b"not-a-str")  # type: ignore[arg-type]


def test_encrypt_asset_rejects_non_bytes():
    enc = GolemAssetEncryption("master")
    with pytest.raises(TypeError):
        enc.encrypt_asset("plain string")  # type: ignore[arg-type]


def test_encrypt_asset_rejects_bad_optional_types():
    enc = GolemAssetEncryption("master")
    with pytest.raises(TypeError):
        enc.encrypt_asset(b"data", region=123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        enc.encrypt_asset(b"data", metadata=["not", "a", "dict"])  # type: ignore[arg-type]


def test_encrypt_decrypt_roundtrip_still_works():
    enc = GolemAssetEncryption("master")
    payload = enc.encrypt_asset(b"secret bytes", region="east-1")
    assert enc.decrypt_asset(payload) == b"secret bytes"


def test_decrypt_asset_rejects_non_dict():
    enc = GolemAssetEncryption("master")
    with pytest.raises(TypeError):
        enc.decrypt_asset("not a dict")  # type: ignore[arg-type]


def test_decrypt_asset_reports_missing_fields():
    enc = GolemAssetEncryption("master")
    with pytest.raises(ValueError, match="missing fields"):
        enc.decrypt_asset({"ciphertext": "AA=="})


def test_decrypt_asset_rejects_bad_base64():
    enc = GolemAssetEncryption("master")
    bad = {"ciphertext": "!!!", "tag": "!!!", "iv": "!!!", "salt": "!!!"}
    with pytest.raises(ValueError, match="invalid base64"):
        enc.decrypt_asset(bad)


def test_decrypt_asset_rejects_bad_iterations():
    enc = GolemAssetEncryption("master")
    payload = enc.encrypt_asset(b"data")
    payload["iterations"] = 0
    with pytest.raises(ValueError, match="iterations"):
        enc.decrypt_asset(payload)


def test_encrypt_file_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        GolemAssetEncryption.encrypt_file(str(tmp_path / "nope.bin"), "master")


def test_decrypt_file_rejects_non_json(tmp_path):
    p = tmp_path / "corrupt.encrypted"
    p.write_text("this is not json")
    with pytest.raises(ValueError, match="not valid JSON"):
        GolemAssetEncryption.decrypt_file(str(p), "master")


# --------------------------------------------------------------------------
# airgapped_controller
# --------------------------------------------------------------------------
import golem668.airgapped_controller as ac


def _point_paths_at(tmp_path):
    ac.BASE_DIR = str(tmp_path)
    ac.QUEUE_DIR = os.path.join(ac.BASE_DIR, "golem_queue")
    ac.PENDING_DIR = os.path.join(ac.QUEUE_DIR, "pending")
    ac.PROCESSED_DIR = os.path.join(ac.QUEUE_DIR, "processed")
    ac.ASSESSMENT_FILE = os.path.join(ac.QUEUE_DIR, "latest_assessment.json")
    ac.INDEX_FILE = os.path.join(ac.QUEUE_DIR, "index.json")


@pytest.mark.parametrize("bad_id", ["../escape", "a/b", "..", "", "with space"])
def test_validate_task_id_rejects_unsafe(bad_id):
    with pytest.raises(ValueError):
        ac.validate_task_id(bad_id)


def test_validate_task_id_accepts_uuid_like():
    assert ac.validate_task_id("abc-123_DEF.4") == "abc-123_DEF.4"


def test_from_json_requires_id_and_task():
    with pytest.raises(TypeError):
        ac.TaskItem.from_json("nope")
    with pytest.raises(ValueError):
        ac.TaskItem.from_json({"task": "no id"})
    with pytest.raises(ValueError):
        ac.TaskItem.from_json({"id": "x"})


def test_synthesize_rejects_non_dict(tmp_path):
    _point_paths_at(tmp_path)
    with pytest.raises(TypeError):
        ac.synthesize(["not", "a", "dict"])


def test_enqueue_rejects_traversal_id(tmp_path):
    _point_paths_at(tmp_path)
    ac.ensure_dirs()
    item = ac.TaskItem(
        sort_index=(ac.PRIORITY_MAP["medium"], 1.0),
        id="../../evil",
        priority="medium",
        owner=None,
        task="x",
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        due=None,
    )
    with pytest.raises(ValueError):
        ac.enqueue_task(item)


def test_enqueue_rejects_empty_task(tmp_path):
    _point_paths_at(tmp_path)
    ac.ensure_dirs()
    item = ac.TaskItem(
        sort_index=(ac.PRIORITY_MAP["medium"], 1.0),
        id="ok-id",
        priority="medium",
        owner=None,
        task="   ",
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        due=None,
    )
    with pytest.raises(ValueError):
        ac.enqueue_task(item)


def test_import_usb_missing_file(tmp_path):
    _point_paths_at(tmp_path)
    with pytest.raises(FileNotFoundError):
        ac.import_usb(str(tmp_path / "nope.pkg"), "pass")


def test_import_usb_rejects_bad_structure(tmp_path):
    _point_paths_at(tmp_path)
    ac.ensure_dirs()
    p = tmp_path / "bad.pkg"
    p.write_text(json.dumps({"salt": "00", "nonce": "00"}))  # missing ciphertext
    with pytest.raises(ValueError, match="salt"):
        ac.import_usb(str(p), "pass")


@pytest.mark.skipif(not ac.CRYPTO_AVAILABLE, reason="cryptography required")
def test_export_then_import_roundtrip_sanitizes_ids(tmp_path):
    _point_paths_at(tmp_path)
    ac.ensure_dirs()
    # enqueue a legitimate task, export, then import into a fresh queue
    item = ac.TaskItem(
        sort_index=(ac.PRIORITY_MAP["high"], 1.0),
        id="task-alpha",
        priority="high",
        owner="op",
        task="do the thing",
        tags=["t"],
        created_at="2026-01-01T00:00:00Z",
        due=None,
    )
    ac.enqueue_task(item)
    pkg = str(tmp_path / "out.pkg")
    ac.export_usb(pkg, "correct-passphrase")

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    _point_paths_at(fresh)
    ac.import_usb(pkg, "correct-passphrase")
    pending = [f for f in os.listdir(ac.PENDING_DIR) if f.endswith(".task")]
    assert len(pending) == 1
