# nantas/herdr task tracking

These conventions apply only to this custom fork. GitHub Issues in
[nantas/herdr](https://github.com/nantas/herdr/issues) track personal features,
bugs, and maintenance. Upstream contribution and release rules in AGENTS.md
still apply to operations targeting herdrdev/herdr.

## Repository targeting

Use `--repo nantas/herdr` on every `gh issue` and `gh pr` command. For `gh api`,
use an explicit `repos/nantas/herdr/...` path. Never infer the task repository
from gh's default selection; origin is the fork and upstream is herdrdev/herdr.
A bare `#N` means an issue in the fork; use `PR #N` for a pull request.
External PR discovery is not part of this personal task queue; inspect PRs when
explicitly requested.

Before claiming work, read the full issue and comments, check its assignee and
linked work, and verify the authenticated account and fork permissions. Assign
accepted work to the acting human account and record the scope in a comment.
Keep the issue open until the implementation is delivered and its acceptance
criteria are verified; local edits or a claim alone are not completion.

## Triage roles

Role names map directly to GitHub labels:

- Category: `bug`, `enhancement` (including maintenance improvements).
- State: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.

Use one category and one state for triaged tasks. Create a missing label only
when needed. `ready-for-agent` means scope and acceptance criteria are clear
and executable; assignment records who has claimed it. It does not mean done.
Preserve approved scope when resuming a task. Use the available triage skill
when invoked; do not install a repository-local replacement. The old
upstream-specific `.agents/skills/triage/` has been removed.

## Domain context

Use a single root `CONTEXT.md` for the project's domain vocabulary and model.
Read it when present before domain design or implementation. Create it only
when a task establishes concrete domain knowledge worth retaining; do not
create placeholder sections or per-domain context directories. Record durable
architectural decisions under `docs/agents/adr/` when needed, with links from CONTEXT.md.
Local plans and exploratory handoffs remain in `.local/prd/` per AGENTS.md.
