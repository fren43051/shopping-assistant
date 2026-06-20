import pytest
from pydantic import ValidationError
from app.agent import award_loyalty_points, AwardLoyaltyPointsRequest, loyalty_accounts, processed_transactions

@pytest.fixture(autouse=True)
def reset_state():
    """Clear state before each test to ensure isolation."""
    loyalty_accounts.clear()
    processed_transactions.clear()

def test_successful_award():
    """Test that valid purchase correctly awards points."""
    req = AwardLoyaltyPointsRequest(
        user_id="user123",
        purchase_amount=150.0,
        transaction_id="tx-001"
    )
    result = award_loyalty_points(req)

    assert "Success" in result
    assert "150 points" in result
    assert loyalty_accounts["user123"] == 150
    assert "tx-001" in processed_transactions

def test_negative_purchase_amount():
    """Test that schema validation fails for negative purchase amounts."""
    with pytest.raises(ValidationError) as exc_info:
        AwardLoyaltyPointsRequest(
            user_id="user123",
            purchase_amount=-50.0,
            transaction_id="tx-002"
        )
    assert "Input should be greater than 0" in str(exc_info.value)

def test_replay_attack():
    """Test that using the same transaction ID multiple times is blocked."""
    req1 = AwardLoyaltyPointsRequest(
        user_id="user123",
        purchase_amount=100.0,
        transaction_id="tx-003"
    )

    # First call succeeds
    result1 = award_loyalty_points(req1)
    assert "Success" in result1
    assert loyalty_accounts["user123"] == 100

    # Second call with identical transaction_id fails
    result2 = award_loyalty_points(req1)
    assert "Error" in result2
    assert "already been processed" in result2

    # Points should remain unchanged
    assert loyalty_accounts["user123"] == 100

def test_missing_user_id():
    """Test that schema validation fails if user_id is empty or missing."""
    with pytest.raises(ValidationError):
        AwardLoyaltyPointsRequest(
            user_id="",
            purchase_amount=50.0,
            transaction_id="tx-004"
        )
