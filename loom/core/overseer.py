import os
import shutil
import time
import logging
import subprocess
import concurrent.futures
import re
import json
import random
from enum import Enum
from datetime import datetime
from pathlib import Path

from backend.agents.logger import get_agent_logger

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import google.generativeai as genai
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv

from backend.state import ConductorState, LoopIteration, AttemptRecord, BacklogTask, TaskType
from loom.environment.git import GitClient
from loom.environment.phoenix import PhoenixServer
from loom.agents.stitch import StitchClient, StitchQuotaError
from loom.agents.jules import JulesClient
from loom.agents.mock_jules import MockJulesClient
from loom.agents.architect import ArchitectAgent
from loom.agents.vision import VisionAgent
from loom.agents.pm import PMAgent
from loom.agents.vibe import VibeAgent
from loom.agents.reflection import ReflectionAgent

load_dotenv(override=True)

logger = get_agent_logger("loom", "overseer")

class LoomPhase(Enum):
    INSPIRATION = "Inspiration"
    DESIGN = "Design"
    IMPLEMENTATION = "Implementation"
    VALIDATION = "Validation"
    REFLECTION = "Reflection"
    DECISION = "Decision"

class Overseer:
    def __init__(self):
        self.state = ConductorState.load()
        self.git = GitClient()
        
        # Use service name for PocketBase inside Docker
        pb_host = os.getenv("PB_HOSTNAME", "loom-pocketbase")
        self.pb_url = f"http://{pb_host}:8090"
        
        # Use Mock Jules if requested
        if os.getenv("USE_MOCK_JULES", "").lower() == "true":
            logger.action("[bold yellow]Using Mock Jules Client (Local Gemini)[/bold yellow]", context={"mock": True})
            self.jules = MockJulesClient()
        else:
            self.jules = JulesClient()
            
        self.stitch = StitchClient()
        self.phoenix = PhoenixServer()
        
        # Iteration-specific state
        self.current_iteration_record = None
        self.current_brainstorm_output = None
        self.happiness_score = 0.0
        self.last_critique = ""
        self.app_screenshot = None
        self.app_screenshot_path = None
        self.patch_dest_rel = None
        
        # Long-term memory
        self.lab_memory = {}
        memory_path = Path("loom_memory.json")
        if memory_path.exists() and memory_path.is_dir():
            shutil.rmtree(memory_path)
            
        if memory_path.exists():
            try:
                with open(memory_path, "r", encoding="utf-8") as f:
                    self.lab_memory = json.load(f)
            except Exception as e:
                logger.error_event(f"Failed to load loom_memory.json: {e}", context={"error": str(e)})
        else:
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump({"archive_count": 0, "technical_learnings": [], "past_projects": []}, f)
        
        # Ensure artifacts directory exists
        os.makedirs("viewer/public/artifacts", exist_ok=True)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error_event("GEMINI_API_KEY not found. Overseer will be lobotomized.", context={"missing_key": True})
        else:
            genai.configure(api_key=api_key)
            # Principal Overseer (Logic & Planning)
            self.model = genai.GenerativeModel('gemini-3.1-pro-preview')
            # Specialized Reviewers (Fast & Efficient)
            self.architect = ArchitectAgent('gemini-3-flash-preview')
            self.vision = VisionAgent('gemini-3-flash-preview')
            self.pm = PMAgent('gemini-3.1-pro-preview')
            self.vibe = VibeAgent('gemini-3.1-pro-preview')
            self.reflection = ReflectionAgent('gemini-3-flash-preview')

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
    def _generate_content_with_retry(self, model, content, generation_config=None):
        """Helper to call Gemini with robust exponential backoff retries."""
        try:
            # Add a request-level timeout to force a DeadlineExceeded exception
            logger.action(f"Sending request to Gemini ({model.model_name})...", context={"model": getattr(model, "model_name", "unknown")})
            return model.generate_content(content, generation_config=generation_config, request_options={"timeout": 360})
        except Exception as e:
            logger.error_event(f"Gemini call failed (attempting retry): {e}", context={"error": str(e)})
            raise e

    def think(self, context: str, image_data: bytes = None, temperature: float = 0.7) -> str:
        """Consults the LLM for the next move with a hidden nonce to avoid caching."""
        if not hasattr(self, 'model'): return "Mock thought: Proceed."
        
        import uuid
        nonce = uuid.uuid4().hex[:8]
        prompt = f"You are the Overseer of BuilderLoom. We're building software together. [Request ID: {nonce}] Context: {context}"
        generation_config = genai.types.GenerationConfig(temperature=temperature)
        
        if image_data:
            content = [prompt, {"mime_type": "image/png", "data": image_data}]
            response = self._generate_content_with_retry(self.model, content, generation_config=generation_config)
        else:
            response = self._generate_content_with_retry(self.model, prompt, generation_config=generation_config)
        return response.text

    def _take_screenshot(self, url_or_path: str, wait_ms: int = 5000, return_logs: bool = False):
        from playwright.sync_api import sync_playwright
        logs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Set standard desktop viewport
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            if return_logs:
                page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
                page.on("pageerror", lambda exc: logs.append(f"[uncaught error] {exc}"))

            if url_or_path.startswith("http"):
                page.goto(url_or_path)
            else:
                # Handle Windows paths for file:// URIs
                clean_path = url_or_path.replace('\\', '/')
                page.goto(f"file:///{clean_path}")
            page.wait_for_timeout(wait_ms)
            screenshot = page.screenshot()
            browser.close()
            
            if return_logs:
                return screenshot, logs
            return screenshot

    def evaluate_architecture(self, branch_name: str) -> tuple[float, str, list]:
        return self.architect.evaluate(app_meta=self.state.app_meta)

    def evaluate_happiness(self, active_task: BacklogTask, target_route: str = "/") -> tuple[float, str, bytes]:
        score = 10.0 
        critique = "No critique."
        app_screenshot = None
        try:
            self.phoenix.spawn()
            self.phoenix.wait_for_ready()
            logger.action(f"Phoenix Server is up. App is running. Verifying route {target_route} with Vision...", context={"target_route": target_route})
            
            try:
                # 1. Capture Live App
                if self.app_screenshot_path and os.path.exists(f"viewer/public/{self.app_screenshot_path}"):
                    logger.action(f"Using Playwright evidence screenshot: {self.app_screenshot_path}", context={"screenshot_path": self.app_screenshot_path})
                    with open(f"viewer/public/{self.app_screenshot_path}", "rb") as f:
                        app_screenshot = f.read()
                    console_logs = [] 
                else:
                    app_screenshot, console_logs = self._take_screenshot(f"http://localhost:{self.phoenix.port}{target_route}", return_logs=True)
                
                # 2. Collect ALL reference images for this iteration
                ref_images = []
                # Always include the primary reference.png if it exists
                ref_primary = os.path.abspath("app/design/reference.png")
                if os.path.exists(ref_primary):
                    with open(ref_primary, "rb") as f:
                        ref_images.append(f.read())
                
                # Look for other images in the artifacts directory for this iteration
                artifact_dir = "viewer/public/artifacts"
                if os.path.exists(artifact_dir):
                    iter_prefix = f"iter_{self.state.current_iteration}_"
                    for f_name in os.listdir(artifact_dir):
                        if f_name.startswith(iter_prefix) and f_name.endswith(".png"):
                            # Filter for images that were part of the chosen design path
                            if "evolved" in f_name or "seed" in f_name or "theme" in f_name:
                                with open(os.path.join(artifact_dir, f_name), "rb") as f:
                                    ref_images.append(f.read())

                if hasattr(self, 'vision'):
                    score, critique = self.vision.evaluate_happiness(
                        app_screenshot=app_screenshot,
                        ref_images=ref_images,
                        app_meta=self.state.app_meta,
                        inspiration_goal=active_task.description,
                        target_route=target_route,
                        console_logs=console_logs
                    )
            except Exception as e:
                logger.error_event(f"Vision verification failed: {e}", context={"error": str(e)})
                score = 5
                critique = f"Vision failed: {e}"

        except Exception as e:
            logger.error_event(f"Happiness Check Failed: {e}", context={"error": str(e)})
            score = 0
            # Capture last 30 lines of Vite logs to help Jules diagnose the crash
            vite_logs = self.phoenix.get_logs(tail_lines=30)
            critique = f"Server failed to boot: {e}\n\n=== VITE ERROR LOGS ===\n{vite_logs}"
        finally:
            self.phoenix.kill()
        return score, critique, app_screenshot

    def _get_repo_info(self):
        url = self.git.get_remote_url()
        parts = url.split("/")
        repo = parts[-1].replace(".git", "")
        owner = parts[-2]
        return owner, repo

    def _update_env_file(self, key: str, value: str):
        """Updates a specific key in the .env file."""
        env_path = ".env"
        if not os.path.exists(env_path):
            with open(env_path, "w") as f:
                f.write(f"{key}={value}\n")
            return

        with open(env_path, "r") as f:
            lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"{key}={value}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)
        logger.action(f"Updated {env_path} with {key}={value}", context={"key": key})

    def ensure_scaffold(self):
        """Ensures that a basic React + Vite + Tailwind project exists in the app/ directory."""
        if os.path.exists("app/src"):
            return

        logger.action("[bold yellow]No React project detected. Scaffolding initial application...[/bold yellow]", context={"action": "scaffold"})
        
        # 1. Package.json
        package_json = {
            "name": "app",
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite --host",
                "build": "vite build",
                "lint": "eslint .",
                "preview": "vite preview",
                "test:e2e": "playwright test"
            },
            "dependencies": {
                "react": "^19.0.0",
                "react-dom": "^19.0.0",
                "react-router-dom": "^7.0.0",
                "lucide-react": "^0.454.0",
                "pocketbase": "^0.21.1"
            },
            "devDependencies": {
                "@playwright/test": "^1.42.0",
                "@types/node": "^20.11.24",
                "@vitejs/plugin-react": "^4.3.0",
                "autoprefixer": "^10.4.19",
                "postcss": "^8.4.38",
                "tailwindcss": "^3.4.3",
                "typescript": "^5.2.2",
                "vite": "^6.0.0"
            }
        }
        
        os.makedirs("app/src", exist_ok=True)
        os.makedirs("app/public", exist_ok=True)
        
        import json
        with open("app/package.json", "w") as f:
            json.dump(package_json, f, indent=2)
            
        # 2. Vite Config
        with open("app/vite.config.ts", "w") as f:
            f.write("""import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  server: { host: '127.0.0.1' },
  plugins: [react()],
})
""")

        # 3. Tailwind Config
        with open("app/tailwind.config.js", "w") as f:
            f.write("""/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
""")

        # 4. PostCSS Config
        with open("app/postcss.config.js", "w") as f:
            f.write("""export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""")

        # 4.4 .gitattributes (Force LF for cross-platform Git Apply)
        with open("app/.gitattributes", "w", encoding="utf-8", newline='\n') as f:
            f.write("* text=auto eol=lf\n")

        # 4.5 .gitignore
        with open("app/.gitignore", "w") as f:
            f.write("""node_modules
dist
dist-ssr
*.local
.vscode
.idea
.DS_Store
playwright-report
test-results
evidence.png
jules.patch
""")

        # 5. Index.html
        with open("app/index.html", "w") as f:
            f.write("""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Loom App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""")

        # 5.5 Playwright Config
        with open("app/playwright.config.ts", "w") as f:
            f.write("""import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
""")
        os.makedirs("app/tests", exist_ok=True)
        with open("app/tests/verify.spec.ts", "w") as f:
            f.write("""import { test, expect } from '@playwright/test';

test('App initializes correctly', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=Loom Initialized')).toBeVisible();
});
""")

        # 6. Basic SRC files
        with open("app/src/index.css", "w") as f:
            f.write("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n")
            
        # Component directories
        for d in ["components", "hooks", "services", "types", "pages"]:
            os.makedirs(f"app/src/{d}", exist_ok=True)

        with open("app/src/pages/Dashboard.tsx", "w") as f:
            f.write("""export default function Dashboard() { return <div className="p-8"><h1 className="text-3xl font-bold">Dashboard</h1></div>; }""")
            
        with open("app/src/components/Layout.tsx", "w") as f:
            f.write("""import { ReactNode } from 'react';\nimport { Link } from 'react-router-dom';\nexport default function Layout({ children }: { children: ReactNode }) { return <div className="min-h-screen bg-slate-950 text-white"><header className="p-4 border-b border-slate-800"><Link to="/">Loom Zulu</Link></header><main>{children}</main></div>; }""")

        with open("app/src/App.tsx", "w") as f:
            f.write("""import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </Layout>
    </Router>
  )
}
""")

        with open("app/src/main.tsx", "w") as f:
            f.write("""import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
""")

        # 7. Git Init & Commit
        try:
            self.git._run(["git", "init"], cwd="app")
            self.git._run(["git", "add", "."], cwd="app")
            self.git.commit("chore: initial scaffold")
            logger.action("[bold green]Scaffolding complete.[/bold green]", context={"status": "complete"})
        except Exception as e:
            logger.error_event(f"Failed to commit scaffold: {e}", context={"error": str(e)})


    def _check_shutdown(self):
        """Checks if a shutdown was requested and raises an exception to break out of current tasks."""
        self.state = ConductorState.load()
        if self.state.shutdown_requested:
            logger.error_event("[bold red]EMERGENCY SHUTDOWN: TERMINATING TASK[/bold red]", context={"shutdown": True})
            raise InterruptedError("Emergency shutdown requested")

    def _check_for_updates(self):
        """Checks if a soft deploy update was requested and gracefully restarts the factory."""
        if os.path.exists(".pending_update_flag"):
            logger.action("[bold yellow]Software update pending! Restarting factory gracefully...[/bold yellow]", context={"update": True})
            self.state.current_status = "Restarting for update..."
            self.state.save()
            try:
                os.remove(".pending_update_flag")
            except Exception:
                pass
            os._exit(0)

    def _refresh_db_stats(self):
        """Queries PocketBase to get record counts for the Data Soul dashboard panel."""
        try:
            from loom.environment.pocketbase import DatabaseProvisioner
            provisioner = DatabaseProvisioner(pb_url=self.pb_url)
            # Authenticate to get access
            token = provisioner._get_admin_token()
            if not token: return

            collections = ["social_mentions", "content_pipeline", "ax_reports", "knowledge_sources"]
            stats = {}
            import requests
            for col in collections:
                try:
                    resp = requests.get(
                        f"{self.pb_url}/api/collections/{col}/records",
                        params={"perPage": 1, "fields": "totalItems"},
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5
                    )
                    if resp.ok:
                        stats[col] = resp.json().get("totalItems", 0)
                except Exception:
                    continue
            
            if stats:
                self.state.db_stats = stats
                self.state.save()
        except Exception as e:
            logger.error_event(f"Failed to refresh DB stats: {e}", context={"error": str(e)})

    def loop(self):
        logger.action("[bold green]Starting Loom Loop...[/bold green]", context={"loop": "start"})
        self.state.emit_telemetry(agent="overseer", level="info", message="Starting Loom Loop")
        
        prefix = self.state.project_name.lower().replace(" ", "-")
        self.git.ensure_remote(repo_name_prefix=prefix)
        
        self.ensure_scaffold()
        
        while True:
            try:
                # RELOAD STATE to catch external changes (like shutdown signal)
                self.state = ConductorState.load()
                if self.state.shutdown_requested:
                    logger.error_event("[bold red]EMERGENCY SHUTDOWN: TERMINATING LOOM LOOP[/bold red]", context={"shutdown": True})
                    self.state.emit_telemetry(agent="overseer", level="error", message="EMERGENCY SHUTDOWN: TERMINATING LOOM LOOP")
                    self.state.current_status = "SHUTDOWN"
                    self.state.save()
                    break

                self._check_for_updates()
                self._refresh_db_stats()
                self._consume_steering()
                
                # 0. THE VIBE CHECK (If sprint is ending)
                if not self.state.backlog and not self.state.active_task_id:
                    self._check_shutdown()
                    # Run holistic UX check if we have a visual reference
                    if self.app_screenshot:
                        try:
                            vibe_tasks = self.vibe.check_vibe(self.app_screenshot, self.state.app_meta)
                            if vibe_tasks:
                                self.state.backlog.extend(vibe_tasks)
                                self.state.save()
                                logger.action("Vibe Agent requested UX polish before next sprint.", context={"tasks_added": len(vibe_tasks)})
                        except Exception as e:
                            logger.error_event(f"Vibe check failed: {e}", context={"error": str(e)})
                
                # 1. THE PM PHASE (If backlog is empty, generate new P1/P2 tasks)
                if not self.state.backlog and not self.state.active_task_id:
                    self._check_shutdown()
                    roadmap_path = "app/ROADMAP.md"
                    roadmap = self.state.product_roadmap
                    if os.path.exists(roadmap_path):
                        with open(roadmap_path, "r", encoding="utf-8") as f:
                            roadmap = f.read()
                            
                    learnings = ""
                    if self.state.repo_memory.get("learnings"):
                        for l in self.state.repo_memory["learnings"][-5:]:
                            learnings += f"- {l.get('takeaways', '')}\n"
                            
                    new_tasks = self.pm.plan_next_sprint(self.state.app_meta, roadmap, learnings)
                    if new_tasks:
                        self.state.backlog.extend(new_tasks)
                        self.state.save()
                    else:
                        logger.thought("PM Agent returned no tasks. Sleeping.", context={"backlog_empty": True})
                        time.sleep(30)
                        continue
                
                # 2. THE TRIAGE PHASE (Pick highest priority, setup branch)
                self._check_shutdown()
                active_task, branch_name = self._step_triage()
                
                if not active_task:
                    time.sleep(10)
                    continue

                # 3. EXECUTION PHASE
                try:
                    # If happiness was already achieved on this task iteration, skip (resume logic)
                    if self.current_iteration_record and self.current_iteration_record.happiness_score >= 8.0:
                        logger.thought("Happiness already achieved in this iteration. Skipping Design and Implementation.", context={"score": self.current_iteration_record.happiness_score})
                        self.happiness_score = self.current_iteration_record.happiness_score
                        success_branch = self.current_iteration_record.successful_branch or branch_name
                    else:
                        if active_task.requires_design and active_task.type == TaskType.FEATURE:
                            self._check_shutdown()
                            self._step_design(active_task)
                        self._check_shutdown()
                        success_branch = self._step_implementation(branch_name, active_task)
                    self._check_shutdown()
                    self._step_reflection(active_task)
                except InterruptedError:
                    raise
                except Exception as step_error:
                    from loom.agents.stitch import StitchQuotaError
                    if isinstance(step_error, StitchQuotaError):
                        logger.error_event(f"Stitch Quota Exhausted. Entering 1-hour cooldown...", context={"error": str(step_error)})
                        self.state.current_status = "BLOCKED_QUOTA: Sleeping for 1 hour..."
                        self.state.save()
                        time.sleep(3600)
                        continue
                    logger.error_event(f"Iteration aborted due to step error: {step_error}", context={"error": str(step_error)})
                    self.happiness_score = 0.0
                    self.last_critique = f"Aborted during phase {self.state.current_phase}: {step_error}"
                    success_branch = branch_name

                # 4. DECISION PHASE (Merge, mark done, or abandon)
                self._check_shutdown()
                self._step_decision(success_branch, active_task)
                
                time.sleep(10)
            except KeyboardInterrupt:
                raise
            except InterruptedError:
                logger.error_event("[bold red]Loom loop interrupted by emergency shutdown.[/bold red]", context={"shutdown": True})
                self.state.emit_telemetry(agent="overseer", level="error", message="Loom loop interrupted by emergency shutdown")
                self.state.current_status = "SHUTDOWN"
                self.state.save()
                break
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error_event(f"Critical loop error: {e}\n{error_trace}", context={"error": str(e), "traceback": error_trace})
                self.state.emit_telemetry(agent="overseer", level="error", message=str(e), metadata={"traceback": error_trace})
                self.state.add_log(f"TELEMETRY_ERROR: Critical agent loop exception: {e}")
                self.state.current_status = "CRITICAL_ERROR"
                self.state.shutdown_requested = True
                self.state.save()
                break

    def _consume_steering(self):
        """Merges all pending steering notes into a single string, moves them to history, and clears the pending list."""
        if not self.state.pending_steer:
            self.state.repo_memory["active_steering"] = ""
            return

        combined_notes = "\n".join([f"- {note}" for note in self.state.pending_steer])
        steering_block = f"\n### [DIRECTOR'S STEERING FOR THIS ITERATION]\n{combined_notes}\n"
        
        # Move to history
        for note in self.state.pending_steer:
            self.state.steering_history.append({
                "note": note,
                "applied_at_iteration": self.state.current_iteration + 1,
                "timestamp": datetime.now().isoformat()
            })
        
        # Clear pending
        self.state.pending_steer = []
        self.state.repo_memory["active_steering"] = steering_block
        self.state.save()
        
        logger.action(f"Consumed {len(combined_notes.splitlines())} steering notes for the next iteration.", context={"notes": len(combined_notes.splitlines())})

    def _step_triage(self) -> tuple[BacklogTask, str]:
        self.state.current_phase = LoomPhase.INSPIRATION.value
        active_task = None
        branch_name = None
        
        # RESUME LOGIC: If we already have an active task, skip triage and return it
        if self.state.active_task_id:
            active_task = None
            for t in self.state.backlog:
                if t.id == self.state.active_task_id:
                    active_task = t
                    break
            
            if active_task:
                base_name = active_task.id.lower()
                branch_name = base_name if base_name.startswith("task-") else f"task-{base_name}"
                # Ensure we are on the task branch
                self.git.checkout_branch(branch_name)
                # Ensure current iteration record is set
                if self.state.history and self.state.history[-1].goal == active_task.description:
                    self.current_iteration_record = self.state.history[-1]
                return active_task, branch_name
            else:
                # If active task not found in backlog, clear it
                self.state.active_task_id = None
                self.state.save()

        # Normal Triage...
        self.state.backlog.sort(key=lambda t: t.priority)
        
        if not self.state.backlog:
            return None, None
            
        # PEEK and BREAKDOWN if needed
        candidate = self.state.backlog[0]
        # Only breakdown if it's not a bugfix, not genesis, and not the base design
        if candidate.type != TaskType.BUGFIX and 'BASE-DESIGN' not in candidate.id and 'GENESIS' not in candidate.id:
            scope_result = self.pm.breakdown_task_if_needed(candidate)
            action = scope_result.get("action")
            
            if action == "discard":
                reason = scope_result.get("reason", "No reason provided")
                logger.thought(f"PM Agent discarded invalid task '{candidate.id}': {reason}", context={"reason": reason, "task_id": candidate.id})
                self.state.backlog.pop(0)
                self.state.save()
                return self._step_triage() # Recurse to next task
            
            if action == "breakdown":
                logger.action(f"Task '{candidate.id}' is too large. Breaking down into {len(scope_result.get('tasks', []))} sub-tasks.", context={"subtasks_count": len(scope_result.get('tasks', []))})
                
                subtasks = []
                for t in scope_result.get("tasks", []):
                    # Inherit requires_design from parent if it was False
                    if not candidate.requires_design:
                        t.requires_design = False
                    subtasks.append(t)
                
                self.state.backlog.pop(0)
                self.state.backlog = subtasks + self.state.backlog
                self.state.save()
                return self._step_triage() # Recurse to handle the new top task
            
        active_task = self.state.backlog[0]
        self.state.active_task_id = active_task.id
        self.state.save()
        
        base_name = active_task.id.lower()
        branch_name = base_name if base_name.startswith("task-") else f"task-{base_name}"

        # RESUME LOGIC: Check if we are already in an active iteration for this task
        if self.state.history and self.state.history[-1].goal == active_task.description:
            logger.action(f"[bold cyan]Resuming existing Task {active_task.id} on branch: {branch_name}[/bold cyan]", context={"task_id": active_task.id, "branch": branch_name})
            self.current_iteration_record = self.state.history[-1]
            self.git.checkout_branch(branch_name)
            
            try:
                logger.action(f"Merging main into {branch_name} to ensure continuity...", context={"branch": branch_name})
                self.git._run(["git", "merge", "main"], cwd="app")
            except Exception:
                pass
                
            return active_task, branch_name

        self.state.current_iteration += 1
        
        logger.action(f"[bold cyan]Starting Task {active_task.id}: {active_task.description} on branch: {branch_name}[/bold cyan]", context={"task_id": active_task.id, "branch": branch_name})
        
        self.git.checkout_branch(branch_name)
        
        # Setup history record
        self.current_iteration_record = LoopIteration(
            id=self.state.current_iteration,
            timestamp=datetime.now().isoformat(),
            goal=active_task.description,
            target_route=active_task.target_route,
            data_model=active_task.data_model,
            requires_design=active_task.requires_design,
            test_scenario=active_task.test_scenario
        )
        self.state.history.append(self.current_iteration_record)
        self.state.save()
        
        return active_task, branch_name

    def _save_to_lab_memory(self, active_task: BacklogTask):
        """Saves the current inspiration goal to loom_memory.json if it's new."""
        try:
            name = "Unknown"
            niche = active_task.description[:200]
            
            # Try to extract a name if the LLM provided one (optional based on prompt evolution)
            if "[APP_META]" in (self.current_brainstorm_output or ""):
                meta = self.current_brainstorm_output.split("[APP_META]")[1].split("[")[0].strip()
                name = meta.split("\n")[0].replace("Name:", "").strip()

            new_project = {
                "name": name,
                "niche": niche,
                "pitch": active_task.description,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Load fresh copy to avoid overwrite races
            if os.path.exists("loom_memory.json"):
                with open("loom_memory.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"archive_count": 0, "technical_learnings": [], "past_projects": []}
            
            # Avoid duplicates
            if not any(p.get("pitch") == new_project["pitch"] for p in data.get("past_projects", [])):
                data.setdefault("past_projects", []).append(new_project)
                data["archive_count"] = len(data["past_projects"])
                
                with open("loom_memory.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                logger.action(f"Saved project '{name}' to long-term lab memory.", context={"project_name": name})
        except Exception as e:
            logger.error_event(f"Failed to save to loom_memory.json: {e}", context={"error": str(e)})

    def _step_design(self, active_task: BacklogTask):
        self.state.current_phase = LoomPhase.DESIGN.value
        design_file = os.path.abspath("app/design/latest_design.html")

        # RESUME LOGIC: If a design was already chosen for this iteration and exists on disk, skip.
        if self.current_iteration_record and self.current_iteration_record.chosen_design_path:
            if os.path.exists(design_file):
                logger.thought("Reusing existing design for iteration " + str(self.state.current_iteration) + ": " + self.current_iteration_record.chosen_design_path, context={"iteration": self.state.current_iteration, "path": self.current_iteration_record.chosen_design_path})
                return

        if os.getenv("BYPASS_STITCH", "false").lower() == "true":
            logger.action("[bold yellow]BYPASS_STITCH is enabled. Skipping Stitch API call and using existing files in app/design/.[/bold yellow]", context={"bypass": True})
            return

        # EVOLUTIONARY PASS (If it is not the base design and we already have a project)
        if "BASE-DESIGN" not in active_task.id and self.state.current_iteration > 1 and getattr(self.state, 'stitch_project_id', None):
            logger.action(f"Iteration {self.state.current_iteration}: Designing feature pass for project (3-Variant Refinement)...", context={"iteration": self.state.current_iteration})
            self.state.current_status = f"Phase 2: Refining feature layout (3-way parallel)..."
            self.state.save()
            
            prompt = "Generate 3 layout variations to accommodate this new feature: '" + active_task.description + "'. This feature is part of the flow at: " + active_task.target_route + ". Focus on the main content area, but you may add necessary navigation links to the sidebar/header if required. Maintain the established visual identity exactly: " + self.state.app_meta + "."
            
            screen_id = getattr(self.state, 'stitch_screen_id', None)
            
            # Step 1: Generate 3 variants
            feature_variants = self.stitch.generate_variants(
                prompt=prompt,
                project_id=self.state.stitch_project_id,
                screen_id=screen_id,
                count=3,
                creative_range="REFINE",
                aspects=["LAYOUT"]
            )
            
            if feature_variants:
                self.current_iteration_record.design_variants_paths = []
                valid_layouts = []
                ts = int(time.time())
                
                # Step 2: Save the image paths for the Viewer
                for idx, var in enumerate(feature_variants):
                    if not var.get("images"): continue
                    primary_path = None
                    for img_idx, img_bytes in enumerate(var["images"]):
                        var_dest = f"viewer/public/artifacts/iter_{self.state.current_iteration}_evolved_{idx+1}_{img_idx}_{ts}.png"
                        with open(var_dest, "wb") as f: f.write(img_bytes)
                        if img_idx == 0: primary_path = f"artifacts/iter_{self.state.current_iteration}_evolved_{idx+1}_{img_idx}_{ts}.png"
                    
                    self.current_iteration_record.design_variants_paths.append(primary_path)
                    valid_layouts.append(var)

                # Step 3: Use Vision to pick the best one
                if valid_layouts:
                    try:
                        # Use the previously established reference image as the baseline constraint
                        baseline_path = os.path.abspath("app/design/reference.png")
                        
                        best_l_idx, review_text = self.vision.review_layouts(
                            inspiration_goal=active_task.description,
                            valid_layouts=valid_layouts,
                            baseline_img_path=baseline_path
                        )
                        self.current_iteration_record.layout_review_critique = review_text
                        best_l_idx = best_l_idx - 1 # Convert 1-based index to 0-based
                    except Exception as e:
                        logger.error_event(f"Vision layout critique failed for feature: {e}. Defaulting to first variant.", context={"error": str(e)})
                        self.current_iteration_record.layout_review_critique = f"Vision critique failed: {e}. Defaulted to variant 1."
                        best_l_idx = 0
                    
                    var_idx = max(0, min(best_l_idx, len(valid_layouts)-1))
                    winning_layout = valid_layouts[var_idx]
                    
                    self.current_iteration_record.chosen_design_path = self.current_iteration_record.design_variants_paths[var_idx]
                    # In an evolutionary pass, we don't do a theme pass, so the design is the final theme
                    self.current_iteration_record.chosen_theme_path = self.current_iteration_record.chosen_design_path
                    
                    # Clear old design files
                    if os.path.exists("app/design"):
                        for f in os.listdir("app/design"):
                            if f.endswith(".html") or f.endswith(".png"):
                                try: os.remove(os.path.join("app/design", f))
                                except: pass
                    else:
                        os.makedirs("app/design", exist_ok=True)
                        
                    # Save the winning design to the app/design folder for Jules
                    design_file = os.path.abspath("app/design/latest_design.html")
                    if winning_layout.get("html_content"):
                        with open(design_file, "w", encoding="utf-8") as f: 
                            f.write(winning_layout["html_content"])
                    if winning_layout.get("images"):
                        for img_idx, img_bytes in enumerate(winning_layout["images"]):
                            ref_name = "reference.png" if img_idx == 0 else f"reference_{img_idx}.png"
                            with open(os.path.join("app", "design", ref_name), "wb") as f: 
                                f.write(img_bytes)
                                
                    self.state.stitch_screen_id = winning_layout["screen_id"]
                    self.state.save()
                    self.git.commit(f"design: generated {len(valid_layouts)} variants and picked best for iter {self.state.current_iteration}")
            return

        # ITERATION 1 (REVOLUTION - 5-5-5)
        self.state.current_status = f"Overseer is generating 5 structural hypotheses for the product..."
        self.state.save()
        
        # 1. OVERSEER GENERATES DIVERGENT HYPOTHESES
        full_product_vision = self.state.inspiration_goal if self.state.inspiration_goal else active_task.description
        
        brief_prompt = f"""
You have invented the following product: '{full_product_vision}'.
Current Task Focus: '{active_task.description}'
Your task is to generate 5 wildly different 'Structural Hypotheses' for how this product could be realized visually and experientially.

Avoid the 'Premium' trap (generic SaaS aesthetics). Instead, think about the specific materiality and UX density required:
- Is it a dense industrial tool?
- An elastic, playful playground?
- A raw, information-first terminal?
- A spatial, non-linear canvas?
- A rhythmic, narrative-driven sequence?

Provide 5 concise (1-2 sentence) design briefs. Label them [BRIEF 1] through [BRIEF 5].
"""
        brief_response = self.think(brief_prompt, temperature=0.9)
        logger.thought(f"Divergent Briefs:\n{brief_response}", context={"brief_response": brief_response})
        
        briefs = []
        import re
        for i in range(1, 6):
            match = re.search(f"\\[BRIEF {i}\\](.*?)(?=\\[BRIEF|$)", brief_response, re.DOTALL)
            if match: briefs.append(match.group(1).strip())
        
        if not briefs:
             briefs = ["Dense Industrial", "Elastic Playground", "Raw Information Terminal", "Spatial Canvas", "Narrative Sequence"]
        
        self.current_iteration_record.base_briefs = briefs
        self.state.save()
        
        if not self.state.stitch_project_id:
            try:
                self.state.stitch_project_id = self.stitch.create_project(self.state.project_name)
                self.state.save()
                self._update_env_file("STITCH_PROJECT_ID", self.state.stitch_project_id)
            except Exception as e:
                logger.error_event(f"Failed to create Stitch project: {e}", context={"error": str(e)})

        # 2. PARALLEL DISCOVERY (5 Independent Base Seeds in 5 Unique Projects)
        base_variants = []
        if self.current_iteration_record.base_variants_data:
            logger.action("Found existing base variants data. Loading from cache...", context={"cache": True})
            for v_data in self.current_iteration_record.base_variants_data:
                # Load the primary image back into memory for the vision critique
                img_path = f"viewer/public/{v_data['img_path']}"
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        v_data["img"] = f.read()
                    base_variants.append(v_data)
            
            if len(base_variants) < 5:
                logger.thought(f"Only found {len(base_variants)}/5 valid base variants. Re-generating...", context={"found": len(base_variants)})
                base_variants = [] # Force re-generation if incomplete

        if not base_variants:
            logger.action(f"Generating 5 independent base seeds sequentially...", context={"count": 5})
            self.state.current_status = "Phase 1: Generating 5 independent base seeds..."
            self.state.save()
            self.current_iteration_record.base_seed_paths = [None] * 5
            design_prompt = f"Product Identity: {self.state.app_meta}\n\nProduct Vision: {full_product_vision}\n\nTask: {active_task.description}\n\nTarget Route: {active_task.target_route}"
            
            results = []
            for i in range(5):
                if i > 0:
                    logger.thought("Waiting 5s between Stitch calls...", context={"sleep": 5})
                    time.sleep(5)
                    
                brief = briefs[i]
                try:
                    unique_project_name = f"Loom {self.state.current_iteration} - Hypothesis {i+1}"
                    p_id = self.stitch.create_project(unique_project_name)
                    
                    logger.action(f"Generating Seed {i+1}/5 in Project {p_id}...", context={"seed_index": i+1, "project_id": p_id})
                    screens = self.stitch.generate_or_edit_screen(
                        description=f"{design_prompt}\n\nSTRUCTURAL HYPOTHESIS: {brief}",
                        project_id=p_id,
                        screen_id=None 
                    )
                    if screens:
                        win = screens[0]
                        ts = int(time.time())
                        seed_rel_path = None
                        for img_idx, img_bytes in enumerate(win["images"]):
                            path = f"artifacts/iter_{self.state.current_iteration}_seed_{i+1}_{img_idx}_{ts}.png"
                            with open(f"viewer/public/{path}", "wb") as f:
                                f.write(img_bytes)
                            if img_idx == 0: seed_rel_path = path
                        
                        self.current_iteration_record.base_seed_paths[i] = seed_rel_path
                        self.state.save()
                        
                        results.append({
                            "project_id": p_id, 
                            "screen_id": win["screen_id"], 
                            "html": win["html"], 
                            "img": win["images"][0] if win["images"] else None,
                            "img_path": seed_rel_path,
                            "images_count": len(win["images"]),
                            "brief": brief,
                            "index": i
                        })
                except StitchQuotaError as sqe:
                    logger.error_event(f"Stitch Quota Exhausted during genesis: {sqe}. Aborting pass.", context={"error": str(sqe)})
                    break # Stop trying other seeds if we hit the quota
                except Exception as e:
                    logger.error_event(f"Failed to generate seed {i+1}: {e}", context={"error": str(e), "seed_index": i+1})

            base_variants = [r for r in results if r is not None]

            if not base_variants:
                raise Exception("Failed to generate any base design seeds.")
            
            # Save metadata for resumption (exclude raw bytes to keep state small)
            metadata_only = []
            for v in base_variants:
                m = v.copy()
                if "img" in m: del m["img"]
                if "images" in m: del m["images"]
                metadata_only.append(m)
            self.current_iteration_record.base_variants_data = metadata_only
            self.state.save()

        # Overseer picks the best Base Seed
        self.state.current_status = "Selecting the winning structural hypothesis..."
        self.state.save()
        
        design_retry_count = 0
        max_design_retries = 1
        design_critique_context = ""

        while design_retry_count <= max_design_retries:
            try:
                best_base_idx_raw, review_text = self.vision.review_seeds(
                    inspiration_goal=active_task.description, 
                    base_variants=base_variants
                )
                self.current_iteration_record.seed_review_critique = review_text
                
                if best_base_idx_raw == 0 and design_retry_count < max_design_retries:
                    logger.warning("Overseer REJECTED all designs. Triggering a fresh design pass with critique...")
                    design_critique_context = f"\n### PREVIOUS DESIGN CRITIQUE (WHY THE LAST 5 FAILED):\n{review_text}\n"
                    
                    # Wipe and re-generate
                    self.current_iteration_record.base_seed_paths = [None] * 5
                    self.current_iteration_record.base_variants_data = None
                    
                    # Re-run seed generation with critique context
                    design_prompt = f"Task: {active_task.description}\n\nTarget Route: {active_task.target_route}\n{design_critique_context}"
                    results = []
                    for i in range(5):
                        if i > 0: time.sleep(5)
                        brief = briefs[i]
                        try:
                            unique_project_name = f"Loom {self.state.current_iteration} - Reroll {i+1}"
                            p_id = self.stitch.create_project(unique_project_name)
                            logger.info(f"Rerolling Seed {i+1}/5 in Project {p_id}...")
                            screens = self.stitch.generate_or_edit_screen(description=f"{design_prompt}\n\nSTRUCTURAL HYPOTHESIS: {brief}", project_id=p_id)
                            if screens:
                                win = screens[0]
                                ts = int(time.time())
                                seed_rel_path = None
                                for img_idx, img_bytes in enumerate(win["images"]):
                                    path = f"artifacts/iter_{self.state.current_iteration}_reroll_{i+1}_{img_idx}_{ts}.png"
                                    with open(f"viewer/public/{path}", "wb") as f: f.write(img_bytes)
                                    if img_idx == 0: seed_rel_path = path
                                self.current_iteration_record.base_seed_paths[i] = seed_rel_path
                                self.state.save()
                                results.append({"project_id": p_id, "screen_id": win["screen_id"], "html": win["html"], "img": win["images"][0], "img_path": seed_rel_path, "index": i, "brief": brief})
                        except Exception as e:
                            logger.error(f"Failed to generate reroll seed {i+1}: {e}")
                    
                    base_variants = [r for r in results if r is not None]
                    if not base_variants: raise Exception("Reroll failed to generate any base seeds.")
                    design_retry_count += 1
                    continue # Start the voting process again with the new seeds
                
                best_base_idx = max(0, min(len(base_variants)-1, best_base_idx_raw - 1))
                break # Found a winner or reached max retries
            except Exception as e:
                logger.error_event(f"Vision critique failed: {e}. Falling back to first seed.", context={"error": str(e)})
                self.current_iteration_record.seed_review_critique = f"Vision critique failed: {e}."
                best_base_idx = 0
                break
            
        winning_seed = base_variants[best_base_idx]
        self.state.stitch_project_id = winning_seed["project_id"]
        screen_id = winning_seed["screen_id"]
        
        self._update_env_file("STITCH_PROJECT_ID", self.state.stitch_project_id)
        
        # Clear old design files
        if os.path.exists("app/design"):
            for f in os.listdir("app/design"):
                if f.endswith(".html") or f.endswith(".png"):
                    try: os.remove(os.path.join("app/design", f))
                    except: pass
        else:
            os.makedirs("app/design", exist_ok=True)

        with open(design_file, "w", encoding="utf-8") as f:
            f.write(winning_seed["html"])
        
        if winning_seed.get("images"):
            for img_idx, img_bytes in enumerate(winning_seed["images"]):
                ref_name = "reference.png" if img_idx == 0 else f"reference_{img_idx}.png"
                with open(os.path.join("app", "design", ref_name), "wb") as f:
                    f.write(img_bytes)
        
        self.current_iteration_record.design_screenshot_path = self.current_iteration_record.base_seed_paths[winning_seed["index"]]
        self.state.save()

        # 3. SINGLE-CALL LAYOUT REFINEMENT (5 Variants in One Call)
        logger.action("Generating 5 layout variants of the winning seed in a single call...", context={"count": 5})
        self.state.current_status = "Phase 2: Refining layout variants (5-way parallel)..."
        self.state.save()
        
        layout_variants = self.stitch.generate_variants(
            prompt=f"Explore 5 divergent layout refinements for this winning hypothesis. Focus on maximizing the intentionality of the UX for: {active_task.description}.",
            project_id=self.state.stitch_project_id,
            screen_id=screen_id,
            count=5,
            creative_range="EXPLORE",
            aspects=["LAYOUT"]
        )
        
        if layout_variants:
            self.current_iteration_record.design_variants_paths = []
            valid_layouts = []
            ts = int(time.time())
            for idx, var in enumerate(layout_variants):
                if not var.get("images"): continue
                # Capture all images for variant, pick first for primary path
                primary_path = None
                for img_idx, img_bytes in enumerate(var["images"]):
                    var_dest = f"viewer/public/artifacts/iter_{self.state.current_iteration}_layout_{idx+1}_{img_idx}_{ts}.png"
                    with open(var_dest, "wb") as f: f.write(img_bytes)
                    if img_idx == 0: primary_path = f"artifacts/iter_{self.state.current_iteration}_layout_{idx+1}_{img_idx}_{ts}.png"
                
                self.current_iteration_record.design_variants_paths.append(primary_path)
                valid_layouts.append(var)
            
            if valid_layouts:
                try:
                    baseline_path = f"viewer/public/{self.current_iteration_record.design_screenshot_path}"
                    best_l_idx, review_text = self.vision.review_layouts(
                        inspiration_goal=active_task.description,
                        valid_layouts=valid_layouts,
                        baseline_img_path=baseline_path
                    )
                    self.current_iteration_record.layout_review_critique = review_text
                    best_l_idx = best_l_idx - 1 # Convert 1-based index to 0-based index
                except Exception as e:
                    logger.error_event(f"Vision layout critique failed: {e}. Defaulting to baseline.", context={"error": str(e)})
                    self.current_iteration_record.layout_review_critique = f"Vision layout critique failed: {e}. Defaulted to baseline."
                    best_l_idx = 0 # Treat as baseline
                
                if best_l_idx == 0:
                    logger.thought("Overseer chose to stick with the original Base Seed layout.", context={"choice": "baseline"})
                    self.current_iteration_record.chosen_design_path = self.current_iteration_record.design_screenshot_path
                else:
                    var_idx = best_l_idx - 1
                    screen_id = valid_layouts[var_idx]["screen_id"]
                    winning_layout = valid_layouts[var_idx]
                    self.current_iteration_record.chosen_design_path = self.current_iteration_record.design_variants_paths[var_idx]
                    
                    # Clear old design files
                    if os.path.exists("app/design"):
                        for f in os.listdir("app/design"):
                            if f.endswith(".html") or f.endswith(".png"):
                                try: os.remove(os.path.join("app/design", f))
                                except: pass
                    else:
                        os.makedirs("app/design", exist_ok=True)
                            
                    design_file = os.path.abspath("app/design/latest_design.html")
                    if winning_layout.get("html_content"):
                        with open(design_file, "w", encoding="utf-8") as f: f.write(winning_layout["html_content"])
                    if winning_layout.get("images"):
                        for img_idx, img_bytes in enumerate(winning_layout["images"]):
                            ref_name = "reference.png" if img_idx == 0 else f"reference_{img_idx}.png"
                            with open(os.path.join("app", "design", ref_name), "wb") as f: f.write(img_bytes)
            self.state.save()

        # 4. SINGLE-CALL THEME PASS (5 Variants)
        # Always run theme exploration for Iteration 1 to establish the brand
        if self.state.current_iteration == 1:
            self._run_theme_pass(screen_id, active_task, count=5)
        else:
            logger.action("Applying existing App Meta theme to new layout...", context={"theme_pass": False})
            screens = self.stitch.generate_or_edit_screen(
                description=f"Apply this existing visual identity strictly: {self.state.app_meta}. Maintain the current layout exactly.",
                project_id=self.state.stitch_project_id,
                screen_id=screen_id
            )
            if screens:
                # Clear old design files to prevent stale references
                if os.path.exists("app/design"):
                    for f in os.listdir("app/design"):
                        if f.endswith(".html") or f.endswith(".png"):
                            try: os.remove(os.path.join("app/design", f))
                            except: pass
                else:
                    os.makedirs("app/design", exist_ok=True)

                for i, win in enumerate(screens):
                    design_name = "latest_design.html" if i == 0 else f"latest_design_{i}.html"
                    design_file = os.path.abspath(f"app/design/{design_name}")
                    with open(design_file, "w", encoding="utf-8") as f:
                        f.write(win["html"])
                    
                    for idx, img_bytes in enumerate(win["images"]):
                        ref_name = "reference.png" if i == 0 and idx == 0 else f"reference_{i}_{idx}.png"
                        with open(os.path.abspath(f"app/design/{ref_name}"), "wb") as f:
                            f.write(img_bytes)
                            
                    if i == 0:
                        screen_id = win["screen_id"]

        self.state.stitch_screen_id = screen_id
        self.state.save()
        self.git.commit(f"design: unconstrained 5-5-5 discovery for iter {self.state.current_iteration}")

    def _run_theme_pass(self, screen_id, active_task: BacklogTask, count=5):
        logger.action(f"Conducting Theme Pass with {count} variants...", context={"count": count})
        self.state.current_status = f"Phase 3: Exploring {count} color and typography themes..."
        self.state.save()

        theme_variants = self.stitch.generate_variants(
            prompt=f"Explore {count} completely distinct color palettes, dark/light modes, and typography combinations for this layout. The goal is a high-intentionality feel for: {active_task.description}. Do not change the layout structure.",
            project_id=self.state.stitch_project_id,
            screen_id=screen_id,
            count=count,
            creative_range="EXPLORE",
            aspects=["COLOR_SCHEME", "TEXT_FONT"]
        )
        
        if theme_variants:
            self.current_iteration_record.theme_variants_paths = []
            valid_themes = []
            t_ts = int(time.time())
            for idx, var in enumerate(theme_variants):
                if not var.get("images"): continue
                primary_path = None
                for img_idx, img_bytes in enumerate(var["images"]):
                    var_dest = f"viewer/public/artifacts/iter_{self.state.current_iteration}_theme_{idx+1}_{img_idx}_{t_ts}.png"
                    with open(var_dest, "wb") as f: f.write(img_bytes)
                    if img_idx == 0: primary_path = f"artifacts/iter_{self.state.current_iteration}_theme_{idx+1}_{img_idx}_{t_ts}.png"
                
                self.current_iteration_record.theme_variants_paths.append(primary_path)
                valid_themes.append(var)
            
            if valid_themes:
                try:
                    baseline_path = os.path.abspath("app/design/reference.png")
                    best_t_idx, review_text, app_meta = self.vision.review_themes(
                        inspiration_goal=active_task.description,
                        valid_themes=valid_themes,
                        baseline_img_path=baseline_path
                    )
                    self.current_iteration_record.theme_review_critique = review_text
                    
                    if app_meta:
                        self.state.app_meta = app_meta
                        with open("app/APP_META.md", "w", encoding="utf-8") as f: 
                            f.write(self.state.app_meta)
                    
                    best_t_idx = best_t_idx - 1 # Convert 1-based index to 0-based array index
                except Exception as e:
                    logger.error_event(f"Vision theme critique failed: {e}. Defaulting to baseline.", context={"error": str(e)})
                    self.current_iteration_record.theme_review_critique = f"Vision theme critique failed: {e}. Defaulted to baseline."
                    best_t_idx = 0 # Treat as baseline
                
                if best_t_idx == 0:
                    logger.thought("Overseer chose to stick with the baseline theme.", context={"choice": "baseline"})
                else:
                    var_idx = best_t_idx - 1
                    chosen_t = valid_themes[var_idx]
                    self.current_iteration_record.chosen_theme_path = self.current_iteration_record.theme_variants_paths[var_idx]
                    
                    # Clear old design files
                    if os.path.exists("app/design"):
                        for f in os.listdir("app/design"):
                            if f.endswith(".html") or f.endswith(".png"):
                                try: os.remove(os.path.join("app/design", f))
                                except: pass
                    else:
                        os.makedirs("app/design", exist_ok=True)
                            
                    design_file = os.path.abspath("app/design/latest_design.html")
                    if chosen_t.get("html_content"):
                        with open(design_file, "w", encoding="utf-8") as f: f.write(chosen_t["html_content"])
                    if chosen_t.get("images"):
                        for img_idx, img_bytes in enumerate(chosen_t["images"]):
                            ref_name = "reference.png" if img_idx == 0 else f"reference_{img_idx}.png"
                            with open(os.path.join("app", "design", ref_name), "wb") as f: f.write(img_bytes)
            self.state.save()

    def _step_implementation(self, branch_name, active_task: BacklogTask) -> str:
        self.state.current_phase = LoomPhase.IMPLEMENTATION.value

        # Ensure we are on the correct agentic branch for this iteration
        self.git.checkout_branch(branch_name)

        # 1. Autonomous Database Provisioning (The Data Soul)
        # ... PB code ...
        if active_task.data_model:
            # (Rest of PB provisioning remains the same)
            logger.action("Overseer is provisioning PocketBase schema...", context={"data_model": True})
            self.state.current_status = "Provisioning database schema..."
            self.state.save()
            
            try:
                from loom.environment.pocketbase import DatabaseProvisioner
                provisioner = DatabaseProvisioner(pb_url=self.pb_url)
                
                # Ask LLM to translate plain text data model to PocketBase JSON Schema
                schema_prompt = """
Convert the following data model description into a JSON array of PocketBase collection definitions.
Data Model: [DATA_MODEL]

Rules:
1. Each object in the array must represent a collection.
2. Required fields for each collection: "name" (string), "type" ("base" or "auth"), "schema" (array of field definition objects).
3. Valid field types: "text", "number", "bool", "email", "url", "date", "select", "json", "file", "relation".
4. Set "listRule", "viewRule", "createRule", "updateRule", "deleteRule" to "" (empty string = public access) for easy prototyping.
5. Return ONLY valid JSON, no markdown blocks.

Example output:
[
  {
    "name": "posts",
    "type": "base",
    "schema": [
      {"name": "title", "type": "text", "required": true},
      {"name": "views", "type": "number", "required": false}
    ],
    "listRule": "", "viewRule": "", "createRule": "", "updateRule": "", "deleteRule": ""
  }
]
"""
                schema_prompt = schema_prompt.replace("[DATA_MODEL]", active_task.data_model)
                schema_json_str = self._generate_content_with_retry(self.model, schema_prompt).text.strip()
                # Clean markdown if present
                schema_json_str = schema_json_str.replace("```json", "").replace("```", "").strip()
                
                import json
                schema_json = json.loads(schema_json_str)
                
                success = provisioner.provision_schema(schema_json)
                if success:
                    logger.action("Successfully provisioned PocketBase schema.", context={"success": True})
                else:
                    logger.error_event("Failed to provision some or all PocketBase collections.", context={"success": False})
            except Exception as e:
                logger.error_event(f"Failed to provision database: {e}", context={"error": str(e)})

        self._check_shutdown()
        max_attempts = 50
        current_attempt = len(self.current_iteration_record.attempts) + 1
        
        final_refactoring_priorities = []
        
        while current_attempt <= max_attempts:
            self._check_shutdown()
            self._check_for_updates()
            logger.action(f"--- Attempt {current_attempt}/{max_attempts} for Iteration {self.state.current_iteration} ---", context={"attempt": current_attempt, "max_attempts": max_attempts})
            self.state.current_status = f"Jules is coding (Attempt {current_attempt})..."
            self.state.save()
            
            # We stay on the same branch (branch_name) for all attempts in this iteration
            # but we push before calling Jules so it sees our latest (or its latest) work.
            self.git.push_branch(branch_name)

            task_prompt = self._get_jules_prompt(current_attempt, active_task)
            owner, repo_name = self._get_repo_info()
            self.state.active_jules_prompt = task_prompt
            self.state.save()

            # Support Resuming existing session if restart happened mid-attempt
            resume_session = None
            if self.state.active_jules_url:
                # Extract sessions/XXX from the URL
                match = re.search(r'session/(\d+)', self.state.active_jules_url)
                if match:
                    resume_session = f"sessions/{match.group(1)}"

            try:
                self.jules.run_task(task_prompt, owner, repo_name, branch_name, 
                                   activity_callback=lambda act, url: self._update_jules_state(act, url),
                                   resume_session_name=resume_session)
                self._check_shutdown()
                self.git.commit(f"feat: implementation attempt {current_attempt}")
                self.git.push_branch(branch_name)
                
                self._check_shutdown()
                self._save_patch_artifact(current_attempt)
                final_refactoring_priorities = self._evaluate_iteration(current_attempt, branch_name, active_task)
                self._check_shutdown()
            except Exception as e:
                logger.error_event(f"Build failed: {e}", context={"error": str(e)})
                self.happiness_score = 0.0
                self.last_critique = f"Jules run failed: {e}"
                self._record_attempt(current_attempt, active_task)
            finally:
                self.state.active_jules_prompt = None
                self.state.active_jules_url = None
                self.state.active_jules_action = None
                self.state.save()
            
            if self.happiness_score >= 8.0: 
                self.current_iteration_record.successful_branch = branch_name
                self.state.save()
                break
            current_attempt += 1

        # If we failed to reach happiness after all attempts, push the remaining debt to the backlog
        if self.happiness_score < 8.0 and final_refactoring_priorities:
            import uuid
            from backend.state import TaskPriority, TaskType
            for p in final_refactoring_priorities:
                p_int = p.get('priority', 1)
                t_prio = TaskPriority.P0_CRITICAL if p_int == 0 else (TaskPriority.P2_NORMAL if p_int == 2 else TaskPriority.P1_HIGH)
                
                new_refactor = BacklogTask(
                    id=f"REFACTOR-{uuid.uuid4().hex[:6].upper()}",
                    type=TaskType.REFACTOR,
                    priority=t_prio,
                    description=p.get('description', 'Refactor task'),
                    target_route=active_task.target_route,
                    requires_design=False,
                    context=self.current_iteration_record.architectural_critique or ""
                )
                
                if not any(t.description == new_refactor.description for t in self.state.backlog):
                    logger.thought(f"Task abandoned. Architect identified remaining debt: {new_refactor.description}", context={"abandoned": True, "refactor_desc": new_refactor.description})
                    self.state.backlog.append(new_refactor)
            self.state.save()

        return self.current_iteration_record.successful_branch or branch_name

    def _get_jules_prompt(self, attempt, active_task: BacklogTask):
        memory_context = ""
        if self.state.repo_memory.get("learnings"):
            memory_context = "\n=== PAST LEARNINGS (AVOID THESE MISTAKES) ===\n"
            for l in self.state.repo_memory["learnings"][-3:]:
                status = "Success" if l['success'] else "Failure"
                memory_context += f"- Iteration {l['iteration']} ({status}): {l['takeaways']}\n"

        data_model_context = f"\n=== DATA MODEL (POCKETBASE SCHEMA) ===\n{active_task.data_model}\n" if active_task.data_model else ""

        if attempt == 1:
            if active_task.type == "feature" and active_task.requires_design:
                return f"""=== IMMEDIATE TASK ===
IMPLEMENT NEW FEATURE: '{active_task.description}'
TARGET ROUTE: {active_task.target_route}

The design files (HTML and reference image) for this feature are located in the `app/design` folder. You MUST implement this exact design into the React application.

=== CONTEXT & RULES ===
App Identity: {self.state.app_meta}
{data_model_context}
{memory_context}
CRITICAL RULES:
1. NATIVE INTEGRATION: Integrate this new feature into the existing application natively using the established design system (Tailwind classes, layout, components).
2. ROUTING: The target flow/location is: '{active_task.target_route}'. If this requires a new page, set up React Router without breaking existing pages AND add a visible link to it in the main app navigation so the user can reach it. If it is a modal/overlay, integrate it cleanly into the current view.
3. PERSISTENCE: If a Data Model is provided above, you MUST use the `pocketbase` npm package to make the application state persistent. Assume the PocketBase server is running on port 8090 of the same host as the application. Initialize the client using `new PocketBase(window.location.protocol + "//" + window.location.hostname + ":8090")`. Provide a clean API or hook for the UI to interact with.
4. DEEP LINKING: All new UI states, overlays, drawers, or modals MUST be deep-linkable and controllable via URL search parameters (e.g., `/?view=settings` or `/?modal=library`).
5. VERIFICATION: You MUST append a new Playwright integration test block (`test('...', async ({{ page }}) => {{...}})`) to `app/tests/verify.spec.ts` that implements this exact verification scenario: "{active_task.test_scenario}". Do NOT delete existing tests.
6. SCREENSHOT: At the end of your newly added test (after the assertions pass), you MUST take a screenshot of the active feature using `await page.screenshot({{ path: 'evidence.png' }});`. This image is required to prove the feature works visually.
"""
            elif active_task.type == "refactor" and active_task.requires_design:
                return f"""=== IMMEDIATE TASK ===
REFACTOR/REFINE UI: '{active_task.description}'
TARGET ROUTE: {active_task.target_route}

The primary design is LOCKED. Do NOT expect new design assets. Your task is to refine the existing CSS, layout, and logic to better match the current files in `app/design` and fix any UX papercuts or discrepancies mentioned in the description.

=== CONTEXT & RULES ===
App Identity: {self.state.app_meta}
{data_model_context}
{memory_context}
CRITICAL RULES:
1. Focus on visual and functional refinement of the existing '{active_task.target_route}' route.
2. If a Data Model is provided, ensure the PocketBase persistence logic is robust and correctly reflects the schema.
3. VERIFICATION: You MUST update the Playwright integration test in `app/tests/verify.spec.ts` to ensure it continues to pass with these refinements.
4. SCREENSHOT: At the end of the test, you MUST take a screenshot of the active feature using `await page.screenshot({{ path: 'evidence.png' }});`.
"""
            elif active_task.type == "bugfix":
                return f"""=== IMMEDIATE TASK ===
BUGFIX: '{active_task.description}'
TARGET ROUTE: {active_task.target_route}

Context/Error:
{active_task.context}

=== CONTEXT & RULES ===
App Identity: {self.state.app_meta}
{data_model_context}
{memory_context}
CRITICAL RULES:
1. This is a BUGFIX. Do NOT add new features. Focus entirely on resolving the specific error or test failure provided in the context.
2. VERIFICATION: Ensure the Playwright tests in `app/tests/verify.spec.ts` pass after your fix.
3. SCREENSHOT: At the end of the test, you MUST take a screenshot using `await page.screenshot({{ path: 'evidence.png' }});`.
"""
            else:
                return f"""=== IMMEDIATE TASK ===
LOGIC/ARCHITECTURE UPDATE: '{active_task.description}'
TARGET ROUTE: {active_task.target_route}

Task Context:
{active_task.context}

=== CONTEXT & RULES ===
App Identity: {self.state.app_meta}
{data_model_context}
{memory_context}
CRITICAL RULES:
1. This is a LOGIC / ARCHITECTURE update. Do NOT significantly alter the visual design, CSS, or layout unless required to fix a bug.
2. Focus purely on the underlying React logic, state management, or architecture as requested.
3. PERSISTENCE: If a Data Model is provided, you MUST implement the corresponding persistence logic using the `pocketbase` SDK connecting to port 8090 of the current host (`window.location.hostname`).
4. VERIFICATION: You MUST append or update a Playwright integration test block to `app/tests/verify.spec.ts` that implements this exact verification scenario: "{active_task.test_scenario}". Do NOT delete existing tests.
5. SCREENSHOT: At the end of your test (after the assertions pass), you MUST take a screenshot of the active feature using `await page.screenshot({{ path: 'evidence.png' }});`.
"""
        else:
            past_critiques = ""
            if self.current_iteration_record and self.current_iteration_record.attempts:     
                last_att = self.current_iteration_record.attempts[-1]
                past_critiques += f"\n=== PREVIOUS ATTEMPT FEEDBACK (Score: {last_att.score}/10) ===\n{last_att.critique}\n"
            
            return f"""=== IMMEDIATE TASK ===
FIX PREVIOUS IMPLEMENTATION ERRORS FOR: '{active_task.description}'
TARGET ROUTE: {active_task.target_route}

CRITICAL: The code currently in the repository IS the result of your previous attempt ({attempt-1}). You are NOT starting from scratch. You must BUILD ON and FIX the existing code based on the feedback below.

{past_critiques}

=== CONTEXT & RULES ===
App Identity: {self.state.app_meta}
{data_model_context}
{memory_context}
CRITICAL RULES:
1. VERIFICATION: You MUST include or update the Playwright test in `app/tests/verify.spec.ts`.
2. FIX THE ERRORS: Review the feedback/errors from the previous attempt. If a Playwright test failed, fix the React code or the test script to resolve the error.
"""

    def _update_jules_state(self, action, url):
        self.state.active_jules_action = action
        self.state.active_jules_url = url
        self.state.save()

    def _save_patch_artifact(self, attempt):
        patch_src = "app/jules.patch"
        self.patch_dest_rel = None
        if os.path.exists(patch_src):
            ts = int(time.time())
            patch_dest = f"viewer/public/artifacts/iter_{self.state.current_iteration}_att_{attempt}_{ts}.patch"
            shutil.copy(patch_src, patch_dest)
            self.patch_dest_rel = f"artifacts/iter_{self.state.current_iteration}_att_{attempt}_{ts}.patch"

    def _evaluate_iteration(self, attempt, branch, active_task: BacklogTask):
        self.state.current_phase = LoomPhase.VALIDATION.value
        logger.action(f"[bold cyan]Evaluating Attempt {attempt}...[/bold cyan]", context={"attempt": attempt})
        self.state.current_status = f"Evaluating (Attempt {attempt})..."
        self.state.save()
        
        # Reset score/critique for this attempt
        self.happiness_score = 0.0
        self.last_critique = ""
        self.app_screenshot = None
        self.app_screenshot_path = None
        refactoring_priorities = []

        try:
            # Build check
            build_success, build_error = self._run_build()
            if not build_success:
                logger.error_event(f"Build failed for attempt {attempt}: {build_error}", context={"build_error": build_error, "attempt": attempt})
                self.happiness_score, self.last_critique = 0.0, f"Build error: {build_error}"
            else:
                logger.action("Build successful.", context={"build_success": True})
                # Test check
                test_success, test_error = self._run_tests(attempt)
                if not test_success:
                    logger.error_event(f"Tests failed for attempt {attempt}: {test_error}", context={"test_error": test_error, "attempt": attempt})
                    self.happiness_score, self.last_critique = 0.0, f"Test error: {test_error}"
                    
                    # Generate a P0 Bugfix task if not already in a bugfix
                    if active_task.type != "bugfix":
                        import uuid
                        from backend.state import TaskPriority, TaskType
                        bugfix_task = BacklogTask(
                            id=f"BUGFIX-{uuid.uuid4().hex[:6].upper()}",
                            type=TaskType.BUGFIX,
                            priority=TaskPriority.P0_CRITICAL,
                            description=f"Fix failing Playwright test: {active_task.test_scenario}",
                            target_route=active_task.target_route,
                            requires_design=False,
                            context=f"The test failed during execution.\nError Output:\n{test_error}"
                        )
                        # De-duplicate bugfixes
                        if not any(t.description == bugfix_task.description for t in self.state.backlog):
                            logger.thought(f"Sentry identified a broken build. Pushing P0 BUGFIX to backlog.", context={"bugfix_pushed": True})
                            self.state.backlog.insert(0, bugfix_task)
                            self.state.save()
                else:
                    logger.action("Tests passed.", context={"test_success": True})
                    # Vision check
                    if active_task.requires_design:
                        self.happiness_score, self.last_critique, self.app_screenshot = self.evaluate_happiness(active_task, target_route=active_task.target_route)
                    else:
                        self.happiness_score, self.last_critique = 10.0, "Logic update successful."
                    
                    # Arch check
                    if self.happiness_score >= 8.0:
                        arch_score, arch_critique, refactoring_priorities = self.evaluate_architecture(branch)
                        if arch_score < 8:
                            self.happiness_score, self.last_critique = arch_score, f"Visuals good, arch bad: {arch_critique}"
                        
                        # Store the architect critique in the iteration record for display
                        self.current_iteration_record.architectural_critique = arch_critique
        except Exception as e:
            logger.error_event(f"Evaluation crashed: {e}", context={"error": str(e)})
            self.happiness_score, self.last_critique = 0.0, f"Evaluation error: {str(e)}"

        # ALWAYS Record attempt
        self._record_attempt(attempt, active_task)
        return refactoring_priorities

    def _run_build(self):
        try:
            subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd="app", check=True, capture_output=True, text=True, shell=(os.name == 'nt'))
            subprocess.run(["npm", "run", "build"], cwd="app", check=True, capture_output=True, text=True, shell=(os.name == 'nt'))
            return True, ""
        except subprocess.CalledProcessError as e: return False, e.stderr or e.stdout
        except Exception as e: return False, str(e)

    def _run_tests(self, attempt):
        self.phoenix.spawn()
        self.phoenix.wait_for_ready()
        try:
            # Install playwright browsers if not present
            subprocess.run(["npx", "playwright", "install", "chromium"], cwd="app", check=True, capture_output=True, text=True, shell=(os.name == 'nt'))
            result = subprocess.run(["npx", "playwright", "test"], cwd="app", capture_output=True, text=True, shell=(os.name == 'nt'))
            
            # Check for Evidence
            if os.path.exists("app/evidence.png"):
                ts = int(time.time())
                evidence_path = f"viewer/public/artifacts/iter_{self.state.current_iteration}_attempt_{attempt}_evidence_{ts}.png"
                shutil.move("app/evidence.png", evidence_path)
                # Store relative path for UI
                self.app_screenshot_path = f"artifacts/iter_{self.state.current_iteration}_attempt_{attempt}_evidence_{ts}.png"
                logger.action(f"Evidence captured: {evidence_path}", context={"evidence_path": evidence_path})
            
            return result.returncode == 0, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)
        finally:
            self.phoenix.kill()

    def _record_attempt(self, attempt, active_task: BacklogTask):
        ts = int(time.time())
        app_screenshot_path = None
        
        # 1. Surface Screenshot (Prefer evidence.png from tests, fallback to live capture)
        if hasattr(self, 'app_screenshot_path') and self.app_screenshot_path:
            app_screenshot_path = self.app_screenshot_path
        elif self.app_screenshot:
            app_screenshot_path = f"artifacts/iter_{self.state.current_iteration}_attempt_{attempt}_app_{ts}.png"
            with open(f"viewer/public/{app_screenshot_path}", "wb") as f:
                f.write(self.app_screenshot)
        
        # 2. Persist the Code Patch as an artifact so the Viewer can display it
        jules_patch_artifact = None
        patch_src = "app/jules.patch"
        if os.path.exists(patch_src):
            jules_patch_artifact = f"artifacts/iter_{self.state.current_iteration}_attempt_{attempt}_patch_{ts}.patch"
            import shutil
            shutil.copy(patch_src, f"viewer/public/{jules_patch_artifact}")
        
        attempt_record = AttemptRecord(
            attempt_number=attempt,
            prompt_used=self._get_jules_prompt(attempt, active_task),
            app_screenshot_path=app_screenshot_path,
            jules_patch_path=jules_patch_artifact,
            jules_url=self.state.active_jules_url,
            jules_action="COMPLETED",
            score=self.happiness_score,
            critique=self.last_critique
        )
        self.current_iteration_record.attempts.append(attempt_record)
        self.current_iteration_record.happiness_score = self.happiness_score
        self.state.save()

    def _step_reflection(self, active_task: BacklogTask):
        self.state.current_phase = LoomPhase.REFLECTION.value
        logger.action("Conducting Reflection Pass...", context={"reflection_pass": True})
        self.state.current_status = "Reflecting on iteration..."
        self.state.save()
        
        learnings = self.reflection.reflect_on_task(
            active_task=active_task,
            happiness_score=self.happiness_score,
            last_critique=self.last_critique,
            app_meta=self.state.app_meta
        )
        logger.thought(f"Learnings:\n{learnings}", context={"learnings": learnings})
        
        # Save to the iteration record for the Viewer UI
        self.current_iteration_record.reflection_learnings = learnings
        
        if "learnings" not in self.state.repo_memory:
            self.state.repo_memory["learnings"] = []
            
        # Deduplication check: remove previous reflection for the same iteration to prevent bloat
        self.state.repo_memory["learnings"] = [
            l for l in self.state.repo_memory["learnings"] 
            if l.get("iteration") != self.state.current_iteration
        ]
        
        self.state.repo_memory["learnings"].append({
            "iteration": self.state.current_iteration,
            "goal": active_task.description,
            "success": self.happiness_score >= 8.0,
            "takeaways": learnings
        })
        self.state.save()
        self._save_learning_to_lab_memory(learnings)

    def _save_learning_to_lab_memory(self, learning_text: str):
        """Appends technical takeaways to the permanent ML dataset."""
        try:
            if not os.path.exists("loom_memory.json"):
                return
            
            with open("loom_memory.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                
            data.setdefault("technical_learnings", []).append({
                "timestamp": datetime.now().isoformat(),
                "project": self.state.project_name,
                "learning": learning_text
            })
            
            with open("loom_memory.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error_event(f"Failed to append learning to loom_memory.json: {e}", context={"error": str(e)})

    def _step_decision(self, branch, active_task: BacklogTask):
        self.state.current_phase = LoomPhase.DECISION.value
        if self.happiness_score >= 8.0:
            logger.action(f"Happiness achieved on branch {branch}! Merging to main.", context={"branch": branch})
            self.git.checkout_branch("main")
            try:
                self.git._run(["git", "merge", "-X", "theirs", branch], cwd="app")
                self.git.push_branch("main")
                
                # FINAL PRODUCTION BUILD (For the Live App)
                logger.action("Triggering final production build for the live app...", context={"build": "production"})
                self._run_build()
                
                self.state.current_status = "Merge successful. Preparing for next loop..."
                
                # Clear from backlog and reset active task
                self.state.backlog = [t for t in self.state.backlog if t.id != active_task.id]
                self.state.active_task_id = None
                self.state.save()
            except Exception as e:
                logger.error_event(f"Merge to main failed: {e}. Resetting main.", context={"error": str(e)})
                self.git._run(["git", "reset", "--hard", "origin/main"], cwd="app")
        else:
            # If max attempts reached, we might want to abandon. 
            # For now, let's assume if it reached here without high score, it stays 'todo' in the backlog
            # but we clear the active_task_id so triage can potentially repick or re-eval
            logger.thought("Happiness not met for this iteration.", context={"happiness_score": self.happiness_score})
            
            # Check if we should abandon (e.g. after many attempts)
            if len(self.current_iteration_record.attempts) >= 10:
                logger.thought(f"Task {active_task.id} failed after many attempts. Abandoning.", context={"abandon": True, "task_id": active_task.id})
                if self.current_iteration_record:
                    self.current_iteration_record.abandoned = True
                
                self.state.backlog = [t for t in self.state.backlog if t.id != active_task.id]
                self.state.active_task_id = None
                
                self.git.checkout_branch("main")
                self.git._run(["git", "reset", "--hard", "origin/main"], cwd="app")
                self.git._run(["git", "clean", "-fd"], cwd="app")
                
                # If we don't have any previous successful iterations, the genesis project failed.
                if not any(h.happiness_score >= 8.0 for h in self.state.history[:-1]):
                    logger.thought("Genesis project failed. Resetting design state to restart 5-5-5 genesis.", context={"genesis_failed": True})
                    self.state.stitch_project_id = None
                    self.state.stitch_screen_id = None
                    self.state.app_meta = ""
                    self.state.product_phase = "Phase 1: Core Loop MVP"
                    self.state.product_roadmap = ""
                    if os.path.exists("app/APP_META.md"):
                        try: os.remove("app/APP_META.md")
                        except: pass
            
            self.state.save()
