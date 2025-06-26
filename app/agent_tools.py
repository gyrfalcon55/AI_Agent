# app/agent_tools.py
import datetime
from typing import List, Optional
from langchain.tools import tool
from . import google_calendar # Import our google_calendar module
import pytz # for timezone handling

# Initialize Google Calendar Service once
# IMPORTANT: This will trigger the OAuth flow if token.pickle doesn't exist
# Make sure credentials.json is in the project root as discussed.
print("Initializing Google Calendar Service...")
calendar_service = google_calendar.get_calendar_service()
print("Google Calendar Service Initialized.")

@tool
def check_calendar_availability_tool(
    start_time_str: str,
    end_time_str: str,
    timezone_str: str = "Asia/Kolkata" # Default timezone
) -> List[dict]:
    """
    Checks for free/busy times in the user's primary calendar within a given range.
    Input dates and times should be in a parsable format (e.g., 'YYYY-MM-DDTHH:MM:SS').
    The function handles timezone conversion for the query.

    Args:
        start_time_str: The start datetime string (e.g., "2025-06-25T10:00:00").
        end_time_str: The end datetime string (e.g., "2025-06-25T11:00:00").
        timezone_str: The IANA timezone string (e.g., "America/New_York", "Asia/Kolkata").

    Returns:
        A list of dictionaries, where each dictionary represents a busy period
        with 'start' and 'end' keys (e.g., [{'start': '...', 'end': '...'}]).
        Returns an empty list if no busy periods or on error.
    """
    try:
        target_tz = pytz.timezone(timezone_str)
        start_time = datetime.datetime.fromisoformat(start_time_str).astimezone(target_tz)
        end_time = datetime.datetime.fromisoformat(end_time_str).astimezone(target_tz)

        # Ensure start_time and end_time are timezone-aware if they aren't already
        if start_time.tzinfo is None:
            start_time = target_tz.localize(start_time)
        if end_time.tzinfo is None:
            end_time = target_tz.localize(end_time)

        busy_periods = google_calendar.check_calendar_availability(
            calendar_service, start_time, end_time
        )
        return busy_periods
    except Exception as e:
        print(f"Error in check_calendar_availability_tool: {e}")
        return []

@tool
def create_calendar_event_tool(
    summary: str,
    description: str,
    start_time_str: str,
    end_time_str: str,
    attendees: Optional[List[str]] = None,
    timezone_str: str = "Asia/Kolkata" # Default timezone
) -> dict:
    """
    Creates an event on the user's primary Google Calendar.
    Input dates and times should be in a parsable format (e.g., 'YYYY-MM-DDTHH:MM:SS').
    The function handles timezone conversion for the event creation.

    Args:
        summary: The title of the event.
        description: A detailed description of the event.
        start_time_str: The start datetime string (e.g., "2025-06-25T10:00:00").
        end_time_str: The end datetime string (e.g., "2025-06-25T11:00:00").
        attendees: An optional list of email addresses for attendees.
        timezone_str: The IANA timezone string (e.g., "America/New_York", "Asia/Kolkata").

    Returns:
        A dictionary representing the created event (e.g., {'htmlLink': '...'}),
        or None if the event creation failed.
    """
    try:
        target_tz = pytz.timezone(timezone_str)
        start_time = datetime.datetime.fromisoformat(start_time_str).astimezone(target_tz)
        end_time = datetime.datetime.fromisoformat(end_time_str).astimezone(target_tz)

        if start_time.tzinfo is None:
            start_time = target_tz.localize(start_time)
        if end_time.tzinfo is None:
            end_time = target_tz.localize(end_time)

        event = google_calendar.create_calendar_event(
            calendar_service, summary, description, start_time, end_time, attendees
        )
        return event if event else {}
    except Exception as e:
        print(f"Error in create_calendar_event_tool: {e}")
        return {}

# List of all tools
agent_tools = [check_calendar_availability_tool, create_calendar_event_tool]