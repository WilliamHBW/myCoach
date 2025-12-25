"""
Training Plans API endpoints.
"""
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.plan import TrainingPlan
from app.models.record import WorkoutRecord
from app.services.agent import CoachAgent, ActionType, AgentRequest
from app.services.external import ExportService

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
    stream: bool = Field(default=False, description="Enable streaming response")


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
    Generate a new training plan using AI CoachAgent.
    Also stores initial plan context for vector-based retrieval.
    """
    logger.info("Generating new training plan")
    
    try:
        agent = CoachAgent(db)
        result = await agent.generate_plan(
            user_profile=request.userProfile,
            start_date=request.startDate,
        )
        
        if not result.success:
            raise ValueError(result.error or "Plan generation failed")
        
        plan_data = result.plan or {}
        
        # Parse start date
        try:
            start_date = date.fromisoformat(request.startDate)
        except ValueError:
            start_date = date.today()
        
        # Save to database
        db_plan = TrainingPlan(
            start_date=start_date,
            user_profile=request.userProfile,
            macro_plan=plan_data.get("macroPlan"),
            total_weeks=plan_data.get("totalWeeks", 4),
            weeks=plan_data.get("weeks", result.updated_weeks or []),
        )
        db.add(db_plan)
        await db.flush()
        await db.refresh(db_plan)
        
        # Store initial plan context for vector retrieval
        try:
            await agent.store_initial_plan_context(
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
    Uses CoachAgent with vector context for enhanced responses.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    logger.info("Chat modify request", plan_id=str(plan_id))
    
    try:
        agent = CoachAgent(db)
        modification_result = await agent.modify_plan(
            plan_id=str(plan_id),
            plan_data={
                "weeks": plan.weeks,
                "userProfile": plan.user_profile,
                "startDate": plan.start_date.isoformat(),
            },
            user_message=request.message,
            conversation_history=request.conversationHistory,
        )
        
        # If plan was updated, save to database
        if modification_result.updated_weeks:
            plan.weeks = modification_result.updated_weeks
            plan.updated_at = datetime.utcnow()
            await db.flush()
            logger.info("Plan updated via chat", plan_id=str(plan_id))
        
        return ChatModifyResponse(
            message=modification_result.message,
            updatedPlan=modification_result.updated_weeks,
        )
        
    except Exception as e:
        logger.error("Chat modify error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/chat/stream")
async def chat_modify_plan_stream(
    plan_id: UUID,
    request: ChatModifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Modify plan through natural language chat with streaming response.
    
    Returns Server-Sent Events (SSE) stream.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    logger.info("Chat modify stream request", plan_id=str(plan_id))
    
    agent = CoachAgent(db)
    
    async def generate():
        try:
            stream_request = AgentRequest(
                action=ActionType.MODIFY_PLAN,
                plan_id=str(plan_id),
                plan_data={
                    "weeks": plan.weeks,
                    "userProfile": plan.user_profile,
                    "startDate": plan.start_date.isoformat(),
                },
                user_message=request.message,
                conversation_history=request.conversationHistory,
                stream=True,
            )
            
            async for chunk in agent.execute_stream(stream_request):
                yield f"data: {chunk}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error("Streaming error", error=str(e))
            yield f"data: 错误: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


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
        from app.services.agent.actions.generate_plan import GeneratePlanAction
        
        action = GeneratePlanAction()
        next_result = await action.generate_next_cycle(
            user_profile=plan.user_profile,
            macro_plan=plan.macro_plan,
            current_weeks_count=current_weeks_count
        )
        
        if not next_result.get("success"):
            raise ValueError(next_result.get("error", "Generation failed"))
        
        next_weeks = next_result["data"]["weeks"]
        
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


@router.get("/{plan_id}/export/ical")
async def export_plan_to_ical(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Export training plan to iCal (.ics) format.
    
    Downloads an iCal file that can be imported into
    Google Calendar, Apple Calendar, Outlook, etc.
    """
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    logger.info("Exporting plan to iCal", plan_id=str(plan_id))
    
    try:
        export_service = ExportService()
        
        ical_content = export_service.export_to_ical(
            plan_data={"weeks": plan.weeks},
            start_date=plan.start_date,
            calendar_name=f"训练计划 - {plan.user_profile.get('goal', '健身')}"
        )
        
        filename = export_service.get_ical_filename(str(plan_id))
        content_type = export_service.get_ical_content_type()
        
        return Response(
            content=ical_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error("iCal export error", error=str(e))
        raise HTTPException(status_code=500, detail="导出失败，请重试")
