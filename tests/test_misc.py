# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Sequence

import pytest

from japanese.helpers.misc import compact_seq


@pytest.mark.parametrize(
    "items, expected",
    [
        (["a", "b", "a", "c", "b"], ("a", "b", "c")),
        ([], ()),
    ],
)
def test_compact_seq_preserves_first_occurrence_order(items: list[str], expected: Sequence[str]) -> None:
    """compact_seq returns an immutable, deduplicated sequence preserving first occurrences."""
    assert compact_seq(items) == expected
