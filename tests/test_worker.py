# -*- coding: utf-8 -*-
import datetime
import pytest
import icalendar
import pytz
from maxd.config import Configuration, CalendarConfig
from maxd.worker import Worker, LocalCalendarEventFetcher, _to_utc_datetime, Event


class TestWorker(object):

	def test_execute(self):
		config = Configuration('tests/fixtures/config/basic.cfg')
		w = Worker(config)
		w.execute()

	# def test_apply_range_filter(self):
	# 	w = Worker(None)
	#
	# 	with open('tests/fixtures/calendars/repeating.ics', 'r') as f:
	# 		events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']
	#
	# 	print(events)
	#
	# 	filtered = w.apply_range_filter(events, datetime.datetime(2015, 12, 21), datetime.datetime(2015, 12, 28))
	#
	# 	assert len(filtered) == 4
	# 	assert all([x['SUMMARY'] == 'Ending repeating event' for x in filtered])
	#
	# def test_apply_filters_no_filters(self):
	# 	cc = CalendarConfig(name='test', url='tests/fixtures/calendars/single_event.ics')
	#
	# 	n = datetime.datetime.now(tz=pytz.UTC)
	# 	events = [Event(name='test', start=n, end=n)]
	# 	w = Worker(None)
	# 	filtered_events = w.apply_user_filter(cc, events)
	# 	assert filtered_events == events
	#
	# def test_apply_range_filter_exclude(self):
	# 	w = Worker(None)
	#
	# 	with open('tests/fixtures/calendars/repeating.ics', 'r') as f:
	# 		events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']
	#
	# 	filtered = w.apply_range_filter(events, datetime.datetime(2015, 12, 28), datetime.datetime(2016, 01, 01))
	# 	# weekly event: once (2015-12-29)
	# 	# daily event: 4 (2015-12-28 till 2015-12-31)
	# 	assert len(filtered) == 5

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
