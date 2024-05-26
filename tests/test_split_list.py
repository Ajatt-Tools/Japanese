# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.helpers.misc import split_list


def test_split_list() -> None:
    assert list(split_list([1, 2, 3], n_chunks=2)) == [[1, 2], [3]]
    assert list(split_list([1, 2, 3, 4], n_chunks=2)) == [[1, 2], [3, 4]]
    assert list(split_list([1, 2, 3, 4, 5], n_chunks=2)) == [[1, 2, 3], [4, 5]]
    assert list(split_list([1, 2, 3, 4, 5, 6, 7], n_chunks=2)) == [[1, 2, 3, 4], [5, 6, 7]]
    assert list(split_list([1, 2, 3, 4, 5, 6, 7, 8], n_chunks=3)) == [[1, 2, 3], [4, 5, 6], [7, 8]]
