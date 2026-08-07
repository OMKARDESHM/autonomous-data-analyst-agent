import pandas as pd
from agents import visualization_agent


def test_visualization_bar_chart():
    df = pd.DataFrame({"category": ["A", "B", "A"], "value": [10, 20, 5]})
    out = visualization_agent(df)
    assert isinstance(out, dict)
    assert "figure" in out and "chart_type" in out
    assert out["chart_type"] == "bar"


def test_visualization_line_chart():
    df = pd.DataFrame({"v1": [1, 2, 3], "v2": [4, 5, 6]})
    out = visualization_agent(df)
    assert out["chart_type"] == "line"
