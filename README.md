---
created: 2026-02-10
last_edited: 2026-02-10
version: 1.0
provenance: con_zreDLAsCmbNBlcd1
---

# N5 OS: Zo Persona Optimization

A portable, Zo‑native bootloader that installs a coordinated **persona agency** with automatic switching. Built to replicate the core mechanics of V’s persona system for other Zo users.

## What this sets up

**Personas (7):** Operator, Builder, Debugger, Strategist, Writer, Researcher, Teacher

**Switching model (hybrid):**
- **Hard switches** for distinct cognitive stances: Builder, Debugger, Strategist, Writer
- **Methodology injection** (no switch) for technique-only personas: Researcher, Teacher

**Mandatory install flow:**
1. System scan
2. Socratic clarification (you review a proposal + answer targeted questions)
3. Apply install (personas + rules + routing contract)

---

## Quick start

```bash
python3 scripts/bootloader.py --scan
# Review INSTALL_PROPOSAL.md and update templates/personalize.md
python3 scripts/bootloader.py --apply
```

---

## What’s inside

- `docs/architecture.md` — the design rationale and switching logic
- `docs/advised-filestructure.md` — recommended structure + fuzzy install guidance
- `templates/personas/` — persona prompts (generic, editable)
- `templates/personalize.md` — your naming + routing preferences
- `scripts/bootloader.py` — scan → proposal → apply install

---

## License

MIT (add one if you want to publish).