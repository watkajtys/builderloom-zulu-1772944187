"""
Reflection Agent Module for BuilderLoom.
Evaluates the outcome of a sprint task to distill persistent technical learnings.
"""

import logging

import google.generativeai as genai
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from loom.agents.base import AgentProxy
from backend.state import BacklogTask

logger = logging.getLogger("loom")

class ReflectionAgent(AgentProxy): # pylint: disable=too-few-public-methods
    """
    An agent that reviews the execution of a task and extracts 
    technical principles and learnings for future iterations.
    """

    def __init__(self, model_name: str = 'gemini-3-flash-preview'):
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
            logger.info("Sending request to Reflection Agent (%s)...", self.model.model_name)
            return self.model.generate_content(content, request_options={"timeout": 360})
        except Exception as e:
            logger.warning("Reflection Agent Gemini call failed (attempting retry): %s", e)
            raise

    def reflect_on_task(
        self, active_task: BacklogTask, happiness_score: float, last_critique: str, app_meta: str
    ) -> str:
        """
        Analyzes the outcome of a task and returns a concise learning summary.
        """
        logger.info("Reflection Agent is distilling learnings from the recent task...")

        reflection_prompt = f"""
You are the Technical Lead for BuilderLoom.
We just completed an execution sprint for the following task: '{active_task.description}'.

OUTCOME:
- Final Score: {happiness_score}/10
- Final Critique: {last_critique}

APP IDENTITY:
{app_meta}

CRITICAL DIRECTIVES:
1. Analyze why this task succeeded or failed based on the critique and score.
2. Formulate a specific, actionable technical principle we should remember for future tasks (e.g., "Always use standard anchor tags instead of window.location for routing", or "The Architect hates when we put state in the root layout").
3. Format your response as a single, concise, professional paragraph.

Provide the learning paragraph below:
"""
        try:
            response = self._generate_content_with_retry(reflection_prompt)
            learnings = response.text.strip()
            return learnings
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Reflection analysis failed: %s", e)
            return "Failed to generate reflection due to an error."
