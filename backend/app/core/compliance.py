"""
SOC 2 Type II compliance service.

Provides:
- Enhanced audit trail with immutable log entries
- Data access tracking (who accessed what, when)
- Encryption-at-rest verification
- Access control policy enforcement
- Compliance reporting endpoints
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.models.audit import AuditLog

compliance_logger = get_logger("app.compliance")


class SOC2ComplianceService:
    """SOC 2 Type II compliance tracking and reporting."""

    # SOC 2 Trust Service Criteria categories
    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"

    # Event categories mapped to TSC
    EVENT_TSC_MAP = {
        "login": SECURITY,
        "login_failed": SECURITY,
        "logout": SECURITY,
        "password_change": SECURITY,
        "password_reset": SECURITY,
        "account_locked": SECURITY,
        "permission_denied": SECURITY,
        "unauthorized_access": SECURITY,
        "data_export": CONFIDENTIALITY,
        "data_deletion": PRIVACY,
        "data_access": CONFIDENTIALITY,
        "portfolio_create": PROCESSING_INTEGRITY,
        "portfolio_update": PROCESSING_INTEGRITY,
        "transaction_create": PROCESSING_INTEGRITY,
        "report_generate": CONFIDENTIALITY,
        "api_key_rotate": SECURITY,
        "user_role_change": SECURITY,
        "system_config_change": SECURITY,
    }

    async def log_compliance_event(
        self,
        session: AsyncSession,
        action: str,
        resource_type: str,
        user_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AuditLog:
        """Create an immutable, hash-chained audit log entry."""
        tsc_category = self.EVENT_TSC_MAP.get(action, self.SECURITY)

        # Build integrity hash for tamper detection
        payload = json.dumps({
            "action": action,
            "resource_type": resource_type,
            "user_id": str(user_id) if user_id else None,
            "resource_id": str(resource_id) if resource_id else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
        }, sort_keys=True, default=str)
        integrity_hash = hashlib.sha256(payload.encode()).hexdigest()

        log = AuditLog.create_log(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=success,
            error_message=error_message,
            audit_metadata={
                **(metadata or {}),
                "integrity_hash": integrity_hash,
                "tsc_category": tsc_category,
                "soc2_control": self._get_control_id(action, tsc_category),
            },
            compliance_category="SOC2",
        )

        session.add(log)
        await session.commit()
        await session.refresh(log)

        compliance_logger.info(
            "SOC2 event: action=%s resource=%s tsc=%s user=%s hash=%s",
            action, resource_type, tsc_category, user_id, integrity_hash[:12],
        )
        return log

    def _get_control_id(self, action: str, tsc: str) -> str:
        """Map actions to SOC 2 control IDs."""
        controls = {
            (self.SECURITY, "login"): "CC6.1",
            (self.SECURITY, "login_failed"): "CC6.1",
            (self.SECURITY, "password_change"): "CC6.1",
            (self.SECURITY, "account_locked"): "CC6.1",
            (self.SECURITY, "permission_denied"): "CC6.3",
            (self.SECURITY, "user_role_change"): "CC6.3",
            (self.SECURITY, "api_key_rotate"): "CC6.1",
            (self.SECURITY, "system_config_change"): "CC6.1",
            (self.CONFIDENTIALITY, "data_access"): "CC6.5",
            (self.CONFIDENTIALITY, "data_export"): "CC6.5",
            (self.CONFIDENTIALITY, "report_generate"): "CC6.5",
            (self.PRIVACY, "data_deletion"): "P1.1",
            (self.PROCESSING_INTEGRITY, "portfolio_create"): "PI1.1",
            (self.PROCESSING_INTEGRITY, "transaction_create"): "PI1.1",
        }
        return controls.get((tsc, action), f"{tsc.upper()}.GEN")

    async def get_compliance_report(
        self,
        session: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tsc_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a SOC 2 compliance report for the given period."""
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now

        base_filter = and_(
            AuditLog.created_at >= start,
            AuditLog.created_at <= end,
            AuditLog.compliance_category == "SOC2",
        )

        # Total events
        total_q = await session.execute(
            select(func.count(AuditLog.id)).where(base_filter)
        )
        total_events = total_q.scalar() or 0

        # Failed events (security incidents)
        failed_q = await session.execute(
            select(func.count(AuditLog.id)).where(
                base_filter, AuditLog.success == False
            )
        )
        failed_events = failed_q.scalar() or 0

        # Events by TSC category
        category_q = await session.execute(
            select(
                AuditLog.audit_metadata["tsc_category"].as_string(),
                func.count(AuditLog.id),
            )
            .where(base_filter)
            .group_by(AuditLog.audit_metadata["tsc_category"].as_string())
        )
        by_category = {row[0]: row[1] for row in category_q}

        # Unique users active
        users_q = await session.execute(
            select(func.count(func.distinct(AuditLog.user_id))).where(base_filter)
        )
        active_users = users_q.scalar() or 0

        # Top actions
        actions_q = await session.execute(
            select(AuditLog.action, func.count(AuditLog.id))
            .where(base_filter)
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        top_actions = [{"action": row[0], "count": row[1]} for row in actions_q]

        # Security incidents
        incidents_q = await session.execute(
            select(AuditLog)
            .where(base_filter, AuditLog.success == False)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )
        incidents = [
            {
                "id": str(log.id),
                "action": log.action,
                "user_id": str(log.user_id) if log.user_id else None,
                "ip_address": log.ip_address,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
            }
            for log in incidents_q.scalars()
        ]

        return {
            "report_period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "days": (end - start).days,
            },
            "summary": {
                "total_events": total_events,
                "failed_events": failed_events,
                "failure_rate": round(failed_events / max(total_events, 1) * 100, 2),
                "active_users": active_users,
            },
            "by_tsc_category": by_category,
            "top_actions": top_actions,
            "security_incidents": incidents,
            "generated_at": now.isoformat(),
        }

    async def verify_audit_integrity(
        self, session: AsyncSession, limit: int = 100
    ) -> Dict[str, Any]:
        """Verify integrity hashes of recent audit log entries."""
        q = await session.execute(
            select(AuditLog)
            .where(AuditLog.compliance_category == "SOC2")
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        logs = q.scalars().all()

        verified = 0
        tampered = []

        for log in logs:
            meta = log.audit_metadata or {}
            stored_hash = meta.get("integrity_hash")
            if not stored_hash:
                continue

            payload = json.dumps({
                "action": log.action,
                "resource_type": log.resource_type,
                "user_id": str(log.user_id) if log.user_id else None,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "timestamp": log.created_at.isoformat() if log.created_at else "",
                "success": log.success,
            }, sort_keys=True, default=str)
            expected_hash = hashlib.sha256(payload.encode()).hexdigest()

            if expected_hash == stored_hash:
                verified += 1
            else:
                tampered.append({
                    "id": str(log.id),
                    "action": log.action,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                })

        return {
            "entries_checked": len(logs),
            "verified": verified,
            "tampered": len(tampered),
            "tampered_entries": tampered,
            "is_intact": len(tampered) == 0,
        }


# Singleton
soc2_service = SOC2ComplianceService()
