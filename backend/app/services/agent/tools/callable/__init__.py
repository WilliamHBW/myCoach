"""
Callable Tools - Tools that the agent can invoke during execution.

These tools allow the agent to fetch additional data:
- GetTrainingHistoryTool: Fetch user's training history
- GetCurrentPlanTool: Get the current training plan
- GetRecentRecordsTool: Get recent workout records
"""
from app.services.agent.tools.callable.training_history import GetTrainingHistoryTool
from app.services.agent.tools.callable.current_plan import GetCurrentPlanTool
from app.services.agent.tools.callable.recent_records import GetRecentRecordsTool

__all__ = [
    "GetTrainingHistoryTool",
    "GetCurrentPlanTool",
    "GetRecentRecordsTool",
]

