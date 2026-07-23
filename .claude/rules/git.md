# Git Rules

## Purpose
Version control conventions — applies to every commit/branch/PR in this repo.

## Responsibilities
Keep history readable and `main` always deployable.

## Coding Rules
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `perf:` (`CONTRIBUTING.md#commit-convention`).
- One concern per commit and per PR — don't bundle an unrelated fix into a feature PR.
- Branch names: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`, off `main`.

## Conventions
- Squash-merge PRs into `main`.
- Never force-push a shared/reviewed branch without flagging it first.
- Never amend a commit that's already been pushed/reviewed — push a new commit instead.

## Best Practices
- Write commit messages explaining *why*, not just *what* (the diff shows what).
- Keep PRs small enough to review in one sitting; split otherwise.

## Avoid
- `--no-verify`/skipping hooks without explicit user instruction.
- `git push --force` to `main`.
- Committing generated/build artifacts, `.env` files, or secrets.

## Review Checklist
- [ ] Commit messages follow Conventional Commits.
- [ ] PR is single-concern.
- [ ] No secrets/`.env`/build artifacts in the diff.
- [ ] Branch named per convention.
