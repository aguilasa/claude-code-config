# Claude Command: Commit

This command helps you create well-formatted commits with conventional commit messages

## Usage

To create a commit, just type:

```
/commit
```

## What This Command Does

1. Checks which files are staged with `git status`
2. If 0 files are staged, automatically adds all modified and new files with `git add`
3. Performs a `git diff` to understand what changes are being committed
4. Analyzes the diff to determine if multiple distinct logical changes are present
5. If multiple distinct changes are detected, suggests breaking the commit into multiple smaller
   commits
6. For each commit (or the single commit if not split), creates a commit message using conventional commit format

## Best Practices for Commits

- **Atomic commits**: Each commit should contain related changes that serve a single purpose
- **Split large changes**: If changes touch multiple concerns, split them into separate commits
- **Conventional commit format**: Use the format `<type>(<scope>): <description>` where type is one of:
    - `build`: Updates made to the build system or external dependencies
    - `revert`: Reverts a previous commit
    - `ci`: Changes to CI configuration and scripts
    - `feat`: A new feature
    - `fix`: A bug fix
    - `docs`: Documentation changes
    - `style`: Code style changes (formatting, etc)
    - `refactor`: Code changes that neither fix bugs nor add features
    - `perf`: Performance improvements
    - `test`: Adding or fixing tests
    - `chore`: Changes to the build process, tools, etc.
**Important Notes:**
- Scope in the first parentheses is optional and represents the area of change
- **Present tense, imperative mood**: Write commit messages as commands (e.g., "add feature" not "
  added feature")
- **Concise first line**: Keep the first line under 72 characters
- **Language**: The `type` must always be in English. The `scope` and `description` should be in US English, unless the project's `CLAUDE.md` file specifies another language for commit messages

## Guidelines for Splitting Commits

When analyzing the code changes, consider splitting commits based on these criteria:

1. **Different concerns**: Changes to unrelated parts of the codebase
2. **Different types of changes**: Mixing features, fixes, refactoring, etc.
3. **File patterns**: Changes to different types of files (e.g., source code vs documentation)
4. **Logical grouping**: Changes that would be easier to understand or review separately
5. **Size**: Very large changes that would be clearer if broken down

## Examples

Good commit messages:

```
chore: improve accessibility for account screen

Enhances the accessibility for the user account screen by adding content descriptions

```

## Important Notes

- If specific files are already staged, the command will only commit those files
- If no files are staged, it will automatically stage all modified and new files
- The commit message will be constructed based on the changes detected
- Before committing, the command will review the diff to identify if multiple commits would be more
  appropriate
- If suggesting multiple commits, it will help you stage and commit the changes separately
- Always reviews the commit diff to ensure the message matches the changes
- Do NOT add Claude co-authorship footer to commits