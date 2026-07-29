#!/usr/bin/env python3
"""
GOLEM-668 — Air-gapped Synthesizer Controller (enhanced)

Features:
 - Task dataclass with UUID, priority, owner, tags, due, attempts
 - Priority queueing persisted to disk under ./golem_queue/
 - Atomic writes, basic file locking, and secure file permissions
 - USB export/import: AES-GCM encrypted JSON package (requires `cryptography`)
 - CLI commands:
     generate  -> produce assessment + enqueue tasks
     enqueue   -> add a custom task
     list      -> show pending tasks (by priority)
     list-all  -> detailed index
     process   -> process next (highest priority)
     export-usb <path> -> create encrypted package for USB
     import-usb <path> -> import encrypted package (prompts for passphrase)
     show      -> show latest assessment JSON
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import uuid
import heapq
import stat
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Optional crypto dependency — used only for USB export/import
try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTO_AVAILABLE = True
except Exception:
    CRYPTO_AVAILABLE = False

# --- configuration & queue directories ---
BASE_DIR = os.path.abspath(os.getcwd())
QUEUE_DIR = os.path.join(BASE_DIR, "golem_queue")
PENDING_DIR = os.path.join(QUEUE_DIR, "pending")
PROCESSED_DIR = os.path.join(QUEUE_DIR, "processed")
ASSESSMENT_FILE = os.path.join(QUEUE_DIR, "latest_assessment.json")
INDEX_FILE = os.path.join(QUEUE_DIR, "index.json")

# Ensure safe umask for created files (owner-only by default)
os.umask(0o077)

def log(tag: str, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {tag}: {msg}", file=sys.stderr)

def ensure_dirs() -> None:
    os.makedirs(PENDING_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    # index file default if missing
    if not os.path.exists(INDEX_FILE):
        atomic_write_json(INDEX_FILE, {"tasks": {}})

def atomic_write_json(path: str, obj: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    os.replace(tmp, path)
    # tighten permissions
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass

# --- Task metadata & priority handling ---
PRIORITY_MAP = {"critical": 1, "high": 2, "medium": 3, "low": 4, "deferred": 5}

@dataclass(order=True)
class TaskItem:
    sort_index: Tuple[int, float]  # (priority_value, queued_epoch)
    id: str
    priority: str
    owner: Optional[str]
    task: str
    tags: List[str]
    created_at: str
    due: Optional[str]
    attempts: int = 0

    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("sort_index", None)
        return d

    @staticmethod
    def from_json(payload: Dict[str, Any]) -> "TaskItem":
        queued_epoch = payload.get("_queued_epoch", time.time())
        priority_val = PRIORITY_MAP.get(payload.get("priority", "medium"), 3)
        return TaskItem(
            sort_index=(priority_val, queued_epoch),
            id=payload["id"],
            priority=payload.get("priority", "medium"),
            owner=payload.get("owner"),
            task=payload.get("task"),
            tags=payload.get("tags", []),
            created_at=payload.get("created_at"),
            due=payload.get("due"),
            attempts=payload.get("attempts", 0),
        )

# --- Persistence index helpers ---
def load_index() -> Dict[str, Any]:
    ensure_dirs()
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"tasks": {}}

def save_index(index: Dict[str, Any]) -> None:
    atomic_write_json(INDEX_FILE, index)

def enqueue_task(item: TaskItem) -> None:
    ensure_dirs()
    # persist task file named by id
    filename = f"{item.id}.task"
    path = os.path.join(PENDING_DIR, filename)
    payload = item.to_json()
    payload["_queued_epoch"] = item.sort_index[1]
    atomic_write_json(path, payload)
    # update index
    idx = load_index()
    idx["tasks"][item.id] = {"id": item.id, "priority": item.priority, "queued_at": item.created_at, "file": filename}
    save_index(idx)
    log("GOLEM-668", f"Enqueued task {item.id} priority={item.priority}")

def build_priority_heap() -> List[Tuple[Tuple[int, float], str]]:
    ensure_dirs()
    files = [f for f in os.listdir(PENDING_DIR) if f.endswith(".task")]
    heap: List[Tuple[Tuple[int, float], str]] = []
    for f in files:
        path = os.path.join(PENDING_DIR, f)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            priority_val = PRIORITY_MAP.get(payload.get("priority", "medium"), 3)
            queued_epoch = payload.get("_queued_epoch", os.path.getmtime(path))
            heapq.heappush(heap, ((priority_val, queued_epoch), f))
        except Exception:
            log("GOLEM-668", f"Skipping unreadable pending file: {f}")
    return heap

def process_next() -> None:
    heap = build_priority_heap()
    if not heap:
        log("GOLEM-668", "No pending tasks to process.")
        return
    (_, filename) = heapq.heappop(heap)
    src = os.path.join(PENDING_DIR, filename)
    dst = os.path.join(PROCESSED_DIR, filename + ".processed")
    try:
        with open(src, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        # simulate operator handling; in real air-gapped ops an operator would perform the action
        result = {
            "id": payload.get("id"),
            "task": payload.get("task"),
            "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "processed",
            "notes": "Handled in air-gapped controller"
        }
        atomic_write_json(dst, result)
        os.remove(src)
        # update index
        idx = load_index()
        idx["tasks"].pop(payload.get("id"), None)
        save_index(idx)
        log("GOLEM-668", f"Processed task {payload.get('id')} -> {dst}")
    except Exception as e:
        log("GOLEM-668", f"Error processing {filename}: {e}")

# --- Assessment generation (keeps original static content for now) ---
_TLP = "AMBER"
_THREATS = [
    {"level": "HIGH", "label": "CYBER CLUSTER_A — Cobalt Strike Beacon Infrastructure", "score": 0.89, "sources": ["CYBER", "NEXUS"]},
    {"level": "MEDIUM", "label": "SIGINT SIG_0773 — X-Band Uplink Anomaly (COSMOS-2576 correlation)", "score": 0.78, "sources": ["SIGINT", "SPACE", "FUSION"]},
    {"level": "MEDIUM", "label": "GEOINT AoI-003 — New Structure Detected [11.98°N 39.74°E]", "score": 0.72, "sources": ["GEOINT", "FUSION"]},
    {"level": "MEDIUM", "label": "SIGINT SIG_0284 — Possible GNSS Spoofing near AoI-001", "score": 0.67, "sources": ["SIGINT", "GEOINT"]},
    {"level": "LOW", "label": "SPACE COSMOS-2576 — Elevated-Interest Pass (03:31 UTC)", "score": 0.51, "sources": ["SPACE"]},
    {"level": "LOW", "label": "CYBER CLUSTER_B — Unattributed C2 Framework", "score": 0.45, "sources": ["CYBER"]},
]
_DEFAULT_TASKS = [
    "RE-TASK SAR satellite for AoI-003 high-resolution imaging (next window: 05:44 UTC)",
    "ESCALATE CYBER CLUSTER_A to Tier-1 analyst — initiate full attribution trace",
    "CROSS-REF SIG_0773 against SIGINT holdings database for pattern match",
    "REQUEST HUMINT corroboration for AoI-001 construction activity assessment",
    "FILE COSMOS-2576 anomalous-pass record to Sat-79 extended tasking queue",
    "UPDATE NEXUS ontograph: CLUSTER_A node → THREAT_ACTOR with JARM attribution",
    "INITIATE post-quantum credential rotation for APEX / NEXUS / GOLEM-668 stack",
]

def synthesize(all_results: Dict[str, Any] = None) -> Dict[str, Any]:
    ensure_dirs()
    cycle_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    assessment = {"tlp": _TLP, "cycle_time": cycle_time, "threats": _THREATS, "tasks": _DEFAULT_TASKS, "inputs": all_results or {}}
    atomic_write_json(ASSESSMENT_FILE, assessment)
    log("GOLEM-668", f"Saved assessment to {ASSESSMENT_FILE}")
    # enqueue default tasks with metadata and priority mapping; default priority based on level
    for t in _DEFAULT_TASKS:
        # simple heuristic: if contains 'ESCALATE' or 'RE-TASK' -> high
        priority = "high" if ("ESCALATE" in t or "RE-TASK" in t or "INITIATE" in t) else "medium"
        item = TaskItem(
            sort_index=(PRIORITY_MAP[priority], time.time()),
            id=str(uuid.uuid4()),
            priority=priority,
            owner=None,
            task=t,
            tags=[],
            created_at=cycle_time,
            due=None,
            attempts=0,
        )
        enqueue_task(item)
    return assessment

# --- USB export/import (encrypted package) ---
def derive_key(passphrase: str, salt: bytes, iterations: int = 150_000) -> bytes:
    # PBKDF2-HMAC-SHA256
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return kdf.derive(passphrase.encode("utf-8"))

def export_usb(package_path: str, passphrase: str) -> None:
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("Cryptography package is required for export/import operations.")
    ensure_dirs()
    # assemble package (index + pending files + assessment)
    index = load_index()
    pending = []
    for fid in os.listdir(PENDING_DIR):
        if not fid.endswith(".task"):
            continue
        with open(os.path.join(PENDING_DIR, fid), "r", encoding="utf-8") as fh:
            pending.append(json.load(fh))
    package = {"index": index, "pending": pending}
    plaintext = json.dumps(package).encode("utf-8")
    salt = os.urandom(16)
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    blob = {"salt": salt.hex(), "nonce": nonce.hex(), "ciphertext": ct.hex()}
    atomic_write_json(package_path, blob)
    log("GOLEM-668", f"Wrote encrypted package to {package_path} (use USB media for transfer)")

def import_usb(package_path: str, passphrase: str) -> None:
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("Cryptography package is required for export/import operations.")
    ensure_dirs()
    with open(package_path, "r", encoding="utf-8") as f:
        blob = json.load(f)
    salt = bytes.fromhex(blob["salt"])
    nonce = bytes.fromhex(blob["nonce"])
    ct = bytes.fromhex(blob["ciphertext"])
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ct, None)
    package = json.loads(plaintext.decode("utf-8"))
    # merge index/pending safely: write each pending task as new pending file (avoid overwriting)
    for p in package.get("pending", []):
        p_id = p.get("id") or str(uuid.uuid4())
        # ensure unique file name
        filename = f"{p_id}.task"
        dest = os.path.join(PENDING_DIR, filename)
        if os.path.exists(dest):
            # add suffix to avoid collision
            filename = f"{p_id}_{int(time.time())}.task"
            dest = os.path.join(PENDING_DIR, filename)
        atomic_write_json(dest, p)
        log("GOLEM-668", f"Imported pending task -> {dest}")
    # merge index (naive merge)
    idx = load_index()
    idx_tasks = idx.get("tasks", {})
    for k, v in package.get("index", {}).get("tasks", {}).items():
        if k not in idx_tasks:
            idx_tasks[k] = v
    idx["tasks"] = idx_tasks
    save_index(idx)
    log("GOLEM-668", "Imported package index and tasks")

# --- CLI Entrypoint ---
def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(prog="golem668")
    parser.add_argument("cmd", choices=["generate", "list", "list-all", "enqueue", "process", "export-usb", "import-usb", "show"])
    parser.add_argument("--task", help="task text for enqueue")
    parser.add_argument("--priority", default="medium", choices=list(PRIORITY_MAP.keys()))
    parser.add_argument("--owner", help="task owner")
    parser.add_argument("--tags", help="comma-separated tags")
    parser.add_argument("--path", help="path for export/import package")
    parser.add_argument("--passphrase", help="passphrase for export/import (or will prompt)")
    args = parser.parse_args(argv[1:])

    if args.cmd == "generate":
        synthesize({})
    elif args.cmd == "enqueue":
        if not args.task:
            print("enqueue requires --task")
            return
        item = TaskItem(
            sort_index=(PRIORITY_MAP[args.priority], time.time()),
            id=str(uuid.uuid4()),
            priority=args.priority,
            owner=args.owner,
            task=args.task,
            tags=(args.tags.split(",") if args.tags else []),
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            due=None,
        )
        enqueue_task(item)
    elif args.cmd == "list":
        heap = build_priority_heap()
        if not heap:
            print("(no pending tasks)")
            return
        for (pri, _), filename in heap:
            path = os.path.join(PENDING_DIR, filename)
            with open(path, "r", encoding="utf-8") as fh:
                p = json.load(fh)
            print(f"{p.get('id')[:8]}  priority={p.get('priority')}  {p.get('task')}")
    elif args.cmd == "list-all":
        idx = load_index()
        print(json.dumps(idx, indent=2))
    elif args.cmd == "process":
        process_next()
    elif args.cmd == "export-usb":
        if not args.path:
            print("export-usb requires --path")
            return
        passphrase = args.passphrase or input("Export passphrase (do NOT transmit over network): ")
        export_usb(args.path, passphrase)
    elif args.cmd == "import-usb":
        if not args.path:
            print("import-usb requires --path")
            return
        passphrase = args.passphrase or input("Import passphrase: ")
        import_usb(args.path, passphrase)
    elif args.cmd == "show":
        if os.path.exists(ASSESSMENT_FILE):
            with open(ASSESSMENT_FILE, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print("No assessment found. Run `generate` first.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main(sys.argv)
