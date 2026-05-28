---
type: reference
---

# Agent Factory Reference

> The Chief of Staff vault includes an **agent creation workbench** as a sub-system. Use `/new-agent` to create production-grade AI agents for Claude Code, OpenAI Custom GPTs, or Google Gemini Gems; use `/list-agents` to list what you've already created. This file is the source of truth for the creation workflow and platform-specific guidance — both skills (and you when guiding the user) read it as canonical reference.

> Agents you create live alongside the CoS vault, in `claude-agents/`, `openai-gpts/`, and `gemini-gems/` at the repo root, each with a `_template/` reference folder.

## Agent Maker — Core Behavior

When running `/new-agent`, act as an expert AI agent architect. You design and build production-grade agents for **Claude Code**, **OpenAI Custom GPTs**, and **Google Gemini Gems**. You are a specialist in token-efficient prompt engineering and proactive co-creation.

- **Always ask questions** until you fully understand the user's goal — never assume
- **Suggest features** the user hasn't considered (hooks, skills, capabilities, edge cases)
- **Ask before doing web research** on domain-specific best practices
- **Show summary + preview** of main artifacts before saving — iterate on feedback
- **All generated artifacts in English** — conversation in the user's language
- **Never modify `_template/` folders** — copy structure into new agent folders

## Creation Workflow

Follow these phases for every new agent. Adapt depth to complexity — skip substeps for simple agents, go deep for complex ones.

### Phase 1 — Discovery
- Determine agent type: Claude Code (`claude-agents/`), OpenAI GPT (`openai-gpts/`), or Gemini Gem (`gemini-gems/`)
- Ask about: purpose, target audience, key behaviors, constraints, domain context
- Ask if web research is needed to understand the domain better
- For vague ideas: help the user define scope through guided questions
- For clear ideas: validate understanding, then move to brainstorm

### Phase 2 — Brainstorm
- Map which platform features apply to this agent:
  - **Claude Code**: custom agents, skills, hooks (Pre/PostToolUse, Stop, SessionStart), MCP servers, settings permissions, memory
  - **OpenAI GPT**: capabilities (web search, code interpreter, image gen, canvas), knowledge files, actions, conversation starters
  - **Gemini Gem**: instructions, knowledge files (max 10), Google Search grounding, code execution, Imagen, file analysis, Workspace integration
- Suggest features and improvements the user may not have considered
- Discuss edge cases: what happens when the user asks something off-scope? What guardrails are needed?
- Agree on the final feature set before proceeding

### Phase 3 — Spec
- Create `{type}/{agent-name}/README.md` with:
  - **Purpose**: one-paragraph description
  - **Features**: bullet list of agreed capabilities
  - **Architecture**: which artifacts will be created and why
  - **Files**: manifest of all files to generate
  - **Integration**: how to deploy this agent to a target project
  - **Changelog**: `- YYYY-MM-DD: Initial creation`

### Phase 4 — Build
- Generate all artifacts (see platform-specific guides below)
- Follow templates in `_template/` for structure reference
- Ensure token efficiency — every line must earn its place

### Phase 5 — Review
- Present a summary: what was created, key decisions, file list
- Show preview of the main artifact (CLAUDE.md or prompt.md)
- Iterate on user feedback — update artifacts and README changelog
- Suggest possible future improvements

---

## Claude Code Agent Guide

### What to Generate (decide per agent)

| Artifact | When to Create |
|----------|---------------|
| `CLAUDE.md` | **Always** — core instructions for the agent |
| `.claude/agents/*.md` | When the agent needs specialized sub-agents |
| `.claude/skills/*/SKILL.md` | When repetitive workflows need slash commands |
| `.claude/settings.json` | **Always** — explicit permissions even if minimal |
| `.claude/hooks/*.sh` | When deterministic validation/automation is needed |
| `.mcp.json` | When external tool integrations are required |

### CLAUDE.md Token Efficiency Rules

- **Max ~200 lines** — if longer, split into @imported files
- **Bullets, not prose** — each line is a scannable fact
- **Only write what Claude can't infer** from reading the code
- **Use @imports** for detailed docs: `See @docs/api-patterns.md`
- **Emphasis sparingly**: `IMPORTANT` or `YOU MUST` only for critical rules
- **Test**: for each line ask "Would removing this cause mistakes?" — if not, delete it
- **CLAUDE.md is an index** — workflow details in `workflows/`, reference docs in `docs/` or `context/`
- **Use @imports for context**: `See @context/team.md` auto-loads files into Claude's context
- **Recommended sections** (adapt per agent): Purpose, Context (@imports), Role, Behavioral Guidelines (trigger/behavior), Interaction Model (if interactive), Workflows (trigger/file table), Conventions, Constraints (with rationale)
- **Don't include**: Project structure trees (Claude can `ls`), detailed workflow steps (they live in `workflows/`)

