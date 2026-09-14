# Git Conventions

## Language

Branch names and commit messages must be written in **US English**.

## Commit format

```
<type>(<scope>): <imperative description>
```

The description must be clear, concise and in the imperative mood (e.g. "add CPF validation").

## Allowed types

| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Refactor with no behavior change |
| `test` | Adding or fixing tests |
| `docs` | Documentation |
| `style` | Formatting, no logic change |
| `perf` | Performance improvement |
| `build` | Build system or external dependencies |
| `ci` | CI/CD configuration |
| `chore` | Maintenance, build tasks, etc. |
| `revert` | Reverts a previous commit |

## Good examples

```
feat(boleto): add support for Sicredi boleto
fix(contract): correct installment calculation with discount
refactor(entry): extract validation logic into a utility class
test(boleto): add tests for barcode generation
chore(deps): bump OkHttp to 4.12
```

## Never mention `.claude/`, `CLAUDE.md` or `docs/` in commit or PR text

`.claude/`, `CLAUDE.md` and `docs/` are git-ignored in this project. Whoever reads the commit or
the PR on Bitbucket **does not have those files** — the reference becomes a broken link and the
rationale has nothing to stand on.

This applies to commit messages (subject and body), PR descriptions and PR comments. Do not write
`.claude/rules/bank-integrations.md`, `.claude/rules/git.md`, `CLAUDE.md`, nor any path to a
document under `docs/` or to an agent/report under `.claude/`.

Write the content of the rule, not its path:

```
# wrong
feat(boleto): add support for Sicredi boleto

Follows the standard in .claude/rules/bank-integrations.md and the design
documented in docs/sicredi-integration.md.

# right
feat(boleto): add support for Sicredi boleto

Uses the LottustechCore CNAB formatters, no manual field formatting.
Sicredi layout isolated in apicobranca/sicredi/cnab/.
```

References to versioned files are welcome and should continue (Java class, Flyway script under
`src/main/resources/scripts/`, `pom.xml`, `application.yml`).

**Exception:** when the diff itself is about those names — for instance a commit that adds
`CLAUDE.md`, `.claude` or `docs/` to `.gitignore` — they show up because they **are** the subject
of the change, not as a reference to a rule. In that case it is legitimate and necessary for the
commit to make sense.

## Commit grouping

- Each commit must have **one cohesive responsibility**
- Do not mix different types in the same commit (e.g. `feat` + `fix`)
- Prefer grouping by type and scope

## Branches

Use kebab-case in English with a type prefix:

```
feat/ailos-boleto-integration
fix/late-payment-interest-calculation
refactor/service-to-controller-migration
chore/spring-dependency-updates
```

## Main branches

- `main` — production
- `staging` — homologation (current working branch)
- Create branches off `staging` for features/fixes

## Files that must never be committed

- **`docs/`** — local documentation folder, ignored by `.gitignore` and blocked by the pre-commit hook. Never include files from `docs/` in commits, even if they show up as untracked.
- **`CLAUDE.md` and `.claude/`** — local agent configuration, also ignored by `.gitignore`. Do not add them to a commit even if they show up as untracked.

Besides not being committed, these three must also never be **mentioned** in commit or PR text —
see the section above.

## Pull requests

- use the Bitbucket MCP to create pull requests
- whenever a pull request is requested, assume the current branch is to be merged into the `staging` branch, unless the user specifies otherwise. If the current branch is not on the remote, push it before opening the pull request.
- the PR body does not mention `.claude/`, `CLAUDE.md` or `docs/` (see the section above) — explain the rule instead of pointing at the file that holds it
