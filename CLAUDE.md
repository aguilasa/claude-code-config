# CLAUDE.md

Repository of personal Claude Code artifacts (commands, skills, agents, hooks, configs).

## Rules for this repo

- **Never commit a secret.** Tokens, API keys, `settings.local.json`, `.env` — all blocked in `.gitignore`. In MCP configs use a `${MY_VAR}` placeholder, never the value.
- **One artifact per file or directory.** Command = `commands/name.md`. Skill = `skills/name/SKILL.md`. Agent = `agents/name.md`.
- **Frontmatter is required.** Every command, skill, and agent `.md` starts with YAML containing `description`. Claude uses that `description` to decide whether to trigger — state **when** to use it, not just what it does.
- **Names in kebab-case**, no accents, no spaces.
- When adding an artifact that needs a new directory, update the structure table in `README.md`.

## Formats

Command (`commands/example.md`):
```markdown
---
description: One line stating when to use this command.
argument-hint: [file]
allowed-tools: Bash(git*), Read
---

Instructions for Claude. `$ARGUMENTS` receives whatever followed the /command.
```

Agent (`agents/example.md`):
```markdown
---
name: example
description: When Claude should delegate to this subagent.
tools: Read, Grep, Glob
model: sonnet
---

Subagent system prompt.
```

Skill (`skills/example/SKILL.md`):
```markdown
---
name: example
description: When to use it, with explicit triggers ("use when the user asks for X, Y, Z").
---

Skill body. Supporting resources in `references/`, `scripts/`, `assets/`.
```

## Commits

Conventional Commits — see `commands/commit.md`. Scope is the artifact directory:
`feat(commands): add /deploy`, `fix(skills): correct transcribe-media trigger`.
