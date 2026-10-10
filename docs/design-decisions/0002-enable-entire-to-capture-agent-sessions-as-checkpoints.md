# Enable Entire to capture agent sessions as checkpoints

**Date:** 2026-10-10  
**Status:** proposed

## Context

Most of this repository is written by coding agents (Claude Code, Codex): the
Template Generator produces whole worlds, and the base template is built the
same way (see decision 0001). A commit shows what changed, but not the prompts,
reasoning and tool calls behind it. That context is lost once the session ends.

We want every agent-written commit to link back to the session that produced
it, so a change can be reviewed and understood later.

## Decision

Use [Entire](https://entire.io) to record agent sessions as checkpoints linked
to commits.

- **Agents covered:** Codex and Claude Code. Entire also generated hook files
  for Cursor (`.cursor/hooks.json`); these are committed with the rest, but
  Cursor is not a supported workflow.
- **Checkpoint storage:** `git-refs` (the default), so checkpoints travel with
  `git push` and no extra service is needed to store them.
- **Telemetry:** off (`--telemetry=false`).
- **Hooks:** `--absolute-git-hook-path`, so git hooks work regardless of the
  `PATH` in the shell or GUI that runs git.
- **Committed vs. local:**

  | Path | Committed | Why |
  | --- | --- | --- |
  | `.entire/settings.json`, `.entire/.gitignore` | yes | Shared project config. |
  | `.claude/settings.json`, `.codex/hooks.json`, `.cursor/hooks.json` | yes | Agent hooks that call `entire hooks ...`. Each hook exits quietly when `entire` is not installed, so contributors without it are not blocked. |
  | `.entire/logs/`, `metadata/`, `tmp/`, `settings.local.json` | no | Already ignored by `.entire/.gitignore`; local state. |

- **Per-person setup:** each contributor installs Entire and runs the setup in
  their own clone (see the implementation plan). Hooks are shared; the login
  and the git hook installation are not.
- **Server side:** the repository owner connects the repository through the
  Entire GitHub App. Without it, checkpoints are still pushed but sessions do
  not appear in Entire.

## Consequences

- Easier: reviewing agent-written commits with their full session context;
  explaining why a generated world or template looks the way it does.
- Required: every contributor runs the local setup once per clone; sessions
  started before setup are not captured, so start fresh sessions afterwards.
- Required: answer *yes* to the "link the commit to session context" prompt,
  or the commit has no checkpoint.
- Risk: session transcripts can contain secrets or private data, and
  checkpoints are pushed to the remote. Keep secrets out of prompts and review
  what Entire's redaction covers before making the repository public.
- Deferred: enforcing checkpoints in CI, and any non-`git-refs` storage.

## Alternatives considered

- **Do nothing; rely on commit messages and PR descriptions.** Cheap, but the
  reasoning and failed attempts are lost, which is the context we most want.
- **Commit session transcripts into the repository.** Pollutes history and
  diffs, and is hard to redact.
- **Use each agent's own local history.** Per machine and per tool, so it is
  not shared and does not link to commits.

## Implementation plan

1. **Install and sign in** (once per machine):

   ```sh
   curl -fsSL https://entire.io/install.sh | bash
   entire login
   ```

2. **Enable in the clone** (already run once by the first contributor):

   ```sh
   entire enable --agent codex --telemetry=false --absolute-git-hook-path
   entire agent add claude-code
   entire agent list
   entire status
   ```

3. **Commit the shared config** (`.entire/settings.json`, `.entire/.gitignore`,
   `.claude/settings.json`, `.codex/hooks.json`, `.cursor/hooks.json`) in one
   change, after reviewing each file for local-only content.
4. **Verify a checkpoint:** start fresh Codex and Claude Code sessions, make a
   small change, commit it (answer *yes* to linking), then:

   ```sh
   entire checkpoint list
   entire checkpoint explain HEAD
   ```

5. **Push and connect:** push the commit; the repository owner installs the
   Entire GitHub App for this repository.
6. **Document it:** add a short "Contributing with agents" note to the README
   pointing at this decision.

Acceptance criteria:

- `entire status` reports enabled with `git-refs` storage and telemetry off.
- A commit made from a fresh Claude Code session and one from a fresh Codex
  session each show a checkpoint in `entire checkpoint list`.
- After the push, both sessions appear in Entire for the connected repository.
- A clone without `entire` installed can still run Claude Code and Codex
  without hook errors.

## Supersedes

None.
