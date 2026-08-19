"""
visualization_test.py

Unit tests for visualization_agent.
No database or LLM required — operates purely on Pandas DataFrames.
"""

import pytest
import pandas as pd
from agents import visualization_agent


@pytest.fixture
def category_numeric_df():
    return pd.DataFrame({
        "region": ["North", "South", "East", "West"],
        "revenue": [10000, 8000, 12000, 9500],
        "profit": [3000, 2000, 4000, 2800],
    })


@pytest.fixture
def two_numeric_df():
    return pd.DataFrame({
        "quantity": [10, 20, 30, 40],
        "revenue": [1000, 2000, 3000, 4000],
    })


@pytest.fixture
def single_numeric_df():
    return pd.DataFrame({"revenue": [100, 200, 300, 150, 250]})


@pytest.fixture
def datetime_df():
    return pd.DataFrame({
        "sale_date": pd.to_datetime(["2025-01", "2025-02", "2025-03", "2025-04"]),
        "revenue": [5000, 7000, 6000, 8000],
    })


class TestVisualizationAgent:
    def test_returns_dict(self, category_numeric_df):
        result = visualization_agent(category_numeric_df)
        assert isinstance(result, dict)

    def test_has_required_keys(self, category_numeric_df):
        result = visualization_agent(category_numeric_df)
        for key in ("figure", "figures", "chart_type", "chart_types"):
            assert key in result

    def test_bar_chart_for_category_numeric(self, category_numeric_df):
        result = visualization_agent(category_numeric_df)
        assert "bar" in result["chart_types"]
        assert result["figure"] is not None

    def test_line_chart_for_multi_numeric(self, category_numeric_df):
        result = visualization_agent(category_numeric_df)
        assert "line" in result["chart_types"]

    def test_histogram_for_single_numeric(self, single_numeric_df):
        result = visualization_agent(single_numeric_df)
        assert "histogram" in result["chart_types"]

    def test_box_plot_for_single_numeric(self, single_numeric_df):
        result = visualization_agent(single_numeric_df)
        assert "box" in result["chart_types"]

    def test_scatter_for_two_numerics(self, two_numeric_df):
        result = visualization_agent(two_numeric_df)
        assert "scatter" in result["chart_types"] or "line" in result["chart_types"]

    def test_time_series_for_datetime(self, datetime_df):
        result = visualization_agent(datetime_df)
        assert "time_series" in result["chart_types"]

    def test_empty_df_returns_no_figures(self):
        result = visualization_agent(pd.DataFrame())
        assert result["figures"] == []
        assert result["figure"] is None

    def test_none_returns_no_figures(self):
        result = visualization_agent(None)
        assert result["figures"] == []

    def test_figures_is_list(self, category_numeric_df):
        result = visualization_agent(category_numeric_df)
        assert isinstance(result["figures"], list)
        assert len(result["figures"]) >= 1

    def test_first_figure_is_primary(self, category_numeric_df):
        result = visualization_agent(category_numeric_df)
        assert result["figure"] is result["figures"][0]
