# app/agent_state.py
from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage

class AgentState(TypedDict):
    """
    Represents the state of our conversational agent.

    Attributes:
        messages: A list of messages forming the conversation history.
        current_plan: A string representing the agent's current understanding
                      of the user's request and the next action to take.
        calendar_query_start: Extracted start time for a calendar query.
        calendar_query_end: Extracted end time for a calendar query.
        event_summary: Summary for a new event.
        event_description: Description for a new event.
        event_start_time: Start time for a new event.
        event_end_time: End time for a new event.
        event_attendees: List of attendees for a new event.
        availability_results: Results from a calendar availability check.
        booking_status: Status of a booking attempt (e.g., "success", "failed", "pending_confirmation").
        tool_output: Output from the last tool execution.
        error_message: Any error message encountered.
    """
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    current_plan: str
    calendar_query_start: str
    calendar_query_end: str
    event_summary: str
    event_description: str
    event_start_time: str
    event_end_time: str
    event_attendees: List[str]
    availability_results: List[dict]
    booking_status: str
    tool_output: str
    error_message: str