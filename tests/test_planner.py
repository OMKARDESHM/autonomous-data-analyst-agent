from agents import planner_agent


def test_planner_detects_sql_and_viz():
    req = "Show monthly sales by region and plot a chart"
    plan = planner_agent(req)
    assert isinstance(plan, dict)
    assert "sql_required" in plan
    assert "visualization_required" in plan
    assert "steps" in plan
    assert isinstance(plan["steps"], list)


def test_planner_non_sql_request():
    req = "Explain company vacation policy to employees"
    plan = planner_agent(req)
    assert isinstance(plan, dict)
    # planner may decide no SQL is required for documentation-style requests
    assert "sql_required" in plan
