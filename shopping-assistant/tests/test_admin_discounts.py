import pytest
from app.agent import (
    update_discount_status,
    UpdateDiscountStatusRequest,
    valid_codes
)

@pytest.fixture(autouse=True)
def reset_state():
    """Reset the valid_codes state before each test."""
    valid_codes.clear()
    valid_codes.update({"WELCOME50", "SUMMER20"})

def test_elevation_of_privilege_blocked():
    """Test that non-admin users cannot modify discount statuses."""
    req = UpdateDiscountStatusRequest(
        user_id="user123", # Not an admin
        code="NEWCODE100",
        active=True
    )
    result = update_discount_status(req)

    assert "Error" in result
    assert "Unauthorized" in result
    assert "NEWCODE100" not in valid_codes

def test_successful_activation_case_insensitive():
    """Test that an admin can activate a code, and it is converted to uppercase."""
    req = UpdateDiscountStatusRequest(
        user_id="admin999", # Admin user
        code="fall30",    # Lowercase input
        active=True
    )
    result = update_discount_status(req)

    assert "Success" in result
    assert "activated" in result
    assert "FALL30" in valid_codes
    assert "fall30" not in valid_codes

def test_successful_deactivation():
    """Test that an admin can deactivate an existing code."""
    req = UpdateDiscountStatusRequest(
        user_id="admin999",
        code="summer20", # Also tests case-insensitivity during deactivation
        active=False
    )
    result = update_discount_status(req)

    assert "Success" in result
    assert "deactivated" in result
    assert "SUMMER20" not in valid_codes
