from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent


TRANSITIONS = {
    "待识别": {"待派单", "已取消"},
    "待派单": {"已派单", "已取消"},
    "已派单": {"已接单", "处理中", "已取消"},
    "已接单": {"处理中", "已取消"},
    "处理中": {"待回访", "已完成"},
    "待回访": {"已完成", "处理中"},
    "已完成": set(),
    "已取消": set(),
}


class OrderFlowAgent(BaseAgent):
    name = "order-flow-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        current = str(state.get("current_status"))
        target = str(state.get("target_status"))
        if target not in TRANSITIONS.get(current, set()):
            return AgentResult(agent=self.name, success=False, message=f"不允许从 {current} 流转到 {target}")
        return AgentResult(agent=self.name, success=True, output={"previous_status": current, "status": target})
