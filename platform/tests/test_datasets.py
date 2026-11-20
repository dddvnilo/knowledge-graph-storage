import pytest

from ksplatform import DatasetError, ResponseDataset


def test_parses_items_and_responses():
    dataset = ResponseDataset.from_csv_bytes(b"a,b\n1,0\n1,1\n")
    assert dataset.items == ["a", "b"]
    assert dataset.responses == [[1, 0], [1, 1]]
    assert dataset.n_respondents == 2
    assert len(dataset.content_hash) == 64


def test_same_bytes_give_same_hash():
    data = b"a,b\n1,0\n"
    assert ResponseDataset.from_csv_bytes(data).content_hash == ResponseDataset.from_csv_bytes(data).content_hash


@pytest.mark.parametrize(
    "data, message",
    [
        (b"a,b\n", "at least one response row"),
        (b"a,a\n1,0\n", "unique"),
        (b"a,b\n1,2\n", "0 or 1"),
        (b"a,b\n1\n", "expected 2 values"),
        (b"a,\n1,0\n", "item id"),
    ],
)
def test_rejects_invalid_files(data, message):
    with pytest.raises(DatasetError, match=message):
        ResponseDataset.from_csv_bytes(data)
