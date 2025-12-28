"""
Workout Records API endpoints.
"""
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger, AIDebugLogger
from app.models.record import WorkoutRecord
from app.services.agent import CoachAgent
from app.services.adapter import get_ai_adapter, ChatMessage
from app.prompts.templates import SYSTEM_PROMPT, FITNESS_REPORT_PROMPT

logger = get_logger(__name__)
debug_logger = AIDebugLogger(logger)
router = APIRouter()


# ========================================
# Request/Response Schemas
# ========================================

class CreateRecordRequest(BaseModel):
    """Request to create a new workout record."""
    data: dict[str, Any] = Field(..., description="Workout data")
    planId: str | None = Field(None, description="Associated plan ID")


class RecordResponse(BaseModel):
    """Workout record response."""
    id: str
    createdAt: int
    planId: str | None
    data: dict[str, Any]
    analysis: str | None


class AnalyzeRecordResponse(BaseModel):
    """Response from record analysis with optional update suggestion."""
    id: str
    createdAt: int
    planId: str | None
    data: dict[str, Any]
    analysis: str | None
    suggestUpdate: bool = False
    updateSuggestion: Optional[str] = None


class AnalyzeRecordRequest(BaseModel):
    """Request to analyze a workout record."""
    pass  # No additional fields needed


class UpdateRecordRequest(BaseModel):
    """Request to update a workout record."""
    data: dict[str, Any] = Field(..., description="Updated workout data")


class BatchDeleteRequest(BaseModel):
    """Request to delete multiple workout records."""
    ids: list[UUID] = Field(..., description="List of record IDs to delete")


class FitnessReportResponse(BaseModel):
    """Response containing fitness assessment report."""
    hasData: bool = Field(..., description="Whether user has workout data")
    recordCount: int = Field(0, description="Total number of records analyzed")
    report: Optional[str] = Field(None, description="AI-generated fitness report")
    summary: Optional[dict[str, Any]] = Field(None, description="Statistical summary")


# ========================================
# Helper Functions (Internal)
# ========================================

def _build_fitness_summary(records: list[WorkoutRecord]) -> dict[str, Any]:
    """Build statistical summary from workout records."""
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Filter recent records (last 30 days)
    recent_records = [
        r for r in records 
        if r.created_at >= thirty_days_ago
    ]
    
    # Activity type distribution
    activity_types = []
    total_duration = 0
    total_heart_rate_sum = 0
    heart_rate_count = 0
    total_trimp = 0
    trimp_count = 0
    
    for record in recent_records:
        data = record.data or {}
        
        # Activity type
        activity_type = data.get("type") or data.get("sport_type") or "unknown"
        activity_types.append(activity_type)
        
        # Duration
        duration = data.get("duration") or data.get("moving_time") or 0
        if isinstance(duration, str):
            try:
                duration = int(duration)
            except ValueError:
                duration = 0
        total_duration += duration
        
        # Heart rate
        hr = data.get("heartRate") or data.get("average_heartrate")
        if hr:
            try:
                total_heart_rate_sum += float(hr)
                heart_rate_count += 1
            except (ValueError, TypeError):
                pass
        
        # TRIMP / Training load
        trimp = (
            data.get("trimp") or 
            data.get("suffer_score") or 
            data.get("icu_training_load")
        )
        if trimp:
            try:
                total_trimp += float(trimp)
                trimp_count += 1
            except (ValueError, TypeError):
                pass
    
    # Calculate statistics
    type_counter = Counter(activity_types)
    type_distribution = dict(type_counter.most_common(5))
    
    avg_duration = total_duration / len(recent_records) if recent_records else 0
    avg_heart_rate = total_heart_rate_sum / heart_rate_count if heart_rate_count > 0 else None
    avg_trimp = total_trimp / trimp_count if trimp_count > 0 else None
    
    # Weekly frequency
    weeks_span = max(1, (now - thirty_days_ago).days / 7)
    weekly_frequency = len(recent_records) / weeks_span
    
    return {
        "period_days": 30,
        "total_records": len(records),
        "recent_records": len(recent_records),
        "weekly_frequency": round(weekly_frequency, 1),
        "activity_type_distribution": type_distribution,
        "total_duration_minutes": round(total_duration),
        "avg_duration_minutes": round(avg_duration),
        "avg_heart_rate": round(avg_heart_rate) if avg_heart_rate else None,
        "avg_trimp": round(avg_trimp, 1) if avg_trimp else None,
    }


