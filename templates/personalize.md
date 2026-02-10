---
created: 2026-02-10
last_edited: 2026-02-10
version: 1.0
provenance: con_zreDLAsCmbNBlcd1
---
# Personalization

Fill these out after running `--scan`. The installer will not apply changes until `approve_install: true`.

## Required (names)

operator_name: "Operator"
builder_name: "Builder"
debugger_name: "Debugger"
strategist_name: "Strategist"
writer_name: "Writer"
researcher_name: "Researcher"
teacher_name: "Teacher"

## Required (rules)

rule_prefix: "persona"

## Required (structure)

documents_system_path: "/home/workspace/Documents/System"
learning_ledger_path: "/home/workspace/Documents/System/persona-learnings.md"

## Optional

voice_notes: ""
custom_domain_analogies: ""

## Approval (must be true to install)

approve_install: false

---

## Socratic clarification (answer before install)

1. Which personas are you installing, and why those?
2. Where will the routing contract and learning ledger live?
3. What rule prefix should be used to avoid collisions?
4. What would break if these rules mis‑route a request?
5. How will you verify the personas are switching correctly?
