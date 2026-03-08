"""
Vision Agent Module for BuilderLoom.
Provides AI-driven visual evaluations of UI designs and implementations.
"""

import os
import logging
from typing import Tuple, List, Optional

import google.generativeai as genai
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loom.agents.base import AgentProxy

logger = logging.getLogger("loom")


class VisionAgent(AgentProxy):
    """
    An agent that performs visual reviews of generated designs and application screenshots.
    Evaluates aesthetics, layout cohesion, and thematic alignment.
    """

    def __init__(self, model_name: str = 'gemini-3-flash-preview'):
        self.model = genai.GenerativeModel(model_name)

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=4, max=120),
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
            logger.info("Sending request to Vision (%s)...", self.model.model_name)
            return self.model.generate_content(content, request_options={"timeout": 360})
        except Exception as e:
            logger.warning("Vision Gemini call failed (attempting retry): %s", e)
            raise

    def review_seeds(self, inspiration_goal: str, base_variants: list) -> Tuple[int, str]:
        """Reviews the initial structural hypothesis (seeds) and returns the winning index."""
        prompt = [f"Select the best Structural Hypothesis for: '{inspiration_goal}'.\n\n"
                  "CRITICAL DIRECTIVES:\n"
                  "1. **EMERGENT AESTHETICS:** Prioritize the design that 'feels' the most "
                  "professional and intentional, even if it diverges from its original brief.\n"
                  "2. **PRODUCT SOUL:** Which design feels like it has a point of view? Look for "
                  "superior use of space, visual hierarchy, and a clear 'vibe'.\n"
                  "3. **UTILITY:** Choose the one that feels like a real tool you'd want to use.\n"
                  "\n"
                  "TASK:\n"
                  "1. Analyze the strengths and weaknesses of each design.\n"
                  "2. Explain which one best captures the 'soul' of the product.\n"
                  "3. **QUALITY THRESHOLD:** If NONE of these designs are professional or "
                  "high-quality enough to be the foundation of a real product, output INDEX 0.\n"
                  f"4. Output ONLY the winning integer index (0-{len(base_variants)}) "
                  "on the very last line."]

        content = []
        for idx, var in enumerate(base_variants):
            prompt.append(f"Image {idx+1}: {var['brief']}")
            if var.get("img"):
                content.append({"mime_type": "image/png", "data": var["img"]})

        try:
            review_response = self._generate_content_with_retry([*prompt, *content])
            review_text = review_response.text.strip()
            logger.info("Seed Review Critique:\n%s", review_text)

            try:
                best_base_idx_raw = int(''.join(filter(str.isdigit, review_text.split("\n")[-1])))
            except ValueError:
                best_base_idx_raw = 1  # Default to 1 if we can't parse

            return best_base_idx_raw, review_text
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Seed review failed: %s", e)
            raise

    def review_layouts(self, inspiration_goal: str, valid_layouts: list,
                       baseline_img_path: str) -> Tuple[int, str]:
        """Reviews layout variants against a baseline and returns the winning index."""
        num_variants = len(valid_layouts)
        max_index = num_variants + 1 # Baseline is Image 1
        
        prompt = ["Select the absolute best layout for: '" + inspiration_goal + "'.\n"
                  "Image 1 is your current baseline. Images 2-" + str(max_index) + " are new variations.\n\n"
                  "CRITICAL DIRECTIVES:\n"
                  "1. **BEAUTY & COHESION:** Do not just look for layout changes. Look for the "
                  "variant that is the most visually balanced and 'high-end' in its execution.\n"
                  "2. **THE VIBE CHECK:** The new layout MUST feel native to the baseline shell. While structural "
                  "additions to navigation (like new sidebar items) are acceptable if required by the feature, "
                  "reject any variation that wildly breaks the established color palette or core typography.\n"
                  "3. **INTENTIONALITY:** Which design feels the most like it was crafted by a "
                  "senior designer with a strong vision?\n"
                  "4. **SOUL:** If one design is technically accurate but another 'feels' better, "
                  "choose the one that feels better.\n\n"
                  "TASK:\n"
                  "1. Evaluate the usability, balance, and aesthetic soul of each layout against Image 1.\n"
                  "2. Choose the definitive winner.\n"
                  "3. Output ONLY the winning integer index (1-" + str(max_index) + ") on the very last line."]

        content = []
        if os.path.exists(baseline_img_path):
            with open(baseline_img_path, "rb") as f:
                content.append({"mime_type": "image/png", "data": f.read()})

        for var in valid_layouts:
            content.append({"mime_type": "image/png", "data": var["images"][0]})

        try:
            review_response = self._generate_content_with_retry([*prompt, *content])
            review_text = review_response.text.strip()
            logger.info("Layout Review Critique:\n%s", review_text)

            best_idx = int(''.join(filter(str.isdigit, review_text.split("\n")[-1])))
            return best_idx, review_text
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Layout review failed: %s", e)
            raise

    def review_themes(self, inspiration_goal: str, valid_themes: list,
                      baseline_img_path: str) -> Tuple[int, str, Optional[str]]:
        """Reviews color and typography variants against a baseline layout."""
        prompt = [f"Select the absolute best visual theme for: '{inspiration_goal}'.\n"
                  "Image 1 is your current baseline. Images 2-6 are new explorations.\n\n"
                  "CRITICAL DIRECTIVES:\n"
                  "1. **VISUAL GRAVITAS:** Prioritize the theme that gives the product "
                  "the most weight and professional 'polish'.\n"
                  "2. **EMERGENT VIBE:** Which combination of colors and type feels the most "
                  "'right' for this specific product's soul?\n"
                  "3. **COHESION:** Look for harmony between the layout and the new theme.\n\n"
                  "TASK:\n"
                  "1. Pick the best theme.\n"
                  "2. Define [APP_META] (Name, Palette, Typography) for this winning choice.\n"
                  "3. Output the winning integer index (1-6) on the very last line."]

        content = []
        if os.path.exists(baseline_img_path):
            with open(baseline_img_path, "rb") as f:
                content.append({"mime_type": "image/png", "data": f.read()})

        for var in valid_themes:
            content.append({"mime_type": "image/png", "data": var["images"][0]})

        try:
            review_response = self._generate_content_with_retry([*prompt, *content])
            review_text = review_response.text.strip()
            logger.info("Theme Review Critique:\n%s", review_text)

            app_meta = None
            if "[APP_META]" in review_text:
                meta_part = review_text.split("[APP_META]")[1]
                if "[" in meta_part:
                    app_meta = meta_part.split("[")[0].strip()
                else:
                    app_meta = meta_part.strip()

            best_idx = int(''.join(filter(str.isdigit, review_text.split("\n")[-1])))
            return best_idx, review_text, app_meta
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Theme review failed: %s", e)
            raise

    # pylint: disable=too-many-arguments, too-many-locals, too-many-positional-arguments
    def evaluate_happiness(self, app_screenshot: bytes, ref_images: List[bytes],
                           app_meta: str, inspiration_goal: str, target_route: str,
                           console_logs: Optional[List[str]] = None) -> Tuple[float, str]:
        """Compares the actual running app against the target design reference to score it."""
        prompt = [
            f"You are the Overseer. Your goal was to implement: '{inspiration_goal}'.\n",
            f"App Identity (Meta): {app_meta}\n",
            f"Target Route: {target_route}\n",
            "The first image is the actual React app running."
        ]
        content = [{"mime_type": "image/png", "data": app_screenshot}]

        if ref_images:
            prompt.append(f"The following {len(ref_images)} images are the target design references"
                          " we are trying to achieve (Desktop, Mobile, or variants).")
            for img_bytes in ref_images[:5]:  # Limit to 5 images to avoid token blowup
                content.append({"mime_type": "image/png", "data": img_bytes})

        prompt.append("Score how well the actual app matches the target design and the core App "
                      "Identity from 0 to 10. Pay special attention to whether the new feature was "
                      "integrated correctly without destroying existing UI.\n"
                      "CRITICAL: Focus strictly on visuals, layout, and cohesion. DO NOT critique "
                      "the code structure or architecture.\n"
                      "Output the integer score using the exact tag `[VISION_SCORE]: X` on its own line, "
                      "followed by your brief critique.")

        if console_logs:
            logs_str = "\n".join(console_logs[:20])  # Limit to 20 lines
            prompt.append("\nCRITICAL: The browser console reported the following logs/errors. "
                          f"Factor these heavily into your score and critique:\n{logs_str}")

        try:
            response = self._generate_content_with_retry([*prompt, *content])
            critique = response.text.strip()
            logger.info("Vision Evaluation Critique:\n%s", critique)

            score = self._parse_score(critique, "[VISION_SCORE]")
            score = max(0.0, min(10.0, score))
            return score, critique
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Vision evaluation failed: %s", e)
            return 5.0, f"Vision evaluation failed: {str(e)}"
