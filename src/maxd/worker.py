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

				yield item


class HTTPCalendarEventFetcher(EventFetcher):
	pass


class Worker(object):

	def __init__(self, config):
		self.config = config
		self.exception = None

	def execute(self):
		logger.info("Running...")

		start = datetime.datetime.now(tz=pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
		end = start + datetime.timedelta(days=7) - datetime.timedelta(seconds=1)

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

		# fetch all ical event for this calendar
		events = fetcher.fetch(calendar_config)

		# filter the fetched events for the current period and convert them to Event instances
		logger.info("Applying range filter to fetched events")
		events = self.apply_range_filter(events, start, end)

		logger.info("Applying user filter to events")
		return self.apply_user_filter(calendar_config, events)

	def apply_range_filter(self, events, start, end):

		def _expand(events, start, end):
			start = start.astimezone(pytz.UTC).replace(tzinfo=None) if start.tzinfo else start
			end = end.astimezone(pytz.UTC).replace(tzinfo=None) if end.tzinfo else end

			for event in events:
				if 'RRULE' in event:
					event_start_utc = event['DTSTART'].dt.astimezone(pytz.UTC).replace(tzinfo=None)
					rule = rrule.rrulestr(event.get('RRULE').to_ical().decode('utf-8'), dtstart=event_start_utc)
					if rule._until:
						# The until field in the RRULE may contain a timezone (even if it's UTC).
						# Make sure its UTC and remove the tzinfo
						rule._until = rule._until.astimezone(pytz.UTC).replace(tzinfo=None)

					for dt in rule.between(start, end, inc=True):
						yield event, dt.replace(tzinfo=pytz.UTC)
				else:
					yield event, event['DTSTART'].dt.astimezone(pytz.UTC)

		filtered_events = filter(lambda item: start <= item[1] <= end, _expand(events, start, end))

		for ev, event_start in filtered_events:
			event_end = event_start + (ev['DTEND'].dt - ev['DTSTART'].dt)
			yield Event(name=str(ev['SUMMARY']), start=event_start, end=event_end)

	def apply_user_filter(self, calendar_config, events):
		return events

	def create_schedule(self, events):
		schedule = {}

		warmup = self.config.warmup_duration

		for event in events:
			logger.info(event)

			start = event.start - warmup

			# restrict end of period to the end of the day
			end_of_day = (event.start + datetime.timedelta(hours=23, minutes=59, seconds=59)).replace(hour=0, minute=0, second=0) - datetime.timedelta(seconds=1)
			end = min(event.end, end_of_day)
			logger.debug(" Begin warmup: %s, end warm: %s" % (start, end))

			schedule[start.weekday()] = schedule.get(start.weekday(), []) + [(start, end)]

		for wd in sorted(schedule.keys()):
			logger.debug("Weekday %s:" % wd)
			for start, end in sorted(schedule[wd]):
				logger.debug("  %s -> %s" % (start, end))

		return schedule