def format_calendar_event(event):
    """Format a single calendar event for display

    Args:
        event: A Microsoft Graph event object

    Returns:
        String with formatted event details
    """
    # Start with the ID (crucial for operations like delete/update)
    result = f"ID: {event.id}\n"
    result += f"Subject: {event.subject}\n"

    # Add organizer info
    if event.organizer and event.organizer.email_address:
        result += f"Organizer: {event.organizer.email_address.name or 'Unknown'} <{event.organizer.email_address.address or 'No email'}>\n"


    # Variables to store parsed datetime objects for start and end
    start_dt = None
    end_dt = None

    # Add time info with better formatting
    if event.start:
        # Format: "Monday, May 5, 2025 at 5:30 PM (AEST)"
        start_time = event.start.date_time
        if start_time:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00').split('.')[0])
                formatted_start = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
                result += f"Start: {formatted_start} ({event.start.time_zone.replace(' Time', '')})\n"
            except Exception:
                result += f"Start: {event.start.date_time} ({event.start.time_zone})\n"

    if event.end:
        # Format: "Monday, May 5, 2025 at 6:45 PM (AESST)"
        end_time = event.end.date_time
        if end_time:
            try:
                from datetime import datetime
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00').split('.')[0])

                # Just show time for end if same day
                if start_dt and end_dt and end_dt.date() == start_dt.date():
                    formatted_end = end_dt.strftime("%I:%M %p")
                else:
                    formatted_end = end_dt.strftime("%A, %B %d, %Y at %I:%M %p")

                result += f"End: {formatted_end} ({event.end.time_zone.replace(' Time', '')})\n"
            except Exception:
                result += f"End: {event.end.date_time} ({event.end.time_zone})\n"

    # Add location if available
    if event.location and event.location.display_name:
        result += f"Location: {event.location.display_name}\n"

    # Add online meeting info if available
    if hasattr(event, 'is_online_meeting') and event.is_online_meeting:
        result += f"Online Meeting: Yes\n"
        if hasattr(event, 'online_meeting_url') and event.online_meeting_url:
            result += f"Meeting URL: {event.online_meeting_url}\n"

    # Add attendee count if there are attendees
    if event.attendees:
        result += f"Attendees: {len(event.attendees)}\n"

    return result


def format_event_page(event_page):
    """Format a page of calendar events for display

    Args:
        event_page: Page of events from the GraphController API

    Returns:
        String with formatted event list
    """
    result = ""

    if event_page and event_page.value:
        # Format each event
        for i, event in enumerate(event_page.value, 1):
            result += f"{i}. {format_calendar_event(event)}\n"
    else:
        result += "No events found."

    return result