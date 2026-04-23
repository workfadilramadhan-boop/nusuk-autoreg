from src.utils import generate_password, normalize_dob, normalize_indo_phone


def test_generate_password_meets_nusuk_rules():
    pw = generate_password(12)
    assert len(pw) >= 8
    assert any(c.isupper() for c in pw)
    assert any(c.islower() for c in pw)
    assert any(c.isdigit() for c in pw)
    assert any(c in "!@#$%^&*" for c in pw)


def test_normalize_indo_phone_strips_prefix():
    assert normalize_indo_phone("+62 812-3456-7890") == "81234567890"
    assert normalize_indo_phone("081234567890") == "81234567890"
    assert normalize_indo_phone("6281234567890") == "81234567890"
    assert normalize_indo_phone("81234567890") == "81234567890"


def test_normalize_dob_formats():
    assert normalize_dob("1995-03-21") == ("21", "03", "1995")
    assert normalize_dob("21/03/1995") == ("21", "03", "1995")
    assert normalize_dob("21-3-1995") == ("21", "03", "1995")
