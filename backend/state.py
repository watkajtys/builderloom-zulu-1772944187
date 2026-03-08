import logging
import os
import shutil
import threading
import time
from enum import Enum
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger("loom")
STATE_FILE = Path("session_state.json")
EXECUTION_STATE_FILE = Path("execution_state.json")

class TaskPriority(int, Enum):
    P0_CRITICAL = 0
    P1_HIGH = 1
    P2_NORMAL = 2

class TaskType(str, Enum):
    FEATURE = "feature"
    REFACTOR = "refactor"
    BUGFIX = "bugfix"

class BacklogTask(BaseModel):
    id: str
    type: TaskType
    priority: TaskPriority
    description: str
    target_route: str = "/"
    data_model: Optional[str] = None
    requires_design: bool = True
    test_scenario: str = ""
    context: str = ""
    status: str = "todo"

class AttemptRecord(BaseModel):
    attempt_number: int
    prompt_used: str
    app_screenshot_path: Optional[str] = None
    jules_patch_path: Optional[str] = None
    jules_url: Optional[str] = None
    jules_action: Optional[str] = None
    score: int
    critique: str

class LoopIteration(BaseModel):
    id: int
    timestamp: str
    goal: str
    target_route: str = "/"
    data_model: Optional[str] = None
    requires_design: bool = True
    test_scenario: Optional[str] = None
    negative_history: List[str] = []
    brainstorming_output: Optional[str] = None
    base_briefs: List[str] = []
    base_seed_paths: List[Optional[str]] = []
    base_variants_data: Optional[List[dict]] = None
    seed_review_critique: Optional[str] = None
    design_screenshot_path: Optional[str] = None
    design_variants_paths: List[Optional[str]] = []
    layout_review_critique: Optional[str] = None
    chosen_design_path: Optional[str] = None
    design_review_critique: Optional[str] = None
    theme_variants_paths: List[Optional[str]] = []
    chosen_theme_path: Optional[str] = None
    theme_review_critique: Optional[str] = None
    attempts: List[AttemptRecord] = []
    happiness_score: int = 0  # Final score of this iteration
    successful_branch: Optional[str] = None
    abandoned: bool = False
    architectural_critique: Optional[str] = None
    reflection_learnings: Optional[str] = None
    git_commit: Optional[str] = None

_global_state = None
_state_lock = threading.RLock()

