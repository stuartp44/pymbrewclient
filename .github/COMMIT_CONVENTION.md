# Commit Message Guidelines

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages. This enables automatic versioning and changelog generation.

## Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Types

- **feat**: A new feature (triggers minor version bump)
- **fix**: A bug fix (triggers patch version bump)
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (formatting, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvements (triggers patch version bump)
- **test**: Adding or updating tests
- **build**: Changes to build system or dependencies
- **ci**: Changes to CI configuration
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

## Breaking Changes

To indicate a breaking change (triggers major version bump), add `!` after the type/scope:

```
feat!: drop support for Python 3.9
```

Or include `BREAKING CHANGE:` in the footer:

```
feat: add new authentication system

BREAKING CHANGE: API tokens now required for all endpoints
```

## Examples

### Feature
```
feat(cli): add --json output format option

Adds support for JSON output format in CLI commands for better
integration with other tools.
```

### Bug Fix
```
fix(client): handle timeout errors gracefully

Previously, timeout errors would crash the application.
Now they are caught and logged properly.
```

### Breaking Change
```
feat(api)!: redesign authentication flow

BREAKING CHANGE: The authentication system has been completely
redesigned. Users now need to use API tokens instead of username/password.

Migration guide available at docs/migration.md
```

## Scope

The scope should be the name of the module affected (e.g., cli, client, rest, api).

## Subject

- Use imperative, present tense: "add" not "added" nor "adds"
- Don't capitalize first letter
- No period (.) at the end

## Benefits

Following this convention enables:
- Automatic version bumping based on commit types
- Automatic CHANGELOG generation
- Better commit history readability
- Clear communication of changes to users
