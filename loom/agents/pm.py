"""
Product Manager (PM) Agent Module for BuilderLoom.
Translates high-level product roadmaps into actionable Kanban backlog tasks.
"""

import json
import logging
import uuid
from typing import List

import google.generativeai as genai
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from loom.agents.base import AgentProxy
from backend.state import BacklogTask, TaskType, TaskPriority

logger = logging.getLogger("loom")

class PMAgent(AgentProxy): # pylint: disable=too-few-public-methods
    """
    An agent that acts as a Product Manager. It reads the overall project roadmap
    and generates specific, micro-level execution tasks for the Backlog.
    """

    def __init__(self, model_name: str = 'gemini-3.1-pro-preview'):
        self.model = genai.GenerativeModel(model_name)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=(
            retry_if_exception_type(exceptions.DeadlineExceeded) |
            retry_if_exception_type(exceptions.ServiceUnavailable) |
            retry_if_exception_type(exceptions.InternalServerError) |
            retry_if_exception_type(exceptions.ResourceExhausted)
        ),
        reraise=True
    )
    def _generate_content_with_retry(self, content):
        try:
            logger.info("Sending request to PM Agent (%s)...", self.model.model_name)
            return self.model.generate_content(content, request_options={"timeout": 360})
        except Exception as e:
            logger.warning("PM Agent Gemini call failed (attempting retry): %s", e)
            raise

    def breakdown_task_if_needed(self, task: BacklogTask) -> dict:
        """
        Evaluates a single task. If it's too large, breaks it down into smaller BacklogTasks.
        """
        logger.info(f"PM Agent scoping task: {task.id}")

        prompt = """
You are an elite Engineering Manager. Review this pending task:

TASK DESCRIPTION:
[TASK_DESCRIPTION]

YOUR OBJECTIVE:
1. Determine if this task is too large to be completed in a SINGLE, focused pull request by an AI coder (touching <3 files).
2. Validate if the task is technically sound and relevant to the product. If it is non-sensical, non-technical (e.g. "make me a sandwich"), or completely out of scope, you should DISCARD it.

- If it is small and atomic (e.g., "Add a button", "Create a single API route"), return:
{ "action": "proceed" }

- If it is large, complex, or multi-step, break it down into 2-4 sequential sub-tasks:
{ "action": "breakdown", "tasks": [...] }

- If it is invalid, non-technical, or redundant, return:
{ "action": "discard", "reason": "Explanation of why this task is invalid" }

Output MUST be a valid JSON object matching this exact schema:
{
  "action": "proceed" | "breakdown" | "discard",
  "reason": "Optional reason for discard",
  "tasks": [
    {
      "type": "feature" | "refactor" | "bugfix",
      "priority": 1 | 2,
      "description": "Sub-task description",
      "requires_design": boolean,
      "requires_data_change": boolean,
      "context": "Context for the engineer"
    }
  ]
}

Return ONLY the JSON.
"""
        prompt = prompt.replace("[TASK_DESCRIPTION]", task.description)
        try:
            response = self._generate_content_with_retry(prompt)
            text = response.text.strip()

            result = self._parse_json(text)
            
            if result.get("action") == "breakdown":
                subtasks = []
                for t_data in result.get("tasks", []):
                    task_id = f"TASK-{uuid.uuid4().hex[:6].upper()}"
                    
                    # Only pass the data_model to subtasks that actually need it
                    # If the subtask doesn't explicitly mention needing a data model change, 
                    # we prefer null to reduce noise.
                    inherited_model = task.data_model if t_data.get("requires_data_change") else None
                    
                    subtask = BacklogTask(
                        id=task_id,
                        type=t_data.get("type", TaskType.FEATURE),
                        priority=task.priority,
                        description=t_data.get("description", ""),
                        target_route=task.target_route,
                        data_model=inherited_model,
                        requires_design=t_data.get("requires_design", False),
                        context=t_data.get("context", "")
                    )
                    subtasks.append(subtask)
                return {"action": "breakdown", "tasks": subtasks}
                
            return {"action": "proceed"}

        except Exception as e:
            import traceback
            logger.error(f"PM Agent failed to scope task: {e}\n{traceback.format_exc()}")
            return {"action": "proceed"}

    # pylint: disable=too-many-locals
    def plan_next_sprint(
        self, app_meta: str, roadmap: str, past_learnings: str = ""
    ) -> List[BacklogTask]:
        """
        Translates the high-level roadmap into 3-5 concrete BacklogTask objects.
        """
        logger.info("PM Agent is planning the next sprint based on the roadmap...")

        prompt = """
You are the elite Product Manager for BuilderLoom.
Your job is to read the macro-level ROADMAP and generate the next micro-level Kanban sprint.

APP IDENTITY:
[APP_META]

ROADMAP:
[ROADMAP]

PAST LEARNINGS (Context):
[PAST_LEARNINGS]

CRITICAL DIRECTIVES:
1. Identify the *current* active phase of the roadmap. Do not generate tasks for future phases yet.
2. Break that phase down into 3-5 sequential, atomic engineering tasks.
3. Keep the scope of each task extremely small. "Build a login page" is too big. "Implement the Login UI layout", "Implement PocketBase Auth Hook", "Wire Login UI to Auth Hook" are better.
4. If a task requires a visual layout/UI, set `requires_design` to true. If it is purely state management or API logic, set it to false.
5. DATA MODEL SELECTION: Set `data_model` to the relevant JSON schema ONLY if the task requires creating new database tables or modifying existing ones. If the task is purely UI refinement, logic, or using existing tables, set `data_model` to null.
6. All tasks you generate MUST have `priority: 1` (P1_HIGH) or `priority: 2` (P2_NORMAL).

Output MUST be a valid JSON array of task objects matching this exact schema:
[
  {
    "type": "feature",
    "priority": 1,
    "description": "Short description of the task",
    "target_route": "/login",
    "data_model": "Optional JSON schema if this requires a new database table, else null",
    "requires_design": true,
    "test_scenario": "User fills out form and clicks submit, verifying state updates",
    "context": "Any extra notes for the Engineer"
  }
]

Return ONLY the JSON array.
"""
        prompt = prompt.replace("[APP_META]", app_meta)
        prompt = prompt.replace("[ROADMAP]", roadmap)
        prompt = prompt.replace("[PAST_LEARNINGS]", past_learnings)

        try:
            response = self._generate_content_with_retry(prompt)
            text = response.text.strip()

            tasks_data = self._parse_json(text)
            backlog_tasks = []

            for t_data in tasks_data:
                # Generate a unique ID
                task_id = f"TASK-{uuid.uuid4().hex[:6].upper()}"

                # Map integer priorities to the Enum
                priority_int = t_data.get("priority", 1)
                priority = TaskPriority.P1_HIGH
                if priority_int == 2:
                    priority = TaskPriority.P2_NORMAL
                elif priority_int == 0:
                    priority = TaskPriority.P0_CRITICAL

                # Validate type
                task_type_str = t_data.get("type", "feature").lower()
                if task_type_str == "refactor":
                    task_type = TaskType.REFACTOR
                elif task_type_str == "bugfix":
                    task_type = TaskType.BUGFIX
                else:
                    task_type = TaskType.FEATURE

                task = BacklogTask(
                    id=task_id,
                    type=task_type,
                    priority=priority,
                    description=t_data.get("description", "Unknown task"),
                    target_route=t_data.get("target_route", "/"),
                    data_model=t_data.get("data_model"),
                    requires_design=t_data.get("requires_design", True),
                    test_scenario=t_data.get("test_scenario", ""),
                    context=t_data.get("context", ""),
                    status="todo"
                )
                backlog_tasks.append(task)

            logger.info("PM Agent generated %d new tasks.", len(backlog_tasks))
            return backlog_tasks

        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("PM Agent failed to generate sprint plan: %s", e)
            return []
