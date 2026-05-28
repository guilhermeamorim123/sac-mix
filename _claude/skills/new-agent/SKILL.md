---
name: new-agent
description: Start the structured agent creation workflow
argument-hint: "[optional: agent name or brief description]"
user-invocable: true
---

# New Agent Creation

Start the Agent Maker workflow to create a new AI agent.

## If arguments were provided
Use `$ARGUMENTS` as the initial context for the agent being created. Skip asking for the basic description and jump to clarifying questions.

## Workflow

Begin **Phase 1 — Discovery**:

1. Ask the user what type of agent to create:
   - **Claude Code Agent** → artifacts go in `claude-agents/{name}/`
   - **OpenAI Custom GPT** → artifacts go in `openai-gpts/{name}/`
   - **Gemini Gem** → artifacts go in `gemini-gems/{name}/`

2. Ask probing questions to understand:
   - What problem does this agent solve?
   - Who is the target user?
   - What are the key behaviors and capabilities?
   - What constraints or guardrails are needed?
   - Is there a specific domain that requires web research?

3. Once you have full clarity, move to **Phase 2 — Brainstorm** and suggest features, platform capabilities, and improvements the user may not have considered.

4. Continue through all phases as defined in `docs/reference/agent-factory.md`: Discovery → Brainstorm → Spec → Build → Review. Read that file for the full creation workflow and platform-specific guidance (Claude Code / OpenAI GPT / Gemini Gem) BEFORE building any artifact.

**Remember**: Ask questions relentlessly. Do not proceed to building until the user has confirmed the spec.
