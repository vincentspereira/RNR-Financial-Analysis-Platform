"""
Comprehensive audit logging system for security and compliance
"""
import json
import hashlib
from datetime import datetime, timezone, timezone
from typing import Any, Dict, Optional, List
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_async_session, AsyncSessionLocal
from app.core.logging import get_logger
from app.models.audit import AuditLog


class AuditEventType(Enum):
    """Audit event types for categorization"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_REFRESH = "token_refresh"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    
    # Data events
    DATA_CREATE = "data_create"
    DATA_READ = "data_read"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGE = "config_change"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    
    # Security events
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_INPUT = "invalid_input"
    
    # Financial events
    PORTFOLIO_CREATE = "portfolio_create"
    PORTFOLIO_UPDATE = "portfolio_update"
    TRANSACTION_CREATE = "transaction_create"
    CALCULATION_PERFORMED = "calculation_performed"
    REPORT_GENERATED = "report_generated"


class ComplianceCategory(Enum):
    """Compliance categories for regulatory requirements"""
    SOX = "SOX"  # Sarbanes-Oxley Act
    GDPR = "GDPR"  # General Data Protection Regulation
    PCI_DSS = "PCI_DSS"  # Payment Card Industry Data Security Standard
    HIPAA = "HIPAA"  # Health Insurance Portability and Accountability Act
    FINRA = "FINRA"  # Financial Industry Regulatory Authority
    SEC = "SEC"  # Securities and Exchange Commission


class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self):
        self.logger = get_logger("audit")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        compliance_category: Optional[ComplianceCategory] = None,
        risk_level: str = "LOW",
        success: bool = True
    ) -> UUID:
        """Log an audit event"""
        
        audit_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        
        # Create audit log entry
        audit_entry = {
            "audit_id": str(audit_id),
            "timestamp": timestamp.isoformat(),
            "event_type": event_type.value,
            "user_id": str(user_id) if user_id else None,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "session_id": session_id,
            "compliance_category": compliance_category.value if compliance_category else None,
            "risk_level": risk_level,
            "success": success
        }
        
        # Calculate integrity hash
        audit_hash = self._calculate_hash(audit_entry)
        audit_entry["integrity_hash"] = audit_hash
        
        # Log to structured logger
        self.logger.info(
            f"Audit Event: {event_type.value}",
            extra={
                "audit_event": True,
                "event_type": event_type.value,
                "user_id": str(user_id) if user_id else None,
                "resource_type": resource_type,
                "action": action,
                "success": success,
                "risk_level": risk_level,
                "compliance_category": compliance_category.value if compliance_category else None,
                "details": details
            }
        )
        
        # Store in database
        try:
            async with AsyncSessionLocal() as db:
                audit_log = AuditLog(
                    id=audit_id,
                    event_type=event_type.value,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action or event_type.value,
                    details=details or {},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                    compliance_category=compliance_category.value if compliance_category else None,
                    risk_level=risk_level,
                    success=success,
                    integrity_hash=audit_hash,
                    created_at=timestamp
                )
                
                db.add(audit_log)
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to store audit log: {str(e)}")
        
        return audit_id
    
    def _calculate_hash(self, audit_entry: Dict[str, Any]) -> str:
        """Calculate integrity hash for audit entry"""
        # Create a consistent string representation
        hash_data = json.dumps(audit_entry, sort_keys=True, default=str)
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    async def verify_integrity(self, audit_id: UUID) -> bool:
        """Verify the integrity of an audit log entry"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AuditLog).where(AuditLog.id == audit_id)
                )
                audit_log = result.scalar_one_or_none()
                
                if not audit_log:
                    return False
                
                # Recreate the audit entry for hash calculation
                audit_entry = {
                    "audit_id": str(audit_log.id),
                    "timestamp": audit_log.created_at.isoformat(),
                    "event_type": audit_log.event_type,
                    "user_id": str(audit_log.user_id) if audit_log.user_id else None,
                    "resource_type": audit_log.resource_type,
                    "resource_id": str(audit_log.resource_id) if audit_log.resource_id else None,
                    "action": audit_log.action,
                    "details": audit_log.details,
                    "ip_address": audit_log.ip_address,
                    "user_agent": audit_log.user_agent,
                    "session_id": audit_log.session_id,
                    "compliance_category": audit_log.compliance_category,
                    "risk_level": audit_log.risk_level,
                    "success": audit_log.success
                }
                
                calculated_hash = self._calculate_hash(audit_entry)
                return calculated_hash == audit_log.integrity_hash
                
        except Exception as e:
            self.logger.error(f"Failed to verify audit log integrity: {str(e)}")
            return False
    
    async def get_audit_trail(
        self,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail with filtering options"""
        try:
            async with AsyncSessionLocal() as db:
                query = select(AuditLog)
                
                conditions = []
                if user_id:
                    conditions.append(AuditLog.user_id == user_id)
                if resource_type:
                    conditions.append(AuditLog.resource_type == resource_type)
                if event_type:
                    conditions.append(AuditLog.event_type == event_type.value)
                if start_date:
                    conditions.append(AuditLog.created_at >= start_date)
                if end_date:
                    conditions.append(AuditLog.created_at <= end_date)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(AuditLog.created_at.desc()).limit(limit)
                
                result = await db.execute(query)
                audit_logs = result.scalars().all()
                
                return [
                    {
                        "id": str(log.id),
                        "timestamp": log.created_at.isoformat(),
                        "event_type": log.event_type,
                        "user_id": str(log.user_id) if log.user_id else None,
                        "resource_type": log.resource_type,
                        "resource_id": str(log.resource_id) if log.resource_id else None,
                        "action": log.action,
                        "details": log.details,
                        "ip_address": log.ip_address,
                        "success": log.success,
                        "risk_level": log.risk_level,
                        "compliance_category": log.compliance_category
                    }
                    for log in audit_logs
                ]
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit trail: {str(e)}")
            return []
    
    async def generate_compliance_report(
        self,
        compliance_category: ComplianceCategory,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for regulatory requirements"""
        try:
            async with AsyncSessionLocal() as db:
                query = select(AuditLog).where(
                    and_(
                        AuditLog.compliance_category == compliance_category.value,
                        AuditLog.created_at >= start_date,
                        AuditLog.created_at <= end_date
                    )
                )
                
                result = await db.execute(query)
                audit_logs = result.scalars().all()
                
                # Generate report statistics
                total_events = len(audit_logs)
                successful_events = sum(1 for log in audit_logs if log.success)
                failed_events = total_events - successful_events
                
                event_types = {}
                risk_levels = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
                
                for log in audit_logs:
                    event_types[log.event_type] = event_types.get(log.event_type, 0) + 1
                    risk_levels[log.risk_level] = risk_levels.get(log.risk_level, 0) + 1
                
                return {
                    "compliance_category": compliance_category.value,
                    "report_period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "summary": {
                        "total_events": total_events,
                        "successful_events": successful_events,
                        "failed_events": failed_events,
                        "success_rate": (successful_events / total_events * 100) if total_events > 0 else 0
                    },
                    "event_breakdown": event_types,
                    "risk_distribution": risk_levels,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {str(e)}")
            return {}


# Global audit logger instance
audit_logger = AuditLogger()


# Convenience functions for common audit events
async def log_authentication_event(
    event_type: AuditEventType,
    user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
):
    """Log authentication-related events"""
    return await audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        details=details,
        compliance_category=ComplianceCategory.SOX,
        risk_level="MEDIUM" if not success else "LOW"
    )


async def log_data_access_event(
    event_type: AuditEventType,
    user_id: UUID,
    resource_type: str,
    resource_id: Optional[UUID] = None,
    action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Log data access events"""
    return await audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        details=details,
        compliance_category=ComplianceCategory.GDPR,
        risk_level="LOW"
    )


async def log_security_event(
    event_type: AuditEventType,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    risk_level: str = "HIGH"
):
    """Log security-related events"""
    return await audit_logger.log_event(
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
        success=False,
        risk_level=risk_level,
        compliance_category=ComplianceCategory.SOX
    )
