"""
Agent Actions - Task-specific action implementations.

Each action encapsulates the logic for a specific task type:
- GeneratePlanAction: Create new training plans
- ModifyPlanAction: Modify existing plans through chat
- AnalyzeRecordAction: Analyze workout records
"""
from app.services.agent.actions.base import BaseAction, Tool
from app.services.agent.actions.generate_plan import GeneratePlanAction
from app.services.agent.actions.modify_plan import ModifyPlanAction
from app.services.agent.actions.analyze_record import AnalyzeRecordAction

__all__ = [
    "BaseAction",
    "Tool",
    "GeneratePlanAction",
    "ModifyPlanAction",
    "AnalyzeRecordAction",
]

