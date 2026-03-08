import os
import json
import pytest
<<<<<<< ours
from backend.state import ConductorState, BacklogTask, TaskType, TaskPriority
import backend.state

# Ensure files are cleared before and after each test
@pytest.fixture(autouse=True)
def clean_state_files():
    # Setup
    backend.state._global_state = None
    if os.path.exists("session_state.json"):
        os.remove("session_state.json")
    if os.path.exists("execution_state.json"):
        os.remove("execution_state.json")
    
    yield
    
    # Teardown
    backend.state._global_state = None
    if os.path.exists("session_state.json"):
        os.remove("session_state.json")
    if os.path.exists("execution_state.json"):
        os.remove("execution_state.json")

def test_state_instantiation_and_dump():
    # Ensure it's empty to start
    assert backend.state._global_state is None

    # Load should instantiate a new state since files were removed
    state = ConductorState.load()
    assert state is not None
    assert state.schema_version == "1.0.0"
    
    # Modify state
    state.project_name = "Test Project"
    
    # Save to disk
    state.save()
    
    # Verify files exist
    assert os.path.exists("session_state.json")
    assert os.path.exists("execution_state.json")
    
    # Verify the saved content using native JSON load
    with open("session_state.json", "r", encoding="utf-8") as f:
        session_data = json.load(f)
        assert session_data["project_name"] == "Test Project"
        # Since exclude was used, ensure ui_containers doesn't exist here
        assert "ui_containers" not in session_data
        
    with open("execution_state.json", "r", encoding="utf-8") as f:
        exec_data = json.load(f)
        assert exec_data["schema_version"] == "1.0.0"
        # Make sure ui components exist in execution
        assert "ui_containers" in exec_data
        assert "ui_agents" in exec_data
        assert "ui_metrics" in exec_data

from loom.core.overseer import Overseer

class MockOverseer(Overseer):
    """Subclass to override external dependencies like git, generative AI setup, and long-running loops."""
    def __init__(self):
        # Instead of calling super().__init__() and letting it setup real clients,
        # we will selectively mock properties and just load state.
        self.state = ConductorState.load()
        self.state.shutdown_requested = False
        
        # Add a backlog task so it does something
        self.state.backlog.append(
            BacklogTask(
                id="TEST-TASK-1",
                type=TaskType.FEATURE,
                priority=TaskPriority.P0_CRITICAL,
                description="Mock test task"
            )
        )
        self.state.save()
        
        # Mock external dependencies used in triage
        class MockGit:
            def checkout_branch(self, branch): pass
        self.git = MockGit()
        
        class MockPM:
            def breakdown_task_if_needed(self, task): return {"action": "proceed"}
        self.pm = MockPM()

    def loop(self):
        """A single iteration loop that doesn't run forever."""
        # Just run the triage step instead of full loop
        try:
            self._step_triage()
            # If we successfully triage, we would have picked up the task
            assert self.state.active_task_id == "TEST-TASK-1"
            assert self.state.current_status != "CRITICAL_ERROR"
        except Exception as e:
            pytest.fail(f"Loop iteration raised an unexpected exception: {e}")

def test_overseer_initialization_and_loop_iteration():
    # The Overseer relies on external APIs in normal execution,
    # so we test the subclass which mocks out the problematic network setups
    mock_overseer = MockOverseer()
    
    # Run a single loop iteration and verify it handles it without crashing
    mock_overseer.loop()
=======
from unittest.mock import MagicMock
from backend.state import ConductorState
import backend.state
from loom.core.overseer import Overseer

def test_state_json_schema_output(tmp_path, monkeypatch):
    # Change current working directory to temp so we don't pollute the real files
    monkeypatch.setattr(backend.state, 'STATE_FILE', tmp_path / "session_state.json")
    monkeypatch.setattr(backend.state, 'EXECUTION_STATE_FILE', tmp_path / "execution_state.json")
    
    state = ConductorState.reset()
    state.save()
    
    assert (tmp_path / "session_state.json").exists()
    assert (tmp_path / "execution_state.json").exists()
    
    with open(tmp_path / "session_state.json", "r") as f:
        session_data = json.load(f)
        
    with open(tmp_path / "execution_state.json", "r") as f:
        execution_data = json.load(f)
        
    assert session_data.get("schema_version") == "1.0.0"
    assert execution_data.get("schema_version") == "1.0.0"
    
    # Check that UI properties are in execution_state but not in session_state
    assert "ui_containers" in execution_data
    assert "ui_agents" in execution_data
    assert "ui_metrics" in execution_data
    
    assert "ui_containers" not in session_data
    assert "ui_agents" not in session_data
    assert "ui_metrics" not in session_data

class MockOverseer(Overseer):
    def __init__(self):
        self.state = ConductorState.reset()
        self.git = MagicMock()
        self.phoenix = MagicMock()
        self.jules = MagicMock()
        self.stitch = MagicMock()
        self.current_iteration_record = None
        self.happiness_score = 0
        self.last_critique = ""
        self.app_screenshot = None
        self.app_screenshot_path = None
        self.patch_dest_rel = None
        self.lab_memory = {}
        
        self.model = MagicMock()
        self.architect = MagicMock()
        self.vision = MagicMock()
        self.pm = MagicMock()
        self.vibe = MagicMock()
        self.reflection = MagicMock()
        self.pb_url = "http://localhost:8090"

    def ensure_scaffold(self):
        pass

def test_overseer_error_catching_logic(tmp_path, monkeypatch):
    monkeypatch.setattr(backend.state, 'STATE_FILE', tmp_path / "session_state.json")
    monkeypatch.setattr(backend.state, 'EXECUTION_STATE_FILE', tmp_path / "execution_state.json")
    
    overseer = MockOverseer()
    # Mock consume_steering to raise an exception and trigger the error boundary
    overseer._consume_steering = MagicMock(side_effect=Exception("Simulated error for telemetry test"))
    
    overseer.loop()
    
    assert overseer.state.current_status == "CRITICAL_ERROR"
    assert overseer.state.shutdown_requested is True
    assert any("TELEMETRY_ERROR: Critical agent loop exception: Simulated error for telemetry test" in log for log in overseer.state.live_logs)

>>>>>>> theirs
