# mcpserver/graph/calendar_service.py
from msgraph import GraphServiceClient
from typing import List, Optional
from msgraph.generated.users.item.calendar.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder
from msgraph.generated.models.event import Event
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.location import Location
from msgraph.generated.models.attendee import Attendee
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.attendee_type import AttendeeType
from msgraph.generated.models.online_meeting_provider_type import OnlineMeetingProviderType
from kiota_abstractions.base_request_configuration import RequestConfiguration
import datetime


class CalendarService:
    """Service for calendar-related operations using Microsoft Graph API"""

    def __init__(self, user_client: GraphServiceClient):
        self.user_client = user_client

    async def list_events(self, count: int = 10):
        """
        List calendar events from the user's default calendar

        Args:
            count: Maximum number of events to retrieve

        Returns:
            Collection of events
        """


        # Create request configuration with query parameters directly
        request_config = RequestConfiguration()

        # Add query parameters as a dictionary
        request_config.query_parameters = {
            "$select": "subject,bodyPreview,organizer,attendees,start,end,location",
            "$top": count,
            "$orderby": "createdDateTime DESC"
        }

        # Add timezone preference header
        request_config.headers.add("Prefer", 'outlook.timezone="AUS Eastern Standard Time"')

        events = await self.user_client.me.events.get(request_configuration=request_config)
        return events

    async def create_event(self, subject: str, body: str, start_datetime: str,
                           end_datetime: str, time_zone: str = "Pacific Standard Time",
                           location: str = None, attendees: List[dict] = None):
        """
        Create a new calendar event

        Args:
            subject: Subject of the event
            body: Body content of the event
            start_datetime: Start time in format "YYYY-MM-DDTHH:MM:SS"
            end_datetime: End time in format "YYYY-MM-DDTHH:MM:SS"
            time_zone: Time zone for the event times
            location: Optional location name
            attendees: Optional list of attendees in format [{"email": "...", "name": "...", "type": "required|optional"}]

        Returns:
            The created event
        """
        # Create event object
        event = Event()
        event.subject = subject

        # Set body
        event.body = ItemBody()
        event.body.content_type = BodyType.Html
        event.body.content = body

        # Set times
        event.start = DateTimeTimeZone()
        event.start.date_time = start_datetime
        event.start.time_zone = time_zone

        event.end = DateTimeTimeZone()
        event.end.date_time = end_datetime
        event.end.time_zone = time_zone

        # Set location if provided
        if location:
            event.location = Location()
            event.location.display_name = location

        # Set attendees if provided
        if attendees:
            event.attendees = []
            for person in attendees:
                attendee = Attendee()
                attendee.email_address = EmailAddress()
                attendee.email_address.address = person.get("email")

                if "name" in person:
                    attendee.email_address.name = person.get("name")

                # Set type (required, optional, resource)
                if person.get("type", "").lower() == "optional":
                    attendee.type = AttendeeType.Optional
                else:
                    attendee.type = AttendeeType.Required

                event.attendees.append(attendee)

        # Allow new time proposals by default
        event.allow_new_time_proposals = True

        # Create request configuration
        request_configuration = RequestConfiguration()
        request_configuration.headers.add("Prefer", f'outlook.timezone="{time_zone}"')

        # Create the event
        result = await self.user_client.me.events.post(event, request_configuration=request_configuration)
        return result

    async def list_events_by_date_range(self, start_date=None, end_date=None):
        """
        List calendar events within a specific date range

        Args:
            start_date: Start date in format "YYYY-MM-DD" (default: today)
            end_date: End date in format "YYYY-MM-DD" (default: 2 weeks from start_date)

        Returns:
            Collection of events within the date range
        """

        # Calculate default date range if not provided
        if not start_date:
            # Get current date
            today = datetime.datetime.now().date()
            start_date = today.strftime("%Y-%m-%d")

        if not end_date:
            # Convert start_date string to date object
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            # Add two weeks to start date
            end_date_obj = start_date_obj + datetime.timedelta(days=14)
            end_date = end_date_obj.strftime("%Y-%m-%d")

        # Format the dates for the calendar view
        start_datetime = f"{start_date}T00:00:00"
        end_datetime = f"{end_date}T23:59:59"

        # Create the proper query parameters
        query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
            start_date_time=start_datetime,
            end_date_time=end_datetime,
            select=["subject", "bodyPreview", "organizer", "attendees", "start", "end", "location", "isOnlineMeeting",
                    "onlineMeetingUrl"],
            orderby=["start/dateTime asc"]
        )

        # Create request configuration
        request_config = RequestConfiguration(
            query_parameters=query_params
        )

        # Set timezone header
        request_config.headers.add("Prefer", 'outlook.timezone="AUS Eastern Standard Time"')

        # Use calendar view endpoint
        events = await self.user_client.me.calendar.calendar_view.get(
            request_configuration=request_config
        )

        return events

    async def create_event(self, subject: Optional[str], body: Optional[str], start_datetime: Optional[str], end_datetime: Optional[str],
                           time_zone="AUS Eastern Standard Time", location: Optional[str]=None,
                           is_online_meeting: Optional[bool]=False, attendees: Optional[str]=None):
        """
        Create a new calendar event

        Args:
            subject: Subject of the event
            body: Body content of the event
            start_datetime: Start time in format "YYYY-MM-DDTHH:MM:SS"
            end_datetime: End time in format "YYYY-MM-DDTHH:MM:SS"
            time_zone: Time zone for the event times
            location: Optional location name
            is_online_meeting: Whether to make this an online meeting
            attendees: Optional list of attendees in format [{"email": "...", "name": "...", "type": "required|optional"}]

        Returns:
            The created event
        """

        # Create event object
        event = Event()
        event.subject = subject

        # Set body
        event.body = ItemBody()
        event.body.content_type = BodyType.Html
        event.body.content = body

        # Set times
        event.start = DateTimeTimeZone()
        event.start.date_time = start_datetime
        event.start.time_zone = time_zone

        event.end = DateTimeTimeZone()
        event.end.date_time = end_datetime
        event.end.time_zone = time_zone

        # Set location if provided
        if location:
            event.location = Location()
            event.location.display_name = location

        # Set online meeting if requested
        if is_online_meeting:
            event.is_online_meeting = True
            event.online_meeting_provider = OnlineMeetingProviderType.TeamsForBusiness

        # Set attendees if provided
        if attendees:
            event.attendees = []
            for person in attendees:
                attendee = Attendee()
                attendee.email_address = EmailAddress()
                attendee.email_address.address = person.get("email")

                if "name" in person:
                    attendee.email_address.name = person.get("name")

                # Set attendee type
                if person.get("type", "").lower() == "optional":
                    attendee.type = AttendeeType.Optional
                else:
                    attendee.type = AttendeeType.Required

                event.attendees.append(attendee)

        # Allow new time proposals by default
        event.allow_new_time_proposals = True

        # Create request configuration
        request_configuration = RequestConfiguration()
        request_configuration.headers.add("Prefer", f'outlook.timezone="{time_zone}"')

        # Create the event
        result = await self.user_client.me.events.post(event, request_configuration=request_configuration)
        return result

    async def delete_event(self, event_id: str, notify_attendees: bool = True):
        """
        Delete a calendar event

        Args:
            event_id: ID of the event to delete
            notify_attendees: Whether to send cancellation notices to attendees (default: True)

        Returns:
            True if the deletion was successful
        """

        # Set up configuration with query parameter to control notification
        request_config = RequestConfiguration()
        if not notify_attendees:
            # Use the proper query parameter to suppress notifications
            request_config.query_parameters = {
                "$disableNotification": True
            }

        # Delete the event with the request configuration
        await self.user_client.me.events.by_event_id(event_id).delete(request_configuration=request_config)
        return True