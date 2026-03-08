# BuilderLoom Self-Improvement Roadmap

## Phase 1: Diagnostics and Safety
- Analyze the core overseer loop and agent boundaries.
- Implement better error handling and telemetry inside Python agent nodes to prevent silent loops.
- Add unit tests for state.py and overseer.py using pytest.

## Phase 2: Agent Autonomy
- Enhance PM Agent to self-correct invalid tasks instead of just discarding them.
- Give the Architect Agent the ability to read project-level files like 
equirements.txt to suggest better libraries.

## Phase 3: UI Enhancement
- Refactor the React Viewer (iewer/index.html) to display the live state of multiple nested tasks.
- Add visual indicators for the current execution phase.
