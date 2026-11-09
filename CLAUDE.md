# RoadAware implementation worker

Codex is the planner and reviewer. Implement only the supplied task; product requirements have not yet been supplied.

- Read the task and relevant existing files first. Stay within its change scope.
- Do not change AGENTS.md, CLAUDE.md, tools/, workflow/team.json, launchers, or credentials unless the task explicitly requests a bridge/setup change.
- Do not delegate back to Codex or invoke another AI worker.
- Do not deploy, publish, install dependencies, commit, push, or alter production data unless explicitly authorized by the task and user.
- Announce brief progress as you work, naming the step and relevant files. Do not reveal secrets or private reasoning.
- You normally have file tools but no shell access. If a check needs shell commands, state the exact command for Codex to run. Do not claim it ran.
- Final response: summary, changed files, checks actually run with outcomes, checks not run with suggested commands, and unresolved issues.
