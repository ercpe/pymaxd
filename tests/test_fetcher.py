# -*- coding: utf-8 -*-
from maxd.config import CalendarConfig
from maxd.fetcher import LocalCalendarEventFetcher
import datetime
import pytz

class TestFetcher(object):

	def test_local_fetcher(self):
		f = LocalCalendarEventFetcher()
		events = list(f.fetch(CalendarConfig(name='test', url='tests/fixtures/calendars/single_event.ics')))
		assert len(events) == 1

		event = events[0]

		assert event['SUMMARY'] == 'Test Event'
		assert event['DTSTART'].dt == datetime.datetime(2015, 12, 20, 9, 0, tzinfo=pytz.UTC)
		assert event['DTEND'].dt == datetime.datetime(2015, 12, 20, 10, 0, tzinfo=pytz.UTC)