### Agent Definition Format (.claude/agents/*.md)

```yaml
---
name: agent-name          # kebab-case, max 64 chars
description: When to use  # Claude uses this to auto-delegate
tools: Read, Grep, Glob   # Only grant necessary tools
model: sonnet              # sonnet|opus|haiku|inherit
---

Instructions for the agent...
```

### Skill Definition Format (.claude/skills/*/SKILL.md)

```yaml
---
name: skill-name
description: When to trigger this skill
argument-hint: "[arg]"
user-invocable: true
allowed-tools: Read, Grep
---

Skill instructions... Use $ARGUMENTS for passed args.
```

#### Skill Best Practices

- **Interactive skills trigger Phase 1** of a workflow — read context, then ASK before presenting full output
- **Reference detailed workflow files**: `"Follow the PHASED workflow in workflows/prepare-meeting.md"`
- **Include IMPORTANT instruction**: `"Do NOT build full output before asking user their intent"`
- **Keep `allowed-tools` minimal** — read-only skills: `Read, Glob, Grep`; write skills add `Write, Edit`
- **Argument hints guide the user**: `argument-hint: <member-name>` shows expected input format

### Hook Patterns

| Event | Use Case |
|-------|----------|
| `PreToolUse` + matcher `Bash` | Validate/block dangerous commands |
| `PreToolUse` + matcher `Edit\|Write` | Block edits to protected files |
| `PostToolUse` + matcher `Edit\|Write` | Auto-format, auto-lint |
| `Stop` | Run tests after Claude finishes |
| `SessionStart` | Environment setup, dependency checks |

Hook config goes in `.claude/settings.json` under `"hooks"` key. Exit codes: 0=allow, 2=block.

### Workflow Design Patterns

For agents that interact with users (not pure automation), design workflows as **phased conversations**, not step lists.

#### The Phased Workflow Pattern

| Phase | Purpose | Example |
|-------|---------|---------|
| **Intent** | Ask the user what they want before acting | "What's your goal for this meeting?" |
| **Present & Pause** | Deliver findings in digestible blocks, wait for reaction | Show summary → ask "Does this match your read?" |
| **Challenge** | Surface blind spots, patterns, uncomfortable truths | "You haven't discussed X in 3 meetings. Consider it?" |
| **Validate** | Confirm facts and commitments before saving | "I captured these action items. Correct?" |
| **Close** | Confirm what was done, suggest next steps | "Saved. Next time, I'll remind you about X." |

**Rules:**
- Mark PAUSE points explicitly in workflow files: `PAUSE: "Question for the user"`
- Skills should trigger Phase 1 (interactive), never skip to full output
- Include edge cases: first time, missing data, urgent situations, user has no clear intent
- Workflow detail files live in `workflows/` — CLAUDE.md only has the trigger/file index table

#### Behavioral Guidelines Pattern

Use **trigger → behavior** pairs instead of vague adjectives:

- BAD: `"Be proactive and direct"`
- GOOD: `"When action item appears 3+ times → flag with ⚠️ RECORRENTE and suggest specific action"`
- GOOD: `"When user avoids addressing a problem → challenge once with concrete suggestion, then respect"`

#### Constraints Pattern

Every constraint needs rationale:

- BAD: `"Don't modify old records"`
- GOOD: `"NEVER modify records older than 7 days — they are the historical log"`
- GOOD: `"NEVER fabricate data — if signals are unclear, mark as N/A"`

### Output Structure

```
claude-agents/{agent-name}/
├── README.md              # Spec + integration guide + changelog
├── CLAUDE.md              # Agent's main instructions (index, ≤150 lines)
├── .claude/
│   ├── settings.json      # Permissions + hooks (always create)
│   ├── agents/            # Sub-agent definitions
│   └── skills/            # Slash commands
│       └── {skill-name}/
│           └── SKILL.md
├── workflows/             # Detailed workflow files (if agent has workflows)
│   └── {workflow-name}.md
├── context/               # Context/knowledge files referenced via @import
│   └── *.md
├── templates/             # Output templates (if agent generates structured files)
│   └── *.md
├── scripts/               # Automation scripts (if needed)
│   └── *.py / *.sh
└── .mcp.json              # MCP servers (if needed)
```

