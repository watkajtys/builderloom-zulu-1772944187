"""
Architect Agent Module for BuilderLoom.
Provides an AI-driven architectural reviewer that analyzes React codebases.
"""

import os
import json
import logging
from typing import Tuple, List, Dict

import google.generativeai as genai
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loom.agents.base import AgentProxy

logger = logging.getLogger("loom")


class ArchitectAgent(AgentProxy): # pylint: disable=too-few-public-methods
    """
    An agent that performs architectural reviews of the codebase using an LLM.
    It generates a dependency graph and evaluates modularity, bloat, and best practices.
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
            logger.info("Sending request to Architect (%s)...", self.model.model_name)
            return self.model.generate_content(content, request_options={"timeout": 360})
        except Exception as e:
            logger.warning("Architect Gemini call failed (attempting retry): %s", e)
            raise

    def _get_dependency_graph(self, app_dir: str) -> str:
        """Runs madge to extract a JSON representation of the AST dependency graph."""
        logger.info("Extracting AST Dependency Graph via Madge...")
        try:
            # We run it inside app_dir/src specifically to keep the graph focused on source files
            src_dir = os.path.join(app_dir, "src")
            if not os.path.exists(src_dir):
                return "{}"

            # Using npx --yes to auto-install madge if it's somehow missing
            # Using --ts-config if we wanted to be super strict, but default is fine for Vite
            output = self._run(["npx", "--yes", "madge", "--json", "src/"], cwd=app_dir)

            # The output of madge --json might have npm warnings. We extract just the JSON.
            try:
                # Find the first { and last }
                start_idx = output.find('{')
                end_idx = output.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    clean_json = output[start_idx:end_idx+1]
                    parsed = json.loads(clean_json)
                    return json.dumps(parsed, indent=2)
            except json.JSONDecodeError as parse_e:
                logger.warning("Failed to parse Madge JSON output: %s", parse_e)

            return "{}"
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Failed to generate dependency graph: %s", e)
            return "{}"

    def _gather_source_code(self, app_dir: str) -> Tuple[str, int, dict]:
        """Reads all source files and package.json to prepare for evaluation."""
        source_code = ""
        total_files = 0
        largest_file = {"name": "", "lines": 0}

        for root, _, files in os.walk(os.path.join(app_dir, "src")):
            for file in files:
                if file.endswith(('.tsx', '.ts', '.jsx', '.js', '.css')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            line_count = len(content.splitlines())
                            total_files += 1

                            if line_count > largest_file["lines"]:
                                largest_file = {"name": file, "lines": line_count}

                            rel_path = os.path.relpath(file_path, app_dir)
                            source_code += (
                                f"\n--- {rel_path} ({line_count} lines) ---\n"
                                f"```\n{content}\n```\n"
                            )
                    except OSError as read_e:
                        logger.debug("Failed to read file %s: %s", file_path, read_e)

        try:
            with open(os.path.join(app_dir, "package.json"), "r", encoding="utf-8") as f:
                pkg_json_content = f.read()
                source_code += f"\n--- package.json ---\n```json\n{pkg_json_content}\n```\n"
        except OSError:
            logger.debug("package.json not found or not readable.")

        return source_code, total_files, largest_file

    def evaluate(self, app_meta: str, app_dir: str = "app") -> Tuple[float, str, List[Dict]]:
        """
        Evaluates the full codebase architecture by generating a dependency graph,
        collecting source code, and requesting an architectural review from the LLM.
        """
        logger.info("Evaluating full codebase architecture...")
        try:
            source_code, total_files, largest_file = self._gather_source_code(app_dir)
            dependency_graph = self._get_dependency_graph(app_dir)

            metrics_summary = (
                "SYSTEM ARCHITECTURE METRICS:\n"
                f"- Total Source Files: {total_files}\n"
                f"- Largest File: {largest_file['name']} ({largest_file['lines']} lines)\n"
            )

            prompt = """
You are an expert Principal Software Engineer acting as the Architectural Reviewer for BuilderLoom.
The application is built using React, Vite, and Tailwind CSS.
App Identity & Core Architecture: [APP_META]

Please review the provided system metrics, dependency graph, and raw codebase below.

[METRICS_SUMMARY]

--- DEPENDENCY GRAPH (AST Map) ---
[DEPENDENCY_GRAPH]

Evaluate the architecture based on:
1. Modularity & Coupling: Analyze the DEPENDENCY GRAPH. Are there deep circular dependencies? Does a single file act as a bottleneck importing too many unrelated modules (Spaghetti Code)?
2. Component Bloat: Look at the file line counts in the headers. Does the codebase rely on massive "God Components" instead of breaking UI and logic down contextually?
3. Technical best practices (React hooks, state management, pure functions).
4. Maintainability, readability, and file structure.
5. Alignment with the App Identity/Architecture defined above.

Provide a highly technical architectural critique. Focus strictly on the code quality, structural coupling, and bloat.
CRITICAL: You are a strict Grumpy Senior Architect. You MUST deduct points if you see clear evidence of "God Components", excessive coupling, bad naming, or missing types.

If you detect major refactoring needs, DO NOT JUST COMPLAIN. Provide a prioritized action plan.
Output MUST be strictly valid JSON in the following format:
{
  "score": 7,
  "critique": "Overall good, but App.tsx is a God Component.",
  "refactoring_priorities": [
    {"priority": 0, "description": "Extract Profile components from App.tsx"},
    {"priority": 1, "description": "Move db connection logic to a dedicated module"}
  ]
}
Note: Priority 0 is CRITICAL (must fix now), Priority 1 is HIGH, Priority 2 is NORMAL.

FULL CODEBASE:
[SOURCE_CODE_PLACEHOLDER]
"""
            prompt = prompt.replace("[APP_META]", app_meta)
            prompt = prompt.replace("[METRICS_SUMMARY]", metrics_summary)
            prompt = prompt.replace("[DEPENDENCY_GRAPH]", dependency_graph)
            prompt = prompt.replace("[SOURCE_CODE_PLACEHOLDER]", source_code)
            
            review_response = self._generate_content_with_retry(prompt)
            review_text = review_response.text.strip()
            
            logger.info("Architectural Critique:\n%s", review_text)

            try:
                data = self._parse_json(review_text)
                score = float(data.get("score", 5.0))
                critique = data.get("critique", "No critique provided.")
                priorities = data.get("refactoring_priorities", [])
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning("Failed to parse Architect JSON: %s", e)
                score = 5.0
                critique = review_text
                priorities = []

            score = max(1.0, min(10.0, score))
            return score, critique, priorities

        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Failed to evaluate architecture: %s", e)
            return 5.0, f"Architectural evaluation failed: {str(e)}", []
