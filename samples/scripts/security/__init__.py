"""
Security hook scripts invoked by PreToolUse/PostToolUse hooks in
`~/.claude/settings.json`.

Modules:
    check_bash_command — PreToolUse Bash hook. Blocks writes to protected
                         paths (closes the Bash gap in the Edit/Write
                         hook) + dangerous git operations (push to main,
                         force push, reset --hard main) + inline
                         exec-hijacking env-var assignments
                         (GIT_SSH_COMMAND, NODE_OPTIONS, LD_PRELOAD, ...).
"""
