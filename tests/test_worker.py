# -*- coding: utf-8 -*-
import datetime
import pytest
import icalendar
import pytz

from pymax.objects import ProgramSchedule

try:
	from StringIO import StringIO
except ImportError:
	from io import StringIO
from maxd.config import Configuration
from maxd.worker import Worker, Schedule, _to_utc_datetime


class TestWorker(object):

	# def test_execute(self):
	# 	config = Configuration('tests/fixtures/config/basic.cfg')
	# 	w = Worker(config)
	# 	w.execute()

	def test_apply_range_filter(self):
		w = Worker(Configuration('/dev/null'))

		with open('tests/fixtures/calendars/repeating.ics', 'r') as f:
			events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']

		filtered = w.apply_range_filter(events, datetime.datetime(2015, 12, 21, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 27, tzinfo=pytz.UTC))
		filtered = list(filtered)

		assert len(filtered) == 4

	def test_apply_range_filter_exclude(self):
		w = Worker(Configuration('/dev/null'))

		with open('tests/fixtures/calendars/repeating.ics', 'r') as f:
			events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']

		filtered = w.apply_range_filter(events,
										datetime.datetime(2015, 12, 28, tzinfo=pytz.UTC),
										datetime.datetime(2016, 1, 1, tzinfo=pytz.UTC))
		filtered = list(filtered)
		print(filtered)

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

	def test_create_schedule_all_day_events(self, monkeypatch):
		# the static schedule is always in local time, so monkeypatch dateutil.tz.tzlocal() to return a constant
		# timezone to avoid test failures in different timezones
		def faketz():
			return pytz.timezone('Europe/Berlin')
		import dateutil.tz
		monkeypatch.setattr(dateutil.tz, 'tzlocal', lambda: faketz())

		w = Worker(Configuration('/dev/null'))

		with open('tests/fixtures/calendars/feiertage.ics', 'r') as f:
			events = [o for o in icalendar.Calendar.from_ical(f.read()).walk() if o.name == 'VEVENT']

		vevents = w.apply_range_filter(events,
									   start=datetime.datetime(2015, 12, 21, tzinfo=pytz.UTC),
									   end=datetime.datetime(2015, 12, 27, 23, 59, 59, tzinfo=pytz.UTC))

		schedule = w.create_schedule(vevents)
		assert schedule.events == {
			4: [
				(datetime.datetime(2015, 12, 25, 5, 30, 0, tzinfo=pytz.timezone('Europe/Berlin')), datetime.datetime(2015, 12, 25, 23, 0, 0, tzinfo=pytz.timezone('Europe/Berlin'))),
			],
			5: [
				(datetime.datetime(2015, 12, 26, 5, 30, 0, tzinfo=pytz.timezone('Europe/Berlin')), datetime.datetime(2015, 12, 26, 23, 0, 0, tzinfo=pytz.timezone('Europe/Berlin'))),
			],
		}

	def test_get_static_schedule(self, monkeypatch):
		# the static schedule is always in local time, so monkeypatch dateutil.tz.tzlocal() to return a constant
		# timezone to avoid test failures in different timezones
		def faketz():
			return pytz.timezone('Europe/Berlin')
		import dateutil.tz
		monkeypatch.setattr(dateutil.tz, 'tzlocal', lambda: faketz())

		w = Worker(Configuration('/dev/null'))
		w.config.cfg_parser.readfp(StringIO("""
[static]
monday = 11:00 - 12:00
tuesday = 12:00 - 13:00
wednesday = 13:00 - 14:00
thursday = 14:00 - 15:00
friday = 15:00 - 16:00
saturday = 16:00 - 17:00
sunday = 17:00 - 18:00
"""))
		static_schedule = w.get_static_schedule(datetime.datetime(2015, 12, 21, tzinfo=pytz.UTC))

		def _dt_time(day, h, m):
			return datetime.datetime(2015, 12, day, h, m, tzinfo=pytz.UTC)

		# While the static schedules are presented in local time in the configuration file, the get_static_schedule
		# method converts them to UTC. 2015-12-21 in Europe/Berlin is +0100
		# get_static_schedule also substracts warmup_duration from the start datetime.
		# in the result, the start datetime is -01:30 and the end datetime -01:00
		assert static_schedule.events == {
			0: [(_dt_time(21, 9, 30), _dt_time(21, 11, 0))],
			1: [(_dt_time(22, 10, 30), _dt_time(22, 12, 0))],
			2: [(_dt_time(23, 11, 30), _dt_time(23, 13, 0))],
			3: [(_dt_time(24, 12, 30), _dt_time(24, 14, 0))],
			4: [(_dt_time(25, 13, 30), _dt_time(25, 15, 0))],
			5: [(_dt_time(26, 14, 30), _dt_time(26, 16, 0))],
			6: [(_dt_time(27, 15, 30), _dt_time(27, 17, 0))]
		}


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

	def test_get_effective_contained(self):
		def _t(h, m):
			return datetime.datetime(2015, 12, 21, h, m, tzinfo=pytz.UTC)

		# periods which are contained in a larger period must be removed
		assert Schedule({
			0: [
				(_t(5, 0), _t(10, 0)),
				(_t(7, 0), _t(8, 0))
			]
		}).effective().events == {
			0: [
				(_t(5, 0), _t(10, 0)),
			]
		}

		# same as above, but items revers
		assert Schedule({
			0: [
				(_t(7, 0), _t(8, 0)),
				(_t(5, 0), _t(10, 0)),
			]
		}).effective().events == {
			0: [
				(_t(5, 0), _t(10, 0)),
			]
		}

	def test_get_effective_extend(self):
		def _t(h, m):
			return datetime.datetime(2015, 12, 21, h, m, tzinfo=pytz.UTC)

		# extend periods:
		# 0600  0700
		#   30        0900
		# -> 06:00 - 09:00
		assert Schedule({
			0: [
				(_t(6, 0), _t(7, 0)),
				(_t(6, 30), _t(9, 0)),
			]
		}).effective().events == {
			0: [
				(_t(6, 0), _t(9, 0)),
			]
		}

		# extend periods:
		# 0600  0700
		#   30        0900
		#                             1500 1700
		# -> 06:00 - 09:00
		# -> 15:00 - 17:00
		assert Schedule({
			0: [
				(_t(6, 0), _t(7, 0)),
				(_t(15, 0), _t(17, 0)),
				(_t(6, 30), _t(9, 0)),
			]
		}).effective().events == {
			0: [
				(_t(6, 0), _t(9, 0)),
				(_t(15, 0), _t(17, 0)),
			]
		}

	def test_get_effective_overlapped_and_contained(self):
		def _t(h, m):
			return datetime.datetime(2015, 12, 21, h, m, tzinfo=pytz.UTC)

		# a larger schedule supersedes the smaller ones which would be merged
		assert Schedule({
			0: [
				(_t(6, 0), _t(7, 0)),
				(_t(6, 30), _t(9, 0)),
				(_t(4, 00), _t(21, 0))
			]
		}).effective().events == {
			0: [
				(_t(4, 0), _t(21, 0)),
			]
		}

		# Overlapping and superseding periods together
		assert Schedule({
			0: [
				(_t(6, 0), _t(7, 0)),
				(_t(15, 0), _t(17, 0)),
				(_t(6, 30), _t(9, 0)),
				(_t(13, 0), _t(18, 0)),
			]
		}).effective().events == {
			0: [
				(_t(6, 0), _t(9, 0)),
				(_t(13, 0), _t(18, 0)),
			]
		}

	def test_as_timezone(self):
		def _t(h, m):
			return datetime.datetime(2015, 12, 21, h, m, tzinfo=pytz.UTC)

		schedule = Schedule({
			0: [
				(_t(6, 0), _t(9, 0)),
			]
		}).effective()

		schedule.as_timezone(pytz.timezone('Europe/Berlin'))
		assert schedule.events == {
			0: [
				(_t(6, 0), _t(9, 0)), # still the same as in UTC
			]
		}

	def test_to_schedule(self):
		schedule = Schedule({
			0: [
				(datetime.datetime(2015, 12, 21, 6, tzinfo=pytz.UTC), datetime.datetime(2015, 12, 21, 9, tzinfo=pytz.UTC)),
			]
		}).effective()

		assert list(schedule.to_program(0, 10, 20)) == [
			ProgramSchedule(10, datetime.time(), datetime.time(6)),
			ProgramSchedule(20, datetime.time(6), datetime.time(9)),
			ProgramSchedule(10, datetime.time(9), 1440),
		]


class TestFetcherUtils(object):

	def test_dt_conversion_none_arg(self):
		return _to_utc_datetime(None) is None

	def test_dt_conversion_already_utc(self):
		dt = datetime.datetime(2015, 12, 20, tzinfo=pytz.UTC)
		assert _to_utc_datetime(dt) == dt

	def test_dt_conversion_different_timezones(self):
		dt = datetime.datetime(2015, 12, 20, 10, 0, 0, tzinfo=pytz.timezone('Europe/Berlin'))
		assert _to_utc_datetime(dt).timetuple() == dt.utctimetuple()
