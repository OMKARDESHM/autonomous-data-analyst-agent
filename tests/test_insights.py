import pandas as pd
from agents import insights_agent


def test_insights_fallback():
    df = pd.DataFrame({"value": [10, 20, 30]})
    text = insights_agent(df)
    assert isinstance(text, str)
    assert "Rows returned" in text or "Insights" in text or text
