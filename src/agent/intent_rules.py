KEYWORDS = {
    "暖通空调": ("空调", "制冷", "温度", "暖气", "aircon"),
    "设备故障": ("故障", "异响", "损坏", "无法启动", "泵", "pump"),
    "照明设施": ("路灯", "照明", "闪烁", "灯不亮", "light"),
    "安全隐患": ("消防", "隐患", "堵塞", "漏电", "烟雾", "smoke", "fire"),
    "环境卫生": ("垃圾", "积水", "异味", "保洁", "water"),
}


def classify_intent_rules(text: str, *, area: str = "未知区域", evidence: list[str] | None = None) -> dict[str, object]:
    merged = " ".join([text, *(evidence or [])]).lower()
    scores = {category: sum(word in merged for word in words) for category, words in KEYWORDS.items()}
    category, hits = max(scores.items(), key=lambda item: item[1])
    if hits == 0:
        category = "综合服务"
    visual_tokens = " ".join(evidence or []).lower()
    if any(token in visual_tokens for token in ("smoke", "fire", "烟雾", "消防")):
        category = "安全隐患"
    urgent = any(word in merged for word in ("消防", "漏电", "被困", "大量积水", "紧急", "smoke", "fire"))
    high = urgent or any(word in merged for word in ("故障", "无法", "堵塞"))
    priority = "紧急" if urgent else "高" if high else "中"
    return {
        "category": category,
        "priority": priority,
        "confidence": min(0.98, round(0.72 + hits * 0.09, 2)),
        "tags": [category, priority, area],
        "intent_source": "rules",
        "rationale": "keyword classifier with multimodal evidence",
    }
