"""
Unit tests — Domain Models.

Tests that Pydantic domain models validate correctly, reject invalid data,
and have appropriate defaults. No DB or external dependencies required.
"""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.models.domain.action import Action, ActionRiskLevel, ActionStatus, ActionType
from backend.models.domain.anomaly import Anomaly, AnomalySeverity, AnomalyStatus, AnomalyType
from backend.models.domain.incident import Incident, IncidentSeverity, IncidentStatus
from backend.models.domain.outcome import ActionResult, Outcome, RecoveryStatus

# =============================================================================
# Incident Tests
# =============================================================================


class TestIncidentModel:
    def test_valid_incident_creates_successfully(self):
        inc = Incident(title="DB latency spike", severity=IncidentSeverity.HIGH)
        assert inc.title == "DB latency spike"
        assert inc.severity == IncidentSeverity.HIGH
        assert inc.status == IncidentStatus.DETECTED
        assert isinstance(inc.id, uuid.UUID)
        assert isinstance(inc.detected_at, datetime)

    def test_incident_id_is_auto_generated(self):
        inc1 = Incident(title="A", severity=IncidentSeverity.LOW)
        inc2 = Incident(title="B", severity=IncidentSeverity.LOW)
        assert inc1.id != inc2.id

    def test_incident_affected_services_defaults_to_empty(self):
        inc = Incident(title="Test", severity=IncidentSeverity.MEDIUM)
        assert inc.affected_services == []

    def test_incident_accepts_affected_services(self):
        inc = Incident(
            title="Cascade",
            severity=IncidentSeverity.CRITICAL,
            affected_services=["api", "worker", "db"],
        )
        assert "api" in inc.affected_services

    def test_incident_empty_title_fails(self):
        with pytest.raises(ValidationError):
            Incident(title="", severity=IncidentSeverity.LOW)

    def test_incident_title_too_long_fails(self):
        with pytest.raises(ValidationError):
            Incident(title="x" * 256, severity=IncidentSeverity.LOW)

    def test_incident_invalid_severity_fails(self):
        with pytest.raises(ValidationError):
            Incident(title="Test", severity="super_critical")

    def test_incident_resolved_at_is_none_by_default(self):
        inc = Incident(title="Test", severity=IncidentSeverity.LOW)
        assert inc.resolved_at is None

    def test_incident_status_enum_values(self):
        statuses = [s.value for s in IncidentStatus]
        assert "detected" in statuses
        assert "resolved" in statuses
        assert "escalated" in statuses


# =============================================================================
# Anomaly Tests
# =============================================================================


class TestAnomalyModel:
    def test_valid_anomaly_creates_successfully(self):
        a = Anomaly(
            anomaly_type=AnomalyType.METRIC,
            severity=AnomalySeverity.HIGH,
            service_name="worker",
        )
        assert a.service_name == "worker"
        assert a.status == AnomalyStatus.OPEN
        assert a.confidence == 1.0

    def test_anomaly_confidence_clamped_below_zero_fails(self):
        with pytest.raises(ValidationError):
            Anomaly(
                anomaly_type=AnomalyType.METRIC,
                severity=AnomalySeverity.LOW,
                service_name="svc",
                confidence=-0.1,
            )

    def test_anomaly_confidence_clamped_above_one_fails(self):
        with pytest.raises(ValidationError):
            Anomaly(
                anomaly_type=AnomalyType.METRIC,
                severity=AnomalySeverity.LOW,
                service_name="svc",
                confidence=1.1,
            )

    def test_anomaly_valid_confidence_boundary_zero(self):
        a = Anomaly(
            anomaly_type=AnomalyType.LOG_PATTERN,
            severity=AnomalySeverity.MEDIUM,
            service_name="api",
            confidence=0.0,
        )
        assert a.confidence == 0.0

    def test_anomaly_valid_confidence_boundary_one(self):
        a = Anomaly(
            anomaly_type=AnomalyType.TRACE,
            severity=AnomalySeverity.HIGH,
            service_name="api",
            confidence=1.0,
        )
        assert a.confidence == 1.0

    def test_anomaly_empty_service_name_fails(self):
        with pytest.raises(ValidationError):
            Anomaly(
                anomaly_type=AnomalyType.METRIC,
                severity=AnomalySeverity.LOW,
                service_name="",
            )

    def test_anomaly_incident_id_defaults_to_none(self):
        a = Anomaly(
            anomaly_type=AnomalyType.EVENT,
            severity=AnomalySeverity.LOW,
            service_name="gateway",
        )
        assert a.incident_id is None


