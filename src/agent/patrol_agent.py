from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent


class PatrolAgent(BaseAgent):
    name = "patrol-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        alerts = []
        if int(state.get("backlog_count", 0)) > 20:
            alerts.append("待处理工单积压超过阈值")
        if float(state.get("worker_utilization", 0)) > 0.85:
            alerts.append("现场人员平均负载过高")
        if int(state.get("hotspot_count", 0)) > 10:
            alerts.append("检测到高频问题区域")
        return AgentResult(agent=self.name, success=True, output={"alerts": alerts, "alert_count": len(alerts)})
