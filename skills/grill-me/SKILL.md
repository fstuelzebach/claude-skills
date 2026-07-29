---
name: grill-me
description: Interview the user in dependency-aware rounds until reaching shared understanding of a plan or design. Use when the user wants to stress-test a plan, get grilled on their design, or mentions "grill me". Pass "quick" for one-at-a-time mode.
---

## Pre-flight

Before asking anything, explore the codebase to auto-answer what can be derived
from code. Do not ask questions that have clear answers there.

## Round-based interviewing

Interview me in rounds. Each round is a batch of 2–4 independent questions —
questions whose answers don't depend on each other. Questions that depend on
earlier answers are held back and asked in the next round once those answers land.

Format each round exactly like this:

---
**Round N of ~M**

**Q1.** [Question]
→ Recommended: [your recommendation + one-line rationale]

**Q2.** [Question]
→ Recommended: [your recommendation + one-line rationale]

---

Label dependency notes inline if a question in the same round is weakly sensitive
to another: "(if Q1 → yes, lean toward X)". Only split into a new round when a
question genuinely cannot be framed without the prior answer.

Continue until every branch of the decision tree is resolved.

## Closing

Write a **Shared understanding** paragraph summarising every decision made —
crisp enough to paste directly into a plan or CLAUDE.md.

## Quick mode

If invoked as `/grill-me quick`, skip rounds and ask one question at a time
(original behaviour). Use this for short checks with 3 questions or fewer.