import pytest
from aegis_backend.routers.documents import chunk_text
from aegis_backend.indian_legal_helper import IndianLegalHelper
from aegis_backend.core.security import hash_password, verify_password

def test_chunk_text():
    text = "word " * 1000
    chunks = chunk_text(text, chunk_size=400, chunk_overlap=80)
    assert len(chunks) > 1
    # Check that chunks have expected length and some overlap
    first_chunk_words = chunks[0].split()
    assert len(first_chunk_words) <= 400
    assert first_chunk_words[-1] == "word"

def test_indian_legal_helper_convert_section():
    # IPC to BNS
    res_ipc = IndianLegalHelper.convert_section("ipc", "302")
    assert res_ipc is not None
    assert res_ipc["new_section"] == "101"
    assert res_ipc["act"] == "BNS"

    # CrPC to BNSS
    res_crpc = IndianLegalHelper.convert_section("crpc", "154")
    assert res_crpc is not None
    assert res_crpc["new_section"] == "173"
    assert res_crpc["act"] == "BNSS"

    # Evidence (IEA) to BSA
    res_iea = IndianLegalHelper.convert_section("iea", "3")
    assert res_iea is not None
    assert res_iea["new_section"] == "2"
    assert res_iea["act"] == "BSA"

    # Invalid section
    res_invalid = IndianLegalHelper.convert_section("ipc", "999")
    assert res_invalid is None

def test_indian_legal_helper_normalize_citation():
    # AIR SC
    norm_air = IndianLegalHelper.normalize_citation("AIR 1996 SC 1234")
    assert norm_air == "1996-sc-1234"

    # INSC
    norm_insc = IndianLegalHelper.normalize_citation("2024 INSC 15")
    assert norm_insc == "2024-sc-15"

    # Fallback normalization
    norm_fallback = IndianLegalHelper.normalize_citation("random citation string")
    assert norm_fallback == "random-citation-string"

def test_password_hashing():
    pw = "SuperSecurePassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("WrongPassword", hashed)