async def _generate_ai_fitness_report(summary: dict[str, Any]) -> str:
    """Generate AI fitness report based on summary statistics."""
    adapter = get_ai_adapter()
    
    # Build user prompt with summary data
    summary_text = f"""### 用户运动数据统计（最近30天）

- **总记录数**：{summary['total_records']} 条（近30天：{summary['recent_records']} 条）
- **每周训练频率**：{summary['weekly_frequency']} 次/周
- **运动类型分布**：{summary['activity_type_distribution']}
- **总训练时长**：{summary['total_duration_minutes']} 分钟
- **平均每次训练时长**：{summary['avg_duration_minutes']} 分钟
"""
    
    if summary.get('avg_heart_rate'):
        summary_text += f"- **平均心率**：{summary['avg_heart_rate']} bpm\n"
    
    if summary.get('avg_trimp'):
        summary_text += f"- **平均TRIMP训练冲量**：{summary['avg_trimp']}\n"
    
    summary_text += "\n请根据以上数据生成运动能力评估报告。"
    
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=FITNESS_REPORT_PROMPT + "\n\n" + summary_text),
    ]
    
    with debug_logger.track_call(
        provider=settings.AI_PROVIDER,
        model=adapter.model,
        endpoint="fitness_report"
    ) as call:
        call.add_messages([m.to_dict() for m in messages])
        
        response = await adapter.chat_completion(
            messages=messages,
            temperature=0.7
        )
        
        call.set_response(
            content=response.content,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens
        )
    
    return response.content


# ========================================
# API Endpoints
# ========================================

