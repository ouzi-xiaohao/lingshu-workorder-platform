from app.agent_engine import WorkerCandidate, choose_worker, classify_intent


def test_classifies_air_conditioner_issue():
    result = classify_intent("B2 办公区空调无法制冷")
    assert result["category"] == "暖通空调"
    assert result["priority"] == "高"


def test_dispatch_prefers_matching_available_worker():
    workers = [
        WorkerCandidate("1", "甲", "综合服务", 121.47, 31.23, 0, 4, 99),
        WorkerCandidate("2", "乙", "暖通空调", 121.47, 31.23, 1, 4, 92),
    ]
    result = choose_worker("暖通空调", 121.47, 31.23, workers)
    assert result and result["worker_name"] == "乙"
