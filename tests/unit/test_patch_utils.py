from app.domain.patch_utils import iter_added_lines


def test_iter_added_lines_simple_hunk() -> None:
    patch = """@@ -1,2 +1,3 @@
 a
-b
+c
+d
"""
    got = list(iter_added_lines(patch))
    assert got == [(2, "c"), (3, "d")]


def test_iter_added_lines_new_file() -> None:
    patch = """@@ -0,0 +1,2 @@
+first
+second
"""
    got = list(iter_added_lines(patch))
    assert got == [(1, "first"), (2, "second")]


def test_iter_added_lines_empty_patch() -> None:
    assert list(iter_added_lines(None)) == []
    assert list(iter_added_lines("")) == []
