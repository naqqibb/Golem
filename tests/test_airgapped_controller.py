import json
import os
import tempfile
from datetime import datetime

import pytest

import importlib


@pytest.fixture
def temp_cwd(tmp_path, monkeypatch):
    # Create a temporary working directory and switch
    p = tmp_path / "work"
    p.mkdir()
    monkeypatch.chdir(p)
    yield p


def test_generate_and_process(tmp_path, monkeypatch, capsys):
    # Import module after changing cwd so BASE_DIR uses tmp path
    import golem668.airgapped_controller as ac

    # override BASE_DIR and derived paths to tmpdir
    ac.BASE_DIR = str(tmp_path)
    ac.QUEUE_DIR = os.path.join(ac.BASE_DIR, "golem_queue")
    ac.PENDING_DIR = os.path.join(ac.QUEUE_DIR, "pending")
    ac.PROCESSED_DIR = os.path.join(ac.QUEUE_DIR, "processed")
    ac.ASSESSMENT_FILE = os.path.join(ac.QUEUE_DIR, "latest_assessment.json")
    ac.INDEX_FILE = os.path.join(ac.QUEUE_DIR, "index.json")

    # Generate assessment and enqueue tasks
    assessment = ac.synthesize({})
    assert os.path.exists(ac.ASSESSMENT_FILE)

    # Ensure pending tasks exist
    pending = [f for f in os.listdir(ac.PENDING_DIR) if f.endswith('.task')]
    assert len(pending) == len(assessment['tasks'])

    # Process one task
    ac.process_next()
    processed = [f for f in os.listdir(ac.PROCESSED_DIR) if f.endswith('.processed')]
    assert len(processed) == 1

    # Index should be updated
    idx = ac.load_index()
    assert isinstance(idx, dict)


def test_enqueue_custom_task(tmp_path):
    import golem668.airgapped_controller as ac
    ac.BASE_DIR = str(tmp_path)
    ac.QUEUE_DIR = os.path.join(ac.BASE_DIR, "golem_queue")
    ac.PENDING_DIR = os.path.join(ac.QUEUE_DIR, "pending")
    ac.PROCESSED_DIR = os.path.join(ac.QUEUE_DIR, "processed")
    ac.ASSESSMENT_FILE = os.path.join(ac.QUEUE_DIR, "latest_assessment.json")
    ac.INDEX_FILE = os.path.join(ac.QUEUE_DIR, "index.json")

    # Ensure clean dirs
    ac.ensure_dirs()
    # create custom task
    item = ac.TaskItem(
        sort_index=(ac.PRIORITY_MAP['medium'], 1.0),
        id='test-task-1234',
        priority='medium',
        owner='tester',
        task='Do a local check',
        tags=['unit'],
        created_at=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        due=None,
    )
    ac.enqueue_task(item)
    # verify file and index
    assert os.path.exists(os.path.join(ac.PENDING_DIR, 'test-task-1234.task'))
    idx = ac.load_index()
    assert 'test-task-1234' in idx.get('tasks', {})
