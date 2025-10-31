"""
Reporting API endpoints for PDF generation and custom reports
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

from app.services.report.pdf_generator import report_builder, ReportType, ReportConfig, ReportSection, ChartConfig, ChartType
from app.core.logging import get_logger
from app.core.monitoring import metrics_collector

router = APIRouter()
reports_logger = get_logger("reports.api")


# Request/Response Models
class ReportGenerationRequest(BaseModel):
    report_type: ReportType = Field(..., description="Type of report to generate")
    title: str = Field(..., description="Report title")
    subtitle: Optional[str] = Field(None, description="Report subtitle")
    data: Dict[str, Any] = Field(..., description="Report data")
    user_info: Optional[Dict[str, Any]] = Field(None, description="User information")
    format: str = Field("pdf", description="Output format (pdf, html)")


class CustomReportRequest(BaseModel):
    title: str = Field(..., description="Report title")
    subtitle: Optional[str] = Field(None, description="Report subtitle")
    sections: List[Dict[str, Any]] = Field(..., description="Report sections configuration")
    author: Optional[str] = Field(None, description="Report author")
    company: Optional[str] = Field(None, description="Company name")
    page_size: str = Field("letter", description="Page size (letter, A4)")


class ScheduledReportRequest(BaseModel):
    report_type: ReportType = Field(..., description="Type of report")
    title: str = Field(..., description="Report title")
    schedule: str = Field(..., description="Cron expression for scheduling")
    recipients: List[str] = Field(..., description="Email recipients")
    data_source: Dict[str, Any] = Field(..., description="Data source configuration")
    enabled: bool = Field(True, description="Whether the scheduled report is enabled")


class ReportResponse(BaseModel):
    report_id: str
    title: str
    report_type: str
    generated_at: datetime
    file_size: int
    download_url: str
    expires_at: datetime


class ScheduledReportResponse(BaseModel):
    schedule_id: str
    report_type: str
    title: str
    schedule: str
    recipients: List[str]
    enabled: bool
    next_run: datetime
    created_at: datetime


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks
):
    """Generate a financial report"""
    try:
        reports_logger.info(f"Generating {request.report_type.value} report: {request.title}")
        
        # Generate report based on type
        if request.report_type == ReportType.PORTFOLIO_SUMMARY:
            pdf_bytes = await report_builder.build_portfolio_summary_report(
                portfolio_data=request.data,
                user_info=request.user_info or {}
            )
        elif request.report_type == ReportType.PERFORMANCE_ANALYSIS:
            pdf_bytes = await report_builder.build_performance_analysis_report(
                performance_data=request.data
            )
        elif request.report_type == ReportType.RISK_ASSESSMENT:
            pdf_bytes = await report_builder.build_risk_assessment_report(
                risk_data=request.data
            )
        else:
            # Custom report
            pdf_bytes = await _generate_custom_report(request)
        
        # Generate report ID and store (in production, save to storage)
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.title) % 10000}"
        
        # In production, you would save the PDF to cloud storage
        # For now, we'll simulate this
        download_url = f"/api/v1/reports/download/{report_id}"
        
        # Log metrics
        metrics_collector.increment_counter("reports_generated", {"type": request.report_type.value})
        
        # Background task to clean up old reports
        background_tasks.add_task(_cleanup_old_reports)
        
        return ReportResponse(
            report_id=report_id,
            title=request.title,
            report_type=request.report_type.value,
            generated_at=datetime.now(),
            file_size=len(pdf_bytes),
            download_url=download_url,
            expires_at=datetime.now().replace(hour=23, minute=59, second=59)  # Expires end of day
        )
        
    except Exception as e:
        reports_logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.post("/generate/custom", response_model=ReportResponse)
async def generate_custom_report(request: CustomReportRequest):
    """Generate a custom report with user-defined sections"""
    try:
        reports_logger.info(f"Generating custom report: {request.title}")
        
        # Convert request to ReportConfig
        sections = []
        for section_data in request.sections:
            section = ReportSection(
                title=section_data.get('title', ''),
                content_type=section_data.get('content_type', 'text'),
                content=section_data.get('content', ''),
                style=section_data.get('style')
            )
            sections.append(section)
        
        config = ReportConfig(
            title=request.title,
            subtitle=request.subtitle,
            author=request.author,
            company=request.company,
            sections=sections,
            page_size=request.page_size
        )
        
        # Generate PDF
        pdf_bytes = await report_builder.pdf_generator.generate_report(config)
        
        # Generate report ID
        report_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.title) % 10000}"
        
        # Log metrics
        metrics_collector.increment_counter("reports_generated", {"type": "custom"})
        
        return ReportResponse(
            report_id=report_id,
            title=request.title,
            report_type="custom",
            generated_at=datetime.now(),
            file_size=len(pdf_bytes),
            download_url=f"/api/v1/reports/download/{report_id}",
            expires_at=datetime.now().replace(hour=23, minute=59, second=59)
        )
        
    except Exception as e:
        reports_logger.error(f"Error generating custom report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate custom report: {str(e)}")


@router.get("/download/{report_id}")
async def download_report(report_id: str):
    """Download a generated report"""
    try:
        # In production, retrieve from storage
        # For now, generate a mock PDF
        mock_pdf_content = f"""
        Report ID: {report_id}
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        This is a mock PDF download. In production, this would be the actual PDF file.
        """.encode('utf-8')
        
        # Create streaming response
        def generate():
            yield mock_pdf_content
        
        return StreamingResponse(
            generate(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{report_id}.pdf"
            }
        )
        
    except Exception as e:
        reports_logger.error(f"Error downloading report {report_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Report not found or expired")


@router.get("/preview/{report_id}")
async def preview_report(report_id: str):
    """Preview a report in the browser"""
    try:
        # In production, retrieve from storage and return PDF for inline viewing
        mock_pdf_content = f"""
        Report Preview - ID: {report_id}
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        This is a mock PDF preview. In production, this would display the actual PDF.
        """.encode('utf-8')
        
        return Response(
            content=mock_pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=preview_{report_id}.pdf"
            }
        )
        
    except Exception as e:
        reports_logger.error(f"Error previewing report {report_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Report not found")


@router.post("/schedule", response_model=ScheduledReportResponse)
async def schedule_report(request: ScheduledReportRequest):
    """Schedule a recurring report"""
    try:
        reports_logger.info(f"Scheduling {request.report_type.value} report: {request.title}")
        
        # Validate cron expression (basic validation)
        if not _validate_cron_expression(request.schedule):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
        
        # Generate schedule ID
        schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.title) % 10000}"
        
        # In production, save to database
        # For now, simulate scheduling
        
        # Calculate next run time (simplified)
        next_run = _calculate_next_run(request.schedule)
        
        # Log metrics
        metrics_collector.increment_counter("reports_scheduled", {"type": request.report_type.value})
        
        return ScheduledReportResponse(
            schedule_id=schedule_id,
            report_type=request.report_type.value,
            title=request.title,
            schedule=request.schedule,
            recipients=request.recipients,
            enabled=request.enabled,
            next_run=next_run,
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        reports_logger.error(f"Error scheduling report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule report: {str(e)}")


@router.get("/scheduled")
async def get_scheduled_reports(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get list of scheduled reports"""
    try:
        # In production, query from database
        # For now, return mock data
        
        mock_schedules = []
        for i in range(min(limit, 10)):
            mock_schedules.append({
                "schedule_id": f"schedule_{i}",
                "report_type": "portfolio_summary",
                "title": f"Weekly Portfolio Report {i}",
                "schedule": "0 9 * * 1",  # Every Monday at 9 AM
                "recipients": ["user@example.com"],
                "enabled": True,
                "next_run": datetime.now().replace(hour=9, minute=0, second=0),
                "created_at": datetime.now(),
                "last_run": datetime.now() if i < 5 else None,
                "status": "active"
            })
        
        return {
            "schedules": mock_schedules,
            "total_count": len(mock_schedules),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        reports_logger.error(f"Error getting scheduled reports: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scheduled reports")


@router.put("/scheduled/{schedule_id}")
async def update_scheduled_report(
    schedule_id: str,
    request: ScheduledReportRequest
):
    """Update a scheduled report"""
    try:
        reports_logger.info(f"Updating scheduled report: {schedule_id}")
        
        # Validate cron expression
        if not _validate_cron_expression(request.schedule):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
        
        # In production, update in database
        # For now, simulate update
        
        next_run = _calculate_next_run(request.schedule)
        
        return ScheduledReportResponse(
            schedule_id=schedule_id,
            report_type=request.report_type.value,
            title=request.title,
            schedule=request.schedule,
            recipients=request.recipients,
            enabled=request.enabled,
            next_run=next_run,
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        reports_logger.error(f"Error updating scheduled report {schedule_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update scheduled report")


@router.delete("/scheduled/{schedule_id}")
async def delete_scheduled_report(schedule_id: str):
    """Delete a scheduled report"""
    try:
        reports_logger.info(f"Deleting scheduled report: {schedule_id}")
        
        # In production, delete from database
        # For now, simulate deletion
        
        return {"message": f"Scheduled report {schedule_id} deleted successfully"}
        
    except Exception as e:
        reports_logger.error(f"Error deleting scheduled report {schedule_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete scheduled report")


@router.get("/history")
async def get_report_history(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get report generation history"""
    try:
        # In production, query from database
        # For now, return mock data
        
        mock_history = []
        for i in range(min(limit, 20)):
            mock_history.append({
                "report_id": f"report_{i}",
                "title": f"Portfolio Report {i}",
                "report_type": report_type or "portfolio_summary",
                "generated_at": datetime.now(),
                "generated_by": "user@example.com",
                "file_size": 1024 * (i + 1),
                "status": "completed",
                "download_count": i % 5,
                "expires_at": datetime.now().replace(hour=23, minute=59, second=59)
            })
        
        return {
            "reports": mock_history,
            "total_count": len(mock_history),
            "filters": {
                "report_type": report_type,
                "start_date": start_date,
                "end_date": end_date
            },
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        reports_logger.error(f"Error getting report history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve report history")


@router.get("/templates")
async def get_report_templates():
    """Get available report templates"""
    try:
        templates = [
            {
                "template_id": "portfolio_summary",
                "name": "Portfolio Summary",
                "description": "Comprehensive overview of portfolio holdings and performance",
                "sections": ["overview", "holdings", "allocation", "performance"],
                "required_data": ["portfolio_data", "user_info"]
            },
            {
                "template_id": "performance_analysis",
                "name": "Performance Analysis",
                "description": "Detailed analysis of portfolio performance over time",
                "sections": ["summary", "charts", "benchmarks", "attribution"],
                "required_data": ["performance_data", "benchmark_data"]
            },
            {
                "template_id": "risk_assessment",
                "name": "Risk Assessment",
                "description": "Comprehensive risk analysis and metrics",
                "sections": ["risk_metrics", "var_analysis", "stress_tests", "recommendations"],
                "required_data": ["portfolio_data", "market_data"]
            },
            {
                "template_id": "trading_signals",
                "name": "Trading Signals Report",
                "description": "ML-generated trading signals and recommendations",
                "sections": ["signals", "technical_analysis", "recommendations"],
                "required_data": ["signals_data", "market_data"]
            }
        ]
        
        return {
            "templates": templates,
            "total_count": len(templates)
        }
        
    except Exception as e:
        reports_logger.error(f"Error getting report templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve report templates")


# Helper functions
async def _generate_custom_report(request: ReportGenerationRequest) -> bytes:
    """Generate custom report from request"""
    # This would implement custom report generation logic
    # For now, return mock PDF
    mock_content = f"Custom Report: {request.title}\nGenerated: {datetime.now()}"
    return mock_content.encode('utf-8')


async def _cleanup_old_reports():
    """Background task to clean up old reports"""
    try:
        # In production, delete expired reports from storage
        reports_logger.info("Cleaning up old reports")
        # Simulate cleanup
        pass
    except Exception as e:
        reports_logger.error(f"Error cleaning up old reports: {str(e)}")


def _validate_cron_expression(cron_expr: str) -> bool:
    """Validate cron expression (basic validation)"""
    try:
        parts = cron_expr.split()
        return len(parts) == 5  # Basic validation
    except:
        return False


def _calculate_next_run(cron_expr: str) -> datetime:
    """Calculate next run time from cron expression (simplified)"""
    # In production, use a proper cron library like croniter
    # For now, return next hour
    return datetime.now().replace(minute=0, second=0) + timedelta(hours=1)


# Import required modules
from datetime import timedelta