"""
Billing & Subscription API endpoints.

Provides endpoints for managing subscriptions, viewing plans,
checking usage, and handling Stripe webhooks.
"""
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.schemas.billing import (
    CancelSubscriptionRequest,
    CreateSubscriptionRequest,
    InvoiceResponse,
    PlansListResponse,
    PlanResponse,
    PortalUrlResponse,
    SubscriptionResponse,
    SubscriptionStatusResponse,
    UpdateSubscriptionRequest,
    UsageSummaryResponse,
    WebhookResponse,
)
from app.services.billing import stripe_service, usage_tracker
from app.services.billing.plans import DEFAULT_PLANS
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/billing", tags=["billing"])
logger = get_logger("api.billing")


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")
    access_token = authorization.split(" ")[1]
    user = await auth_service.verify_session(access_token, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled")
    return user


async def _get_user_subscription(
    user_id: str, db: AsyncSession
) -> Optional[UserSubscription]:
    """Get user's active subscription."""
    uid = user_id
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == uid,
        UserSubscription.status.in_(["active", "trialing"]),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_plan_by_name(name: str, db: AsyncSession) -> Optional[SubscriptionPlan]:
    """Get a plan by name from DB or defaults."""
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.name == name)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _get_default_plan(name: str) -> Optional[dict]:
    """Get a default plan by name."""
    for plan in DEFAULT_PLANS:
        if plan["name"].lower() == name.lower():
            return plan
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/plans",
    response_model=PlansListResponse,
    summary="List available plans",
    description="Get all available subscription plans.",
)
async def list_plans(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """List all available subscription plans."""
    try:
        # Try to get plans from DB first
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True).order_by(SubscriptionPlan.sort_order)
        result = await db.execute(stmt)
        db_plans = result.scalars().all()

        if db_plans:
            plans = [
                PlanResponse(
                    id=str(p.id),
                    name=p.name,
                    description=p.description,
                    price_monthly=p.price_monthly,
                    price_annually=p.price_annually,
                    features=p.features if isinstance(p.features, list) else [],
                    limits=p.limits if isinstance(p.limits, dict) else {},
                )
                for p in db_plans
            ]
        else:
            # Fall back to default plans
            plans = [
                PlanResponse(
                    id=f"default_{i}",
                    name=p["name"],
                    description=p["description"],
                    price_monthly=p["price_monthly"],
                    price_annually=p.get("price_annually"),
                    features=p["features"],
                    limits=p["limits"],
                )
                for i, p in enumerate(DEFAULT_PLANS)
            ]

        return PlansListResponse(plans=plans, total=len(plans))

    except Exception as exc:
        logger.error(f"Error listing plans: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve plans.")


