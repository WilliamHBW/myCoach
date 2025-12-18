"""
Workout Records API endpoints.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.record import WorkoutRecord
from app.services.ai import AIService

logger = get_logger(__name__)
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


class AnalyzeRecordRequest(BaseModel):
    """Request to analyze a workout record."""
    pass  # No additional fields needed


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
    
    await db.delete(record)
    
    logger.info("Record deleted", record_id=str(record_id))
    
    return {"message": "记录已删除"}


@router.post("/{record_id}/analyze", response_model=RecordResponse)
async def analyze_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a workout record using AI.
    """
    result = await db.execute(
        select(WorkoutRecord).where(WorkoutRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    logger.info("Analyzing record", record_id=str(record_id))
    
    try:
        ai_service = AIService()
        analysis = await ai_service.analyze_workout_record({
            "type": record.data.get("type"),
            "duration": record.data.get("duration"),
            "rpe": record.data.get("rpe"),
            "heartRate": record.data.get("heartRate"),
            "notes": record.data.get("notes"),
        })
        
        # Save analysis to database
        record.analysis = analysis
        await db.flush()
        
        logger.info("Record analyzed", record_id=str(record_id))
        
        return RecordResponse(
            id=str(record.id),
            createdAt=int(record.created_at.timestamp() * 1000),
            planId=str(record.plan_id) if record.plan_id else None,
            data=record.data,
            analysis=record.analysis,
        )
        
    except Exception as e:
        logger.error("Analysis error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

