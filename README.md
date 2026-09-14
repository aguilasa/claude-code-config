# claude-code-config

Personal artifacts for [Claude Code](https://claude.com/claude-code): commands, skills, agents, hooks, rules, and configuration.

## Structure

| Directory | What goes here |
|---|---|
| `commands/` | Slash commands (`/name`). One `.md` file per command. |
| `skills/` | Skills. One directory per skill, with `SKILL.md` plus supporting resources. |
| `agents/` | Subagents (`.md` with frontmatter `name`, `description`, `tools`, `model`). |
| `rules/` | Reusable convention files (git, code style) referenced from `CLAUDE.md`. |
| `hooks/` | Hook scripts (PreToolUse, PostToolUse, SessionStart, etc.). |
| `output-styles/` | Output styles / response personalities. |
| `settings/` | Example and backup `settings.json` files (no secrets). |
| `mcp/` | MCP server configuration (example `.mcp.json`, no tokens). |
| `plugins/` | Custom plugins and marketplaces. |
| `docs/` | Notes, references, and decisions. |

## Installation

Symlink the artifacts into `~/.claude/` to use them globally:

```bash
ln -sfn "$PWD/commands"      ~/.claude/commands
ln -sfn "$PWD/skills"        ~/.claude/skills
ln -sfn "$PWD/agents"        ~/.claude/agents
ln -sfn "$PWD/output-styles" ~/.claude/output-styles
```

Careful: if `~/.claude/commands` and friends already have content, back it up first — the symlink replaces the directory.

## Conventions

- Files named in `kebab-case.md`.
- Every command, skill, and agent starts with YAML frontmatter (`description` is required — it decides when Claude triggers the artifact).
- Write `description` as an imperative that states **when** to use it, not just what it does.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/) (see `commands/commit.md`).

## Secrets

No tokens, keys, or `settings.local.json` in this repo — see `.gitignore`. MCP configs are versioned with placeholders (`${VAR}`), never real values.

## License

MIT — see [LICENSE](LICENSE).
