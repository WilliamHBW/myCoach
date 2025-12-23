"""
Training Plans API endpoints.
"""
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.plan import TrainingPlan
from app.models.record import WorkoutRecord
from app.services.ai import AIService, AgentService

logger = get_logger(__name__)
router = APIRouter()


# ========================================
# Request/Response Schemas
# ========================================

class GeneratePlanRequest(BaseModel):
    """Request to generate a new training plan."""
    userProfile: dict[str, Any] = Field(..., description="User questionnaire answers")
    startDate: str = Field(..., description="Plan start date (YYYY-MM-DD)")


class UpdatePlanRequest(BaseModel):
    """Request to update plan weeks."""
    weeks: list[dict[str, Any]] = Field(..., description="Updated weeks array")


class ChatModifyRequest(BaseModel):
    """Request to modify plan via chat."""
    message: str = Field(..., description="User's modification request")
    conversationHistory: list[dict[str, str]] = Field(
        default=[], description="Previous chat messages"
    )


class ConfirmUpdateRequest(BaseModel):
    """Request to confirm plan update after analysis suggestion."""
    updateSuggestion: str = Field(..., description="The update suggestion from analysis")
    conversationHistory: list[dict[str, str]] = Field(
        default=[], description="Previous chat messages"
    )


class UpdateWithRecordsRequest(BaseModel):
    """Request to update plan based on workout records."""
    completionData: dict[str, Any] = Field(..., description="Completion analysis data")
    progress: dict[str, Any] = Field(..., description="Current plan progress")


class PlanResponse(BaseModel):
    """Training plan response."""
    id: str
    createdAt: int
    startDate: str
    userProfile: dict[str, Any]
    macroPlan: dict[str, Any] | None = None
    totalWeeks: int = 4
    weeks: list[dict[str, Any]]


class ChatModifyResponse(BaseModel):
    """Chat modification response."""
    message: str
    updatedPlan: list[dict[str, Any]] | None = None
    suggestUpdate: bool = False
    updateSuggestion: Optional[str] = None


# ========================================
# API Endpoints
# ========================================

