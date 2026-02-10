#!/usr/bin/env python3
"""Bootloader for Zo Persona Optimization.

Flow:
1) --scan (default): scans workspace and writes INSTALL_PROPOSAL.md
2) --apply: requires templates/personalize.md with approve_install: true
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import request

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"
PERSONA_TEMPLATES_DIR = TEMPLATES_DIR / "personas"
ROUTING_TEMPLATE_PATH = TEMPLATES_DIR / "routing-contract.md"
PERSONALIZE_PATH = TEMPLATES_DIR / "personalize.md"
WORKSPACE_ROOT = Path("/home/workspace")
INSTALL_PROPOSAL_PATH = REPO_ROOT / "INSTALL_PROPOSAL.md"

HARD_SWITCH_RULES = [
    {
        "key": "builder",
        "name": "builder switch",
        "condition": "When the user asks to build, create, implement, deploy, or code systems",
    },
    {
        "key": "debugger",
        "name": "debugger switch",
        "condition": "When the user asks to debug, troubleshoot, verify, test, or audit",
    },
    {
        "key": "strategist",
        "name": "strategist switch",
        "condition": "When the user needs decisions, options, tradeoffs, or strategy",
    },
    {
        "key": "writer",
        "name": "writer switch",
        "condition": "When the user needs external-facing writing or polished drafts",
    },
]

METHODOLOGY_RULES = [
    {
        "key": "researcher",
        "name": "researcher methodology",
        "condition": "When the user asks for research across multiple sources",
    },
    {
        "key": "teacher",
        "name": "teacher methodology",
        "condition": "When the user asks for a deep explanation or wants to learn",
    },
]


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_simple_kv(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key:
            data[key] = value
    return data


def parse_personalize() -> Dict[str, str]:
    raw = load_text(PERSONALIZE_PATH)
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            raw = parts[2]
    return parse_simple_kv(raw)


def find_candidates() -> Dict[str, List[str]]:
    candidates = {"documents_system": []}
    for root, dirs, _ in os.walk(WORKSPACE_ROOT):
        depth = Path(root).relative_to(WORKSPACE_ROOT).parts
        if len(depth) > 3:
            dirs[:] = []
            continue
        if Path(root).name.lower() == "system" and Path(root).parent.name.lower() in {"documents", "docs"}:
            candidates["documents_system"].append(root)
    if (WORKSPACE_ROOT / "Documents" / "System").exists():
        candidates["documents_system"].insert(0, str(WORKSPACE_ROOT / "Documents" / "System"))
    return candidates


def propose_mapping(candidates: Dict[str, List[str]]) -> Dict[str, str]:
    doc_system = candidates["documents_system"][0] if candidates["documents_system"] else str(WORKSPACE_ROOT / "Documents" / "System")
    return {
        "documents_system_path": doc_system,
        "learning_ledger_path": str(Path(doc_system) / "persona-learnings.md"),
    }


def apply_placeholders(text: str, mapping: Dict[str, str]) -> str:
    for key, value in mapping.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def learning_block(ledger_path: str) -> str:
    if not ledger_path:
        return ""
    return (
        "## Learning Ledger\n\n"
        "If you learn something that should persist beyond this task, append a brief note to:\n"
        f"{ledger_path}\n"
    )


def write_install_proposal(mapping: Dict[str, str], persona_names: Dict[str, str]) -> None:
    lines = [
        "---",
        "created: 2026-02-10",
        "last_edited: 2026-02-10",
        "version: 1.0",
        "provenance: bootloader-scan",
        "---",
        "",
        "# Install Proposal (Socratic Step)",
        "",
        "## Proposed Paths",
        f"- documents_system_path: {mapping['documents_system_path']}",
        f"- learning_ledger_path: {mapping['learning_ledger_path']}",
        "",
        "## Personas to Create",
    ]
    for role, name in persona_names.items():
        lines.append(f"- {role}: {name}")
    lines += [
        "",
        "## What Will Be Installed",
        "- Routing contract file",
        "- Learning ledger file (if not exists)",
        "- 7 persona prompts (in Zo settings)",
        "- 6 rules (4 hard-switch, 2 methodology)",
        "",
        "## How ad-hoc changes are applied across the board",
        "- All persona names are injected into prompts and rule instructions",
        "- The routing contract uses the same names",
        "- Paths from personalization override defaults before writing files",
        "",
        "## Socratic questions (answer in templates/personalize.md)",
        "1. Which personas are you installing, and why those?",
        "2. Where will the routing contract and learning ledger live?",
        "3. What rule prefix avoids collisions in your system?",
        "4. What would break if rules mis-route a request?",
        "5. How will you verify switching correctness?",
    ]
    INSTALL_PROPOSAL_PATH.write_text("\n".join(lines), encoding="utf-8")


def api_request(method: str, path: str, payload: Dict) -> Dict:
    token = os.environ.get("ZO_CLIENT_IDENTITY_TOKEN")
    if not token:
        raise RuntimeError("ZO_CLIENT_IDENTITY_TOKEN not found. Run inside Zo.")
    url = f"https://api.zo.computer/{path}"
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method)
    req.add_header("authorization", token)
    req.add_header("content-type", "application/json")
    with request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def create_persona(name: str, prompt: str) -> str:
    result = api_request("POST", "personas", {"name": name, "prompt": prompt})
    return result.get("id", "")


def create_rule(name: str, condition: str, instruction: str) -> str:
    result = api_request("POST", "rules", {"condition": condition, "instruction": instruction})
    return result.get("id", "")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def apply_install() -> None:
    if not INSTALL_PROPOSAL_PATH.exists():
        raise RuntimeError("INSTALL_PROPOSAL.md not found. Run --scan first.")

    personalize = parse_personalize()
    if personalize.get("approve_install", "false").lower() != "true":
        raise RuntimeError("approve_install is not true. Update templates/personalize.md first.")

    candidates = find_candidates()
    mapping = propose_mapping(candidates)
    mapping.update({
        "documents_system_path": personalize.get("documents_system_path", mapping["documents_system_path"]),
        "learning_ledger_path": personalize.get("learning_ledger_path", mapping["learning_ledger_path"]),
    })

    persona_names = {
        "operator": personalize.get("operator_name", "Operator"),
        "builder": personalize.get("builder_name", "Builder"),
        "debugger": personalize.get("debugger_name", "Debugger"),
        "strategist": personalize.get("strategist_name", "Strategist"),
        "writer": personalize.get("writer_name", "Writer"),
        "researcher": personalize.get("researcher_name", "Researcher"),
        "teacher": personalize.get("teacher_name", "Teacher"),
    }

    docs_system = Path(mapping["documents_system_path"])
    ensure_dir(docs_system)

    # Write routing contract
    routing = apply_placeholders(load_text(ROUTING_TEMPLATE_PATH), {
        "operator_name": persona_names["operator"],
        "builder_name": persona_names["builder"],
        "debugger_name": persona_names["debugger"],
        "strategist_name": persona_names["strategist"],
        "writer_name": persona_names["writer"],
        "researcher_name": persona_names["researcher"],
        "teacher_name": persona_names["teacher"],
    })
    (docs_system / "persona-routing-contract.md").write_text(routing, encoding="utf-8")

    # Learning ledger
    ledger_path = Path(mapping["learning_ledger_path"])
    if not ledger_path.exists():
        ledger_content = """---
