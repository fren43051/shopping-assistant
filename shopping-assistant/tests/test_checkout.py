import pytest
from app.agent import (
    process_cart_checkout,
    ProcessCartCheckoutRequest,
    carts,
    orders,
    used_discount_codes
)

@pytest.fixture(autouse=True)
def reset_state():
    """Reset state before each test."""
    carts.clear()
    orders.clear()
    used_discount_codes.clear()

    # Setup mock carts
    carts["cart-001"] = {"user_id": "user123", "total": 100.0, "status": "pending"}
    carts["cart-002"] = {"user_id": "user456", "total": 50.0, "status": "pending"}

def test_successful_checkout_no_discount():
    req = ProcessCartCheckoutRequest(
        user_id="user123",
        cart_id="cart-001"
    )
    result = process_cart_checkout(req)

    assert "Success" in result
    assert "100.0" in result
    assert carts["cart-001"]["status"] == "completed"
    assert "cart-001" in orders

def test_successful_checkout_with_discount():
    req = ProcessCartCheckoutRequest(
        user_id="user123",
        cart_id="cart-001",
        discount_code="WELCOME50"
    )
    result = process_cart_checkout(req)

    assert "Success" in result
    assert "Discount applied" in result
    assert "80.0" in result # 20% discount on 100.0
    assert carts["cart-001"]["status"] == "completed"

def test_idor_wrong_user():
    """Test Elevation of Privilege boundary: user checking out someone else's cart."""
    req = ProcessCartCheckoutRequest(
        user_id="user999", # Wrong user
        cart_id="cart-001"
    )
    result = process_cart_checkout(req)

    assert "Error" in result
    assert "Unauthorized" in result
    assert carts["cart-001"]["status"] == "pending"

def test_replay_attack():
    """Test Tampering boundary: completing the same cart twice."""
    req = ProcessCartCheckoutRequest(
        user_id="user123",
        cart_id="cart-001"
    )

    # First checkout
    process_cart_checkout(req)
    assert carts["cart-001"]["status"] == "completed"

    # Second checkout (replay)
    result = process_cart_checkout(req)
    assert "Error" in result
    assert "already been completed" in result

def test_invalid_discount():
    """Test Tampering boundary: using an invalid discount code aborts checkout."""
    req = ProcessCartCheckoutRequest(
        user_id="user123",
        cart_id="cart-001",
        discount_code="FAKECODE"
    )
    result = process_cart_checkout(req)

    assert "Error" in result
    assert "not valid" in result
    assert carts["cart-001"]["status"] == "pending" # Checkout aborted