---

## OpenAI Custom GPT Guide

### Prompt Structure (≤8000 characters)

Organize the system prompt in this order. Allocate characters by priority:

| Section | ~% Budget | Purpose |
|---------|-----------|---------|
| Role & Objective | 15% | Who the GPT is, what success looks like |
| Instructions | 30% | Step-by-step workflows, trigger/instruction pairs |
| Rules & Constraints | 20% | Negative constraints, scope limits, guardrails |
| Knowledge File Refs | 10% | Explicit file names and when to consult them |
| Output Format | 10% | Tone, structure, length, formatting |
| Edge Cases & Security | 10% | Off-scope handling, anti-injection, anti-leak |
| Notes | 5% | Final polish, style reminders |

### Prompt Engineering Rules

- **Use labeled Markdown sections** — the model treats each as separate intent
- **Trigger/instruction pairs** for complex workflows: define trigger condition then action
- **Negative constraints are powerful**: "NEVER do X" is more reliable than "try to avoid X"
- **Reference knowledge files by name**: "Consult `style-guide.md` for tone and voice"
- **Few-shot examples go in knowledge files**, not in the prompt — save character budget
- **Security block**: always include anti-injection and anti-prompt-leak rules
- **Max 4-5 workflows** per prompt — more dilutes the model's attention on each
- **Constraint reliability hierarchy**: `NEVER` > `Do not` > `Try to avoid`
- **Budget overflow priority** (what to cut first): Notes → Output Format → Knowledge Refs → Rules → Instructions → Role — never cut Role below ~600 chars. On Windows, CRLF adds ~1 byte per line to `wc -c` — subtract line count from byte count for true char total
- **Workflow-specific knowledge files**: when a workflow has detailed methodology, put it in a dedicated knowledge file and keep only concise steps in the prompt — reference the file with **"read `file.md` fully before starting"** at the workflow's opening line
- **Knowledge file enforcement** — "prefer the file" fails in practice. Use NEVER-strength language:
  - BAD: "If information conflicts, prefer the knowledge file"
  - GOOD: "NEVER respond from training data alone when a guide covers the topic — follow the guide's steps exactly"
  - Each workflow referencing a guide needs: "You MUST follow the guide — do not substitute with training data"
- **Prescriptive workflow steps** — abstract steps fail. Specify HOW with observable signals:
  - BAD: "Assess the user's level and adapt accordingly"
  - GOOD: "Infer level: beginner (no jargon), intermediate (uses terminology), advanced (asks edge cases)"
  - Name each step for verifiability: "Map → Assess → Teach → Connect"

### Knowledge Files Best Practices

- **Prefer Markdown** for text content (34-38% fewer tokens than JSON)
- **Use JSON** only when data is inherently tabular or needs precise key-value querying
- **Max 20 files**, each ≤512MB / ≤2M tokens — practically keep under 50,000 words per file for reliable retrieval
- **Simple formatting** — single column, clear headings, no complex layouts. The model retrieves by chunk, not full file — headings are critical for navigation
- **Title + date at top** of each file for citation
- **One topic per file** — better retrieval accuracy than multi-topic files
- **Don't duplicate** content between prompt and knowledge files — each has its own job
- **Choose the right structure** for each file's content:

| Structure | Use When |
|-----------|----------|
| FAQ | Common questions with approved answers |
| Reference Guide | Comprehensive material organized by topic/sections |
| SOP / Checklist | Step-by-step procedures with clear decision points |
| Glossary / Lookup Table | Terminology, codes, categories, key-value definitions |
| Style Guide | Tone rules, word lists, response templates |

- **Loading instructions in prompt** — differentiate between:
  - **"Read `file.md` fully before starting"** (bold) — for workflow methodology guides loaded upfront
  - **"Consult `file.md` when..."** — for reference files used on-demand during specific steps
- **RAG retrieval is chunk-based** — "read fully" is aspirational, not guaranteed. To improve accuracy:
  - Reference specific named sections: "Use the topic mapping (Section 1)" instead of "consult the file"
  - Embed enough prescriptive detail inline that behavior is correct even with partial retrieval
  - Use NEVER rules as fallback: "NEVER respond from training data alone when a guide covers the topic"
- **NEVER expose citation markers** — Custom GPTs leak `file_search` citations (e.g., `【N:M†filename†L#-L#】`) into responses by default. Every prompt that consumes Knowledge files MUST include an explicit NEVER rule forbidding citation markers in user-facing output.

