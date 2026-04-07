"""
Stripe integration service for subscription management.

Handles customer creation, subscription lifecycle, and webhook processing.
Gracefully handles the case where Stripe is not configured.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.billing.stripe_service")

# Try importing stripe
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


class StripeService:
    """Stripe integration for subscription and billing management."""

    def __init__(self) -> None:
        api_key = getattr(settings, "STRIPE_API_KEY", None)
        if STRIPE_AVAILABLE and api_key:
            stripe.api_key = api_key
            self._configured = True
        else:
            self._configured = False

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def create_customer(self, user_id: str, email: str, name: str = "") -> Optional[str]:
        """Create a Stripe customer for a user."""
        if not self._configured:
            logger.warning("Stripe not configured, skipping customer creation")
            return None

        try:
            customer = stripe.Customer.create(
                metadata={"user_id": user_id},
                email=email,
                name=name,
            )
            return customer.id
        except stripe.error.StripeError as exc:
            logger.error(f"Stripe customer creation error: {exc}")
            return None

    async def create_subscription(
        self, customer_id: str, price_id: str
    ) -> Optional[Dict[str, Any]]:
        """Create a subscription in Stripe."""
        if not self._configured:
            return None

        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(
                    subscription.current_period_start, tz=timezone.utc
                ),
                "current_period_end": datetime.fromtimestamp(
                    subscription.current_period_end, tz=timezone.utc
                ),
                "client_secret": (
                    subscription.latest_invoice.payment_intent.client_secret
                    if hasattr(subscription, "latest_invoice") and subscription.latest_invoice
                    else None
                ),
            }
        except stripe.error.StripeError as exc:
            logger.error(f"Stripe subscription creation error: {exc}")
            return None

    async def cancel_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Cancel a subscription immediately."""
        if not self._configured:
            return None

        try:
            subscription = stripe.Subscription.delete(subscription_id)
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
            }
        except stripe.error.StripeError as exc:
            logger.error(f"Stripe cancellation error: {exc}")
            return None

    async def update_subscription(
        self, subscription_id: str, new_price_id: str
    ) -> Optional[Dict[str, Any]]:
        """Update (upgrade/downgrade) a subscription to a new price."""
        if not self._configured:
            return None

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            updated = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0].id,
                    "price": new_price_id,
                }],
                proration_behavior="create_prorations",
            )
            return {
                "subscription_id": updated.id,
                "status": updated.status,
            }
        except stripe.error.StripeError as exc:
            logger.error(f"Stripe subscription update error: {exc}")
            return None

    async def handle_webhook(self, payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
        """Process Stripe webhook events."""
        if not self._configured:
            return None

        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
        if not webhook_secret:
            logger.warning("No Stripe webhook secret configured")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )

            event_type = event["type"]
            event_data = event["data"]["object"]

            result = {"event_type": event_type, "processed": False}

            if event_type == "customer.subscription.updated":
                result["processed"] = True
                result["subscription_id"] = event_data.get("id")
                result["status"] = event_data.get("status")

            elif event_type == "customer.subscription.deleted":
                result["processed"] = True
                result["subscription_id"] = event_data.get("id")

            elif event_type == "invoice.payment_succeeded":
                result["processed"] = True
                result["subscription_id"] = event_data.get("subscription")

            elif event_type == "invoice.payment_failed":
                result["processed"] = True
                result["subscription_id"] = event_data.get("subscription")

            return result

        except stripe.error.SignatureVerificationError:
            logger.warning("Invalid webhook signature")
            return None
        except Exception as exc:
            logger.error(f"Webhook processing error: {exc}")
            return None

    async def get_customer_portal_url(
        self, customer_id: str, return_url: str
    ) -> Optional[str]:
        """Generate a Stripe Customer Portal URL."""
        if not self._configured:
            return None

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as exc:
            logger.error(f"Portal URL error: {exc}")
            return None

    async def get_invoices(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get invoice history for a customer."""
        if not self._configured:
            return []

        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
            return [
                {
                    "id": inv.id,
                    "amount_paid": inv.amount_paid / 100,  # Stripe amounts are in cents
                    "currency": inv.currency,
                    "status": inv.status,
                    "created": datetime.fromtimestamp(inv.created, tz=timezone.utc),
                    "pdf_url": inv.invoice_pdf,
                }
                for inv in invoices.data
            ]
        except stripe.error.StripeError as exc:
            logger.error(f"Invoice fetch error: {exc}")
            return []