# =============================================================================
# Action Tests
# =============================================================================


class TestActionModel:
    def test_valid_action_creates_successfully(self):
        incident_id = uuid.uuid4()
        action = Action(
            incident_id=incident_id,
            action_type=ActionType.RESTART_SERVICE,
            risk_level=ActionRiskLevel.LOW,
            target_service="worker",
        )
        assert action.incident_id == incident_id
        assert action.status == ActionStatus.PROPOSED
        assert action.parameters == {}

    def test_action_empty_target_service_fails(self):
        with pytest.raises(ValidationError):
            Action(
                incident_id=uuid.uuid4(),
                action_type=ActionType.RESTART_SERVICE,
                risk_level=ActionRiskLevel.LOW,
                target_service="",
            )

    def test_action_parameters_accepts_mixed_types(self):
        action = Action(
            incident_id=uuid.uuid4(),
            action_type=ActionType.SCALE_SERVICE,
            risk_level=ActionRiskLevel.MEDIUM,
            target_service="api",
            parameters={"replicas": 3, "wait": True, "strategy": "rolling"},
        )
        assert action.parameters["replicas"] == 3
        assert action.parameters["wait"] is True

    def test_action_executed_at_is_none_by_default(self):
        action = Action(
            incident_id=uuid.uuid4(),
            action_type=ActionType.NOTIFY_OPERATOR,
            risk_level=ActionRiskLevel.LOW,
            target_service="ops-team",
        )
        assert action.executed_at is None

    def test_action_type_enum_includes_no_action(self):
        # no_action is an explicit decision type, not a placeholder
        assert ActionType.NO_ACTION.value == "no_action"


# =============================================================================
# Outcome Tests
# =============================================================================


class TestOutcomeModel:
    def test_valid_outcome_creates_successfully(self):
        outcome = Outcome(
            action_id=uuid.uuid4(),
            incident_id=uuid.uuid4(),
            action_result=ActionResult.SUCCESS,
        )
        assert outcome.recovery_status == RecoveryStatus.VERIFICATION_PENDING
        assert outcome.execution_duration_seconds is None

    def test_outcome_negative_duration_fails(self):
        with pytest.raises(ValidationError):
            Outcome(
                action_id=uuid.uuid4(),
                incident_id=uuid.uuid4(),
                action_result=ActionResult.SUCCESS,
                execution_duration_seconds=-1.0,
            )

    def test_outcome_recovery_status_can_be_set(self):
        outcome = Outcome(
            action_id=uuid.uuid4(),
            incident_id=uuid.uuid4(),
            action_result=ActionResult.SUCCESS,
            recovery_status=RecoveryStatus.RECOVERED,
        )
        assert outcome.recovery_status == RecoveryStatus.RECOVERED

    def test_outcome_action_and_recovery_status_are_independent(self):
        """Action can succeed while system does not recover — these are separate concerns."""
        outcome = Outcome(
            action_id=uuid.uuid4(),
            incident_id=uuid.uuid4(),
            action_result=ActionResult.SUCCESS,
            recovery_status=RecoveryStatus.NOT_RECOVERED,
        )
        assert outcome.action_result == ActionResult.SUCCESS
        assert outcome.recovery_status == RecoveryStatus.NOT_RECOVERED
