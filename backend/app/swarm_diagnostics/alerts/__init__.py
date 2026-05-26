"""
Alert rules and severity classification for swarm diagnostics.
"""

from app.swarm_diagnostics.models.anomaly_signal import Severity


ALERT_RULES: list[dict] = [
    # Critical — immediate attention
    {"anomaly_type": "delegation_loop", "min_severity": Severity.CRITICAL, "channels": ["log", "endpoint"]},
    {"anomaly_type": "deadlock", "min_severity": Severity.CRITICAL, "channels": ["log", "endpoint"]},
    {"anomaly_type": "retry_storm", "min_severity": Severity.CRITICAL, "channels": ["log"]},
    # Warning — should be investigated
    {"anomaly_type": "propagation_failure", "min_severity": Severity.WARNING, "channels": ["log"]},
    {"anomaly_type": "consensus_conflict", "min_severity": Severity.WARNING, "channels": ["log"]},
    {"anomaly_type": "emergent_behavior", "min_severity": Severity.WARNING, "channels": ["log"]},
    {"anomaly_type": "agent_divergence", "min_severity": Severity.WARNING, "channels": ["log"]},
    {"anomaly_type": "sync_delay", "min_severity": Severity.WARNING, "channels": ["log"]},
    {"anomaly_type": "deadlock", "min_severity": Severity.WARNING, "channels": ["log"]},
    # Info — observability data
    {"anomaly_type": "stale_memory", "min_severity": Severity.INFO, "channels": ["log"]},
    {"anomaly_type": "event_storm", "min_severity": Severity.INFO, "channels": ["log"]},
]


def should_alert(signal_severity: Severity, rule_min_severity: Severity) -> bool:
    severity_order = {Severity.CRITICAL: 3, Severity.WARNING: 2, Severity.INFO: 1}
    return severity_order.get(signal_severity, 0) >= severity_order.get(rule_min_severity, 0)