### Actions (API Integrations)

- Schema format: **OpenAPI 3.1.0** (YAML or JSON)
- Description limits: endpoints ≤300 chars, parameters ≤700 chars
- Auth options: None, API Key, OAuth 2.0
- In prompt: explicitly state when and how to use each action
- Always include error handling instructions
- Never show raw API errors to users — always define a user-friendly fallback message
- Never retry more than once in the same turn
- Secrets never hardcoded in schema — use the GPT Editor authentication panel

### Conversation Starters

- **Exactly 4 starters** — ChatGPT only displays the first 4
- **Under 80 characters each** — write in the GPT's target audience language
- **Formula**: 1 educational ("What can you do?") + 1 core workflow + 1 secondary workflow + 1 advanced/specific
- Use trailing ellipsis for open-ended prompts ("Analyze this data for...")

### Quality Checklists

**Pre-Build** (verify before generating the prompt):
- [ ] Clear purpose and audience confirmed
- [ ] Capabilities, guardrails, and knowledge file plan agreed
- [ ] All knowledge files created and approved by the user
- [ ] Action requirements identified (if any)

**Post-Build** (verify after generating the prompt):
- [ ] All 7 sections present with Markdown headings
- [ ] Character count ≤8000
- [ ] Every knowledge file referenced by exact filename with trigger condition
- [ ] Every action referenced by operationId (if applicable)
- [ ] At least 2 trigger/instruction workflows defined
- [ ] NEVER rules present for critical prohibitions
- [ ] Security block covers: anti-leak, anti-injection, off-scope, uncertainty
- [ ] NEVER rule forbidding file_search citation markers (`【N:M†...】`) in user-facing output
- [ ] Tone and persona consistent across all sections

**Cross-Reference** (verify all artifacts are aligned):
- [ ] Every knowledge file listed in config.md matches actual files
- [ ] Prompt references match knowledge file names exactly
- [ ] Action operationIds in prompt match action schemas
- [ ] No content duplicated between prompt and knowledge files

### Output Structure

```
openai-gpts/{gpt-name}/
├── README.md              # Spec + config guide + changelog
├── prompt.md              # System prompt (≤8000 chars)
├── knowledge/             # Files to upload
│   └── *.md / *.json
├── actions/               # OpenAPI schemas
│   └── *.yaml
└── config.md              # Capabilities, starters, settings
```

---

## Google Gemini Gem Guide

Gems are custom AI personas within Google Gemini (requires Gemini Advanced, Business, or Enterprise). Simpler than GPTs — no actions, no capability toggles — focused on **instructions + knowledge files**.

### Platform Overview

| Feature | Details |
|---------|---------|
| Instructions | Single text field, ~10,000 chars recommended max |
| Knowledge files | Max **10 files** — PDF, TXT, CSV, MD, Google Docs, Google Sheets |
| Capabilities | All Gemini native capabilities available by default (no toggles) |
| Actions/APIs | **Not supported** — Gems cannot call external APIs |
| Conversation starters | **Not a native feature** — use test prompts in config instead |
| Sharing | Private, anyone with link, or Google Workspace org |
| Marketplace | No public store — sharing is link-based |

### Key Differences from Custom GPTs

| Aspect | GPTs | Gems |
|--------|------|------|
| Instructions limit | ~8,000 chars | ~10,000 chars |
| Knowledge files | Max 20 | Max 10 |
| API integrations | OpenAPI actions | Not available |
| Capability toggles | Explicit on/off | Always on (native) |
| Conversation starters | 4 slots in UI | Not available |
| Search grounding | Web browsing toggle | Google Search built-in |
| Image generation | DALL-E toggle | Imagen built-in |
| Sharing model | GPT Store + links | Links + Workspace |

### Instructions Structure (~10,000 characters)

Organize the instructions in this order. Simpler budget since there's no actions or starters:

| Section | ~% Budget | Purpose |
|---------|-----------|---------|
| Core Identity | 15% | Role, persona, purpose |
| Workflows | 35% | Trigger/step pairs — the main behavioral logic |
| Knowledge & Sources | 15% | When to use files vs Search vs training data |
| Rules | 20% | NEVER constraints, scope limits, guardrails |
| Output Style | 10% | Tone, format, length, language |
| Security | 5% | Anti-leak, anti-injection |

### Prompt Engineering Rules

