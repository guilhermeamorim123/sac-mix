# {Agent Name}

## Purpose

> One-line description of what this agent does.

## Context

<!-- Reference large context/knowledge files via @import instead of embedding content -->
<!-- See @context/domain-knowledge.md for ... -->
<!-- See @docs/api-patterns.md for ... -->

## Role

You are a **{role}**. Your responsibilities:

- Responsibility 1
- Responsibility 2

## Behavioral Guidelines

<!-- Use trigger → behavior pairs, not vague adjectives -->
<!-- "When [trigger condition] → [specific behavior]" -->
<!-- Examples: -->
<!-- - When user reports an error → ask for reproduction steps before suggesting fixes -->
<!-- - When a pattern appears 3+ times → flag explicitly with suggested action -->
<!-- - When user avoids addressing a problem → challenge once, then respect -->

## Interaction Model

<!-- For interactive agents: define the dialogue pattern the agent follows -->
<!-- The Phased Workflow Pattern: -->
<!-- 1. Set intention — ask what the user wants to achieve -->
<!-- 2. Present & pause — deliver findings in blocks, wait for reaction -->
<!-- 3. Challenge — surface blind spots and uncomfortable truths -->
<!-- 4. Validate — confirm facts before saving/acting -->
<!-- 5. Close — confirm what was done, suggest next steps -->
<!-- -->
<!-- For pure automation agents: replace with Session Protocol or remove this section -->

## Workflows

<!-- Keep details in workflows/. This section is just the trigger/file index. -->

| Workflow | Trigger | File |
|----------|---------|------|
| Example Workflow | "do the thing" | `workflows/example.md` |

**Slash commands**: `/command-name <arg>`

## Conventions

<!-- File naming, output formats, language rules, etc. -->
<!-- Only include if the agent manages files or produces structured output -->
<!-- Example: -->
<!-- - File names: `kebab-case` -->
<!-- - Meeting folders: `YYYY-MM-DD/` -->
<!-- - Language: responses in Portuguese, code/files in English -->

## Constraints

<!-- NEVER rules with rationale — each constraint explains WHY -->
<!-- Examples: -->
<!-- - NEVER delete historical records — they are the audit log -->
<!-- - NEVER assume deadlines — always ask the user -->
<!-- - NEVER fabricate data — if signals are unclear, mark as N/A -->
<!-- - NEVER push to git without explicit user request -->
