# app/google_calendar.py
import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import pytz # Make sure you have installed pytz: pip install pytz

# If modifying these scopes, delete the file token.pickle.
# This scope allows full access to manage calendars, which is needed for booking.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- Start of the crucial path handling ---
# Get the absolute path of the directory where the current script (google_calendar.py) is located.
# This ensures that no matter where the main application is run from, this script
# can find its related files ('credentials.json' and 'token.pickle').
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the absolute path to 'credentials.json'.
# Assuming 'credentials.json' is in the same directory as 'google_calendar.py' (i.e., 'app/' directory).
CREDENTIALS_FILE_PATH = os.path.join(current_script_dir, 'credentials.json')

# Construct the absolute path for 'token.pickle'.
# This ensures 'token.pickle' is also saved and loaded from the 'app/' directory.
TOKEN_FILE_PATH = os.path.join(current_script_dir, 'token.pickle')
# --- End of the crucial path handling ---


def get_calendar_service():
    """
    Authenticates with Google Calendar API.
    It attempts to load saved credentials from 'token.pickle'.
    If no valid credentials exist, it initiates the OAuth 2.0 flow
    using 'credentials.json' (which should be in the same directory).
    The generated token is then saved to 'token.pickle' for future use.
    """
    creds = None
    
    # Check if a token file already exists at the specified path
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials or they are expired/invalid, initiate the flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh token if expired
            creds.refresh(Request())
        else:
            # Use the absolute path for 'credentials.json'
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE_PATH, SCOPES)
            # 'port=0' lets it pick an available port for the local server authentication.
            # If you consistently face "localhost refused to connect" issues,
            # you can try a specific, less common port like `port=8888`.
            creds = flow.run_local_server(port=0) 
        
        # Save the credentials for the next run to the specified path
        with open(TOKEN_FILE_PATH, 'wb') as token:
            pickle.dump(creds, token)

    # Build and return the Google Calendar service object
    service = build('calendar', 'v3', credentials=creds)
    return service

def check_calendar_availability(service, start_time: datetime.datetime, end_time: datetime.datetime):
    """
    Checks for free/busy times in the user's primary calendar within a given range.
    
    Args:
        service: An authenticated Google Calendar API service object.
        start_time: A timezone-aware datetime object marking the start of the query range.
        end_time: A timezone-aware datetime object marking the end of the query range.

    Returns:
        A list of dictionaries, where each dictionary represents a busy period
        with 'start' and 'end' keys (e.g., [{'start': '2025-06-25T10:00:00Z', 'end': '2025-06-25T11:00:00Z'}]).
        Returns an empty list if no busy periods or on error.
    """
    try:
        body = {
            "timeMin": start_time.isoformat(), # ISO format includes timezone information
            "timeMax": end_time.isoformat(),
            "items": [{"id": "primary"}] # Query the user's primary calendar
        }
        events_result = service.freebusy().query(body=body).execute()
        
        # Extract busy periods from the primary calendar's response
        busy_periods = events_result.get('calendars', {}).get('primary', {}).get('busy', [])
        return busy_periods
    except HttpError as error:
        print(f"An error occurred while checking availability: {error}")
        return []

def create_calendar_event(service, summary: str, description: str, start_time: datetime.datetime, end_time: datetime.datetime, attendees: list = None):
    """
    Creates an event on the user's primary Google Calendar.
    
    Args:
        service: An authenticated Google Calendar API service object.
        summary: The title of the event.
        description: A detailed description of the event.
        start_time: A timezone-aware datetime object for the event's start.
        end_time: A timezone-aware datetime object for the event's end.
        attendees: An optional list of email addresses for attendees.

    Returns:
        A dictionary representing the created event (e.g., {'htmlLink': '...'}),
        or None if the event creation failed.
    """
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(), # ISO format includes timezone information
            'timeZone': 'Asia/Kolkata', # Default to India timezone (Visakhapatnam)
        },
        'end': {
            'dateTime': end_time.isoformat(), # ISO format includes timezone information
            'timeZone': 'Asia/Kolkata', # Default to India timezone (Visakhapatnam)
        },
        'reminders': {
            'useDefault': True, # Use default reminders set by the user in Google Calendar
        },
    }

    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]

    try:
        # Insert the event into the primary calendar
        # ADD sendNotifications=True to send invitations to attendees
        event = service.events().insert(
            calendarId='primary', 
            body=event,
            sendNotifications=True # <--- THIS LINE WAS ADDED/MODIFIED
        ).execute()
        print(f"Event created: {event.get('htmlLink')}")
        return event
    except HttpError as error:
        print(f"An error occurred while creating event: {error}")
        return None

# Example usage (for testing this module independently if needed)
if __name__ == '__main__':
    # IMPORTANT: Run this file directly ONCE to generate token.pickle.
    # When you run this, a browser window will open asking you to log in
    # with your Google account and grant permissions.
    # After successful authentication, token.pickle will be created in the 'app/' directory.
    
    print("Attempting to get Google Calendar service...")
    service = get_calendar_service()
    print("Google Calendar service initialized and token.pickle created (if not present).")

    # Define a timezone object for Asia/Kolkata (Visakhapatnam is in this timezone)
    try:
        kolkata_tz = pytz.timezone('Asia/Kolkata')
    except pytz.UnknownTimeZoneError:
        print("Error: 'Asia/Kolkata' timezone not found. Please ensure pytz is installed correctly.")
        print("Using UTC as fallback.")
        kolkata_tz = datetime.timezone.utc
    
    # Get current time in Kolkata timezone
    now_kolkata = datetime.datetime.now(kolkata_tz)
    
    # Example 1: Check availability for the next hour from current time in Kolkata
    later_kolkata_check = now_kolkata + datetime.timedelta(hours=1)
    
    print(f"\nChecking availability from {now_kolkata.isoformat()} to {later_kolkata_check.isoformat()} (Kolkata time)...")
    busy_slots = check_calendar_availability(service, now_kolkata, later_kolkata_check)
    if busy_slots:
        print("Busy slots found:")
        for slot in busy_slots:
            print(f"  Start: {slot.get('start', 'N/A')}, End: {slot.get('end', 'N/A')}")
    else:
        print("No busy slots found in the next hour.")

    # Example 2: Create a test event 2 hours from now for 30 minutes
    event_start = now_kolkata + datetime.timedelta(hours=2)
    event_end = event_start + datetime.timedelta(minutes=30)
    print(f"\nAttempting to create an event from {event_start.isoformat()} to {event_end.isoformat()}...")
    new_event = create_calendar_event(
        service,
        "TailorTalk Test Call", 
        "Discuss project requirements and agent capabilities", 
        event_start, 
        event_end,
        attendees=["sjunaid2034@gmail.com"] # Replace with a real email if you want to test attendees
                                         # Note: Google might send an invite to this email.
    )
    if new_event:
        print(f"Event created successfully: {new_event.get('htmlLink')}")
    else:
        print("Failed to create event.")