@router.post("/generate", response_model=PlanResponse)
async def generate_plan(
    request: GeneratePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new 4-week training plan using AI.
    Also stores initial plan context for vector-based retrieval.
    """
    logger.info("Generating new training plan")
    
    try:
        ai_service = AIService()
        plan_data = await ai_service.generate_training_plan(request.userProfile)
        
        # Parse start date
        try:
            start_date = date.fromisoformat(request.startDate)
        except ValueError:
            start_date = date.today()
        
        # Save to database
        db_plan = TrainingPlan(
            start_date=start_date,
            user_profile=request.userProfile,
            macro_plan=plan_data["macroPlan"],
            total_weeks=plan_data["totalWeeks"],
            weeks=plan_data["weeks"],
        )
        db.add(db_plan)
        await db.flush()
        await db.refresh(db_plan)
        
        # Store initial plan context for vector retrieval
        try:
            agent_service = AgentService(db)
            await agent_service.store_initial_plan_context(
                plan_id=str(db_plan.id),
                plan_data={
                    "weeks": db_plan.weeks,
                    "userProfile": db_plan.user_profile,
                    "startDate": db_plan.start_date.isoformat(),
                }
            )
        except Exception as e:
            # Don't fail plan generation if context storage fails
            logger.warning("Failed to store initial plan context", error=str(e))
        
        logger.info("Plan generated successfully", plan_id=str(db_plan.id))
        
        return PlanResponse(
            id=str(db_plan.id),
            createdAt=int(db_plan.created_at.timestamp() * 1000),
            startDate=db_plan.start_date.isoformat(),
            userProfile=db_plan.user_profile,
            macroPlan=db_plan.macro_plan,
            totalWeeks=db_plan.total_weeks,
            weeks=db_plan.weeks,
        )
        
    except ValueError as e:
        logger.warning("Plan generation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Plan generation error", error=str(e))
        raise HTTPException(status_code=500, detail="计划生成失败，请重试")


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all training plans.
    """
    result = await db.execute(
        select(TrainingPlan).order_by(TrainingPlan.created_at.desc())
    )
    plans = result.scalars().all()
    
    return [
        PlanResponse(
            id=str(plan.id),
            createdAt=int(plan.created_at.timestamp() * 1000),
            startDate=plan.start_date.isoformat(),
            userProfile=plan.user_profile,
            macroPlan=plan.macro_plan,
            totalWeeks=plan.total_weeks,
            weeks=plan.weeks,
        )
        for plan in plans
    ]


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific training plan by ID.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    return PlanResponse(
        id=str(plan.id),
        createdAt=int(plan.created_at.timestamp() * 1000),
        startDate=plan.start_date.isoformat(),
        userProfile=plan.user_profile,
        macroPlan=plan.macro_plan,
        totalWeeks=plan.total_weeks,
        weeks=plan.weeks,
    )


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: UUID,
    request: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update training plan weeks.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    plan.weeks = request.weeks
    plan.updated_at = datetime.utcnow()
    
    await db.flush()
    
    logger.info("Plan updated", plan_id=str(plan_id))
    
    return PlanResponse(
        id=str(plan.id),
        createdAt=int(plan.created_at.timestamp() * 1000),
        startDate=plan.start_date.isoformat(),
        userProfile=plan.user_profile,
        macroPlan=plan.macro_plan,
        totalWeeks=plan.total_weeks,
        weeks=plan.weeks,
    )


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a training plan.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    await db.delete(plan)
    
    logger.info("Plan deleted", plan_id=str(plan_id))
    
    return {"message": "计划已删除"}


@router.post("/{plan_id}/chat", response_model=ChatModifyResponse)
async def chat_modify_plan(
    plan_id: UUID,
    request: ChatModifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Modify plan through natural language chat with AI.
    Uses LangGraph agent with vector context for enhanced responses.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    logger.info("Chat modify request", plan_id=str(plan_id))
    
    try:
        agent_service = AgentService(db)
        modification_result = await agent_service.modify_plan_with_chat(
            plan_id=str(plan_id),
            current_plan={
                "weeks": plan.weeks,
                "userProfile": plan.user_profile,
                "startDate": plan.start_date.isoformat(),
            },
            user_message=request.message,
            conversation_history=request.conversationHistory,
        )
        
        # If plan was updated, save to database
        if modification_result.get("updatedPlan"):
            plan.weeks = modification_result["updatedPlan"]
            plan.updated_at = datetime.utcnow()
            await db.flush()
            logger.info("Plan updated via chat", plan_id=str(plan_id))
        
        return ChatModifyResponse(
            message=modification_result["message"],
            updatedPlan=modification_result.get("updatedPlan"),
        )
        
    except Exception as e:
        logger.error("Chat modify error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/next-cycle", response_model=PlanResponse)
async def generate_next_cycle_api(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate the next cycle of detailed training content.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
        
    if not plan.macro_plan:
        raise HTTPException(status_code=400, detail="该计划没有宏观大纲，无法生成下一阶段内容")
        
    current_weeks_count = len(plan.weeks)
    if current_weeks_count >= plan.total_weeks:
        raise HTTPException(status_code=400, detail="计划已全部细化完成")
        
    try:
        ai_service = AIService()
        next_weeks = await ai_service.generate_next_cycle(
            user_profile=plan.user_profile,
            macro_plan=plan.macro_plan,
            current_weeks_count=current_weeks_count
        )
        
        # Append next weeks to current weeks
        updated_weeks = list(plan.weeks)
        updated_weeks.extend(next_weeks)
        
        plan.weeks = updated_weeks
        plan.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(plan)
        
        logger.info("Next cycle generated", plan_id=str(plan_id))
        
        return PlanResponse(
            id=str(plan.id),
            createdAt=int(plan.created_at.timestamp() * 1000),
            startDate=plan.start_date.isoformat(),
            userProfile=plan.user_profile,
            macroPlan=plan.macro_plan,
            totalWeeks=plan.total_weeks,
            weeks=plan.weeks,
        )
    except Exception as e:
        logger.error("Next cycle generation error", error=str(e))
        raise HTTPException(status_code=500, detail=f"生成下一阶段失败: {str(e)}")


@router.post("/{plan_id}/update", response_model=dict)
async def update_plan_with_records(
    plan_id: UUID,
    request: UpdateWithRecordsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update plan based on workout records analysis.
    Uses LangGraph agent with vector context for enhanced analysis.
    Returns completion scores, analysis, and updated plan.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    logger.info("Update plan with records", plan_id=str(plan_id))
    
    try:
        agent_service = AgentService(db)
        update_result = await agent_service.update_plan_with_records(
            plan_id=str(plan_id),
            plan={
                "weeks": plan.weeks,
                "userProfile": plan.user_profile,
                "startDate": plan.start_date.isoformat(),
            },
            completion_data=request.completionData,
            progress=request.progress,
        )
        
        return {
            "completionScores": update_result["completionScores"],
            "overallAnalysis": update_result["overallAnalysis"],
            "adjustmentSummary": update_result.get("adjustmentSummary", ""),
            "updatedWeeks": update_result["updatedWeeks"],
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Update with records error", error=str(e))
        raise HTTPException(status_code=500, detail="分析失败，请重试")


@router.post("/{plan_id}/confirm-update", response_model=ChatModifyResponse)
async def confirm_update_from_analysis(
    plan_id: UUID,
    request: ConfirmUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm and execute plan update after analysis suggestion.
    
    This endpoint is called when user confirms the update suggestion
    from record analysis (Agent B -> Agent A coordination).
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    logger.info("Confirm update from analysis", plan_id=str(plan_id))
    
    try:
        agent_service = AgentService(db)
        modification_result = await agent_service.handle_update_confirmation(
            plan_id=str(plan_id),
            plan_data={
                "weeks": plan.weeks,
                "userProfile": plan.user_profile,
                "startDate": plan.start_date.isoformat(),
            },
            update_suggestion=request.updateSuggestion,
            conversation_history=request.conversationHistory,
        )
        
        # If plan was updated, save to database
        if modification_result.get("updatedPlan"):
            plan.weeks = modification_result["updatedPlan"]
            plan.updated_at = datetime.utcnow()
            await db.flush()
            logger.info("Plan updated from analysis confirmation", plan_id=str(plan_id))
        
        return ChatModifyResponse(
            message=modification_result["message"],
            updatedPlan=modification_result.get("updatedPlan"),
        )
        
    except Exception as e:
        logger.error("Confirm update error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

