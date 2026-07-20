import pytest

from app.modules.contacts.service import InvalidPhone, normalize_phone


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("091-98765-43210", "+919876543210"),
        ("0198765 43210", "+919876543210"),
        ("+919876543210", "+919876543210"),
    ],
)
def test_normalizes_valid_formats(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["12345", "5876543210", "98765432", "not-a-phone", ""])
def test_rejects_invalid_numbers(raw):
    with pytest.raises(InvalidPhone):
        normalize_phone(raw)
