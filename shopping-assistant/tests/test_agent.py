import pytest
from app.agent import (
    redeem_discount_code,
    used_discount_codes,
    valid_codes
)

@pytest.fixture(autouse=True)
def reset_state():
    """Reset the discount state before each test to guarantee isolation."""
    used_discount_codes.clear()
    valid_codes.clear()
    valid_codes.update({"WELCOME50", "SUMMER20"})

def test_missing_user_id():
    """Security Boundary: Missing Authentication Context
    Ensures that an empty user ID cannot redeem codes.
    """
    result = redeem_discount_code(user_id="", code="WELCOME50")
    assert "Error" in result
    assert "user ID is required" in result
    assert "WELCOME50" not in used_discount_codes

def test_invalid_code_tampering():
    """Security Boundary: Tampering / Input Validation
    Ensures that arbitrary or tampered codes are rejected.
    """
    result = redeem_discount_code(user_id="user123", code="HACKER99")
    assert "Error" in result
    assert "not valid" in result

def test_replay_attack_prevention():
    """Security Boundary: Transaction Replay
    Ensures that a code cannot be redeemed more than once.
    """
    # 1. Legitimate redemption
    success_result = redeem_discount_code(user_id="user123", code="WELCOME50")
    assert "Success" in success_result
    assert "WELCOME50" in used_discount_codes

    # 2. Replay attack (even by a different user)
    replay_result = redeem_discount_code(user_id="attacker99", code="WELCOME50")
    assert "Error" in replay_result
    assert "already been redeemed" in replay_result

def test_case_insensitivity_sanitization():
    """Security Boundary: Data Sanitization
    Ensures that varying casing does not bypass replay protections or fail validation.
    """
    result = redeem_discount_code(user_id="user123", code="summer20")
    assert "Success" in result
    assert "SUMMER20" in used_discount_codes

    # Verify replay with different casing still fails
    replay_result = redeem_discount_code(user_id="user456", code="SuMmEr20")
    assert "Error" in replay_result
    assert "already been redeemed" in replay_result
