import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd

logger = logging.getLogger("RiskEngine")


class RiskLevel(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"
    CAPACITY_EXCEEDED = "capacity_exceeded"


RISK_THRESHOLDS = {
    RiskLevel.NORMAL: (0, 70),
    RiskLevel.ELEVATED: (70, 85),
    RiskLevel.HIGH: (85, 95),
    RiskLevel.CRITICAL: (95, 100),
    RiskLevel.CAPACITY_EXCEEDED: (100, float("inf")),
}

RISK_RECOMMENDATIONS = {
    RiskLevel.NORMAL: ["Operations normal. Continue standard monitoring."],
    RiskLevel.ELEVATED: [
        "Consider activating demand response programs.",
        "Review peaking unit availability.",
        "Notify distribution companies of elevated demand."
    ],
    RiskLevel.HIGH: [
        "Activate peaking generation units immediately.",
        "Prepare load shedding schedule as contingency.",
        "Initiate demand response with large industrial consumers.",
        "Alert neighboring grid operators for potential support."
    ],
    RiskLevel.CRITICAL: [
        "IMMEDIATE ACTION: Activate all available peaking capacity.",
        "Alert all distribution companies.",
        "Execute demand response programs.",
        "Contact neighboring grids for emergency power import.",
        "Prepare controlled load shedding schedule."
    ],
    RiskLevel.CAPACITY_EXCEEDED: [
        "EMERGENCY: Demand exceeds available capacity.",
        "Initiate controlled load shedding immediately.",
        "Contact neighboring grids for emergency import.",
        "Reduce voltage by 5% across non-critical feeders.",
        "Activate emergency generation reserves.",
        "Notify state/national load dispatch center."
    ],
}


@dataclass
class RiskAlert:
    timestamp: datetime
    risk_level: RiskLevel
    predicted_demand: float
    available_capacity: float
    utilization_pct: float
    deficit_mw: float
    area: str
    node: str
    message: str
    recommendations: list = field(default_factory=list)


class RiskEngine:
    def __init__(self, capacity_data: dict = None):
        self.capacity_data = capacity_data or {}

    def calculate_utilization(self, predicted_mw: float, available_mw: float) -> float:
        if available_mw <= 0:
            return 100.0
        return round((predicted_mw / available_mw) * 100, 2)

    def classify_risk(self, utilization_pct: float, deficit_mw: float = 0) -> RiskLevel:
        if utilization_pct > 100 or deficit_mw > 0:
            return RiskLevel.CAPACITY_EXCEEDED
        elif utilization_pct >= 95:
            return RiskLevel.CRITICAL
        elif utilization_pct >= 85:
            return RiskLevel.HIGH
        elif utilization_pct >= 70:
            return RiskLevel.ELEVATED
        return RiskLevel.NORMAL

    def generate_alert(self, area: str, node: str, predicted_demand: float,
                       capacity: float, timestamp: datetime = None) -> RiskAlert:
        timestamp = timestamp or datetime.now()
        utilization = self.calculate_utilization(predicted_demand, capacity)
        deficit = max(0.0, predicted_demand - capacity)
        risk = self.classify_risk(utilization, deficit)
        reserve = self.calculate_reserve_margin(capacity, predicted_demand)

        if risk == RiskLevel.NORMAL:
            msg = (f"Grid operating normally. Utilization: {utilization:.1f}%. "
                   f"Reserve margin: {reserve:.1f}%.")
        elif risk == RiskLevel.ELEVATED:
            msg = (f"Elevated demand. Utilization: {utilization:.1f}%. "
                   f"Reserve margin: {reserve:.1f}%. Monitor closely.")
        elif risk == RiskLevel.HIGH:
            msg = (f"HIGH utilization alert. {utilization:.1f}% of capacity in use. "
                   f"Reserve margin: {reserve:.1f}%. Action required.")
        elif risk == RiskLevel.CRITICAL:
            msg = (f"CRITICAL: {utilization:.1f}% utilization. Reserve margin only {reserve:.1f}%. "
                   f"Immediate peaking unit activation required.")
        else:
            msg = (f"CAPACITY EXCEEDED: Demand {predicted_demand:.0f} MW exceeds "
                   f"available {capacity:.0f} MW by {deficit:.0f} MW. Emergency action required.")

        return RiskAlert(
            timestamp=timestamp,
            risk_level=risk,
            predicted_demand=predicted_demand,
            available_capacity=capacity,
            utilization_pct=utilization,
            deficit_mw=deficit,
            area=area,
            node=node,
            message=msg,
            recommendations=RISK_RECOMMENDATIONS[risk]
        )

    def analyze_system(self, predictions_df: pd.DataFrame,
                        capacity_df: pd.DataFrame = None) -> list:
        alerts = []
        if capacity_df is not None and not capacity_df.empty:
            cap_dict = capacity_df.set_index("area")["available_mw"].to_dict() if "area" in capacity_df.columns else {}
        else:
            cap_dict = {}

        default_cap = self.capacity_data.get("system", {}).get("available_mw",
                       sum(v.get("available_mw", 0) for v in self.capacity_data.values()
                           if isinstance(v, dict)) or 10000.0)

        for idx, row in predictions_df.iterrows():
            area = str(row.get("area", "system"))
            node = str(row.get("node", "system"))
            pred = float(row.get("predicted_demand", row.get("net_demand", 0)))
            cap = float(cap_dict.get(area, default_cap))
            ts = pd.Timestamp(idx) if not isinstance(idx, datetime) else idx
            alert = self.generate_alert(area, node, pred, cap, ts)
            alerts.append(alert)
        return alerts

    def get_high_risk_hours(self, alerts: list) -> list:
        high_risk = [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.CAPACITY_EXCEEDED]
        return [a for a in alerts if a.risk_level in high_risk]

    def calculate_reserve_margin(self, available: float, predicted: float) -> float:
        if predicted <= 0:
            return 100.0
        return round(((available - predicted) / predicted) * 100, 2)

    def generate_risk_summary(self, alerts: list) -> dict:
        if not alerts:
            return {"total_alerts": 0}
        counts = {}
        for level in RiskLevel:
            counts[level.value] = sum(1 for a in alerts if a.risk_level == level)
        utilizations = [a.utilization_pct for a in alerts]
        peak_idx = utilizations.index(max(utilizations))
        worst = alerts[peak_idx]
        return {
            "total_alerts": len(alerts),
            "counts_by_level": counts,
            "peak_utilization_pct": round(max(utilizations), 2),
            "average_utilization_pct": round(sum(utilizations) / len(utilizations), 2),
            "highest_risk_hour": worst.timestamp.isoformat() if hasattr(worst.timestamp, "isoformat") else str(worst.timestamp),
            "highest_risk_level": worst.risk_level.value,
            "highest_demand_mw": round(max(a.predicted_demand for a in alerts), 2),
            "total_deficit_mwh": round(sum(a.deficit_mw for a in alerts), 2),
            "hours_capacity_exceeded": counts.get("capacity_exceeded", 0),
            "hours_critical": counts.get("critical", 0),
        }
