# -*- coding: utf-8 -*-
import logging
import collections
import time
import datetime

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
	return datetime.datetime.fromtimestamp(time.mktime(dt.timetuple()), tz=pytz.UTC)


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

		events = []
		for calendar_config in self.config.calendars:
			try:
				events.extend(self.fetch_events(calendar_config))
			except:
				logger.exception("Failed to read events from %s" % calendar_config.name)

	def fetch_events(self, calendar_config):
		chunks = urlsplit(calendar_config.url)
		if chunks.scheme and chunks.netloc:
			return HTTPCalendarEventFetcher().fetch(calendar_config)
		else:
			return LocalCalendarEventFetcher().fetch(calendar_config)


