# Use Continuous Memory for the Entire hackathon

**Date:** 2026-10-10  
**Status:** proposed

## Context

We are competing at Agentic AI Hack Zürich 2026 in the Entire track and want to
rank as high as possible. The brief does not say how the leaderboard is scored,
so we assume two things count: how deeply the Entire features are used (real
checkpoints, Trails, Graph, Brain), and how convincing the project is, with
evidence behind its claims.

Decision 0002 already enables checkpoints. This repository is a good test bed:
agents generate whole worlds (decision 0001), and generation runs are long,
repeatable and measurable.

## Decision

Build the brief's idea **"Prove what Continuous Memory saves"** (#02) on this
repository, and make the work itself a showcase of the Entire features.

- **Experiment:** run the same set of world-generation and coding tasks in two
  arms, *baseline* (no Graph, no Brain) and *continuous memory* (Graph and Brain
  active). Per run, record tokens (`entire graph stats --repo .`), wall time,
  and correctness (the world's tests pass, plus a rubric check).
- **Tasks:** 4 to 6 fixed prompts of mixed type: add an API route, change the
  template, fix a seeded bug, extend an existing world. Each runs in a fresh
  session, with at least two runs per arm to show variance.
- **Handoff (brief idea #01):** one task starts in Claude Code and finishes in
  Codex. Brain carries the decisions across, with no re-briefing.
- **Review:** all changes go through Trails with the default Runners, so every
  push is evaluated and linked to a PR.
- **Deliverable:** a results page (brief idea #09), generated from checkpoints,
  with a table per task and links to the session behind every number.
- **Rule:** every commit is made from a captured session and linked to its
  checkpoint (answer *yes* to the prompt).

## Consequences

- Easier: a clear story with numbers; all four core features are used for real;
  every claim links to a session.
- Required: the experiment must be fair. Same model, same prompts, clean
  sessions, and the arms are not mixed in one session.
- Risk: results may show little or no saving on a small repository. We report
  what we measure; a negative or mixed result with honest evidence is still a
  valid outcome.
- Risk: Trails needs a feature flag, and repository import needs an org admin.
  Both can delay us (see setup).
- Deferred: building a new agent integration, and the other brief ideas.

## Alternatives considered

- **#01 handoff demo only.** Great live, but one anecdote with no measurement.
  Kept as a part of the experiment.
- **#09 checkpoint-to-demo generator only.** A tool without a claim to test.
  Kept as the report page.
- **#10 adapter for an unsupported agent.** Higher effort, and it does not use
  Graph or Brain.

## Implementation plan

1. **Setup** (see the checklist below). Finish before anything else.
2. **Task set:** write the tasks and the pass/fail checks in `docs/experiment/`.
3. **Baseline arm:** Graph and Brain disabled (do not run `init-agents`, or use
   a branch without the managed blocks). Run each task in a fresh session.
4. **Continuous memory arm:** Graph and Brain active. Run each task in a fresh
   session. Seed Brain by running the earlier tasks first in one arm only.
5. **Handoff run:** one task, Claude Code to Codex.
6. **Collect:** a script reads `entire graph stats`, session times and test
   results into one table.
7. **Report page:** generate it from the table with links to checkpoints.
8. **Demo:** 2 to 3 minutes: the setup, one live run, the table.

Acceptance criteria:

- Every result row links to a checkpoint or session.
- Both arms use identical prompts and the same model.
- At least one task is handed off between two agents without re-briefing.
- All commits are linked to checkpoints and everything is pushed and visible in
  Entire before the deadline.

## Additional setup

Current state, checked 2026-10-10: Entire CLI 0.11.4 is installed and enabled
(Claude Code, Codex, Cursor) and the `graph` plugin v0.4.0 is installed.
`.entire/graph-agent.md`, `AGENTS.md` and `CLAUDE.md` exist but are not yet
committed. 2 checkpoints are not yet on origin. `entire status` warns that one
session's tracking diverged from HEAD. `entire-graph` is not on the `PATH`
(only the managed plugin directory has it). Brain is not installed.

| # | Step | Who | Status |
| - | ---- | --- | ------ |
| 1 | Sign in to Entire with GitHub and authorize the GitHub App | each teammate | to check |
| 2 | Import the repository: an org admin installs the Entire GitHub App. If the repo stays under the personal account `schwarbf`, ask the Entire team on site whether that is supported, or transfer it to an org | admin | to do |
| 3 | Ask on site how the leaderboard is scored, and adjust this plan | anyone | to do |
| 4 | Request Trails access through the form | anyone | to do |
| 5 | Settings, General: turn on Runners, Auto build on push, Trails (needs repo admin) | admin | blocked by 2 and 4 |
| 6 | `entire runner setup -y`, then commit and push `.entire/` | anyone | to do |
| 7 | Commit `.entire/graph-agent.md`, `AGENTS.md`, `CLAUDE.md` (on the continuous-memory arm only, see below) | anyone | to do |
| 8 | Install Brain: `curl -fsSL https://raw.githubusercontent.com/entireio/entire-brain/main/scripts/get-brain.sh \| bash`, then `entire brain init-agents` | anyone | to do |
| 9 | Optional: `claude mcp add entire-brain -- entire brain mcp` and `claude mcp add --transport http entire-docs https://docs.entire.io/mcp` | anyone | to do |
| 10 | Run `entire doctor` and fix the diverged session tracking | anyone | to do |
| 11 | `git push` so the 2 pending checkpoints reach origin | anyone | to do |
| 12 | Make sure `codex` is signed in (installed at `/opt/homebrew/bin/codex`) | anyone | to check |
| 13 | Check that `pixi`, `just` and Docker work, so test runs are the same for every arm | anyone | to check |

Notes:

- The Graph instructions in `CLAUDE.md` and `AGENTS.md` make agents use the
  graph, which would change the baseline arm. Keep the baseline on a branch
  where those files are absent, and run both arms from the same base commit.
- After step 7 and step 8, restart the agents. Check that the first move of a
  session is `entire-graph search` and not a grep.
- Changes in Entire can take up to an hour to sync. Do steps 2, 4 and 11 first.

## Supersedes

None.