@router.get(
    "/subscription",
    summary="Get current subscription",
    description="Get the authenticated user's current subscription details.",
)
async def get_subscription(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Get user's current subscription."""
    try:
        sub = await _get_user_subscription(str(current_user.id), db)

        if not sub:
            return {
                "has_subscription": False,
                "plan_name": "Free",
                "status": "free",
                "features": DEFAULT_PLANS[0]["features"],
                "limits": DEFAULT_PLANS[0]["limits"],
            }

        plan = sub.plan
        return SubscriptionResponse(
            id=str(sub.id),
            plan_name=plan.name if plan else "Unknown",
            status=sub.status,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=sub.cancel_at_period_end,
            features=plan.features if plan and isinstance(plan.features, list) else [],
            limits=plan.limits if plan and isinstance(plan.limits, dict) else {},
        )

    except Exception as exc:
        logger.error(f"Error getting subscription: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve subscription.")


@router.post(
    "/subscribe",
    summary="Create subscription",
    description="Subscribe the authenticated user to a plan.",
)
async def create_subscription(
    request: CreateSubscriptionRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Create a new subscription."""
    try:
        # Check if user already has an active subscription
        existing = await _get_user_subscription(str(current_user.id), db)
        if existing:
            raise HTTPException(status_code=400, detail="User already has an active subscription")

        plan = await _get_plan_by_name(request.plan_name, db)
        default_plan = _get_default_plan(request.plan_name)

        if not plan and not default_plan:
            raise HTTPException(status_code=404, detail=f"Plan not found: {request.plan_name}")

        price_id = plan.stripe_price_id if plan else None

        if stripe_service.is_configured and price_id:
            # Create via Stripe
            customer_id = await stripe_service.create_customer(
                str(current_user.id),
                email=current_user.email,
                name=getattr(current_user, "full_name", ""),
            )

            if customer_id:
                sub_result = await stripe_service.create_subscription(customer_id, price_id)
                if sub_result:
                    # Save to DB
                    plan_id = plan.id if plan else None
                    new_sub = UserSubscription(
                        user_id=current_user.id,
                        plan_id=plan_id,
                        stripe_subscription_id=sub_result["subscription_id"],
                        stripe_customer_id=customer_id,
                        status="active",
                        current_period_start=sub_result["current_period_start"],
                        current_period_end=sub_result["current_period_end"],
                    )
                    db.add(new_sub)
                    await db.commit()

                    return {
                        "status": "active",
                        "plan_name": request.plan_name,
                        "client_secret": sub_result.get("client_secret"),
                    }

        # Without Stripe, create a local subscription record
        if plan:
            new_sub = UserSubscription(
                user_id=current_user.id,
                plan_id=plan.id,
                status="active",
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            )
            db.add(new_sub)
            await db.commit()

        return {
            "status": "active",
            "plan_name": request.plan_name,
            "message": "Subscription created (local mode - no Stripe)",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Subscription creation error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create subscription.")


@router.post(
    "/update",
    summary="Update subscription",
    description="Update the user's subscription to a different plan.",
)
async def update_subscription(
    request: UpdateSubscriptionRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Update user's subscription plan."""
    try:
        sub = await _get_user_subscription(str(current_user.id), db)
        if not sub:
            raise HTTPException(status_code=404, detail="No active subscription found")

        new_plan = await _get_plan_by_name(request.new_plan_name, db)
        if not new_plan:
            raise HTTPException(status_code=404, detail=f"Plan not found: {request.new_plan_name}")

        # Update via Stripe if configured
        if stripe_service.is_configured and sub.stripe_subscription_id and new_plan.stripe_price_id:
            result = await stripe_service.update_subscription(
                sub.stripe_subscription_id, new_plan.stripe_price_id
            )

        # Update local record
        sub.plan_id = new_plan.id
        await db.commit()

        return {
            "status": "updated",
            "plan_name": request.new_plan_name,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Subscription update error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update subscription.")


@router.post(
    "/cancel",
    summary="Cancel subscription",
    description="Cancel the user's subscription.",
)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Cancel user's subscription."""
    try:
        sub = await _get_user_subscription(str(current_user.id), db)
        if not sub:
            raise HTTPException(status_code=404, detail="No active subscription found")

        # Cancel via Stripe
        if stripe_service.is_configured and sub.stripe_subscription_id:
            await stripe_service.cancel_subscription(sub.stripe_subscription_id)

        # Update local record
        sub.status = "canceled"
        sub.cancel_at_period_end = True
        await db.commit()

        return {"status": "canceled", "message": "Subscription will be canceled at end of billing period."}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Subscription cancellation error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel subscription.")


@router.post(
    "/portal",
    response_model=PortalUrlResponse,
    summary="Get Stripe portal URL",
    description="Generate a Stripe Customer Portal URL for self-service billing.",
)
async def get_portal_url(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Get Stripe Customer Portal URL."""
    try:
        sub = await _get_user_subscription(str(current_user.id), db)

        if not sub or not sub.stripe_customer_id:
            return PortalUrlResponse(url=None, configured=False)

        url = await stripe_service.get_customer_portal_url(
            sub.stripe_customer_id,
            return_url="http://localhost:3000/settings/billing",
        )

        return PortalUrlResponse(url=url, configured=url is not None)

    except Exception as exc:
        logger.error(f"Portal URL error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate portal URL.")


@router.get(
    "/usage",
    summary="Get usage stats",
    description="Get the authenticated user's current usage statistics.",
)
async def get_usage(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Get user's usage statistics."""
    try:
        # Get plan limits
        sub = await _get_user_subscription(str(current_user.id), db)
        plan_limits = None
        if sub and sub.plan:
            plan_limits = sub.plan.limits if isinstance(sub.plan.limits, dict) else None

        summary = await usage_tracker.get_usage_summary(
            db, str(current_user.id), plan_limits
        )

        return summary

    except Exception as exc:
        logger.error(f"Usage fetch error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage stats.")


@router.get(
    "/invoices",
    summary="Get invoices",
    description="Get the authenticated user's invoice history.",
)
async def get_invoices(
    current_user=Depends(get_current_user_from_token),
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """Get invoice history."""
    try:
        sub = await _get_user_subscription(str(current_user.id), db)

        if not sub or not sub.stripe_customer_id:
            return {"invoices": [], "total": 0}

        invoices = await stripe_service.get_invoices(sub.stripe_customer_id)

        return {
            "invoices": [
                InvoiceResponse(
                    id=inv["id"],
                    amount_paid=inv["amount_paid"],
                    currency=inv["currency"],
                    status=inv["status"],
                    created=inv.get("created"),
                    pdf_url=inv.get("pdf_url"),
                )
                for inv in invoices
            ],
            "total": len(invoices),
        }

    except Exception as exc:
        logger.error(f"Invoice fetch error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve invoices.")


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Stripe webhook",
    description="Handle incoming Stripe webhook events. This is a public endpoint.",
    include_in_schema=False,
)
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (no auth required)."""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")

        result = await stripe_service.handle_webhook(payload, signature)

        if result:
            return WebhookResponse(
                received=True,
                event_type=result.get("event_type"),
                processed=result.get("processed", False),
            )

        return WebhookResponse(received=True, processed=False)

    except Exception as exc:
        logger.error(f"Webhook error: {exc}", exc_info=True)
        return WebhookResponse(received=True, processed=False)
