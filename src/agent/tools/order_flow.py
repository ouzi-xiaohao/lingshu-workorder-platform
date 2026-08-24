from dataclasses import dataclass


TRANSITIONS = {
    "待识别": {"待派单", "待人审", "已取消"},
    "待人审": {"待派单", "已取消"},
    "待派单": {"已派单", "待人审", "已取消"},
    "已派单": {"已接单", "处理中", "已取消"},
    "已接单": {"处理中", "已取消"},
    "处理中": {"待回访", "已完成"},
    "待回访": {"已完成", "处理中"},
    "已完成": set(),
    "已取消": set(),
}


@dataclass(frozen=True)
class TransitionResult:
    ok: bool
    previous_status: str
    status: str
    message: str = ""


def validate_transition(current_status: str, target_status: str) -> TransitionResult:
    current = str(current_status)
    target = str(target_status)
    if target not in TRANSITIONS.get(current, set()):
        return TransitionResult(
            ok=False,
            previous_status=current,
            status=current,
            message=f"不允许从 {current} 流转到 {target}",
        )
    return TransitionResult(ok=True, previous_status=current, status=target)
