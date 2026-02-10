#!/usr/bin/env python3
"""Bootloader for Zo persona optimization.

Flow:
1) --scan (default) writes INSTALL_PROPOSAL.md so you can personalize + approve.
2) --apply packages the manifest and asks Zo (via /zo/ask) to create personas and rules.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib import request

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"
PERSONA_TEMPLATES_DIR = TEMPLATES_DIR / "personas"
ROUTING_TEMPLATE_PATH = TEMPLATES_DIR / "routing-contract.md"
PERSONALIZE_PATH = TEMPLATES_DIR / "personalize.md"
WORKSPACE_ROOT = Path("/home/workspace")
INSTALL_PROPOSAL_PATH = REPO_ROOT / "INSTALL_PROPOSAL.md"
ZO_ASK_URL = "https://api.zo.computer/zo/ask"

HARD_SWITCH_RULES = [
    {
        "key": "builder",
        "name": "builder switch",
        "condition": "When the user asks to build, create, implement, or deploy systems",
        "instruction_template": "Call set_active_persona('<builder_id>') before substantive work begins.",
    },
    {
        "key": "debugger",
        "name": "debugger switch",
        "condition": "When the user asks to debug, troubleshoot, test, or verify",
        "instruction_template": "Call set_active_persona('<debugger_id>') before substantive work begins.",
    },
    {
        "key": "strategist",
        "name": "strategist switch",
        "condition": "When the user needs decisions, tradeoffs, or strategy",
        "instruction_template": "Call set_active_persona('<strategist_id>') before substantive work begins.",
    },
    {
        "key": "writer",
        "name": "writer switch",
        "condition": "When the user needs external-facing writing or polished drafts",
        "instruction_template": "Call set_active_persona('<writer_id>') before substantive work begins.",
    },
]

METHODOLOGY_RULES = [
    {
        "key": "researcher",
        "name": "researcher methodology",
        "condition": "When the user asks for multi-source research",
        "instruction": "Without changing personas, load and apply the Researcher methodology described in templates/personas/researcher.md (method steps + standards, trimmed frontmatter).",
    },
    {
        "key": "teacher",
        "name": "teacher methodology",
        "condition": "When the user asks for deep explanation or learning support",
        "instruction": "Without changing personas, load and apply the Teacher methodology described in templates/personas/teacher.md (method steps + standards, trimmed frontmatter).",
    },
]


def timestamped(message: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_frontmatter(text: str) -> str:
    match = re.match(r"^---\n.*?\n---\n", text, flags=re.DOTALL)
    return text[match.end():] if match else text


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
        match = re.match(r"^---\n.*?\n---\n", raw, flags=re.DOTALL)
        if match:
            raw = raw[match.end():]
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
    preferred = WORKSPACE_ROOT / "Documents" / "System"
    if preferred.exists():
        candidates["documents_system"].insert(0, str(preferred))
    return candidates


def propose_mapping(candidates: Dict[str, List[str]]) -> Dict[str, str]:
    doc_candidates = candidates.get("documents_system", [])
    doc_system = doc_candidates[0] if doc_candidates else str(WORKSPACE_ROOT / "Documents" / "System")
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


def build_persona_manifest(persona_names: Dict[str, str], ledger_path: str) -> List[Dict[str, Any]]:
    ledger_text = learning_block(ledger_path)
    manifests: List[Dict[str, Any]] = []
    for role, template_path in {
        "operator": PERSONA_TEMPLATES_DIR / "operator.md",
        "builder": PERSONA_TEMPLATES_DIR / "builder.md",
        "debugger": PERSONA_TEMPLATES_DIR / "debugger.md",
        "strategist": PERSONA_TEMPLATES_DIR / "strategist.md",
        "writer": PERSONA_TEMPLATES_DIR / "writer.md",
        "researcher": PERSONA_TEMPLATES_DIR / "researcher.md",
        "teacher": PERSONA_TEMPLATES_DIR / "teacher.md",
    }.items():
        raw_prompt = strip_frontmatter(load_text(template_path))
        placeholders = {f"{r}_name": persona_names[r] for r in persona_names}
        prompt = apply_placeholders(raw_prompt, placeholders)
        if "{{LEARNING_LEDGER_BLOCK}}" in prompt:
            prompt = prompt.replace("{{LEARNING_LEDGER_BLOCK}}", ledger_text)
        elif ledger_text:
            prompt = prompt + "\n\n" + ledger_text
        manifests.append({
            "role": role,
            "name": persona_names[role],
            "prompt": prompt,
            "template_path": str(template_path),
        })
    return manifests


def build_rule_manifest(rule_prefix: str) -> List[Dict[str, str]]:
    rules: List[Dict[str, str]] = []
    for rule in HARD_SWITCH_RULES:
        rules.append({
            "name": f"{rule_prefix}: {rule['name']}",
            "condition": rule["condition"],
            "instruction": rule["instruction_template"],
        })
    for rule in METHODOLOGY_RULES:
        rules.append({
            "name": f"{rule_prefix}: {rule['name']}",
            "condition": rule["condition"],
            "instruction": rule["instruction"],
        })
    return rules


def send_zo_prompt(prompt: str) -> Dict[str, Any]:
    token = os.environ.get("ZO_CLIENT_IDENTITY_TOKEN", "")
    if not token:
        raise RuntimeError("ZO_CLIENT_IDENTITY_TOKEN missing; run inside Zo or export the token.")
    payload = {"input": prompt}
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(ZO_ASK_URL, data=data, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", f"Bearer {token}")
    with request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_json_summary(output: str) -> Dict[str, Any]:
    decoder = json.JSONDecoder()
    start = output.find("{")
    if start == -1:
        return {"error": "No JSON in response", "output": output}
    try:
        summary, _ = decoder.raw_decode(output[start:])
        return summary
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "output": output[start:]}


def build_install_prompt(personas: List[Dict[str, Any]], rules: List[Dict[str, str]]) -> str:
    persona_block = json.dumps([{"name": p["name"], "prompt": p["prompt"]} for p in personas], indent=2)
    rule_block = json.dumps(rules, indent=2)
    return (
        "You are Zo. Run the persona installation manifest below by calling the relevant tools.\n"
        "For each persona entry, immediately call the `create_persona` tool with the `name` and `prompt` values.\n"
        "For each rule entry, call the `create_rule` tool with the `name`, `condition`, and `instruction`.\n"
        "Do not invent additional personas or rules. After each tool call, note the returned ID.\n"
        "Reply with a JSON object describing success, e.g. `{\n  \"success\": true,\n  \"personas\": [{\"name\": \"Builder\", \"id\": \"...\"}],\n  \"rules\": [{\"name\": \"persona: builder switch\", \"id\": \"...\"}]\n}`.\n"
        "If any tool call fails, report `success: false` and include an `error_message`.\n"
        "Do not switch personas while installing.\n\n"
        f"Personas:\n{persona_block}\n\n"
        f"Rules:\n{rule_block}\n"
        "Replace tokens like <builder_id> with the ID returned from the create_persona tool before calling create_rule."
    )


def execute_install_manifest(personas: List[Dict[str, Any]], rules: List[Dict[str, str]]) -> Dict[str, Any]:
    prompt = build_install_prompt(personas, rules)
    response = send_zo_prompt(prompt)
    summary = extract_json_summary(response.get("output", ""))
    summary.setdefault("raw_output", response.get("output", ""))
    return summary


def apply_install() -> None:
    if not INSTALL_PROPOSAL_PATH.exists():
        raise RuntimeError("INSTALL_PROPOSAL.md not found. Run --scan first.")
    personalize = parse_personalize()
    if personalize.get("approve_install", "false").lower() != "true":
        raise RuntimeError("approve_install must be true in templates/personalize.md before applying.")
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
    docs_system.mkdir(parents=True, exist_ok=True)
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
    ledger_path = Path(mapping["learning_ledger_path"])
    if not ledger_path.exists():
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(
            """---
