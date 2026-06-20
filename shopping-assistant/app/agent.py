# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field

import os
import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


used_discount_codes = set()
valid_codes = {"WELCOME50", "SUMMER20"}

loyalty_accounts: dict[str, int] = {}
processed_transactions: set[str] = set()

carts: dict[str, dict] = {}
orders: dict[str, dict] = {}
admins: set[str] = {"admin999"}

class AwardLoyaltyPointsRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="The ID of the registered user.")
    purchase_amount: float = Field(..., gt=0, description="The total amount of the successful purchase.")
    transaction_id: str = Field(..., description="The unique ID of the successful purchase transaction.")

class ProcessCartCheckoutRequest(BaseModel):
    user_id: str = Field(..., description="The registered user ID initiating the checkout.")
    cart_id: str = Field(..., description="The ID of the cart to checkout.")
    discount_code: str | None = Field(default=None, description="Optional discount code to apply.")

class UpdateDiscountStatusRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user requesting the change. Must be an administrator.")
    code: str = Field(..., description="The discount code to activate or deactivate.")
    active: bool = Field(..., description="True to activate the code, False to deactivate.")

def redeem_discount_code(user_id: str, code: str) -> str:
    """Redeems a single-use discount code for a user.

    Args:
        user_id: The ID of the registered user redeeming the code.
        code: The discount code to redeem (e.g. WELCOME50, SUMMER20).

    Returns:
        A string indicating success or failure of the redemption.
    """
    code = code.upper()
    if not user_id:
        return "Error: A registered user ID is required to redeem codes."

    if code not in valid_codes:
        return f"Error: The code '{code}' is not valid."

    if code in used_discount_codes:
        return f"Error: The code '{code}' has already been redeemed."

    used_discount_codes.add(code)
    return f"Success: Code '{code}' redeemed successfully by user {user_id}."


def award_loyalty_points(request: AwardLoyaltyPointsRequest) -> str:
    """Awards loyalty points to a user based on their purchase amount.

    1 point is awarded for every $1 spent.
    """
    if request.transaction_id in processed_transactions:
        return f"Error: Transaction '{request.transaction_id}' has already been processed."

    points = int(request.purchase_amount)
    user_id = request.user_id

    current_points = loyalty_accounts.get(user_id, 0)
    loyalty_accounts[user_id] = current_points + points
    processed_transactions.add(request.transaction_id)

    return f"Success: {points} points awarded to user {user_id}. Total points: {loyalty_accounts[user_id]}."


def process_cart_checkout(request: ProcessCartCheckoutRequest) -> str:
    """Processes a user's cart checkout and applies an optional discount code."""
    cart = carts.get(request.cart_id)

    if not cart:
        return f"Error: Cart '{request.cart_id}' not found."

    # IDOR Protection
    if cart["user_id"] != request.user_id:
        return f"Error: Unauthorized. Cart '{request.cart_id}' does not belong to user '{request.user_id}'."

    # Replay Attack Protection
    if cart["status"] == "completed":
        return f"Error: Cart '{request.cart_id}' has already been completed."

    total = cart["total"]
    discount_applied = False

    # Discount Tampering Protection
    if request.discount_code:
        redeem_result = redeem_discount_code(request.user_id, request.discount_code)
        if "Error" in redeem_result:
            return redeem_result  # Abort checkout if discount fails

        # Apply 20% mock discount
        total = total * 0.8
        discount_applied = True

    # Finalize Checkout
    cart["status"] = "completed"
    orders[request.cart_id] = {
        "user_id": request.user_id,
        "final_total": total,
        "discount_applied": discount_applied
    }

    msg = f"Success: Order processed for cart '{request.cart_id}'. Final total: ${total:.2f}."
    if discount_applied:
        msg += " Discount applied."
    return msg


def update_discount_status(request: UpdateDiscountStatusRequest) -> str:
    """Activates or deactivates a discount code for the store. Requires administrator privileges."""
    if request.user_id not in admins:
        return f"Error: Unauthorized. User '{request.user_id}' does not have administrator privileges."

    code = request.code.upper()
    if request.active:
        valid_codes.add(code)
        return f"Success: Discount code '{code}' has been activated."
    else:
        if code in valid_codes:
            valid_codes.remove(code)
        return f"Success: Discount code '{code}' has been deactivated."


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        api_key=os.environ.get("GEMINI_API_KEY"),  # type: ignore
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are an AI shopping assistant for a retail store. Help users find products, answer questions, assist them in redeeming discount codes, award loyalty points for purchases, process cart checkouts, and manage discount code status for administrators.",
    tools=[redeem_discount_code, award_loyalty_points, process_cart_checkout, update_discount_status],
)

app = App(
    root_agent=root_agent,
    name="app",
)
