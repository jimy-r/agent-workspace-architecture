@echo off
REM Second-opinion auditor (R7). Manual quarterly cadence — no scheduled task.
REM Reference: <workspace>/.claude/agents/audit-second-opinion.md
claude --agent audit-second-opinion --permission-mode auto -p "Run the second-opinion audit on <workspace>/ per the canonical instructions at <workspace>/.claude/agents/audit-second-opinion.md. Write the brief to Reference/Research/YYYY-MM-DD_second-opinion-audit.md (use today's date). Cap at 5 findings. Surface narrative findings, not a structured Setup Review block."
