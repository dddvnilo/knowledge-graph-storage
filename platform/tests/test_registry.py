import pytest

from ksplatform import CATEGORIES, PrerequisiteRelation, ResponseDataset, get_analysis, list_analyses, run_analysis


def test_analyses_are_discovered():
    ids = {analysis.id for analysis in list_analyses()}
    assert {"daks.iita", "kst.space", "kst.validate", "pks.blim"} <= ids


def test_every_analysis_has_a_known_category():
    assert all(analysis.category in CATEGORIES for analysis in list_analyses())


def test_list_by_category():
    ids = {analysis.id for analysis in list_analyses("data_fit")}
    assert ids == {"kst.validate", "pks.blim"}


def test_unknown_analysis():
    with pytest.raises(ValueError, match="Unknown analysis"):
        get_analysis("nope.nothing")


def test_wrong_input_kind_is_rejected_before_running():
    relation = PrerequisiteRelation(items=["a", "b"])
    with pytest.raises(ValueError, match="must be of kind 'responses'"):
        run_analysis("daks.iita", {"responses": relation})


def test_missing_input_is_rejected():
    dataset = ResponseDataset.from_csv_bytes(b"a,b\n1,0\n")
    with pytest.raises(ValueError, match="expects inputs"):
        run_analysis("kst.space", {"responses": dataset})