class ConductorState(BaseModel):
    schema_version: str = "1.0.0"
    project_name: str = "Loom Experiment"
    app_meta: str = ""
    product_phase: str = "Phase 1: Core Loop MVP"
    product_roadmap: str = ""
    repo_memory: dict = {}
    current_iteration: int = 0
    active_branch: str = "main"
    
    # Kanban State
    backlog: List[BacklogTask] = []
    active_task_id: Optional[str] = None
    
    # Legacy fields kept temporarily for backward compatibility with in-flight code
    inspiration_goal: str = ""
    inspiration_target_route: str = "/"
    inspiration_data_model: Optional[str] = None
    inspiration_requires_design: bool = True
    inspiration_mode: str = "design"
    inspiration_test_scenario: str = ""
    
    history: List[LoopIteration] = []
    stitch_project_id: Optional[str] = None
    stitch_screen_id: Optional[str] = None
    active_jules_prompt: Optional[str] = None
    active_jules_url: Optional[str] = None
    active_jules_action: Optional[str] = None
    current_status: str = "Idle"
    current_phase: str = "Inspiration"
    pending_steer: List[str] = []
    steering_history: List[dict] = []
    live_logs: List[str] = []
    shutdown_requested: bool = False
    update_scheduled: bool = False
    db_stats: dict = {}
    
    ui_containers: List[dict] = []
    ui_agents: List[dict] = []
    ui_metrics: dict = {}
    
    def prepare_ui_data(self):
        system_health = 0 if self.shutdown_requested else 100
        
        self.ui_containers = [
            { "id": "1", "name": "loom-pocketbase", "status": "running" if system_health > 0 else "stopped", "image": "pocketbase/pocketbase", "ports": ["8090:8090"] },
            { "id": "2", "name": "loom-python", "status": "running", "image": "python:3.11-slim", "ports": ["8080:8080"] },
            { "id": "3", "name": "loom-react", "status": "stopped" if self.shutdown_requested else "running", "image": "node:20-alpine", "ports": ["5173:5173"] }
        ]
        
        agents = []
        if self.active_jules_action or self.current_status == 'Active':
            agents.append({
                "agentId": "jules-alpha",
                "state": "coding" if self.active_jules_action else "idle",
                "currentTask": f"Task {self.active_task_id}" if self.active_task_id else self.current_phase,
                "happinessScore": self.history[-1].happiness_score if self.history else 8
            })
        else:
            agents.append({
                "agentId": "jules-alpha",
                "state": "idle",
                "currentTask": "Waiting for task",
                "happinessScore": 10
            })
            
        agents.append({
            "agentId": "overseer-beta",
            "state": "reflecting" if self.current_phase == 'Reflection' else "idle",
            "currentTask": f"Phase: {self.current_phase}",
            "happinessScore": 10
        })
        self.ui_agents = agents
        
        self.ui_metrics = {
            "activeContainers": 1 if self.shutdown_requested else 3,
            "agentCount": 2,
            "systemHealth": system_health
        }

    def save(self):
        with _state_lock:
            self.prepare_ui_data()
            
            # Save Execution State independently
            tmp_exec_file = EXECUTION_STATE_FILE.with_suffix(f'.tmp.{threading.get_ident()}.json')
            try:
                with open(tmp_exec_file, "w", encoding="utf-8") as f:
                    # Use Pydantic's native JSON dump to safely serialize enums, datetimes, etc.
                    f.write(self.model_dump_json(indent=2, include={'schema_version', 'ui_containers', 'ui_agents', 'ui_metrics'}))
                os.replace(tmp_exec_file, EXECUTION_STATE_FILE)
            except Exception as e:
                print(f"Warning: Failed to save execution state to disk: {e}")
            finally:
                if tmp_exec_file.exists():
                    try: os.remove(tmp_exec_file)
                    except: pass
            
            # Use a thread-specific temp file to prevent multiple threads from writing to the same file before replacing
            tmp_file = STATE_FILE.with_suffix(f'.tmp.{threading.get_ident()}.json')
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    # We no longer strictly need ui_* in the main file since we split it out,
                    # but leaving it in `self.model_dump_json` is fine as legacy fields if needed
                    # However, to strictly adhere to separating them, we could dump `exclude={'ui_containers', 'ui_agents', 'ui_metrics'}`
                    f.write(self.model_dump_json(indent=2, exclude={'ui_containers', 'ui_agents', 'ui_metrics'}))
                
                # Windows specific: retry replace if file is locked
                max_retries = 20
                for i in range(max_retries):
                    try:
                        os.replace(tmp_file, STATE_FILE)
                        break
                    except OSError as e:
                        if i == max_retries - 1:
                            raise e
                        # Gradually increase sleep time
                        time.sleep(0.05 * (i + 1))
            except Exception as e:
                # Using print instead of logger to prevent infinite recursion with StateLogHandler
                print(f"Warning: Failed to save state to disk (likely locked by viewer): {e}")
            finally:
                if tmp_file.exists():
                    try:
                        os.remove(tmp_file)
                    except:
                        pass
    
    def add_log(self, log_line: str):
        with _state_lock:
            self.live_logs.append(log_line)
            if len(self.live_logs) > 500:
                self.live_logs = self.live_logs[-500:]
            self.save()

    @classmethod
    def reset(cls):
        """Wipes the in-memory global state."""
        global _global_state
        with _state_lock:
            _global_state = cls(live_logs=[])
            return _global_state

    @classmethod
    def load(cls) -> 'ConductorState':
        global _global_state
        with _state_lock:
            if _global_state is not None:
                return _global_state
            
            # Robust initialization to prevent directory-mount errors
            if STATE_FILE.exists() and STATE_FILE.is_dir():
                import shutil
                shutil.rmtree(STATE_FILE)
            
            if STATE_FILE.exists():
                # Retry load if file is temporarily locked (e.g. by save process rename)
                max_retries = 10
                for i in range(max_retries):
                    try:
                        with open(STATE_FILE, "r", encoding="utf-8") as f:
                            _global_state = cls.model_validate_json(f.read())
                            return _global_state
                    except (OSError, Exception) as e:
                        if i == max_retries - 1:
                            print(f"Warning: Failed to load state after {max_retries} attempts: {e}. Starting fresh.")
                            break
                        time.sleep(0.05 * (i + 1))
            _global_state = cls()
            return _global_state
