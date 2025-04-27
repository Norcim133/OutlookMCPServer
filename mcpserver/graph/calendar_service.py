# mcpserver/graph/calendar_service.py
from msgraph import GraphServiceClient
from msgraph.generated.models.event import Event
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.location import Location
from msgraph.generated.models.attendee import Attendee
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.attendee_type import AttendeeType
from kiota_abstractions.base_request_configuration import RequestConfiguration
from typing import List, Optional


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
        from msgraph.generated.users.item.events.events_request_builder import EventsRequestBuilderGetQueryParameters

        query_params = EventsRequestBuilderGetQueryParameters(
            select=['subject', 'bodyPreview', 'organizer', 'attendees', 'start', 'end', 'location'],
            top=count,
            orderby=['createdDateTime DESC']
        )

        request_config = RequestConfiguration(query_parameters=query_params)
        request_config.headers.add("Prefer", 'outlook.timezone="Pacific Standard Time"')

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
        # Create event object based on your research
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