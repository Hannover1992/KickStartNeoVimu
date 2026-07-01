"""Tests fuer cochange_coupling.py (BL-381 AK-2 / BL-342, read-only). Lead-verify aus Repo-Root."""
import cochange_coupling as cc

_LOG = """===h1
a.py
b.py
===h2
a.py
b.py
c.py
===h3
a.py
c.py
"""


def test_parse_git_log_counts_commits():
    commits = cc.parse_git_log(_LOG)
    assert len(commits) == 3
    assert commits[0] == ["a.py", "b.py"]
    assert commits[1] == ["a.py", "b.py", "c.py"]


def test_cochange_pairs_counts():
    commits = cc.parse_git_log(_LOG)
    pairs = cc.cochange_pairs(commits)
    # (a,b) in h1 + h2 = 2 ; (a,c) in h2 + h3 = 2 ; (b,c) in h2 = 1
    assert pairs[("a.py", "b.py")] == 2
    assert pairs[("a.py", "c.py")] == 2
    assert pairs[("b.py", "c.py")] == 1


def test_cap_skips_bulk_commit():
    big = [["f%d" % i for i in range(60)]]  # 60 Dateien, > cap=40
    assert cc.cochange_pairs(big, cap=40) == {}
    # unter cap zaehlt normal
    small = [["x", "y", "z"]]
    assert cc.cochange_pairs(small, cap=40)[("x", "y")] == 1


def test_single_file_commit_no_pairs():
    assert cc.cochange_pairs([["solo.py"]]) == {}


def test_file_degree():
    commits = cc.parse_git_log(_LOG)
    deg = cc.file_degree(cc.cochange_pairs(commits))
    # a.py in (a,b)=2 + (a,c)=2 = 4 ; b.py in (a,b)=2 + (b,c)=1 = 3 ; c.py in (a,c)=2 + (b,c)=1 = 3
    assert deg["a.py"] == 4
    assert deg["b.py"] == 3
    assert deg["c.py"] == 3


def test_glob_filter():
    assert cc._matches_glob(("src/a.py", "src/b.py"), "src/")
    assert not cc._matches_glob(("a.py", "b.py"), "test_")
    assert cc._matches_glob(("a.py", "test_b.py"), "test_")  # ein Treffer reicht


def test_pairs_are_sorted_tuples():
    # Reihenfolge im Commit egal -> immer sortiertes Paar
    p1 = cc.cochange_pairs([["b.py", "a.py"]])
    assert ("a.py", "b.py") in p1 and ("b.py", "a.py") not in p1
