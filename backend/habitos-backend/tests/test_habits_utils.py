from routers.habits import _calc_status, _calc_score


def test_calc_status_over_under_ok():
    assert _calc_status(5, 3, False) == "over"
    assert _calc_status(2, 3, True) == "under"
    assert _calc_status(3, 3, True) == "ok"
    assert _calc_status(3, 3, False) == "ok"


def test_calc_score_empty_and_task_mismatch():
    assert _calc_score([], []) == 0
    assert _calc_score([], [{"id": 1, "daily_limit": 1, "low_warn": 0}]) == 0


def test_calc_score_low_warn_task():
    tasks = [{"id": 1, "daily_limit": 10.0, "low_warn": 1}]
    logs = [{"task_id": 1, "value": 5}]
    assert _calc_score(logs, tasks) == 50


def test_calc_score_high_warn_task():
    tasks = [{"id": 1, "daily_limit": 100.0, "low_warn": 0}]
    logs = [{"task_id": 1, "value": 50}]
    assert _calc_score(logs, tasks) == 100
    logs = [{"task_id": 1, "value": 150}]
    assert _calc_score(logs, tasks) == 50


def test_calc_score_multiple_tasks():
    tasks = [
        {"id": 1, "daily_limit": 10.0, "low_warn": 1},
        {"id": 2, "daily_limit": 20.0, "low_warn": 0},
    ]
    logs = [
        {"task_id": 1, "value": 10},
        {"task_id": 2, "value": 30},
    ]
    # task1 -> 100; task2 -> 50 => average 75
    assert _calc_score(logs, tasks) == 75
