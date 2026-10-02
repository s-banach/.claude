#!/usr/bin/env python3
"""Limiting how long Claude waits for a foreground Bash call, used by `bash-rules.py`.

Claude Code moves a foreground call still running at its timeout to the background, where it keeps running and Claude is notified when it exits.
"""

FOREGROUND_TIMEOUT_MS = 5000


def limited_input(tool_input):
    """Return the Bash tool input with a timeout of at most `FOREGROUND_TIMEOUT_MS`, or None for a background call, which runs unchanged.

    A call that asks for no timeout, or a timeout that is not an integer, gets `FOREGROUND_TIMEOUT_MS`.
    """
    if tool_input.get("run_in_background"):
        return None
    requested = tool_input.get("timeout")
    timeout = min(requested, FOREGROUND_TIMEOUT_MS) if isinstance(requested, int) else FOREGROUND_TIMEOUT_MS
    return tool_input | {"timeout": timeout}