created: 2026-02-10
last_edited: 2026-02-10
version: 1.0
provenance: bootloader-install
---

# Persona Learnings

- 
""",
            encoding="utf-8",
        )
    persona_manifest = build_persona_manifest(persona_names, str(ledger_path))
    rules = build_rule_manifest(personalize.get("rule_prefix", "persona"))
    summary = execute_install_manifest(persona_manifest, rules)
    if not summary.get("success"):
        raise RuntimeError(f"Install failed: {summary.get('error_message', summary)}")
    timestamped("Install manifest submitted. Review Zo's response for created IDs.")
    timestamped(json.dumps(summary, indent=2))


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
        "- 6 rules (4 hard-switch + 2 methodology)",
        "",
        "## How ad-hoc changes are applied across the board",
        "- Persona names and rule prefixes are injected into templates before export",
        "- Routes and learning ledger paths are customizable via personalize.md",
        "",
        "## Socratic questions (answer in templates/personalize.md)",
        "1. Which personas are you installing, and why those?",
        "2. Where will the routing contract and learning ledger live?",
        "3. What rule prefix avoids collisions in your system?",
        "4. What would break if rules mis-route a request?",
        "5. How will you verify switching correctness?",
    ]
    INSTALL_PROPOSAL_PATH.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zo Persona Optimization bootloader")
    parser.add_argument("--scan", action="store_true", help="Scan the workspace and write INSTALL_PROPOSAL.md")
    parser.add_argument("--apply", action="store_true", help="Apply the install manifest via Zo's /zo/ask endpoint")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.scan and not args.apply:
        print("Please specify --scan or --apply. Use --scan first, then update personalize.md, then --apply.")
        sys.exit(1)
    if args.scan:
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
        print(
            f"Wrote {INSTALL_PROPOSAL_PATH}. Review it, update templates/personalize.md, set approve_install: true, then run --apply."
        )
        return
    apply_install()


if __name__ == "__main__":
    main()
