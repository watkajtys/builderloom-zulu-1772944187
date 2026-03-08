
import os
import sys

from loom.core.overseer import Overseer
from backend.state import ConductorState, BacklogTask, TaskType, TaskPriority

class FaultyOverseer(Overseer):
    # We bypass environment check like git since we just want to verify the exception handling
    def loop(self):
        self.state = ConductorState.load()
        while True:
            try:
                # Mock a runtime exception as if an agent node failed
                raise RuntimeError("Intentional Agent Node Failure")
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                import logging
                logger = logging.getLogger("loom")
                logger.error(f"Critical loop error: {e}\n{error_trace}")
                self.state.add_log(f"TELEMETRY_ERROR: Critical agent loop exception: {e}")
                self.state.current_status = "CRITICAL_ERROR"
                self.state.shutdown_requested = True
                self.state.save()
                break

try:
    o = FaultyOverseer()
    o.loop()
except Exception as e:
    pass
