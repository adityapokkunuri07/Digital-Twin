"""
architecture_drift.py — IT Architecture Drift Detection Skill
================================================================
Functional skill that orchestrates the full drift detection pipeline.

Refactored into discrete task methods so the workflow engine can:
  - Chain them as individual nodes
  - Insert human gates between any two steps
  - Toggle individual tasks on/off

Task Methods:
  1. task_resolve_repo    — Resolve repo from monitored_repos
  2. task_clone_snapshot  — Clone + snapshot via GitHubConnector
  3. task_load_rules      — Load architecture rules from DB
  4. task_scan_code       — Run CodeScanner
  5. task_audit_config    — Run ConfigAuditor
  6. task_cross_reference — Cross-reference via DriftEngine (LLM)
  7. task_persist_report  — Persist report to drift_reports

The execute() method remains as a backward-compatible wrapper
that calls all tasks in sequence.
"""
from typing import Dict, Any
from app.skills.functional.base_skill import BaseFunctionalSkill
from app.services.github_connector import GitHubConnector
from app.services.code_scanner import CodeScanner
from app.services.config_auditor import ConfigAuditor
from app.services.drift_engine import DriftEngine


class ItArchitectureDriftSkill(BaseFunctionalSkill):
    """
    Scans a GitHub codebase against ADR-derived architecture rules
    and detects unauthorized shortcuts, rogue dependencies, and
    infrastructure deviations.
    """

    @staticmethod
    def skill_name() -> str:
        return "SKL_IT_ARCH_DRIFT"

    # ══════════════════════════════════════════════════════════════════════
    # DISCRETE TASK METHODS
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def task_resolve_repo(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 1: Resolve repository URL from monitored_repos."""
        from app.services.supabase_client import SupabaseService

        repo_url = state.get("repo_url", "")
        repo_label = state.get("repo_label", "")
        branch = state.get("branch", "main")
        db = SupabaseService()

        if not repo_url and repo_label:
            try:
                result = db.client.table("monitored_repos").select("*").ilike(
                    "label", f"%{repo_label}%"
                ).eq("is_active", True).limit(1).execute()

                if result.data:
                    repo_url = result.data[0]["repo_url"]
                    repo_label = result.data[0]["label"]
                    if not branch or branch == "main":
                        branch = result.data[0].get("default_branch", "main")
            except Exception as e:
                print(f"[ARCH_DRIFT] Repo lookup failed: {e}")

        if not repo_url and not repo_label:
            try:
                result = db.client.table("monitored_repos").select("*").eq(
                    "is_active", True
                ).limit(1).execute()
                if result.data:
                    repo_url = result.data[0]["repo_url"]
                    repo_label = result.data[0]["label"]
                    if branch == "main":
                        branch = result.data[0].get("default_branch", "main")
            except Exception:
                pass

        state["repo_url"] = repo_url
        state["repo_label"] = repo_label
        state["branch"] = branch

        if not repo_url:
            state["error"] = "No repository specified. Please provide a repo_url or repo_label, or register a monitored repo first."

        print(f"[ARCH_DRIFT] Task 1/7 — Resolved repo: {repo_label or repo_url} ({branch})")
        return state

    @staticmethod
    def task_clone_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 2: Clone repo and take snapshot via GitHubConnector."""
        if state.get("error"):
            return state

        owner_id = state.get("owner_id", "architect")
        connector = GitHubConnector(owner_id=owner_id)

        print(f"[ARCH_DRIFT] Task 2/7 — Cloning {state['repo_url']}...")
        snapshot = connector.get_repo_snapshot(state["repo_url"], state["branch"])
        state["snapshot"] = snapshot
        state["temp_dir"] = snapshot.get("temp_dir")
        state["_connector"] = connector  # Keep for cleanup
        return state

    @staticmethod
    def task_load_rules(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 3: Load active architecture rules from DB."""
        if state.get("error"):
            return state

        from app.services.supabase_client import SupabaseService
        db = SupabaseService()

        rules = []
        try:
            result = db.client.table("architecture_rules").select("*").eq(
                "is_active", True
            ).eq("domain", "it").execute()
            rules = result.data if result.data else []
        except Exception as e:
            print(f"[ARCH_DRIFT] Failed to load rules: {e}")

        if not rules:
            print("[ARCH_DRIFT] Warning: No architecture rules found.")
            state["warning"] = "No architecture rules found. Upload ADR documents first."

        state["rules"] = rules
        print(f"[ARCH_DRIFT] Task 3/7 — Loaded {len(rules)} architecture rules")
        return state

    @staticmethod
    def task_scan_code(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 4: Run CodeScanner on application source files."""
        if state.get("error") or state.get("warning"):
            return state

        scanner = CodeScanner()
        snapshot = state.get("snapshot", {})
        code_analysis = scanner.scan(snapshot.get("source", {}))
        state["code_analysis"] = code_analysis
        print(f"[ARCH_DRIFT] Task 4/7 — Code scan complete")
        return state

    @staticmethod
    def task_audit_config(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 5: Run ConfigAuditor on infrastructure/config files."""
        if state.get("error") or state.get("warning"):
            return state

        auditor = ConfigAuditor()
        snapshot = state.get("snapshot", {})
        config_audit = auditor.audit(snapshot.get("config", {}), snapshot.get("infra", {}))
        state["config_audit"] = config_audit
        print(f"[ARCH_DRIFT] Task 5/7 — Config audit complete")
        return state

    @staticmethod
    def task_cross_reference(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 6: Cross-reference code/config against rules via DriftEngine (LLM)."""
        if state.get("error") or state.get("warning"):
            return state

        engine = DriftEngine()
        report = engine.compare(
            rules=state.get("rules", []),
            code_analysis=state.get("code_analysis", {}),
            config_audit=state.get("config_audit", {}),
            repo_url=state.get("repo_url", ""),
            repo_label=state.get("repo_label", ""),
            branch=state.get("branch", "main"),
            trigger_type=state.get("trigger_type", "manual"),
        )
        state["report"] = report
        print(f"[ARCH_DRIFT] Task 6/7 — Cross-reference complete: {report.get('summary', {}).get('total', 0)} violations")
        return state

    @staticmethod
    def task_persist_report(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 7: Persist report to drift_reports table."""
        if state.get("error") or state.get("warning"):
            return state

        from app.services.supabase_client import SupabaseService
        db = SupabaseService()
        report = state.get("report", {})

        try:
            db.client.table("drift_reports").insert({
                "scan_id": report.get("scan_id"),
                "domain": "it",
                "repo_url": state.get("repo_url", ""),
                "repo_label": state.get("repo_label", ""),
                "branch": state.get("branch", "main"),
                "trigger_type": state.get("trigger_type", "manual"),
                "summary": report.get("summary"),
                "violations": report.get("violations"),
                "strategic_recommendation": report.get("strategic_recommendation", ""),
            }).execute()
            print(f"[ARCH_DRIFT] Task 7/7 — Report {report.get('scan_id')} persisted")
        except Exception as e:
            print(f"[ARCH_DRIFT] Failed to persist report: {e}")

        return state

    # ══════════════════════════════════════════════════════════════════════
    # BACKWARD-COMPATIBLE EXECUTE (calls tasks in sequence)
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Full drift detection pipeline — sequential execution of all tasks."""
        state = {
            "repo_url": payload.get("repo_url", ""),
            "repo_label": payload.get("repo_label", ""),
            "branch": payload.get("branch", "main"),
            "trigger_type": payload.get("trigger_type", "manual"),
            "owner_id": payload.get("owner_id", "architect"),
        }

        print(f"\n{'='*60}")
        print(f"[ARCH_DRIFT] Starting scan")
        print(f"{'='*60}\n")

        try:
            state = ItArchitectureDriftSkill.task_resolve_repo(state)
            if state.get("error"):
                return {"error": state["error"], "scan_id": None}

            state = ItArchitectureDriftSkill.task_clone_snapshot(state)
            state = ItArchitectureDriftSkill.task_load_rules(state)

            if state.get("warning"):
                return {
                    "warning": state["warning"],
                    "scan_id": None,
                    "repo_url": state.get("repo_url"),
                    "branch": state.get("branch"),
                }

            state = ItArchitectureDriftSkill.task_scan_code(state)
            state = ItArchitectureDriftSkill.task_audit_config(state)
            state = ItArchitectureDriftSkill.task_cross_reference(state)
            state = ItArchitectureDriftSkill.task_persist_report(state)

            report = state.get("report", {})
            print(f"\n{'='*60}")
            print(f"[ARCH_DRIFT] Scan complete: {report.get('summary', {}).get('total', 0)} violations")
            print(f"{'='*60}\n")

            return report

        except Exception as e:
            print(f"[ARCH_DRIFT] Scan failed: {e}")
            return {"error": str(e), "scan_id": None}

        finally:
            temp_dir = state.get("temp_dir")
            connector = state.get("_connector")
            if temp_dir and connector:
                connector.cleanup(temp_dir)

    @staticmethod
    def describe_result(result: Dict[str, Any]) -> str:
        """Human-readable description for chat responses."""
        if "error" in result:
            return f"Drift scan failed: {result['error']}"

        if "warning" in result:
            return result["warning"]

        summary = result.get("summary", {})
        total = summary.get("total", 0)
        critical = summary.get("critical", 0)
        high = summary.get("high", 0)
        repo = result.get("repo_label") or result.get("repo_url", "unknown")
        branch = result.get("branch", "main")

        if total == 0:
            return f"✅ **No drift detected** in `{repo}` ({branch}). The codebase is fully aligned with your architecture rules."

        severity_str = ""
        if critical > 0:
            severity_str += f"🔴 {critical} critical, "
        if high > 0:
            severity_str += f"🟠 {high} high, "
        severity_str += f"{total} total"

        recommendation = result.get("strategic_recommendation", "")
        violations_preview = ""
        for v in result.get("violations", [])[:3]:
            emoji = "🔴" if v["severity"] == "critical" else "🟠" if v["severity"] == "high" else "🟡"
            violations_preview += f"\n{emoji} **{v['file_path']}** — {v['explanation']}"

        return (
            f"🚨 **Drift Analysis for `{repo}` ({branch})**\n\n"
            f"**{severity_str}** violations found.\n"
            f"{violations_preview}\n\n"
            f"💡 **Recommendation:** {recommendation}"
        )
