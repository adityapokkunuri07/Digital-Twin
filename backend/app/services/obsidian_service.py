import os
import json
from typing import List, Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class ObsidianExportService:
    def __init__(self, vault_path: str = "c:/Users/harin/Downloads/doctor/Digital-Twin/obsidian_vault"):
        self.vault_path = vault_path
        self._ensure_directories()

    def _ensure_directories(self):
        try:
            os.makedirs(os.path.join(self.vault_path, "configs"), exist_ok=True)
            os.makedirs(os.path.join(self.vault_path, "cot_nodes"), exist_ok=True)
            logger.info(f"Obsidian Vault directories verified at: {self.vault_path}")
        except Exception as e:
            logger.error(f"Error creating Obsidian directories: {e}")

    def export_config(
        self, config: Dict[str, Any], nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> str:
        """
        Exports Twin workflow config and associated CoT graph to the vault.
        Returns:
            str: Path of the main config file written.
        """
        config_id = config.get("config_id")
        doctor_id = config.get("doctor_id")
        workflow_config = config.get("workflow_config", {})
        active_version = config.get("active_version", "1.0.0")
        is_feasible = config.get("is_feasible", True)
        errors = config.get("validation_errors", [])

        # 1. Export main config file
        config_filename = f"config_{config_id}.md"
        config_filepath = os.path.join(self.vault_path, "configs", config_filename)

        # Build YAML frontmatter
        yaml_lines = [
            "---",
            f"id: {config_id}",
            f"doctor_id: {doctor_id}",
            f"version: {active_version}",
            f"feasible: {str(is_feasible).lower()}",
            "errors: " + json.dumps(errors),
            "type: twin_config",
            "---"
        ]

        # Build content
        content_lines = [
            f"# Twin Workflow Configuration: {config_id}",
            "",
            "## Configuration Workflow Steps",
            ""
        ]

        steps = workflow_config.get("steps", [])
        for step in steps:
            content_lines.append(f"### Step: {step.get('name', 'Unnamed')} (ID: {step.get('id')})")
            content_lines.append(f"- **Inputs**: {', '.join(step.get('inputs', []))}")
            content_lines.append(f"- **Outputs**: {', '.join(step.get('outputs', []))}")
            content_lines.append(f"- **Dependencies**: {', '.join(step.get('dependencies', []))}")
            content_lines.append("")

        # Add references to CoT nodes
        content_lines.append("## Associated Chain of Thought (CoT) Nodes")
        content_lines.append("")
        for node in nodes:
            node_id = node.get("node_id")
            title = node.get("title", f"Node {node_id}")
            # Obsidian Wiki-link
            content_lines.append(f"- [[node_{node_id}|{title}]] ({node.get('node_type', 'intake')})")

        full_content = "\n".join(yaml_lines + [""] + content_lines)

        try:
            with open(config_filepath, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.info(f"Exported configuration to Obsidian: {config_filepath}")
        except Exception as e:
            logger.error(f"Failed to write Obsidian config: {e}")

        # 2. Export individual CoT nodes
        # Create map of node_id -> edges list
        outgoing_edges = {}
        for edge in edges:
            src = str(edge["source_node_id"])
            tgt = str(edge["target_node_id"])
            rel = edge.get("relationship_type", "related_to")
            if src not in outgoing_edges:
                outgoing_edges[src] = []
            outgoing_edges[src].append((tgt, rel))

        for node in nodes:
            node_id = str(node.get("node_id"))
            title = node.get("title", f"Node {node_id}")
            node_type = node.get("node_type", "intake")
            body = node.get("content", "")
            meta = node.get("metadata", {})

            node_filepath = os.path.join(self.vault_path, "cot_nodes", f"node_{node_id}.md")

            node_yaml = [
                "---",
                f"id: {node_id}",
                f"config_id: {config_id}",
                f"node_type: {node_type}",
                f"title: \"{title}\"",
                f"unlearned: {str(meta.get('unlearned', False)).lower()}",
            ]
            if "unlearning_reason" in meta:
                node_yaml.append(f"unlearning_reason: \"{meta['unlearning_reason']}\"")
            node_yaml.append("---")

            node_content = [
                f"# CoT Node: {title}",
                "",
                "## Content",
                "",
                body,
                ""
            ]

            # Append links to target nodes
            node_edges = outgoing_edges.get(node_id, [])
            if node_edges:
                node_content.append("## Relational Edges")
                node_content.append("")
                for tgt_id, rel in node_edges:
                    node_content.append(f"- **{rel}** -> [[node_{tgt_id}]]")

            full_node_content = "\n".join(node_yaml + [""] + node_content)

            try:
                with open(node_filepath, "w", encoding="utf-8") as f:
                    f.write(full_node_content)
            except Exception as e:
                logger.error(f"Failed to write Obsidian node {node_id}: {e}")

        return config_filepath
