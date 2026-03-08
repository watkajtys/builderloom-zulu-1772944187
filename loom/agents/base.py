import logging
import subprocess
import os
import json
import re
from typing import List, Any, Optional

logger = logging.getLogger("loom")

class AgentProxy:
    def _run(self, command: List[str], cwd: str = ".", quiet: bool = False, check: bool = True) -> str:
        logger.info(f"Running: {' '.join(command)}")
        try:
            result = subprocess.run(
                command, 
                cwd=cwd, 
                capture_output=True, 
                text=True, 
                check=check,
                shell=(os.name == 'nt'),
                timeout=600 # 10 minute timeout
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if not quiet:
                logger.error(f"Command failed: {e.stderr or e.stdout}")
            else:
                logger.debug(f"Command failed (quiet mode): {e.stderr or e.stdout}")
            raise
        except subprocess.TimeoutExpired:
            logger.error("Command timed out!")
            raise

    def _parse_json(self, text: str) -> Any:
        """Robustly extract and parse JSON from LLM response."""
        if not text:
            raise ValueError("Empty response text")
            
        # Try stripping markdown blocks first
        clean_text = text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            pass
            
        # Try finding the largest block with regex
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
                
        raise ValueError("Failed to parse JSON from response")

    def _parse_score(self, text: str, tag: str) -> float:
        """Robustly extract a floating-point score associated with a specific tag."""
        # 1. Try finding the tag specifically: [TAG]: X or TAG: X
        pattern = rf"{re.escape(tag)}[:\s]*(\d+(?:\.\d+)?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
            
        # 2. Look for the last number in the text (often the score line)
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if numbers:
            return float(numbers[-1])
            
        return 5.0 # Neutral default
