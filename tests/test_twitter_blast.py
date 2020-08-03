import pytest
import mock
from hypothesis import given
import hypothesis.strategies as st
import twitter_blast


@given(st.integers(1, 6))
def test_prompt_ranking_value(monkeypatch, inp):
    monkeypatch.setattr("builtins.input", lambda x: str(inp))
    assert twitter_blast.prompt_ranking_value() == (
        twitter_blast.ranking_choices[inp - 1],
        "",
    )

