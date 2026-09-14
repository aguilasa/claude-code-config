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

## Pull requests

- use the `gh` CLI to create pull requests (`gh pr create`)
- whenever a pull request is requested, assume the current branch is to be merged into the `staging` branch, unless the user specifies otherwise. If the current branch is not on the remote, push it before opening the pull request.
