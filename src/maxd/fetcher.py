# -*- coding: utf-8 -*-
from icalendar import Calendar

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