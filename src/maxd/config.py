# -*- coding: utf-8 -*-
import collections
import logging
import datetime
import re
from functools import wraps

try:
	from ConfigParser import ConfigParser
except ImportError: # pragma: no cover
	from configparser import ConfigParser

logger = logging.getLogger(__name__)

def timediff(func):
	def _wrapper(*args):
		result = func(*args)

		if isinstance(result, datetime.timedelta):
			return result

		if isinstance(result, int) or (isinstance(result, str) and result.isdigit()):
			return datetime.timedelta(minutes=int(result))

		m = re.match("(\d{1,2})\:(\d{1,2})", result)
		if m:
			hours, minutes = m.groups()
			return datetime.timedelta(hours=int(hours), minutes=int(minutes))

		raise ValueError("Unparsable time diff: %s" % result)

	return _wrapper

def max_value(max, allow_none=True):
	def _inner(func):
		def _wrapper(*args):
			value = func(*args)

			if value is None:
				if allow_none:
					return value
				else:
					logger.info("Limiting value of %s to max %s" % (value, max))
					return max

			if value > max:
				logger.info("Limiting value of %s to max %s" % (value, max))
				return max

			return value
		return _wrapper
	return _inner

def min_value(min, allow_none=True):
	def _inner(func):
		def _wrapper(*args):
			value = func(*args)

			if value is None:
				if allow_none:
					return value
				else:
					logger.info("Limiting value of %s to min %s" % (value, min))
					return min

			if value < min:
				logger.info("Limiting value of %s to min %s" % (value, min))
				return min

			return value
		return _wrapper
	return _inner


def time_range(s):
	if (s or "").strip():
		periods = [x.strip() for x in s.split(',')]

		for p in periods:
			if not p:
				continue
			m = re.match(r"(\d{1,2}):(\d{1,2})\s*-\s*(\d{1,2}):(\d{1,2})", p)
			if not m:
				raise ValueError("'%s' does not match 'hh:mm - hh:mm'" % p)
			yield int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


class CalendarConfig(collections.namedtuple('CalendarConfig', ('name', 'url', 'username', 'password'))):

	def __new__(cls, **kwargs):
		kwargs.setdefault('username', None)
		kwargs.setdefault('password', None)
		return super(CalendarConfig, cls).__new__(cls, **kwargs)

	@property
	def auth(self):
		return bool(self.username and self.password)


class Configuration(object):

	def __init__(self, config_path):
		self.path = config_path
		self.cfg_parser = None
		self._calendar = None
		self._static = None
		self.reload()

	def reload(self):
		self.cfg_parser = ConfigParser()
		if not self.cfg_parser.read(self.path) == [self.path]:
			raise Exception("Failed to read configuration file %s" % self.path)

	def get_option(self, section, option, default=None):
		return self.cfg_parser.get(section, option) if self.cfg_parser.has_option(section, option) else default

	def get_int(self, section, option, default=None):
		return self.cfg_parser.getint(section, option) if self.cfg_parser.has_option(section, option) else default

	@property
	def calendars(self):
		if self._calendar is None:
			self._calendar = []

			names = [x.strip() for x in self.get_option('GENERAL', 'calendars', '').split(',') if x.strip()]
			for section_name in names:
				url = self.get_option(section_name, 'url')
				if not url:
					logger.warning("Ignoring calendar '%s' (missing url)" % section_name)
					continue

				calconf = CalendarConfig(name=section_name, url=url,
										 username=self.get_option(section_name, 'username'),
										 password=self.get_option(section_name, 'password'))
				self._calendar.append(calconf)

		return self._calendar

	@property
	@max_value(datetime.timedelta(minutes=180))
	@timediff
	def warmup_duration(self):
		return self.get_int('GENERAL', 'warmup', 30)

	@property
	@max_value(30)
	@min_value(5)
	def high_temperature(self):
		return self.get_int('GENERAL', 'high_temperature', 24)

	@property
	@max_value(30)
	@min_value(5)
	def low_temperature(self):
		return self.get_int('GENERAL', 'low_temperature', 10)

	@property
	def cube_serial(self):
		return self.get_option('cube', 'serial')

	@property
	def cube_address(self):
		return self.get_option('cube', 'address')

	@property
	def cube_port(self):
		return self.get_int('cube', 'port', None)

	@property
	def cube_timezone(self):
		return self.get_option('cube', 'timezone')

	@property
	def static_schedule(self):
		if self._static is None:
			schedule = {}

			for weekday, name in (
				(0, 'monday'),
				(1, 'tuesday'),
				(2, 'wednesday'),
				(3, 'thursday'),
				(4, 'friday'),
				(5, 'saturday'),
				(6, 'sunday'),
			):
				s = self.get_option('static', name)
				schedule[weekday] = [
					(datetime.time(a, b), datetime.time(c, d)) for a, b, c, d in time_range(s)
				]
			self._static = schedule

		return self._static

	@property
	def room_id(self):
		return self.get_int('room', 'id')

	@property
	def room_name(self):
		return self.get_int('room', 'name')

	@property
	def room_rf_addr(self):
		return self.get_int('room', 'rf_addr')

	@property
	def has_room_settings(self):
		return self.room_id or self.room_name or self.room_rf_addr

	@property
	def allday_range(self):
		a, b, c, d = list(time_range(self.get_option('GENERAL', 'allday', '06:00 - 23:00')))[0]
		return datetime.time(a, b), datetime.time(c, d)
