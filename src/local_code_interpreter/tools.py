# Copyright (c) Microsoft. All rights reserved.

"""
Local Code Interpreter Tools

Shared tool functions for code interpreter agents.
These can be used with any agent configuration (OpenAI, Azure OpenAI, etc.)
"""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field


def get_release_status(
    release_id: Annotated[str, Field(description="The release identifier (e.g., v1.2.3 or release-123)")],
) -> str:
    """Get the current status of a release."""
    # In a real implementation, this would query your release management system
    return f"Release {release_id}: Status is 'In Progress'. 3/5 stages completed. Last updated: {datetime.now(timezone.utc).isoformat()}"


def list_pending_approvals() -> str:
    """List all pending release approvals."""
    # In a real implementation, this would query your approval system
    approvals = [
        {"release": "v2.1.0", "stage": "Production", "requester": "team-backend", "waiting_since": "2 hours"},
        {"release": "v1.9.5-hotfix", "stage": "Staging", "requester": "team-frontend", "waiting_since": "30 minutes"},
    ]
    if not approvals:
        return "No pending approvals found."
    
    result = "Pending Approvals:\n"
    for a in approvals:
        result += f"  - {a['release']} → {a['stage']} (requested by {a['requester']}, waiting {a['waiting_since']})\n"
    return result


def get_deployment_logs(
    environment: Annotated[str, Field(description="The target environment (e.g., staging, production)")],
    limit: Annotated[int, Field(description="Maximum number of log entries to retrieve")] = 10,
) -> str:
    """Get recent deployment logs for an environment."""
    # In a real implementation, this would fetch actual logs
    logs = [
        f"[{datetime.now(timezone.utc).isoformat()}] Deployment started for environment: {environment}",
        f"[{datetime.now(timezone.utc).isoformat()}] Health checks passed",
        f"[{datetime.now(timezone.utc).isoformat()}] Traffic shifted: 25%",
        f"[{datetime.now(timezone.utc).isoformat()}] Monitoring metrics within thresholds",
    ]
    return f"Recent logs for {environment} (last {min(limit, len(logs))} entries):\n" + "\n".join(logs[:limit])


def trigger_rollback(
    release_id: Annotated[str, Field(description="The release identifier to rollback")],
    reason: Annotated[str, Field(description="Reason for the rollback")],
) -> str:
    """Trigger a rollback for a specific release."""
    # In a real implementation, this would initiate a rollback process
    return f"Rollback initiated for {release_id}. Reason: {reason}. Estimated time: 5 minutes. Rollback ID: RB-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def get_current_time() -> str:
    """Get the current UTC time."""
    return f"Current UTC time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
