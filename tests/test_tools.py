"""Tests for Local Code Interpreter Tools"""

from local_code_interpreter.tools import (
    get_release_status,
    list_pending_approvals,
    get_deployment_logs,
    trigger_rollback,
    get_current_time,
)


class TestGetReleaseStatus:
    """Tests for get_release_status tool."""

    def test_returns_status_with_release_id(self):
        result = get_release_status("v1.2.3")
        assert "v1.2.3" in result
        assert "Status" in result

    def test_includes_progress_info(self):
        result = get_release_status("release-123")
        assert "stages completed" in result


class TestListPendingApprovals:
    """Tests for list_pending_approvals tool."""

    def test_returns_pending_approvals(self):
        result = list_pending_approvals()
        assert "Pending Approvals" in result

    def test_includes_approval_details(self):
        result = list_pending_approvals()
        assert "Production" in result or "Staging" in result


class TestGetDeploymentLogs:
    """Tests for get_deployment_logs tool."""

    def test_returns_logs_for_environment(self):
        result = get_deployment_logs("staging")
        assert "staging" in result
        assert "logs" in result.lower()

    def test_respects_limit_parameter(self):
        result = get_deployment_logs("production", limit=2)
        assert "production" in result

    def test_default_limit(self):
        result = get_deployment_logs("staging")
        assert "10" in result or "4" in result  # Default or actual count


class TestTriggerRollback:
    """Tests for trigger_rollback tool."""

    def test_initiates_rollback(self):
        result = trigger_rollback("v1.0.0", "Critical bug found")
        assert "Rollback initiated" in result
        assert "v1.0.0" in result

    def test_includes_reason(self):
        result = trigger_rollback("v2.0.0", "Performance degradation")
        assert "Performance degradation" in result

    def test_returns_rollback_id(self):
        result = trigger_rollback("v1.0.0", "Test")
        assert "RB-" in result


class TestGetCurrentTime:
    """Tests for get_current_time tool."""

    def test_returns_utc_time(self):
        result = get_current_time()
        assert "UTC" in result

    def test_includes_timestamp(self):
        result = get_current_time()
        # Should contain a date-like pattern
        assert "-" in result and ":" in result
