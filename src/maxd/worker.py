# -*- coding: utf-8 -*-
import logging
import collections
import datetime
from dateutil import rrule

import pytz
import dateutil.tz

from pymax.cube import Discovery, Cube
from pymax.objects import ProgramSchedule

try:
	from urlparse import urlsplit
except ImportError: # pragma: nocover
	from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

weekday_names = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

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


class Schedule(object):

	def __init__(self, weekday_events={}):
		self.events = weekday_events or {}

	def __add__(self, other):
		if not isinstance(other, Schedule):
			raise ValueError("Cannot add %s instance to %s" % (other.__class__.__name__, self.__class__.__name__))

		for k, v in other.items():
			self.events[k] = self.events.get(k, []) + v

		return self

	def items(self):
		return self.events.items()

	def effective(self):
		new = {}

		for weekday, periods in self.events.items():
			periods = sorted(periods)
			new_periods = []

			while periods:
				current = periods.pop(0)
				other = periods

				# remove current period if another period starts before and ends after
				if any((p[0] < current[0] and p[1] > current[1] for p in other)) or \
					any((p[0] < current[0] and p[1] > current[1] for p in new_periods)):
					logger.debug("Removing period %s because it's contained in a larger period" % (current, ))
					continue

				new_periods.append(current)

			# extend periods (change start or end)
			periods = sorted(new_periods)
			new_periods = []
			while periods:
				current = periods.pop(0)
				other = periods

				candidates = [
					(s, e) for s, e in other
					if (current[0] <= s <= current[1]) or (current[0] <= e <= current[1])
				]
				if candidates:
					new_start = min(p[0] for p in candidates + [current])
					new_end = max(p[1] for p in candidates + [current])
					logger.debug("Replacing %s and %s with new: %s to %s" % (current, candidates, new_start, new_end))
					new_periods.append((new_start, new_end))
					for c in candidates:
						del periods[periods.index(c)]
				else:
					new_periods.append(current)

			new[weekday] = new_periods

		return Schedule(new)

	def as_timezone(self, tz):
		for wd, periods in self.events.items():
			self.events[wd] = [
				(start.astimezone(tz), end.astimezone(tz)) for start, end in periods
			]

	def to_program(self, weekday, low_temp, high_temp):
		periods = self.events[weekday]

		start = datetime.time()
		for pstart, pend in periods:
			yield ProgramSchedule(low_temp, start, pstart.time())
			yield ProgramSchedule(high_temp, pstart.time(), pend.time())
			start = pend.time()

		end_of_day = 1440
		if ((start.hour * 60) + start.minute) < end_of_day:
			yield ProgramSchedule(low_temp, start, end_of_day)

	def __eq__(self, other):
		return isinstance(other, Schedule) and self.events == other.events