@router.post("", response_model=RecordResponse)
async def create_record(
    request: CreateRecordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workout record.
    """
    logger.info("Creating workout record")
    
    # Parse plan_id if provided
    plan_id = None
    if request.planId:
        try:
            plan_id = UUID(request.planId)
        except ValueError:
            pass
    
    db_record = WorkoutRecord(
        plan_id=plan_id,
        data=request.data,
    )
    db.add(db_record)
    await db.flush()
    await db.refresh(db_record)
    
    logger.info("Record created", record_id=str(db_record.id))
    
    return RecordResponse(
        id=str(db_record.id),
        createdAt=int(db_record.created_at.timestamp() * 1000),
        planId=str(db_record.plan_id) if db_record.plan_id else None,
        data=db_record.data,
        analysis=db_record.analysis,
    )


@router.get("", response_model=list[RecordResponse])
async def list_records(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all workout records.
    """
    result = await db.execute(
        select(WorkoutRecord).order_by(WorkoutRecord.created_at.desc())
    )
    records = result.scalars().all()
    
    return [
        RecordResponse(
            id=str(record.id),
            createdAt=int(record.created_at.timestamp() * 1000),
            planId=str(record.plan_id) if record.plan_id else None,
            data=record.data,
            analysis=record.analysis,
        )
        for record in records
    ]


@router.get("/fitness-report", response_model=FitnessReportResponse)
async def generate_fitness_report(
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a fitness assessment report based on user's workout history.
    
    Analyzes all workout records and uses AI to generate a comprehensive
    fitness level assessment that can be used for plan creation.
    """
    logger.info("Generating fitness report")
    
    # Fetch all workout records
    result = await db.execute(
        select(WorkoutRecord).order_by(WorkoutRecord.created_at.desc())
    )
    records = list(result.scalars().all())
    
    if not records:
        return FitnessReportResponse(
            hasData=False,
            recordCount=0,
            report=None,
            summary=None
        )
    
    # Build statistical summary
    summary = _build_fitness_summary(records)
    
    # Generate AI report
    try:
        report = await _generate_ai_fitness_report(summary)
    except Exception as e:
        logger.error("Failed to generate AI fitness report", error=str(e))
        # Return summary without AI report if generation fails
        return FitnessReportResponse(
            hasData=True,
            recordCount=len(records),
            report=None,
            summary=summary
        )
    
    logger.info("Fitness report generated", record_count=len(records))
    
    return FitnessReportResponse(
        hasData=True,
        recordCount=len(records),
        report=report,
        summary=summary
    )


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific workout record by ID.
    """
    result = await db.execute(
        select(WorkoutRecord).where(WorkoutRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    return RecordResponse(
        id=str(record.id),
        createdAt=int(record.created_at.timestamp() * 1000),
        planId=str(record.plan_id) if record.plan_id else None,
        data=record.data,
        analysis=record.analysis,
    )


@router.put("/{record_id}", response_model=RecordResponse)
async def update_record(
    record_id: UUID,
    request: UpdateRecordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a workout record.
    """
    result = await db.execute(
        select(WorkoutRecord).where(WorkoutRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # Update the record data
    record.data = request.data
    await db.flush()
    await db.refresh(record)
    
    logger.info("Record updated", record_id=str(record_id))
    
    return RecordResponse(
        id=str(record.id),
        createdAt=int(record.created_at.timestamp() * 1000),
        planId=str(record.plan_id) if record.plan_id else None,
        data=record.data,
        analysis=record.analysis,
    )


@router.delete("/{record_id}")
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a workout record.
    """
    result = await db.execute(
        select(WorkoutRecord).where(WorkoutRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # Notify sync server to untrack this record (if it came from external source)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.INTERVALS_SERVER_URL}/api/sync/untrack-record",
                json={"localRecordId": str(record_id)},
                timeout=2.0
            )
    except Exception as e:
        # Don't fail deletion if notification fails, just log it
        logger.warning("Failed to notify sync server of record deletion", error=str(e))

    await db.delete(record)
    
    logger.info("Record deleted", record_id=str(record_id))
    
    return {"message": "记录已删除"}


@router.post("/batch-delete")
async def batch_delete_records(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete multiple workout records.
    """
    logger.info("Batch deleting workout records", count=len(request.ids))
    
    # Notify sync server for each record
    async with httpx.AsyncClient() as client:
        for record_id in request.ids:
            try:
                await client.post(
                    f"{settings.INTERVALS_SERVER_URL}/api/sync/untrack-record",
                    json={"localRecordId": str(record_id)},
                    timeout=2.0
                )
            except Exception as e:
                logger.warning("Failed to notify sync server of record deletion", record_id=str(record_id), error=str(e))

    # Delete from database
    result = await db.execute(
        select(WorkoutRecord).where(WorkoutRecord.id.in_(request.ids))
    )
    records = result.scalars().all()
    
    for record in records:
        await db.delete(record)
    
    logger.info("Batch delete completed", count=len(records))
    
    return {"message": f"成功删除 {len(records)} 条记录"}


@router.post("/{record_id}/analyze", response_model=AnalyzeRecordResponse)
async def analyze_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a workout record using AI with context awareness.
    
    Uses CoachAgent with vector context for enhanced analysis.
    May suggest plan updates based on analysis results.
    """
    result = await db.execute(
        select(WorkoutRecord).where(WorkoutRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    logger.info("Analyzing record", record_id=str(record_id))
    
    try:
        agent = CoachAgent(db)
        analysis_result = await agent.analyze_record(
            plan_id=str(record.plan_id) if record.plan_id else None,
            record_id=str(record_id),
            record_data=record.data
        )
        
        # Save analysis to database
        analysis_text = analysis_result.analysis or ""
        record.analysis = analysis_text
        await db.flush()
        
        logger.info(
            "Record analyzed",
            record_id=str(record_id),
            suggest_update=analysis_result.suggest_update
        )
        
        return AnalyzeRecordResponse(
            id=str(record.id),
            createdAt=int(record.created_at.timestamp() * 1000),
            planId=str(record.plan_id) if record.plan_id else None,
            data=record.data,
            analysis=record.analysis,
            suggestUpdate=analysis_result.suggest_update,
            updateSuggestion=analysis_result.update_suggestion,
        )
        
    except Exception as e:
        logger.error("Analysis error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