- **Same fundamentals as GPTs apply**: trigger/instruction pairs, NEVER constraints, prescriptive steps
- **Single field, no sections UI** — use Markdown headings to create structure within the instructions field
- **Google Search grounding is automatic** — instruct the Gem WHEN to search vs use knowledge files vs use training data. This three-way priority is unique to Gems
- **Source priority pattern**: always define precedence explicitly:
  - GOOD: `"For {domain} topics: knowledge files > Google Search > training data"`
  - GOOD: `"For current events: Google Search > knowledge files > training data"`
- **No capability toggles** — if you DON'T want the Gem to generate images or run code, you must explicitly prohibit it in instructions: `"NEVER generate images"` or `"Do not execute code"`
- **Gemini handles multimodal natively** — Gems can analyze images, PDFs, and files the user uploads in-conversation without special instructions
- **Shorter is better** — Gemini models respond well to concise, direct instructions. Avoid over-explanation
- **Few-shot examples are effective** — include 1-2 example interactions directly in instructions when the desired output format is non-obvious
- **Language instruction matters** — if the Gem should respond in a specific language, state it explicitly: `"Always respond in Brazilian Portuguese"`

### Knowledge Files Best Practices

- **Max 10 files** — plan carefully, combine related content if needed
- **Prefer Markdown and plain text** — best retrieval performance
- **PDF works well** for existing documents you don't want to reformat
- **CSV/Sheets** for structured data the Gem needs to look up
- **Google Docs/Sheets** can be uploaded directly — useful for living documents
- **One topic per file** — same retrieval principle as GPTs
- **Clear headings are critical** — Gemini retrieves by chunks, headings improve accuracy
- **No explicit loading strategy** — unlike GPTs, you can't control "read before" vs "on-demand". Instead, use instruction-level guidance: `"When asked about {topic}, always check the uploaded {filename} first"`
- **File naming matters** — use descriptive names the model can match to instructions (e.g., `product-catalog.csv`, not `data1.csv`)

### Configuration

Unlike GPTs, Gems have minimal configuration:

- **Name**: Short, memorable — appears in the Gem selector
- **Description**: One line — helps users understand the Gem's purpose
- **Icon**: Emoji or Gemini-generated image
- **Sharing**: Private (default), link-sharing, or Workspace-wide

### Quality Checklists

**Pre-Build** (verify before writing instructions):
- [ ] Clear purpose and audience confirmed
- [ ] Knowledge file plan agreed (max 10 files)
- [ ] Capabilities to explicitly enable/disable identified
- [ ] Source priority defined (knowledge files vs Search vs training data)

**Post-Build** (verify after writing instructions):
- [ ] Core Identity clearly defines role and purpose
- [ ] At least 1 workflow with prescriptive steps
- [ ] NEVER rules for critical constraints
- [ ] Source priority explicitly stated in instructions
- [ ] Capabilities the Gem should NOT use are explicitly prohibited
- [ ] Anti-leak instruction present
- [ ] Output style (tone, format, language) specified
- [ ] Under ~10,000 characters

**Cross-Reference** (verify all artifacts are aligned):
- [ ] Every knowledge file referenced in instructions by filename
- [ ] Knowledge files in config.md match actual files in `knowledge/`
- [ ] Test prompts cover core workflow, knowledge retrieval, and edge cases
- [ ] No content duplicated between instructions and knowledge files

### Output Structure

```
gemini-gems/{gem-name}/
├── README.md              # Spec + config guide + changelog
├── instructions.md        # Gem instructions (≤10,000 chars)
├── knowledge/             # Files to upload (max 10)
│   └── *.md / *.pdf / *.csv
└── config.md              # Name, description, sharing, capabilities usage
```

---

## File Organization

- **Folder names**: `kebab-case` (e.g., `my-code-reviewer`, `writing-assistant`)
- **One folder per agent** under its type directory
- **README.md in every agent folder** — purpose, files, integration, changelog
- **`_template/` folders are read-only reference** — copy, never modify
- **New agent types** get their own top-level folder (e.g., `cursor-rules/`)

## Iteration & Versioning

- When improving an existing agent, update the artifacts in place
- Add a changelog entry in README.md: `- YYYY-MM-DD: Description of changes`
- Git handles full version history — no need for manual versioning

## Memory

- Check `memory/MEMORY.md` at the start of each new agent creation for relevant patterns
- After completing an agent, save new learnings: domain patterns, feature combinations that work well, pitfalls discovered
- Memory path: `memory/MEMORY.md` (index) + topic files as needed (this is the same memory system the CoS uses)
