"""Tool sandbox — validates tool calls before execution.

Prevents path traversal, blocks dangerous hosts, and restricts
access to sensitive tools.
"""
import os
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()

DANGEROUS_TOOLS = {"write_file", "delete_file", "run_javascript", "fill_form"}

BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "169.254.169.254",
}

BLOCKED_SCHEMES = {"file", "ftp", "data", "javascript"}


class ToolSandboxError(Exception):
    pass


def validate_tool_call(tool_name: str, args: dict, user_id: str) -> bool:
    """Validate a tool call before execution.

    Raises ToolSandboxError if the call is blocked.
    Returns True if safe.
    """
    if tool_name in DANGEROUS_TOOLS:
        # Path traversal check
        if "path" in args:
            normalized = os.path.normpath(args["path"])
            if ".." in normalized or normalized.startswith("/"):
                logger.warning("path_traversal_blocked", tool=tool_name, path=args["path"])
                raise ToolSandboxError(f"Path traversal blocked: {args['path']}")

    # URL blocklist check (for any tool with a URL arg)
    if "url" in args:
        try:
            parsed = urlparse(args["url"])
            if parsed.scheme in BLOCKED_SCHEMES:
                raise ToolSandboxError(f"Blocked URL scheme: {parsed.scheme}")
            if parsed.hostname and parsed.hostname in BLOCKED_HOSTS:
                raise ToolSandboxError(f"Blocked host: {parsed.hostname}")
        except ValueError:
            raise ToolSandboxError(f"Invalid URL: {args['url']}")

    return True
