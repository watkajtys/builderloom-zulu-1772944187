"""
Vibe Agent Module for BuilderLoom.
Provides holistic UX and aesthetic evaluations to ensure the product feels cohesive.
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


class VibeAgent(AgentProxy): # pylint: disable=too-few-public-methods
    """
    An agent that performs holistic UX/UI reviews of the entire application state.
    It generates 'UX Polish' tickets if the app's vibe degrades.
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
        """Helper to call Gemini with robust exponential backoff retries."""
        try:
            logger.info("Sending request to Vibe Agent (%s)...", self.model.model_name)
            return self.model.generate_content(content, request_options={"timeout": 360})
        except Exception as e:
            logger.warning("Vibe Agent Gemini call failed (attempting retry): %s", e)
            raise

    def check_vibe(self, app_screenshot: bytes, app_meta: str) -> List[BacklogTask]:
        """
        Reviews the overall vibe of the app and returns a list of polish tasks if needed.
        """
        logger.info("Vibe Agent is checking the holistic product vibe...")

        prompt = """
You are the Chief Product Officer and Design Lead for BuilderLoom.
The engineering team just finished a sprint. Look at the current state of the application.

APP IDENTITY & PRODUCT GOALS:
[APP_META]

CRITICAL DIRECTIVES:
1. Ignore functional bugs or code structure. Focus purely on the VIBE, the UX friction, and the holistic product experience.
2. DOES IT FEEL AND ACT LIKE A REAL PRODUCT? Are we following the product meta? Are we building in the right direction?
3. ARE THERE GAPS? Are there gaps that you feel or notice in the product logic, copy, or UX?
4. DOES IT MAKE SENSE? Are the core value propositions obvious in the product itself? Are the user flows intuitive, or is the UI confusing, cluttered, or disjointed?
5. If the product vibe and UX are perfectly fine and moving in the right direction, output an empty array [].
6. If there are noticeable product papercuts (e.g. confusing copy, bad spacing, disjointed layout, missing obvious buttons), output 1-3 'Product Polish' tickets to fix them before we build any new features.

Output MUST be a valid JSON array of task objects matching this exact schema:
[
  {
    "description": "Short description of the product/UX issue to fix",
    "target_route": "/",
    "context": "Detailed explanation of why it feels off and exactly how to polish it to elevate the product."
  }
]

Return ONLY the JSON array.
"""
        prompt = prompt.replace("[APP_META]", app_meta)
        content = [prompt, {"mime_type": "image/png", "data": app_screenshot}]

        try:
            response = self._generate_content_with_retry(content)
            text = response.text.strip()

            tasks_data = self._parse_json(text)
            backlog_tasks = []

            for t_data in tasks_data:
                task_id = f"VIBE-{uuid.uuid4().hex[:6].upper()}"

                task = BacklogTask(
                    id=task_id,
                    type=TaskType.REFACTOR,
                    priority=TaskPriority.P1_HIGH,
                    description=t_data.get("description", "UX Polish task"),
                    target_route=t_data.get("target_route", "/"),
                    requires_design=False,
                    context=t_data.get("context", "Vibe check requested polish.")
                )
                backlog_tasks.append(task)

            if backlog_tasks:
                logger.info("Vibe Agent identified %d UX polish tasks.", len(backlog_tasks))
            else:
                logger.info("Vibe Agent: Vibe is immaculate. No polish needed.")

            return backlog_tasks

        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Vibe check failed: %s", e)
            return []