created: 2026-02-10
last_edited: 2026-02-10
version: 1.0
provenance: bootloader-install
---

# Persona Learnings

- 
"""
        ensure_dir(ledger_path.parent)
        ledger_path.write_text(ledger_content, encoding="utf-8")

    # Create personas
    created_ids: Dict[str, str] = {}
    for role, template_path in {
        "operator": PERSONA_TEMPLATES_DIR / "operator.md",
        "builder": PERSONA_TEMPLATES_DIR / "builder.md",
        "debugger": PERSONA_TEMPLATES_DIR / "debugger.md",
        "strategist": PERSONA_TEMPLATES_DIR / "strategist.md",
        "writer": PERSONA_TEMPLATES_DIR / "writer.md",
        "researcher": PERSONA_TEMPLATES_DIR / "researcher.md",
        "teacher": PERSONA_TEMPLATES_DIR / "teacher.md",
    }.items():
        prompt = load_text(template_path)
        prompt = apply_placeholders(prompt, {
            "operator_name": persona_names["operator"],
            "builder_name": persona_names["builder"],
            "debugger_name": persona_names["debugger"],
            "strategist_name": persona_names["strategist"],
            "writer_name": persona_names["writer"],
            "researcher_name": persona_names["researcher"],
            "teacher_name": persona_names["teacher"],
        })
        prompt = prompt.replace("{{LEARNING_LEDGER_BLOCK}}", learning_block(mapping["learning_ledger_path"]))
        created_ids[role] = create_persona(persona_names[role], prompt)

    # Create rules
    rule_prefix = personalize.get("rule_prefix", "persona")
    for rule in HARD_SWITCH_RULES:
        persona_id = created_ids.get(rule["key"], "")
        if not persona_id:
            continue
        create_rule(
            f"{rule_prefix}: {rule['name']}",
            rule["condition"],
            f"Call set_active_persona('{persona_id}') before substantive work.",
        )

    for rule in METHODOLOGY_RULES:
        create_rule(
            f"{rule_prefix}: {rule['name']}",
            rule["condition"],
            "Load and apply the methodology from the Researcher/Teacher prompt without switching persona.",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Zo Persona Optimization bootloader")
    parser.add_argument("--scan", action="store_true", help="Scan system and write INSTALL_PROPOSAL.md")
    parser.add_argument("--apply", action="store_true", help="Apply install after approval")
    args = parser.parse_args()

    if args.apply:
        apply_install()
        print("Install complete.")
        return

    candidates = find_candidates()
    mapping = propose_mapping(candidates)
    personalize = parse_personalize()
    persona_names = {
        "operator": personalize.get("operator_name", "Operator"),
        "builder": personalize.get("builder_name", "Builder"),
        "debugger": personalize.get("debugger_name", "Debugger"),
        "strategist": personalize.get("strategist_name", "Strategist"),
        "writer": personalize.get("writer_name", "Writer"),
        "researcher": personalize.get("researcher_name", "Researcher"),
        "teacher": personalize.get("teacher_name", "Teacher"),
    }
    write_install_proposal(mapping, persona_names)
    print(f"Wrote {INSTALL_PROPOSAL_PATH}. Review it and update templates/personalize.md, then run --apply.")


if __name__ == "__main__":
    main()
