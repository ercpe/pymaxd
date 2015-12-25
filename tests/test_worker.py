# -*- coding: utf-8 -*-
import datetime
import pytest
import icalendar
import pytz
try:
	from StringIO import StringIO
except ImportError:
	from io import StringIO
from maxd.config import Configuration, CalendarConfig
from maxd.worker import Worker, LocalCalendarEventFetcher, _to_utc_datetime, Event, Schedule


class TestWorker(object):

	def test_execute(self):
		config = Configuration('tests/fixtures/config/basic.cfg')
		w = Worker(config)
		w.execute()

	def test_apply_range_filter(self):
		w = Worker(None)

		with open('tests/fixtures/calendars/repeating.ics', 'r') as f:
			events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']

		filtered = w.apply_range_filter(events, datetime.datetime(2015, 12, 21, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 28, tzinfo=pytz.UTC))
		filtered = list(filtered)

		assert len(filtered) == 4
		assert all([x.name == 'Ending repeating event' for x in filtered])

	def test_apply_filters_no_filters(self):
		cc = CalendarConfig(name='test', url='tests/fixtures/calendars/single_event.ics')

		n = datetime.datetime.now(tz=pytz.UTC)
		events = [Event(name='test', start=n, end=n)]

		w = Worker(None)
		filtered_events = w.apply_user_filter(cc, events)
		filtered = list(filtered_events)

		assert filtered_events == events

	def test_apply_range_filter_exclude(self):
		w = Worker(None)

		with open('tests/fixtures/calendars/repeating.ics', 'r') as f:
			events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']

		filtered = w.apply_range_filter(events,
										datetime.datetime(2015, 12, 28, tzinfo=pytz.UTC),
										datetime.datetime(2016, 1, 1, tzinfo=pytz.UTC))
		filtered = list(filtered)

		# weekly event: once (2015-12-29)
		# daily event: 4 (2015-12-28 till 2015-12-31)
		assert len(filtered) == 5

	def test_create_schedule(self):
		w = Worker(Configuration('/dev/null'))

		with open('tests/fixtures/calendars/repeating.ics', 'r') as f:
			events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']

		vevents = w.apply_range_filter(events,
									   start=datetime.datetime(2015, 12, 24, tzinfo=pytz.UTC),
									   end=datetime.datetime(2015, 12, 30, 23, 59, 59, tzinfo=pytz.UTC))

		schedule = w.create_schedule(vevents)

		for wd, periods in sorted(schedule.items()):
			print("Weekday %s:" % wd)
			for start, end in sorted(periods):
				print("  %s -> %s" % (start, end))

		d = {
			3: [ # 2015-12-24
				# repeating daily
				(datetime.datetime(2015, 12, 24, 7, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 24, 9, 0, 00, tzinfo=pytz.UTC)),
			],
			4: [ # 2015-12-25
				# repeating daily
				(datetime.datetime(2015, 12, 25, 7, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 25, 9, 0, 00, tzinfo=pytz.UTC)),
			],
			5: [ # 2015-12-26
				# repeating daily
				(datetime.datetime(2015, 12, 26, 7, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 26, 9, 0, 00, tzinfo=pytz.UTC)),
			],
			6: [ # 2015-12-27
				# repeating daily
				(datetime.datetime(2015, 12, 27, 7, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 27, 9, 0, 00, tzinfo=pytz.UTC)),
			],
			0: [ # 2015-12-28
				# repeating daily
				(datetime.datetime(2015, 12, 28, 7, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 28, 9, 0, 00, tzinfo=pytz.UTC)),
			],
			1: [ # 2015-12-29
				# repeating weekly
				(datetime.datetime(2015, 12, 29, 8, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 29, 10, 0, 00, tzinfo=pytz.UTC)),
				# repeating daily
				(datetime.datetime(2015, 12, 29, 7, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 29, 9, 0, 00, tzinfo=pytz.UTC)),
			],
			2: [ # 2015-12-30
				(datetime.datetime(2015, 12, 30, 7, 30, 00, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 30, 9, 0, 00, tzinfo=pytz.UTC)),
			]
		}

		assert schedule == Schedule(d)

	def test_get_static_schedule(self):
		w = Worker(Configuration('/dev/null'))
		w.config.cfg_parser.readfp(StringIO("""
[static]
monday = 01:00 - 02:00
tuesday = 02:00 - 03:00
wednesday = 03:00 - 04:00
thursday = 04:00 - 05:00
friday = 05:00 - 06:00
saturday = 06:00 - 07:00
sunday = 07:00 - 08:00
"""))
		static_schedule = w.get_static_schedule(datetime.datetime(2015, 12, 21, tzinfo=pytz.UTC))

		def _dt_time(day, h, m):
			return datetime.datetime(2015, 12, day, h, m, tzinfo=pytz.UTC)

		assert static_schedule.events == {
			0: [(_dt_time(21, 1, 0), _dt_time(21, 2, 0))],
			1: [(_dt_time(22, 2, 0), _dt_time(22, 3, 0))],
			2: [(_dt_time(23, 3, 0), _dt_time(23, 4, 0))],
			3: [(_dt_time(24, 4, 0), _dt_time(24, 5, 0))],
			4: [(_dt_time(25, 5, 0), _dt_time(25, 6, 0))],
			5: [(_dt_time(26, 6, 0), _dt_time(26, 7, 0))],
			6: [(_dt_time(27, 7, 0), _dt_time(27, 8, 0))]
		}


class TestFetcher(object):

	def test_local_fetcher(self):
		f = LocalCalendarEventFetcher()
		events = list(f.fetch(CalendarConfig(name='test', url='tests/fixtures/calendars/single_event.ics')))
		assert len(events) == 1

		event = events[0]

		assert event['SUMMARY'] == 'Test Event'
		assert event['DTSTART'].dt == datetime.datetime(2015, 12, 20, 9, 0, tzinfo=pytz.UTC)
		assert event['DTEND'].dt == datetime.datetime(2015, 12, 20, 10, 0, tzinfo=pytz.UTC)


class TestFetcherUtils(object):

	def test_dt_conversion_none_arg(self):
		return _to_utc_datetime(None) is None

	def test_dt_conversion_already_utc(self):
		dt = datetime.datetime(2015, 12, 20, tzinfo=pytz.UTC)
		assert _to_utc_datetime(dt) == dt

	def test_dt_conversion_different_timezones(self):
		dt = datetime.datetime(2015, 12, 20, 10, 0, 0, tzinfo=pytz.timezone('Europe/Berlin'))
		assert _to_utc_datetime(dt).timetuple() == dt.utctimetuple()


class TestSchedule(object):

	def test_constructor(self):
		assert Schedule(None).events == {}
		assert Schedule({}).events == {}

	def test_add(self):
		assert (Schedule({0: ['foo']}) + Schedule({1: ['bar']})).events == {
			0: ['foo'],
			1: ['bar']
		}
		assert (Schedule({0: ['foo']}) + Schedule({0: ['bar']})).events == {
			0: ['foo', 'bar'],
		}

		with pytest.raises(ValueError):
			Schedule() + 'lalala'
