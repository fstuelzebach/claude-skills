---
name: improve-prompt
description: Diagnose a prompt and return a paste-ready rewrite — scope, test data, permissions, evidence standard, output contract, candour. Use when the user wants a prompt improved, reviewed, tightened, or written, or wants prompt feedback as a deliverable.
---

# Improve a prompt

Turn a prompt that *sounds* complete into one that actually constrains the work. Use this when
the user asks to improve, review, tighten, critique or write a prompt; when they hand over a
prompt they already ran and want to know why the output disappointed; or when they ask for
prompt feedback as a deliverable alongside other work.

This is not a rewording exercise. Most weak prompts are perfectly clear — they are simply
silent on the decisions that determine the result, and the model fills those silences with
defaults the user would not have chosen.

## Method

**1. Establish what actually happened.** If the prompt has been run, read the output before the
prompt. The gap between what was asked and what came back localises the defect faster than
inspecting the prompt alone. Ask which parts of the result were disappointing and which were
fine. If it hasn't been run, ask what a great result would look like — concretely enough that
you could tell a great one from a mediocre one.

**2. Diagnose against the ten axes below.** Name the silences. For each, state what the model
was left to decide for itself and what it plausibly decided. Be specific: "you didn't say which
files to look at, so it read three and generalised" beats "scope was unclear".

**3. Rewrite, then explain the diff.** Deliver a paste-ready prompt plus a short section on what
changed and why. The explanation is what teaches the user to write the next one themselves.

## The ten axes

**1. Scope and depth.** What is in, what is out, how far to go, and what "done" looks like.
Unbounded prompts get whatever depth fits comfortably in one response. If breadth matters, say
how many; if depth matters, say how deep.

**2. Inputs and test data.** The single most under-specified axis. Generic inputs produce generic
findings. Ask what the *adversarial* cases are — the edge cases, the awkward examples, the ones
that break assumptions — and name them explicitly in the prompt. One well-chosen hard example is
worth ten representative ones. Where the user can't name them, help them derive a set that spans
the real variation.

**3. Permissions and boundaries.** What may the model create, modify, run, install, publish or
delete? What must it ask about first? A model that is unsure defaults to read-only caution and
then under-reports — so silence here costs coverage, quietly. If a sandbox or test account
exists, the prompt should not merely permit writing to it but *require* it.

**4. Evidence standard.** The highest-leverage axis and the one almost everyone omits. An AI
asked for analysis will produce analysis-shaped prose whether or not the analysis happened,
because fluent critique is cheap to generate and the reader usually cannot tell. Counter it by
demanding, in the prompt: a citation per claim (file, line, page, element, observed value); a
stated verification method; explicit marking of inference versus observation; and permission to
say "I could not verify this" instead of asserting.

Push hardest for **claims the user can check without trusting the model's world knowledge.** An
argument from internal inconsistency — two numbers in the same system that cannot both be true —
is verifiable in seconds and survives the model being wrong about outside facts. An argument
from recalled knowledge requires the user to go and check, and may simply be false. Ask for the
first kind by name, with an example of the shape.

**5. Criteria over persona.** "Act like a senior security engineer" buys vocabulary. Vocabulary
is the part a model produces whether or not it did the work. Naming the *checks* — the specific
things to look for and measure — forces the work to happen. Keep persona to one line for tone;
put the weight in an explicit criteria list.

**6. Output contract.** Format, length, audience, structure, file names, and how findings should
be tagged (severity, effort, confidence). Where the user must act on the output, ask for a
prioritised order and say what the priority axis is.

**7. Exclusions.** Known issues, already-rejected ideas, areas deliberately out of bounds. A
three-line "don't bother with these" section reclaims real effort.

**8. Environment and context.** Stack, versions, conventions, where things live, what is
authenticated, what is a snapshot versus live. Context converts abstract advice into a concrete
diff the user can apply.

**9. Self-report.** Require the work to declare its own limits: what was checked and at what
depth, what was *not* checked and why, and what the next run should pursue — separating
hypotheses from conclusions. Ask for a table rather than a paragraph; a paragraph lets the model
gesture at limits without enumerating them. This is what makes repeated runs compound instead of
repeating.

**10. Candour.** Models soften by default, especially about work the user clearly owns. If the
user wants directness, the prompt must grant it explicitly and remove the incentive to pad:
lead with the problem, no compliment sandwich, don't inflate the strengths section to balance
the criticism, distinguish "this is wrong" from "this is taste", and say so when a whole
approach is the mistake. The useful framing is that invented praise is more expensive than harsh
criticism, because it makes the rest of the document less trustworthy.

## Failure modes to name when you see them

**The fluency trap.** Output that reads like expert analysis but rests on a glance. Symptom:
confident claims with no specific values, or findings that would be true of almost any artefact
of that kind. Fix with axis 4.

**The single-example trap.** One test case chosen for convenience, whose peculiarities either
hide whole classes of defect or masquerade as general findings. Fix with axis 2.

**The timid-reviewer trap.** Unclear permissions produce read-only work and thin coverage of
anything requiring interaction — reported as if the area were fine rather than unexamined. Fix
with axes 3 and 9.

**The persona trap.** Job-title framing yields the register of expertise without its substance.
Fix with axis 5.

**The agreeable-review trap.** Findings graded on a curve because the work is good overall, or
because the user obviously cares about it. Fix with axis 10.

## Rules for the rewrite

Keep the user's voice and their domain vocabulary — a rewrite that sounds like a different person
doesn't get used. Make it genuinely paste-ready: no meta-commentary inside the prompt itself, and
mark anything the user must supply with a conspicuous `[[SLOT]]` so it can't be missed. Prefer
concrete instruction over exhortation — "cite the element and its measured value" beats "be
rigorous". Where a real prior run exists, embed its best and worst moments as worked examples;
the *shape* of a good finding teaches more than an abstract standard. Don't inflate: added length
must buy a constraint. Close with a short, honest list of what remains underspecified, including
anything you still need from the user.

## The compounding habit

Whenever the user commissions substantial work from an AI, suggest they add a standing final
deliverable: *feedback on this prompt — what was underspecified, what led you astray, and a
paste-ready improved version.* It costs almost nothing, it is generated while the context is
still live and the friction still fresh, and each run starts from a better prompt than the last.
When producing such feedback yourself, be concrete about your own missteps — the wrong default
you chose, the thing you nearly asserted without checking, the area you skipped — because a
self-review that admits nothing specific teaches nothing.
