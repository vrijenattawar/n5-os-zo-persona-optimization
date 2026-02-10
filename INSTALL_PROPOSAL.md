---
created: 2026-02-10
last_edited: 2026-02-10
version: 1.0
provenance: bootloader-scan
---

# Install Proposal (Socratic Step)

## Proposed Paths
- documents_system_path: /home/workspace/Documents/System
- learning_ledger_path: /home/workspace/Documents/System/persona-learnings.md

## Personas to Create
- operator: Operator
- builder: Builder
- debugger: Debugger
- strategist: Strategist
- writer: Writer
- researcher: Researcher
- teacher: Teacher

## What Will Be Installed
- Routing contract file
- Learning ledger file (if not exists)
- 7 persona prompts (in Zo settings)
- 6 rules (4 hard-switch + 2 methodology)

## How ad-hoc changes are applied across the board
- Persona names and rule prefixes are injected into templates before export
- Routes and learning ledger paths are customizable via personalize.md

## Socratic questions (answer in templates/personalize.md)
1. Which personas are you installing, and why those?
2. Where will the routing contract and learning ledger live?
3. What rule prefix avoids collisions in your system?
4. What would break if rules mis-route a request?
5. How will you verify switching correctness?