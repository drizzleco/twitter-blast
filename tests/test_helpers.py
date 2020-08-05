import pytest
from hypothesis import given
import hypothesis.strategies as st
import helpers


@given(st.lists(st.integers(), min_size=1), st.integers(1))
def test_divide_into_chunks(l, n):
    assert list(helpers.divide_into_chunks(l, n)) == list(
        l[i : i + n] for i in range(0, len(l), max(1, n))
    )
