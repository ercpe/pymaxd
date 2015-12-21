# -*- coding: utf-8 -*-
import datetime

import pytz
from maxd.config import Configuration, CalendarConfig
from maxd.worker import Worker, LocalCalendarEventFetcher, _to_utc_datetime, Event


class TestWorker(object):

	def test_execute(self):
		config = Configuration('tests/fixtures/config/basic.cfg')
		w = Worker(config)
		w.execute()

	def test_apply_filters_no_filters(self):
		cc = CalendarConfig(name='test', url='tests/fixtures/calendars/single_event.ics')

		n = datetime.datetime.now(tz=pytz.UTC)
		events = [Event(name='test', start=n, end=n)]
		w = Worker(None)
		filtered_events = w.apply_filter(cc, events)
		assert filtered_events == events


class TestFetcher(object):

	def test_local_fetcher(self):
		f = LocalCalendarEventFetcher()
		events = list(f.fetch(CalendarConfig(name='test', url='tests/fixtures/calendars/single_event.ics')))
		assert len(events) == 1

		event = events[0]

		assert event.name == 'Test Event'
		assert event.start == datetime.datetime(2015, 12, 20, 9, 0, tzinfo=pytz.UTC)
		assert event.end == datetime.datetime(2015, 12, 20, 10, 0, tzinfo=pytz.UTC)


class TestFetcherUtils(object):

	def test_dt_conversion_none_arg(self):
		return _to_utc_datetime(None) is None

	def test_dt_conversion_already_utc(self):
		dt = datetime.datetime(2015, 12, 20, tzinfo=pytz.UTC)
		assert _to_utc_datetime(dt) == dt

	def test_dt_conversion_different_timezones(self):
		dt = datetime.datetime(2015, 12, 20, 10, 0, 0, tzinfo=pytz.timezone('Europe/Berlin'))
		assert _to_utc_datetime(dt).timetuple() == dt.utctimetuple()
