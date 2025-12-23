"""
LangGraph definitions for Coach Agent system.
Defines the graph structure and node connections for agent coordination.
"""
import uuid
from typing import Any, Optional, List
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.state import AgentState, AgentOutput, AgentAction, create_initial_state
from app.services.agents.plan_agent import PlanModificationAgent
from app.services.agents.analysis_agent import RecordAnalysisAgent
from app.services.context.manager import ContextManager
from app.models.context import ContentType
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoachAgentGraph:
    """
    Main orchestrator for the Coach Agent system.
    
    Manages:
    - Context retrieval and storage
    - Agent invocation
    - State management
    - Agent coordination (B -> A flow)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.context_manager = ContextManager(db)
        self.plan_agent = PlanModificationAgent()
        self.analysis_agent = RecordAnalysisAgent()
        
        # Build graphs
        self._plan_graph = self._build_plan_graph()
        self._analysis_graph = self._build_analysis_graph()
        self._update_graph = self._build_update_graph()
    
    def _build_plan_graph(self) -> StateGraph:
        """Build graph for plan modification workflow."""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("retrieve_context", self._retrieve_context_node)
        graph.add_node("modify_plan", self._plan_modification_node)
        graph.add_node("store_context", self._store_conversation_node)
        
        # Define edges
        graph.set_entry_point("retrieve_context")
        graph.add_edge("retrieve_context", "modify_plan")
        graph.add_edge("modify_plan", "store_context")
        graph.add_edge("store_context", END)
        
        return graph.compile()
    
    def _build_analysis_graph(self) -> StateGraph:
        """Build graph for record analysis workflow."""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("retrieve_context", self._retrieve_context_node)
        graph.add_node("analyze_record", self._analyze_record_node)
        graph.add_node("store_analysis", self._store_analysis_node)
        
        # Define edges
        graph.set_entry_point("retrieve_context")
        graph.add_edge("retrieve_context", "analyze_record")
        graph.add_edge("analyze_record", "store_analysis")
        graph.add_edge("store_analysis", END)
        
        return graph.compile()
    
    def _build_update_graph(self) -> StateGraph:
        """Build graph for plan update with records workflow."""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("retrieve_context", self._retrieve_context_node)
        graph.add_node("analyze_records", self._analyze_with_records_node)
        graph.add_node("store_plan", self._store_plan_context_node)
        
        # Define edges
        graph.set_entry_point("retrieve_context")
        graph.add_edge("retrieve_context", "analyze_records")
        graph.add_edge("analyze_records", "store_plan")
        graph.add_edge("store_plan", END)
        
        return graph.compile()
    
    # ========================================
    # Node implementations
    # ========================================
    
    async def _retrieve_context_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from vector store."""
        try:
            plan_id = state.get("plan_id")
            if not plan_id:
                return state
            
            # Determine query based on available data
            query = state.get("user_message", "")
            if not query and state.get("record_data"):
                record = state["record_data"]
                query = f"{record.get('type', '')} 训练 RPE {record.get('rpe', '')}"
            
            if not query:
                return state
            
            # Retrieve context
            context = await self.context_manager.retrieve_context(
                query=query,
                plan_id=uuid.UUID(plan_id) if plan_id else None,
                limit=5
            )
            
            state["retrieved_context"] = context
            
            logger.debug(
                "Context retrieved",
                plan_id=plan_id,
                context_length=len(context)
            )
            
            return state
            
        except Exception as e:
            logger.warning("Context retrieval failed", error=str(e))
            return state
    
    async def _plan_modification_node(self, state: AgentState) -> AgentState:
        """Execute plan modification agent."""
        return await self.plan_agent.process(state)
    
    async def _analyze_record_node(self, state: AgentState) -> AgentState:
        """Execute record analysis agent."""
        return await self.analysis_agent.analyze_record(state)
    
    async def _analyze_with_records_node(self, state: AgentState) -> AgentState:
        """Execute comprehensive record analysis for plan update."""
        return await self.analysis_agent.analyze_with_records(state)
    
    async def _store_conversation_node(self, state: AgentState) -> AgentState:
        """Store conversation in context."""
        try:
            plan_id = state.get("plan_id")
            if not plan_id or state.get("error"):
                return state
            
            user_message = state.get("user_message", "")
            response = state.get("response_message", "")
            
            if user_message and response:
                await self.context_manager.store_conversation_context(
                    plan_id=uuid.UUID(plan_id),
                    user_message=user_message,
                    assistant_response=response
                )
            
            # If plan was updated, store new plan context
            if state.get("updated_plan"):
                plan_data = state.get("plan_data", {})
                plan_data["weeks"] = state["updated_plan"]
                await self.context_manager.store_plan_context(
                    plan_id=uuid.UUID(plan_id),
                    plan_data=plan_data
                )
            
            return state
            
        except Exception as e:
            logger.warning("Failed to store conversation context", error=str(e))
            return state
    
    async def _store_analysis_node(self, state: AgentState) -> AgentState:
        """Store analysis result in context."""
        try:
            plan_id = state.get("plan_id")
            if not plan_id or state.get("error"):
                return state
            
            analysis = state.get("analysis_result", "")
            if analysis:
                await self.context_manager.store_analysis_context(
                    plan_id=uuid.UUID(plan_id),
                    analysis_text=analysis,
                    record_data=state.get("record_data")
                )
            
            return state
            
        except Exception as e:
            logger.warning("Failed to store analysis context", error=str(e))
            return state
    
    async def _store_plan_context_node(self, state: AgentState) -> AgentState:
        """Store updated plan in context."""
        try:
            plan_id = state.get("plan_id")
            if not plan_id or state.get("error"):
                return state
            
            if state.get("updated_plan"):
                plan_data = state.get("plan_data", {})
                plan_data["weeks"] = state["updated_plan"]
                await self.context_manager.store_plan_context(
                    plan_id=uuid.UUID(plan_id),
                    plan_data=plan_data
                )
            
            return state
            
        except Exception as e:
            logger.warning("Failed to store plan context", error=str(e))
            return state
    
    # ========================================
    # Public API methods
    # ========================================
    
    async def modify_plan(
        self,
        plan_id: str,
        plan_data: dict[str, Any],
        user_message: str,
        conversation_history: Optional[List[dict]] = None
    ) -> AgentOutput:
        """
        Modify training plan through natural language.
        
        Args:
            plan_id: Training plan ID
            plan_data: Current plan data
            user_message: User's modification request
            conversation_history: Previous conversation messages
            
        Returns:
            AgentOutput with response and optional updated plan
        """
        initial_state = create_initial_state(
            plan_id=plan_id,
            plan_data=plan_data,
            user_message=user_message,
            conversation_history=conversation_history,
        )
        
        final_state = await self._plan_graph.ainvoke(initial_state)
        
        return self.plan_agent.to_output(final_state)
    
    async def analyze_record(
        self,
        plan_id: Optional[str],
        record_id: str,
        record_data: dict[str, Any]
    ) -> AgentOutput:
        """
        Analyze a single workout record.
        
        Args:
            plan_id: Associated plan ID (optional)
            record_id: Workout record ID
            record_data: Workout record data
            
        Returns:
            AgentOutput with analysis and optional update suggestion
        """
        initial_state = create_initial_state(
            plan_id=plan_id,
            record_id=record_id,
            record_data=record_data,
        )
        
        final_state = await self._analysis_graph.ainvoke(initial_state)
        
        return self.analysis_agent.to_output(final_state)
    
    async def update_plan_with_records(
        self,
        plan_id: str,
        plan_data: dict[str, Any],
        completion_data: dict[str, Any],
        progress: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update training plan based on workout records.
        
        Args:
            plan_id: Training plan ID
            plan_data: Current plan data
            completion_data: Completion analysis data
            progress: Current plan progress
            
        Returns:
            Dict with completionScores, overallAnalysis, updatedWeeks
        """
        initial_state = create_initial_state(
            plan_id=plan_id,
            plan_data=plan_data,
            completion_data=completion_data,
            progress=progress,
        )
        
        final_state = await self._update_graph.ainvoke(initial_state)
        
        if final_state.get("error"):
            raise ValueError(final_state["error"])
        
        # Parse the analysis result which is JSON string
        import json
        result = json.loads(final_state.get("analysis_result", "{}"))
        
        return result
    
    async def handle_update_confirmation(
        self,
        plan_id: str,
        plan_data: dict[str, Any],
        update_suggestion: str,
        conversation_history: Optional[List[dict]] = None
    ) -> AgentOutput:
        """
        Handle user's confirmation to update plan after analysis suggestion.
        
        This triggers Agent A (PlanModificationAgent) with the suggestion.
        
        Args:
            plan_id: Training plan ID
            plan_data: Current plan data
            update_suggestion: The suggestion from Agent B
            conversation_history: Previous conversation
            
        Returns:
            AgentOutput with modified plan
        """
        # Create a message that includes the suggestion context
        user_message = f"根据之前的训练分析建议，请帮我调整训练计划：\n\n{update_suggestion}"
        
        return await self.modify_plan(
            plan_id=plan_id,
            plan_data=plan_data,
            user_message=user_message,
            conversation_history=conversation_history
        )

