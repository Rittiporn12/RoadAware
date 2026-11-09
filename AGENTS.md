# RoadAware: Codex leads, Claude implements

The product requirements have NOT been supplied. Do not invent the website or scaffold an application until the user supplies them.

## Roles and workflow
- Codex is the user's primary contact: clarify requirements, plan, create bounded task files, delegate implementation to Claude, independently inspect the actual diff, run applicable checks, and report evidence.
- Claude Code is the implementation worker. Use `python3 tools/ai_team.py run workflow/tasks/<task>.md` to delegate. Never launch a second worker concurrently.
- Before each meaningful stage, record a short plain-language update with `python3 tools/ai_team.py note "Codex: <stage and next action>"`. These notes appear in the live Terminal monitor. Record test commands and their outcomes too. Do not record secrets or private reasoning.
- Read the worker's final report in the run directory printed by the bridge. A successful CLI exit is not acceptance: inspect files and independently verify against the task's acceptance criteria.
- After independent verification, record acceptance with `python3 tools/ai_team.py review pass "<evidence>"`, or rejection with `python3 tools/ai_team.py review fail "<specific issues>"`. This updates the live timeline and saved status. A pass means the delegated task passed, not that the whole product is complete.
- On failure, write a specific follow-up task with the original requirements, observed failure, and relevant context. At most two correction rounds per task, then report the blocker to the user. Each run is a fresh Claude conversation.
- Claude handles code changes; Codex handles planning, task documents, verification, and review. Codex may fix the bridge or setup itself.
- Do not deploy, purchase services, change production data, or publish solely because a worker proposes it. Follow the user's authorization for those actions.

## Task contract
Every task includes: goal, current context, files/scope allowed to change, acceptance criteria, verification requested, and constraints. Workers must report changed files, checks actually run, checks not run, and remaining issues. Never treat unexecuted tests as passed.

## Monitor and configuration
- Open `Monitor AI Team.command` for live recorded stages and Claude tool activity. `Start Codex.command` launches the manager in this project.
- `.ai-team/activity.log` is the readable timeline. Each `.ai-team/runs/<id>/` contains raw streamed events, final result, and errors. These files are local and ignored by Git.
- `workflow/team.json` controls the per-run budget, timeout, and available tools. Default Claude tools allow file work, not shell commands. Codex runs tests. Add narrowly scoped shell permissions only when needed for a concrete project.
- Keep credentials and `.env` contents out of task files and logs. No permission-bypass flags.
