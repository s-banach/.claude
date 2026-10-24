#!/usr/bin/env python3
"""Making Claude Code kill a foreground Bash call that runs too long, used by `bash-rules.py`.

Claude Code moves a foreground call still running at its timeout to the background, unless the command starts with `sleep`: that call it kills, along with the processes it started, and reports "Command timed out".
Claude Code makes this choice from the tool input a PreToolUse hook returns, so starting every foreground command with `sleep 0; ` gets it killed at its timeout.
A background call (`run_in_background`) runs unchanged, with no time limit.
Checked against Claude Code 2.1.310, which reads the first word of the first command for this.
"""

FOREGROUND_TIMEOUT_MS = 5000

# A command that starts with `sleep` is killed at its timeout; `sleep 0` returns at once.
KILLED_AT_TIMEOUT_PREFIX = "sleep 0; "


def limited_input(tool_input):
    """Return the Bash tool input that Claude Code kills after at most `FOREGROUND_TIMEOUT_MS`, or None for a background call, which runs unchanged.

    A call that asks for no timeout, or a timeout that is not a positive integer, gets `FOREGROUND_TIMEOUT_MS`.
    """
    if tool_input.get("run_in_background"):
        return None
    requested = tool_input.get("timeout")
    timeout = min(requested, FOREGROUND_TIMEOUT_MS) if isinstance(requested, int) and requested > 0 else FOREGROUND_TIMEOUT_MS
    return tool_input | {"command": KILLED_AT_TIMEOUT_PREFIX + (tool_input.get("command") or ""), "timeout": timeout}
