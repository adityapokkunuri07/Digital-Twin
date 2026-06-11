"""
blast_radius.py — IT Blast Radius Simulator Functional Skill
==============================================================
Orchestrates the full 6-step Blast Radius simulation pipeline.

Refactored into discrete task methods so the workflow engine can:
  - Chain them as individual nodes
  - Insert human gates between any two steps
  - Toggle individual tasks on/off

Task Methods:
  1. task_read_pr       — Fetch PR title, body, and file diffs
  2. task_map_ast       — Parse diffs into structured code signals
  3. task_profile_infra — Profile live Supabase infra load
  4. task_simulate      — Run LLM simulation, get structured risk report
  5. task_comment_pr    — Post Markdown report comment on the GitHub PR
  6. task_persist_report — Save report to blast_radius_reports table

Auto-discovered by skill_router.py — NO edits to shared files needed.
"""
from typing import Dict, Any
from app.skills.functional.base_skill import BaseFunctionalSkill


class ItBlastRadiusSkill(BaseFunctionalSkill):
    """
    Intercepts GitHub PRs and simulates cascading failures,
    circular dependencies, and resource cost impact before merge.
    """

    @staticmethod
    def skill_name() -> str:
        return "SKL_IT_BLAST_RADIUS"

    # ══════════════════════════════════════════════════════════════════════
    # DISCRETE TASK METHODS
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def task_read_pr(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 1: Fetch PR data from GitHub."""
        from app.services.pr_reader import PRReader

        owner_id = state.get("owner_id", "architect")
        reader = PRReader(owner_id=owner_id)
        pr_data = reader.fetch(
            state.get("repo_owner", ""),
            state.get("repo_name", ""),
            state.get("pr_number", 0),
        )

        if "error" in pr_data and not pr_data.get("changed_files"):
            print(f"[BLAST_RADIUS] PR fetch failed: {pr_data.get('error')}")

        state["pr_data"] = pr_data
        print(f"[BLAST_RADIUS] Task 1/6 — PR data fetched")
        return state

    @staticmethod
    def task_map_ast(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 2: Parse diffs into structured code signals."""
        from app.services.ast_mapper import ASTMapper

        pr_data = state.get("pr_data", {})
        code_map = ASTMapper.parse(pr_data.get("changed_files", []))
        state["code_map"] = code_map
        print(f"[BLAST_RADIUS] Task 2/6 — Code signals mapped")
        return state

    @staticmethod
    def task_profile_infra(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 3: Profile live infrastructure load."""
        from app.services.traffic_cop import TrafficCop

        owner_id = state.get("owner_id", "architect")
        traffic = TrafficCop.profile(owner_id=owner_id)
        state["traffic"] = traffic
        print(f"[BLAST_RADIUS] Task 3/6 — Infrastructure profiled")
        return state

    @staticmethod
    def task_simulate(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 4: Run blast radius simulation via LLM."""
        from app.services.blast_engine import BlastEngine

        engine = BlastEngine()
        report = engine.simulate(
            pr_data=state.get("pr_data", {}),
            code_map=state.get("code_map", {}),
            traffic=state.get("traffic", {}),
            pr_number=state.get("pr_number", 0),
            repo_full_name=state.get("repo_full", ""),
        )
        state["report"] = report
        print(f"[BLAST_RADIUS] Task 4/6 — Simulation complete: {report.get('status', 'UNKNOWN')}")
        return state

    @staticmethod
    def task_comment_pr(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 5: Post risk report as comment on GitHub PR."""
        from app.services.pr_commenter import PRCommenter

        owner_id = state.get("owner_id", "architect")
        commenter = PRCommenter(owner_id=owner_id)
        report = state.get("report", {})
        comment_posted = commenter.post(
            state.get("repo_owner", ""),
            state.get("repo_name", ""),
            state.get("pr_number", 0),
            report,
        )
        state["report"]["comment_posted"] = comment_posted
        print(f"[BLAST_RADIUS] Task 5/6 — GitHub comment {'posted' if comment_posted else 'failed'}")
        return state

    @staticmethod
    def task_persist_report(state: Dict[str, Any]) -> Dict[str, Any]:
        """Task 6: Save report to blast_radius_reports table."""
        from app.services.supabase_client import SupabaseService

        report = state.get("report", {})
        try:
            db = SupabaseService()
            db.client.table("blast_radius_reports").insert({
                "pr_number": state.get("pr_number", 0),
                "repo_full_name": state.get("repo_full", ""),
                "owner_id": state.get("owner_id", "architect"),
                "status": report.get("status", "WARNING"),
                "report": report,
            }).execute()
            print(f"[BLAST_RADIUS] Task 6/6 — Report persisted")
        except Exception as e:
            print(f"[BLAST_RADIUS] Failed to persist report: {e}")

        return state

    # ══════════════════════════════════════════════════════════════════════
    # BACKWARD-COMPATIBLE EXECUTE (calls tasks in sequence)
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Full blast radius pipeline — sequential execution of all tasks."""
        repo_owner = payload.get("repo_owner", "")
        repo_name = payload.get("repo_name", "")
        pr_number = int(payload.get("pr_number", 0))
        owner_id = payload.get("owner_id", "architect")
        repo_full = f"{repo_owner}/{repo_name}"

        state = {
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "pr_number": pr_number,
            "owner_id": owner_id,
            "repo_full": repo_full,
        }

        print(f"\n{'='*60}")
        print(f"[BLAST_RADIUS] Starting simulation: PR #{pr_number} in {repo_full}")
        print(f"{'='*60}\n")

        if not repo_owner or not repo_name or not pr_number:
            return {
                "error": "Missing required fields: repo_owner, repo_name, pr_number",
                "pr_number": pr_number,
            }

        state = ItBlastRadiusSkill.task_read_pr(state)
        state = ItBlastRadiusSkill.task_map_ast(state)
        state = ItBlastRadiusSkill.task_profile_infra(state)
        state = ItBlastRadiusSkill.task_simulate(state)
        state = ItBlastRadiusSkill.task_comment_pr(state)
        state = ItBlastRadiusSkill.task_persist_report(state)

        report = state.get("report", {})
        print(f"\n{'='*60}")
        print(f"[BLAST_RADIUS] Complete — Status: {report.get('status')}")
        print(f"{'='*60}\n")

        return report

    @staticmethod
    def describe_result(result: Dict[str, Any]) -> str:
        """Human-readable summary for chat responses."""
        if "error" in result:
            return f"Blast radius simulation failed: {result['error']}"

        status = result.get("status", "UNKNOWN")
        pr_number = result.get("pr_number", "?")
        note = result.get("architect_note", "")
        summary = result.get("blast_radius_summary", {})
        cascading = summary.get("cascading_failures", [])
        confidence = result.get("confidence", "MEDIUM")

        emoji = {"SAFE": "✅", "WARNING": "⚠️", "DANGER": "🚨"}.get(status, "⚠️")

        top_failures = ""
        for f in cascading[:3]:
            top_failures += f"\n• {f}"

        return (
            f"{emoji} **Blast Radius — PR #{pr_number}: {status}** (confidence: {confidence})\n\n"
            f"{note}\n"
            f"{f'**Top risks:{top_failures}**' if top_failures else ''}\n\n"
            f"Full report posted as a comment on the GitHub PR."
        )
