# -*- coding: utf-8 -*-
import logging
import collections
import datetime
from dateutil import rrule

import pytz
from icalendar import Calendar

try:
	from urlparse import urlsplit
except ImportError: # pragma: nocover
	from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

def _to_utc_datetime(dt):
	if dt is None:
		return None

	if dt.tzinfo == pytz.UTC:
		return dt
	return dt.astimezone(pytz.UTC)


class Event(collections.namedtuple('Event', ('name', 'start', 'end'))):

	def __new__(cls, **kwargs):
		kwargs['start'] = _to_utc_datetime(kwargs.pop('start', None))
		kwargs['end'] = _to_utc_datetime(kwargs.pop('end', None))

		return super(Event, cls).__new__(cls, **kwargs)


class EventFetcher(object):

	def fetch(self, calendar_config):
		raise NotImplementedError  # pragma: nocover


class LocalCalendarEventFetcher(EventFetcher):

	def fetch(self, calendar_config):
		with open(calendar_config.url, 'r') as f:
			calendar = Calendar.from_ical(f.read())
			for item in calendar.walk():
				if item.name != "VEVENT":
					continue

				name = item.get('SUMMARY')
				yield Event(name=name, start=item.get('DTSTART').dt, end=item.get('DTEND').dt)


class HTTPCalendarEventFetcher(EventFetcher):
	pass


class Worker(object):

	def __init__(self, config):
		self.config = config
		self.exception = None

	def execute(self):
		logger.info("Running...")

		start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
		end = start + datetime.timedelta(days=7)

		logger.info("Start: %s, end: %s" % (start, end))

		events = []
		for calendar_config in self.config.calendars:
			try:
				events.extend(self.fetch_events(calendar_config, start, end))
			except:
				logger.exception("Failed to read events from %s" % calendar_config.name)

		logger.info("Creating schedule for %s events" % len(events))
		schedule = self.create_schedule(events)

	def fetch_events(self, calendar_config, start, end):
		chunks = urlsplit(calendar_config.url)

		if chunks.scheme and chunks.netloc:
			fetcher = HTTPCalendarEventFetcher()
		else:
			fetcher = LocalCalendarEventFetcher()

		events = fetcher.fetch(calendar_config)

		logger.info("Applying range filter to %s fetched events" % len(events))
		events = self.apply_range_filter(events, start, end)

		logger.info("Applying user filter to %s events" % len(events))
		return self.apply_user_filter(calendar_config, events)

	def apply_range_filter(self, events, start, end):

		def _expand(events, start, end):
			start = start.replace(tzinfo=None)
			end = end.replace(tzinfo=None)

			for event in events:
				if 'RRULE' not in event:
					yield event, event['DTSTART'].dt.astimezone(pytz.UTC)
					continue

				rule = rrule.rrulestr(event.get('RRULE').to_ical())
				if rule._until:
					# The until field in the RRULE may contain a timezone (even if it's UTC).
					# Make sure its UTC and remove it
					rule._until = rule._until.astimezone(pytz.UTC).replace(tzinfo=None)

				for dt in rule.between(start, end):
					yield event, dt

		filtered_events = filter(lambda item: start <= item[1] <= end, _expand(events, start, end))
		return [ev for ev, _ in filtered_events]

	def apply_user_filter(self, calendar_config, events):
		return events

	def create_schedule(self, events):
		return []