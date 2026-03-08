import os
import time
import requests
import logging
from typing import Optional
from loom.agents.base import AgentProxy

logger = logging.getLogger("loom")

class JulesClient(AgentProxy):
    BASE_URL = "https://jules.googleapis.com/v1alpha"

    def __init__(self):
        self.api_key = os.getenv("JULES_API_KEY")
        if not self.api_key:
            logger.warning("JULES_API_KEY missing. Jules tasks will fail.")

    def run_task(self, prompt: str, repo_owner: str, repo_name: str, branch: str, activity_callback=None, resume_session_name: Optional[str] = None) -> str:
        if resume_session_name:
            logger.info(f"Resuming existing Jules Session: {resume_session_name}")
            session_name = resume_session_name
            # We skip the prompt and source checks if resuming
        else:
            logger.info(f"Tasking Jules API: {prompt}")
            expected_source = f"sources/github/{repo_owner}/{repo_name}"
            
            logger.info(f"Waiting for source {expected_source} and branch {branch} to be available to Jules...")
            source_found = False
            branch_found = False
            for attempt in range(60): # 5 minute timeout for branch/source propagation
                time.sleep(5)
                page_token = None
                while True:
                    params = {"pageToken": page_token} if page_token else {}
                    resp = requests.get(f"{self.BASE_URL}/sources", headers={"X-Goog-Api-Key": self.api_key}, params=params)
                    if not resp.ok:
                        break
                    data = resp.json()
                    
                    for s in data.get("sources", []):
                        if s.get("name") == expected_source:
                            source_found = True
                            # Check if branch is in the indexed list
                            repo_info = s.get("githubRepo", {})
                            branches = repo_info.get("branches", [])
                            if any(b.get("displayName") == branch for b in branches):
                                branch_found = True
                                break
                    
                    if branch_found:
                        break
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
                if branch_found:
                    logger.info(f"Source and branch {branch} found by Jules!")
                    break
            else:
                if not source_found:
                    logger.warning("Source not found by Jules, proceeding optimistically...")
                elif not branch_found:
                    logger.warning(f"Branch {branch} not yet indexed by Jules, proceeding optimistically (Jules may fall back to default branch)...")

            payload = {
                "prompt": prompt,
                "sourceContext": {
                    "source": expected_source,
                    "githubRepoContext": {"startingBranch": branch}
                }
            }

            logger.info("Creating Jules Session...")
            resp = requests.post(
                f"{self.BASE_URL}/sessions",
                headers={"X-Goog-Api-Key": self.api_key, "Content-Type": "application/json"},
                json=payload
            )
            if not resp.ok:
                raise Exception(f"Jules Session Failed: {resp.text}")

            session_name = resp.json()["name"]
            session_url = resp.json().get("url", "")
            logger.info(f"Jules Session created: {session_name}")
            
            if activity_callback:
                activity_callback("Initializing...", session_url)

        patch_content = None
        seen_activities = set()
        last_status = None

        for _ in range(1440): # 4 hour timeout
            time.sleep(10)
            
            # EMERGENCY SHUTDOWN CHECK
            from backend.state import ConductorState
            if ConductorState.load().shutdown_requested:
                logger.error("[bold red]JULES SESSION ABORTED BY EMERGENCY SHUTDOWN[/bold red]", extra={"markup": True})
                raise InterruptedError("Emergency shutdown requested during Jules task")

            # Poll for activities to log progress
            try:
                act_resp = requests.get(f"{self.BASE_URL}/{session_name}/activities", headers={"X-Goog-Api-Key": self.api_key})
                if act_resp.ok:
                    activities = act_resp.json().get("activities", [])
                    for act in reversed(activities): # Process oldest to newest to catch the latest
                        act_id = act.get("name")
                        if act_id and act_id not in seen_activities:
                            seen_activities.add(act_id)
                            
                            # Try to extract a meaningful title/description from the activity
                            title = None
                            if "progressUpdated" in act:
                                title = act["progressUpdated"].get("title")
                            elif "planGenerated" in act:
                                title = "Generated execution plan."
                            elif "error" in act:
                                title = f"Error: {act['error']}"
                                
                            if title: 
                                logger.info(f"Jules Activity: {title}")
                                if activity_callback:
                                    activity_callback(title, session_url)
            except Exception as e:
                pass # Non-fatal if we can't fetch activities

            # Check main session status
            status_resp = requests.get(f"{self.BASE_URL}/{session_name}", headers={"X-Goog-Api-Key": self.api_key})
            status = status_resp.json()
            state = status.get("state")
            if state != last_status:
                logger.info(f"Jules Status: {state}")
                last_status = state
            
            if state == "AWAITING_USER_FEEDBACK":
                logger.info("Jules is awaiting feedback. Sending auto-proceed command to unblock...")
                try:
                    # The correct endpoint to reply to Jules is :sendMessage
                    resp = requests.post(
                        f"{self.BASE_URL}/{session_name}:sendMessage",
                        headers={"X-Goog-Api-Key": self.api_key, "Content-Type": "application/json"},
                        json={"prompt": "Please proceed with the current implementation and finalize the code. Do not wait for further feedback."}
                    )
                    if not resp.ok:
                        logger.warning(f"Failed to send auto-feedback: {resp.text}")
                except Exception as e:
                    logger.warning(f"Failed to send auto-feedback: {e}")
            
            if state == "COMPLETED":
                outputs = status.get("outputs", [])
                if outputs and "changeSet" in outputs[0]:
                    git_patch = outputs[0]["changeSet"].get("gitPatch", {})
                    patch_content = git_patch.get("unidiffPatch")
                break
            if state in ["FAILED", "ERROR", "CANCELLED"]:
                raise Exception(f"Jules Task Failed: {status}")

        if not patch_content:
            raise Exception("Jules completed but returned no patch.")

        logger.info("Jules returned a patch successfully.")
        
        # Strip binary patches from jules output as git apply chokes on them
        import re
        parts = re.split(r'(?=^diff --git)', patch_content, flags=re.MULTILINE)
        new_parts = [p for p in parts if 'GIT binary patch' not in p]
        clean_patch = ''.join(new_parts)
        
        # Enforce strict LF line endings to prevent Windows/Mac whitespace rejections
        clean_patch = clean_patch.replace('\r\n', '\n')
        
        patch_path = "app/jules.patch"
        with open(patch_path, "w", encoding="utf-8", newline='\n') as f:
            f.write(clean_patch)
            
        logger.info("Applying patch...")
        try:
            # 1. Ensure a clean baseline by wiping local uncommitted changes
            try:
                self._run(["git", "checkout", "."], cwd="app", quiet=True)
                self._run(["git", "clean", "-fd"], cwd="app", quiet=True)
            except Exception as clean_e:
                logger.warning(f"Failed to clean working directory: {clean_e}")

            # 2. Apply patch with whitespace ignoring and 3way merge fallback
            # We use --3way to allow git to use the index if context is slightly off
            try:
                self._run([
                    "git", "apply", 
                    "--ignore-space-change", 
                    "--ignore-whitespace", 
                    "--whitespace=nowarn",
                    "--3way",
                    "jules.patch"
                ], cwd="app", check=False)
            except Exception as apply_e:
                # If it failed, check if it's because changes are already applied
                # Or try with --reject to at least get what we can
                logger.warning(f"Standard patch application failed, trying with --reject: {apply_e}")
                self._run([
                    "git", "apply", 
                    "--ignore-space-change", 
                    "--ignore-whitespace", 
                    "--whitespace=nowarn",
                    "--reject", 
                    "jules.patch"
                ], cwd="app", check=False)
            
            # 3. Check for rejections - if hunks are rejected, the code might be broken
            import glob
            rej_files = glob.glob("app/**/*.rej", recursive=True)
            if rej_files:
                logger.warning(f"Patch applied with SOME REJECTIONS in: {rej_files}")
                # We don't necessarily raise here anymore, let the build/test check decide if it's broken
                
        except Exception as e:
            logger.error(f"Patch application failed: {e}")
            raise
        
        return "Code Implemented via Jules Patch"
