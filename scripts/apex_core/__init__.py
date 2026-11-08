"""Core library for the Apex plugin (stdlib only)."""

__version__ = "0.1.0"
SCHEMA_VERSION = 1
AUDITOR_NAME = "apex-auditor"


def is_auditor(agent_type) -> bool:
    """True when a hook fires inside the Apex auditor subagent.

    Plugin agents may be reported as ``apex-auditor`` or namespaced as
    ``apex:apex-auditor`` depending on the Claude Code version.
    """
    if not agent_type or not isinstance(agent_type, str):
        return False
    return agent_type.strip().split(":")[-1] == AUDITOR_NAME
