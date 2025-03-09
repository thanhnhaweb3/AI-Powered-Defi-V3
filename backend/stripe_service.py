import stripe
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_API_KEY")

class StripeService:
    def create_payment_intent(self, amount: int, user_id: str) -> dict:
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount * 100,  # Số tiền tính bằng cents
                currency="usd",
                metadata={"user_id": user_id},
                description=f"Purchase {amount} AI credits for {user_id}"
            )
            logger.info(f"Created payment intent for {user_id}: {intent['id']}")
            return {
                "client_secret": intent["client_secret"],
                "payment_intent_id": intent["id"]
            }
        except Exception as e:
            logger.error(f"Stripe error: {str(e)}")
            raise Exception(f"Failed to create payment intent: {str(e)}")

    def confirm_payment(self, payment_intent_id: str) -> bool:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent["status"] == "succeeded":
                logger.info(f"Payment confirmed: {payment_intent_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Stripe confirmation error: {str(e)}")
            raise Exception(f"Failed to confirm payment: {str(e)}")