class Worker(object):

	def __init__(self, config):
		self.config = config
		self.exception = None
		self._current_schedule = None

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

		static_schedule = self.get_static_schedule(start)
		calendar_schedule = self.create_schedule(events)

		if logger.isEnabledFor(logging.DEBUG):
			def _debug_schedule(schedule):
				for wd in sorted(schedule.events.keys()):
					logger.debug("  %s:" % weekday_names[wd])
					for start, end in sorted(schedule.events[wd]):
						logger.debug("    %s -> %s" % (start, end))

			logger.debug("Static schedule:")
			_debug_schedule(static_schedule)

			logger.debug("Calendar events schedule:")
			_debug_schedule(calendar_schedule)

		self.apply_schedule(static_schedule + calendar_schedule)

	def get_static_schedule(self, start):
		d = {}

		for day in range(0, 7):
			# use start (of the week we are looking at), reset to midnight and add x days
			dt = start.astimezone(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=day)
			# static schedules are always considered the local timezone
			local_dt = dt.astimezone(dateutil.tz.tzlocal())

			weekday = dt.weekday()
			d[weekday] = []
			for event_start, event_end in self.config.static_schedule.get(weekday, []):
				# use the *local* datetime of midnight of day x in our window for start and end.
				s = local_dt.replace(hour=event_start.hour, minute=event_start.minute).astimezone(pytz.UTC) - self.config.warmup_duration
				e = local_dt.replace(hour=event_end.hour, minute=event_end.minute).astimezone(pytz.UTC)

				d[weekday].append((s, e))

		return Schedule(d)

	def fetch_events(self, calendar_config, start, end):
		chunks = urlsplit(calendar_config.url)

		if chunks.scheme and chunks.netloc:
			fetcher = HTTPCalendarEventFetcher()
		else:
			fetcher = LocalCalendarEventFetcher()

		# fetch all ical event for this calendar
		events = fetcher.fetch(calendar_config)

		# filter the fetched events for the current period and convert them to Event instances
		logger.info("Applying range filter to fetched events from %s" % calendar_config.name)
		events = self.apply_range_filter(events, start, end)

		return events

	def apply_range_filter(self, events, start, end):
		start = (start.astimezone(pytz.UTC) if start.tzinfo else start).replace(hour=0, minute=0, second=0)
		end = (end.astimezone(pytz.UTC) if end.tzinfo else end).replace(hour=23, minute=59, second=59)

		def _to_all_day(date):
			allday_start, allday_end = self.config.allday_range
			day_start = datetime.datetime.combine(date, allday_start).replace(tzinfo=dateutil.tz.tzlocal())
			day_end = datetime.datetime.combine(date, allday_end).replace(tzinfo=dateutil.tz.tzlocal())
			return day_start.astimezone(pytz.UTC), day_end.astimezone(pytz.UTC)

		def _build_all_events():
			for cal_event in events:
				all_day = cal_event['DTSTART'].dt.__class__ == datetime.date

				all_day_start, all_day_end = _to_all_day(cal_event['DTSTART'].dt)

				if 'RRULE' in cal_event:
					if all_day:
						event_start_utc = all_day_start
					else:
						event_start_utc = cal_event['DTSTART'].dt.astimezone(pytz.UTC)

					rule = rrule.rrulestr(cal_event.get('RRULE').to_ical().decode('utf-8'), dtstart=event_start_utc.replace(tzinfo=None))
					if rule._until:
						# The until field in the RRULE may contain a timezone (even if it's UTC).
						# Make sure its UTC and remove the tzinfo
						rule._until = rule._until.astimezone(pytz.UTC).replace(tzinfo=None)

					for dt in rule.between(start.replace(tzinfo=None), end.replace(tzinfo=None), inc=True):
						if all_day:
							s, e = _to_all_day(dt.date())
							yield Event(name=None, start=s, end=e)
						else:
							dt = dt.replace(tzinfo=pytz.UTC)
							duration = cal_event['DTEND'].dt - cal_event['DTSTART'].dt
							yield Event(name=None, start=dt, end=dt + duration)
				else:
					if all_day:
						s, e = _to_all_day(cal_event['DTSTART'].dt)
						yield Event(name=None, start=s, end=e)
					else:
						yield Event(name=None, start=cal_event['DTSTART'].dt.astimezone(pytz.UTC), end=cal_event['DTEND'].dt.astimezone(pytz.UTC))

		for event in _build_all_events():
			if start <= event.start <= end:
				yield event

	def create_schedule(self, events):
		schedule = {}

		warmup = self.config.warmup_duration

		for event in events:
			logger.debug(event)

			start = event.start - warmup
			if start.date() != event.start.date():
				start = event.start.replace(hour=0, minute=0, second=0)

			end = event.end
			if end.date() != start.date():
				end = event.end.replace(hour=23, minute=59, second=59)

			schedule[start.weekday()] = schedule.get(start.weekday(), []) + [(start, end)]

		return Schedule(schedule)

	def apply_schedule(self, schedule):
		effective_schedule = schedule.effective()

		if logger.isEnabledFor(logging.INFO):
			logger.info("Effective schedule:")
			for weekday_num, items in effective_schedule.items():
				logger.info("%10s: %s" % (weekday_names[weekday_num], ', '.join("%s to %s" % x for x in items)))

		if self._current_schedule == schedule:
			logger.info("Schedule unchanged")
			return

		with self.connect_to_cube() as cube:
			# i would like to use the 'v' message to get the timezone from the cube
			# unfortunately, at least my cube doesn't set the timezone properly when using the max cube software
			if self.config.cube_timezone:
				cube_tz = pytz.timezone(self.config.cube_timezone)
			else:
				cube_tz = dateutil.tz.tzlocal()
			logger.info("Cube time zone: %s" % cube_tz)
			effective_schedule.as_timezone(cube_tz)

			if self.config.has_room_settings:
				rooms = []
				for r in cube.rooms:
					if (self.config.room_id and r.room_id == self.config.room_id) or \
							(self.config.room_name and self.config.room_name == r.name) or \
							(self.config.room_rf_addr and self.config.room_rf_addr == r.rf_address):
						rooms.append(r)
			else:
				rooms = [r for r in cube.rooms]

			if rooms:
				logger.info("Writing program to cube for rooms %s" % rooms)
				low_temp = self.config.low_temperature
				high_temp = self.config.high_temperature
				for weekday_num in effective_schedule.events.keys():
					programs = list(effective_schedule.to_program(weekday_num, low_temp, high_temp))
					logger.info("%10s: %s" % (weekday_names[weekday_num], ', '.join(["%s-%s (%s)" % (x.begin_minutes, x.end_minutes, x.temperature) for x in programs])))

					for room in rooms:
						logger.debug("Setting program for room %s, rf addr: %s on day %s" % (room.room_id, room.rf_address, weekday_num))
						cube.set_program(room.room_id, room.rf_address, weekday_num, programs)
			else:
				logger.warning("Could not find any rooms to write the program for")

		self._current_schedule = schedule

	def connect_to_cube(self):
		cube_addr = None
		cube_port = self.config.cube_port

		if self.config.cube_address:
			cube_addr = self.config.cube_address

		if not cube_addr:
			logger.info("Using discovery to find cube")
			d = Discovery()

			cube_serial = self.config.cube_serial
			if not cube_serial:
				logger.info("Making IDENTIFY discovery to find available cubes")
				response = Discovery().discover()
				logger.info("Got IDENTIFY response: %s" % response)
				if response:
					cube_serial = response.serial
				else:
					raise Exception("No cube found with IDENTIFY discovery")

			# use network configuration discovery
			logger.info("Using NETWORK CONFIG discovery for cube %s" % cube_serial)
			discovery_response = d.discover(cube_serial=cube_serial, discovery_type=Discovery.DISCOVERY_TYPE_NETWORK_CONFIG)
			if discovery_response:
				cube_addr = discovery_response.ip_address
			else:
				raise Exception("Cube %s did not answer with network configuration" % cube_serial)

		logger.info("Cube at %s, port %s" % (cube_addr, cube_port))
		return Cube(address=cube_addr, port=cube_port)