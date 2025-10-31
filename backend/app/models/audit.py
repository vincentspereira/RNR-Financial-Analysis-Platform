"""
Audit and compliance logging models
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    """
    Comprehensive audit log for compliance and security monitoring
    """
    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User information (optional for system actions)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )
    
    # Action information
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), index=True)
    
    # Change tracking
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Request context
    endpoint: Mapped[Optional[str]] = mapped_column(String(255))
    method: Mapped[Optional[str]] = mapped_column(String(10))  # HTTP method
    request_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # Security context
    ip_address: Mapped[Optional[str]] = mapped_column(INET, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # Result information
    success: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Additional metadata
    audit_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Compliance categories
    compliance_category: Mapped[Optional[str]] = mapped_column(
        String(50), 
        index=True
    )  # 'SOX', 'GDPR', 'PCI_DSS', 'SEC', 'FINRA'
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"resource_type='{self.resource_type}', user_id={self.user_id})>"
        )

    @classmethod
    def create_log(
        cls,
        action: str,
        resource_type: str,
        user_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        audit_metadata: Optional[dict] = None,
        compliance_category: Optional[str] = None,
    ) -> "AuditLog":
        """
        Factory method to create audit log entries
        """
        return cls(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            endpoint=endpoint,
            method=method,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            success=success,
            error_message=error_message,
            audit_metadata=audit_metadata or {},
            compliance_category=compliance_category,
        )

    @property
    def has_data_changes(self) -> bool:
        """Check if audit log contains data changes"""
        return bool(self.old_values or self.new_values)

    @property
    def is_security_event(self) -> bool:
        """Check if this is a security-related event"""
        security_actions = [
            'login', 'logout', 'login_failed', 'password_change',
            'account_locked', 'permission_denied', 'unauthorized_access'
        ]
        return self.action.lower() in security_actions

    @property
    def is_financial_event(self) -> bool:
        """Check if this is a financial data-related event"""
        financial_resources = [
            'portfolio', 'transaction', 'financial_statement',
            'financial_ratio', 'market_data'
        ]
        return self.resource_type.lower() in financial_resources

    def get_change_summary(self) -> Optional[dict]:
        """Get a summary of changes made"""
        if not self.has_data_changes:
            return None
        
        summary = {}
        
        if self.old_values and self.new_values:
            # Compare old and new values
            changed_fields = []
            for key in self.new_values:
                if key in self.old_values and self.old_values[key] != self.new_values[key]:
                    changed_fields.append({
                        'field': key,
                        'old_value': self.old_values[key],
                        'new_value': self.new_values[key]
                    })
            summary['changed_fields'] = changed_fields
        elif self.new_values:
            # New record created
            summary['action_type'] = 'create'
            summary['new_record'] = self.new_values
        elif self.old_values:
            # Record deleted
            summary['action_type'] = 'delete'
            summary['deleted_record'] = self.old_values
        
        return summary