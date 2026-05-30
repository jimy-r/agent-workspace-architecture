# Task coordination layer

A handful of markdown files that let the user and Claude track work across sessions. The layer is built around a single state machine:

```
user note  →  Claude asks clarifying Q  →  user answers  →  Claude actions task  →  done
```

## Files

| File                  | Owner   | Purpose                                                                 |
|-----------------------|---------|-------------------------------------------------------------------------|
| `To Do Notes.md`      | user    | Master task list. Claude reads it, asks questions, marks complete.      |
| `To Do Questions.md`  | Claude  | Q&A tracker. Claude posts questions; user answers inline.               |
| `todo.md`             | Claude  | Current implementation plan with checkable items.                       |
| `lessons.md`          | Claude  | Self-improvement loop. Rules to avoid repeated mistakes.                |

## Workflow

1. The user drops a raw note in `To Do Notes.md`.
2. A scheduled agent (the "heartbeat") reads the list on a cadence; every 2 hours is a reasonable starting point.
3. For each task that lacks context, the heartbeat posts a question in `To Do Questions.md`.
4. The user answers inline the next time they open the file.
5. On the next heartbeat cycle, the agent picks up the answer and actions the task.

## Why this shape

- **Async by default.** The user doesn't have to sit in a session. The heartbeat drives forward progress.
- **Auditable.** Every decision has a question+answer pair that future sessions can read.
- **Low-friction.** Adding a task is one line of markdown. No project-management tool required.

## See also

- [`To-Do-Notes.example.md`](To-Do-Notes.example.md): sample master list with active, completed, and archived sections.
