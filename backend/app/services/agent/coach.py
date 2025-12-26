"""
CoachAgent - Unified AI Coach Agent.

The main orchestrator that handles all AI-powered operations:
- Training plan generation
- Plan modification through chat
- Workout record analysis

Uses LangGraph for state management and supports streaming responses.
"""
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent.state import (
    AgentState,
    AgentRequest,
    AgentResponse,
    ActionType,
    create_initial_state,
    MemoryUpdate,
)
from app.services.agent.router import ActionRouter
from app.services.agent.actions import GeneratePlanAction, ModifyPlanAction, AnalyzeRecordAction
from app.services.memory import MemoryManager
from app.services.agent.tools.callable import (
    GetTrainingHistoryTool,
    GetCurrentPlanTool,
    GetRecentRecordsTool,
)
from app.core.logging import get_logger, AgentDecisionLogger, DecisionType

logger = get_logger(__name__)
decision_logger = AgentDecisionLogger(logger)


class CoachAgent:
    """
    Unified Coach Agent for all AI-powered operations.
    
    Coordinates:
    - Memory retrieval and storage
    - Action routing and execution
    - Tool calling
    - Response streaming
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory = MemoryManager(db)
        self.router = ActionRouter(db=db)  # Pass db for actions that need it
        
        # Initialize tools
        self._tools = {
            "get_training_history": GetTrainingHistoryTool(db),
            "get_current_plan": GetCurrentPlanTool(db),
            "get_recent_records": GetRecentRecordsTool(db),
        }
        
        # Build LangGraph
        self._graph = self._build_graph()
    
    def _build_graph(self) -> Any:
        """
        Build the unified LangGraph for agent execution.
        
        Graph structure:
        retrieve_memory -> route_action -> [check_tools -> call_tool]* -> execute_action -> update_memory -> END
        """
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("retrieve_memory", self._retrieve_memory_node)
        graph.add_node("route_action", self._route_action_node)
        graph.add_node("check_tools", self._check_tools_node)
        graph.add_node("call_tool", self._call_tool_node)
        graph.add_node("execute_action", self._execute_action_node)
        graph.add_node("update_memory", self._update_memory_node)
        
        # Set entry point
        graph.set_entry_point("retrieve_memory")
        
        # Define edges
        graph.add_edge("retrieve_memory", "route_action")
        
        # Conditional edge: route_action -> check_tools or execute_action
        graph.add_conditional_edges(
            "route_action",
            self._should_check_tools,
            {
                "check_tools": "check_tools",
                "execute": "execute_action",
            }
        )
        
        # Conditional edge: check_tools -> call_tool or execute_action
        graph.add_conditional_edges(
            "check_tools",
            self._has_pending_tools,
            {
                "call_tool": "call_tool",
                "execute": "execute_action",
            }
        )
        
        # After calling a tool, check for more tools
        graph.add_edge("call_tool", "check_tools")
        
        # After execution, update memory
        graph.add_edge("execute_action", "update_memory")
        
        # End after memory update
        graph.add_edge("update_memory", END)
        
        return graph.compile()
    
    # ========================================
    # Graph Nodes
    # ========================================
    
    async def _retrieve_memory_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from all memory layers."""
        plan_id = state.get("plan_id")
        session_id = state.get("session_id", "")
        trace = state.get("_trace")
        
        # Determine query for semantic search
        query = state.get("user_message", "")
        if not query and state.get("record_data"):
            record = state["record_data"]
            query = f"{record.get('type', '')} 训练 RPE {record.get('rpe', '')}"
        
        if not query:
            query = state.get("action", "training")
        
        try:
            context = await self.memory.get_context(
                plan_id=plan_id,
                query=query,
                session_id=session_id
            )
            
            # Update state with retrieved context
            context_text = context.format_for_prompt()
            state["long_term_context"] = context_text
            state["working_context"] = context.working
            state["user_preferences"] = context.preferences
            
            # Log decision
            if trace:
                trace.log_memory_retrieval(
                    has_long_term=bool(context.long_term),
                    has_preferences=bool(context.preferences),
                    context_length=len(context_text),
                    query=query
                )
            
            logger.debug(
                "Retrieved memory context",
                plan_id=plan_id,
                has_long_term=bool(context.long_term),
                has_preferences=bool(context.preferences)
            )
            
        except Exception as e:
            logger.warning("Memory retrieval failed", error=str(e))
            if trace:
                trace.log_decision(
                    DecisionType.MEMORY_RETRIEVED,
                    "retrieve_memory",
                    decision="Failed to retrieve",
                    reasoning=str(e)
                )
        
        return state
    
    async def _route_action_node(self, state: AgentState) -> AgentState:
        """Route to the appropriate action."""
        trace = state.get("_trace")
        
        try:
            action_type = self.router.route(state)
            state["action"] = action_type
            
            # Determine routing reasoning
            reasoning = self._get_routing_reasoning(state, action_type)
            
            if trace:
                trace.log_action_routing(
                    action=action_type,
                    reasoning=reasoning,
                    alternatives=list(self.router._actions.keys())
                )
            
            logger.debug("Routed to action", action=action_type)
            
        except Exception as e:
            logger.error("Routing failed", error=str(e))
            state["error"] = str(e)
            if trace:
                trace.log_error(f"Routing failed: {str(e)}")
        
        return state
    
    def _get_routing_reasoning(self, state: AgentState, action: str) -> str:
        """Generate reasoning for action routing."""
        if state.get("record_data"):
            return "Record data present -> analyze single record"
        
        if state.get("user_message") and state.get("plan_data"):
            return "User message with existing plan -> modify plan through chat"
        
        if state.get("user_profile"):
            return "User profile present -> generate new plan"
        
        return f"Routed to {action} based on request action type"
    
    async def _check_tools_node(self, state: AgentState) -> AgentState:
        """Check which tools need to be called."""
        if state.get("error"):
            return state
        
        action_type = state.get("action", "")
        action = self.router.get_action(action_type)
        trace = state.get("_trace")
        
        try:
            pending_tools = await action.get_required_tools(state)
            
            # Filter out already-called tools
            called_tools = list(state.get("tool_results", {}).keys())
            remaining = [t for t in pending_tools if t not in called_tools]
            
            state["pending_tools"] = remaining
            
            if trace:
                trace.log_tool_check(
                    required_tools=pending_tools,
                    already_called=called_tools,
                    pending=remaining
                )
            
            logger.debug("Checked tools", pending=remaining)
            
        except Exception as e:
            logger.warning("Tool check failed", error=str(e))
            state["pending_tools"] = []
        
        return state
    
    async def _call_tool_node(self, state: AgentState) -> AgentState:
        """Call the next pending tool."""
        pending = state.get("pending_tools", [])
        trace = state.get("_trace")
        
        if not pending:
            return state
        
        tool_name = pending[0]
        remaining = pending[1:]
        
        try:
            tool = self._tools.get(tool_name)
            if tool:
                result = await tool.execute(state=state)
                
                tool_results = dict(state.get("tool_results", {}))
                tool_results[tool_name] = result
                
                state["tool_results"] = tool_results
                state["pending_tools"] = remaining
                
                # Generate result summary
                result_summary = self._summarize_tool_result(tool_name, result)
                
                if trace:
                    trace.log_tool_call(
                        tool_name=tool_name,
                        success=True,
                        result_summary=result_summary
                    )
                
                logger.debug("Called tool", tool=tool_name, has_result=bool(result))
            else:
                logger.warning("Tool not found", tool=tool_name)
                state["pending_tools"] = remaining
                
                if trace:
                    trace.log_tool_call(
                        tool_name=tool_name,
                        success=False,
                        result_summary="Tool not registered"
                    )
                
        except Exception as e:
            logger.error("Tool call failed", tool=tool_name, error=str(e))
            state["pending_tools"] = remaining
            
            if trace:
                trace.log_tool_call(
                    tool_name=tool_name,
                    success=False,
                    result_summary=f"Error: {str(e)}"
                )
        
        return state
    
    def _summarize_tool_result(self, tool_name: str, result: Any) -> str:
        """Summarize tool result for logging."""
        if result is None:
            return "No result"
        
        if isinstance(result, list):
            return f"Returned {len(result)} items"
        
        if isinstance(result, dict):
            keys = list(result.keys())[:3]
            return f"Dict with keys: {keys}"
        
        return f"Result type: {type(result).__name__}"
    
    async def _execute_action_node(self, state: AgentState) -> AgentState:
        """Execute the routed action."""
        if state.get("error"):
            return state
        
        action_type = state.get("action", "")
        trace = state.get("_trace")
        
        try:
            result = await self.router.execute(state)
            
            # Log execution result
            if trace:
                output_summary = self._summarize_action_output(result)
                trace.log_action_execution(
                    action=action_type,
                    success=not result.get("error"),
                    output_summary=output_summary,
                    has_plan_update=bool(result.get("updated_plan")),
                    suggest_update=result.get("suggest_update", False)
                )
            
            return result
            
        except Exception as e:
            logger.error("Action execution failed", action=action_type, error=str(e))
            state["error"] = str(e)
            state["response_message"] = "抱歉，处理请求时出现错误。请稍后重试。"
            
            if trace:
                trace.log_action_execution(
                    action=action_type,
                    success=False,
                    output_summary=f"Error: {str(e)}"
                )
            
            return state
    
    def _summarize_action_output(self, state: AgentState) -> str:
        """Summarize action output for logging."""
        parts = []
        
        if state.get("error"):
            return f"Error: {state['error'][:50]}"
        
        if state.get("updated_plan"):
            parts.append(f"{len(state['updated_plan'])} weeks updated")
        
        if state.get("analysis_result"):
            parts.append(f"Analysis: {len(state['analysis_result'])} chars")
        
        if state.get("suggest_update"):
            parts.append("Suggests plan update")
        
        if state.get("response_message"):
            msg_len = len(state["response_message"])
            parts.append(f"Response: {msg_len} chars")
        
        return " | ".join(parts) if parts else "Completed"
    
    async def _update_memory_node(self, state: AgentState) -> AgentState:
        """Update memory with results."""
        if state.get("error"):
            return state
        
        plan_id = state.get("plan_id")
        session_id = state.get("session_id", "")
        action_type = state.get("action", "")
        trace = state.get("_trace")
        
        if not plan_id:
            if trace:
                trace.log_memory_update([])
            return state
        
        updated_types = []
        
        try:
            # Store conversation for modify actions
            if action_type == ActionType.MODIFY_PLAN.value:
                user_message = state.get("user_message", "")
                response = state.get("response_message", "")
                
                if user_message and response:
                    await self.memory.store_conversation(
                        plan_id=plan_id,
                        session_id=session_id,
                        user_message=user_message,
                        assistant_response=response
                    )
                    updated_types.append("conversation")
                
                # Update plan context if modified
                if state.get("updated_plan"):
                    plan_data = state.get("plan_data", {})
                    plan_data["weeks"] = state["updated_plan"]
                    await self.memory.store_plan_context(plan_id, plan_data)
                    updated_types.append("plan_context")
            
            # Store analysis for analyze actions
            elif action_type == ActionType.ANALYZE_RECORD.value:
                analysis = state.get("analysis_result", "")
                if analysis:
                    await self.memory.store_analysis(
                        plan_id=plan_id,
                        analysis_text=analysis,
                        record_data=state.get("record_data")
                    )
                    updated_types.append("analysis")
            
            # Store generated plan
            elif action_type == ActionType.GENERATE_PLAN.value:
                if state.get("updated_plan"):
                    plan_data = state.get("tool_results", {}).get("plan_data", {})
                    if plan_data:
                        # Plan ID will be assigned after DB insert
                        updated_types.append("plan_pending")
            
            if trace:
                trace.log_memory_update(updated_types)
            
            logger.debug("Updated memory", action=action_type, updated=updated_types)
            
        except Exception as e:
            logger.warning("Memory update failed", error=str(e))
            if trace:
                trace.log_decision(
                    DecisionType.MEMORY_UPDATED,
                    "update_memory",
                    decision="Failed",
                    reasoning=str(e)
                )
        
        return state
    
    # ========================================
    # Conditional Edge Functions
    # ========================================
    
    def _should_check_tools(self, state: AgentState) -> str:
        """Determine if we should check for tools to call."""
        if state.get("error"):
            return "execute"
        
        action_type = state.get("action", "")
        
        # Only certain actions use tools
        if action_type in [
            ActionType.GENERATE_PLAN.value,
            ActionType.ANALYZE_RECORD.value,
        ]:
            return "check_tools"
        
        return "execute"
    
    def _has_pending_tools(self, state: AgentState) -> str:
        """Check if there are pending tools to call."""
        pending = state.get("pending_tools", [])
        return "call_tool" if pending else "execute"
    
    # ========================================
    # Public API
    # ========================================
    
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Execute an agent request.
        
        Args:
            request: AgentRequest with action parameters
            
        Returns:
            AgentResponse with results
        """
        logger.info(
            "CoachAgent: Executing request",
            action=request.action.value,
            plan_id=request.plan_id,
            session_id=request.session_id
        )
        
        # Create initial state with trace context
        initial_state = create_initial_state(request)
        
        # Use decision logger to trace execution
        with decision_logger.trace(
            session_id=request.session_id,
            plan_id=request.plan_id,
            action_type=request.action.value
        ) as trace:
            # Store trace in state for nodes to access
            initial_state["_trace"] = trace
            
            # Log request received
            trace.log_decision(
                DecisionType.REQUEST_RECEIVED,
                "entry",
                decision=f"Processing {request.action.value}",
                reasoning=self._get_request_reasoning(request),
                has_user_message=bool(request.user_message),
                has_record_data=bool(request.record_data),
            )
            
            # Run the graph
            final_state = await self._graph.ainvoke(initial_state)
            
            # Log final response
            trace.log_decision(
                DecisionType.RESPONSE_GENERATED,
                "exit",
                decision="Success" if not final_state.get("error") else "Failed",
                reasoning=self._get_response_summary(final_state),
                has_plan_update=bool(final_state.get("updated_plan")),
                suggest_update=final_state.get("suggest_update", False),
            )
        
        # Convert to response
        return self._state_to_response(request.action, final_state)
    
    def _get_request_reasoning(self, request: AgentRequest) -> str:
        """Generate reasoning text for the request."""
        parts = []
        
        if request.action == ActionType.GENERATE_PLAN:
            goal = request.user_profile.get("goal", "") if request.user_profile else ""
            parts.append(f"Generate plan for goal: {goal[:50]}" if goal else "Generate new plan")
        
        elif request.action == ActionType.MODIFY_PLAN:
            msg = request.user_message or ""
            parts.append(f"Modify request: {msg[:50]}..." if len(msg) > 50 else f"Modify request: {msg}")
        
        elif request.action == ActionType.ANALYZE_RECORD:
            record_type = request.record_data.get("type", "") if request.record_data else ""
            parts.append(f"Analyze {record_type} workout record")
        
        return " | ".join(parts) if parts else "Processing request"
    
    def _get_response_summary(self, state: AgentState) -> str:
        """Generate summary of the response."""
        if state.get("error"):
            return f"Error: {state['error'][:100]}"
        
        parts = []
        
        if state.get("updated_plan"):
            weeks_count = len(state["updated_plan"])
            parts.append(f"Updated {weeks_count} weeks")
        
        if state.get("analysis_result"):
            parts.append(f"Analysis: {len(state['analysis_result'])} chars")
        
        if state.get("suggest_update"):
            parts.append("Suggested plan update")
        
        if state.get("response_message"):
            msg = state["response_message"]
            parts.append(f"Message: {msg[:50]}..." if len(msg) > 50 else f"Message: {msg}")
        
        return " | ".join(parts) if parts else "Completed"
    
    async def execute_stream(
        self,
        request: AgentRequest
    ) -> AsyncIterator[str]:
        """
        Execute an agent request with streaming output.
        
        Args:
            request: AgentRequest with action parameters
            
        Yields:
            Response chunks as they're generated
        """
        logger.info(
            "CoachAgent: Executing streaming request",
            action=request.action.value,
            plan_id=request.plan_id
        )
        
        # Create initial state
        initial_state = create_initial_state(request)
        
        # Retrieve memory first
        state = await self._retrieve_memory_node(initial_state)
        state = await self._route_action_node(state)
        
        if state.get("error"):
            yield f"错误: {state['error']}"
            return
        
        # Get the action and stream its execution
        action_type = state.get("action", "")
        action = self.router.get_action(action_type)
        
        try:
            async for chunk in action.execute_stream(state):
                yield chunk
                
        except Exception as e:
            yield f"\n\n错误: {str(e)}"
    
    def _state_to_response(
        self,
        action: ActionType,
        state: AgentState
    ) -> AgentResponse:
        """Convert final state to AgentResponse."""
        if state.get("error"):
            return AgentResponse(
                success=False,
                message=state.get("response_message", ""),
                error=state["error"]
            )
        
        response = AgentResponse(
            success=True,
            message=state.get("response_message", "")
        )
        
        # Add action-specific fields
        if action == ActionType.GENERATE_PLAN:
            plan_data = state.get("tool_results", {}).get("plan_data", {})
            response.plan = plan_data
            response.updated_weeks = state.get("updated_plan")
        
        elif action == ActionType.MODIFY_PLAN:
            response.updated_weeks = state.get("updated_plan")
        
        elif action == ActionType.ANALYZE_RECORD:
            response.analysis = state.get("analysis_result")
            response.suggest_update = state.get("suggest_update", False)
            response.update_suggestion = state.get("update_suggestion")
        
        return response
    
    # ========================================
    # Convenience Methods
    # ========================================
    
    async def generate_plan(
        self,
        user_profile: Dict[str, Any],
        start_date: str,
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Generate a new training plan.
        
        Args:
            user_profile: User questionnaire data
            start_date: Plan start date
            session_id: Optional session ID
            
        Returns:
            AgentResponse with generated plan
        """
        request = AgentRequest(
            action=ActionType.GENERATE_PLAN,
            session_id=session_id or str(uuid.uuid4()),
            user_profile=user_profile,
            start_date=start_date,
        )
        return await self.execute(request)
    
    async def modify_plan(
        self,
        plan_id: str,
        plan_data: Dict[str, Any],
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Modify an existing plan through chat.
        
        Args:
            plan_id: Plan ID
            plan_data: Current plan data
            user_message: User's modification request
            conversation_history: Previous messages
            session_id: Optional session ID
            
        Returns:
            AgentResponse with modification result
        """
        request = AgentRequest(
            action=ActionType.MODIFY_PLAN,
            session_id=session_id or str(uuid.uuid4()),
            plan_id=plan_id,
            plan_data=plan_data,
            user_message=user_message,
            conversation_history=conversation_history,
        )
        return await self.execute(request)
    
    async def analyze_record(
        self,
        plan_id: Optional[str],
        record_id: str,
        record_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Analyze a workout record.
        
        Args:
            plan_id: Associated plan ID
            record_id: Record ID
            record_data: Record data
            session_id: Optional session ID
            
        Returns:
            AgentResponse with analysis
        """
        request = AgentRequest(
            action=ActionType.ANALYZE_RECORD,
            session_id=session_id or str(uuid.uuid4()),
            plan_id=plan_id,
            record_id=record_id,
            record_data=record_data,
        )
        return await self.execute(request)
    
    async def store_initial_plan_context(
        self,
        plan_id: str,
        plan_data: Dict[str, Any]
    ) -> None:
        """
        Store initial plan context after generation.
        
        Args:
            plan_id: Plan ID
            plan_data: Plan data to store
        """
        await self.memory.store_plan_context(plan_id, plan_data)

