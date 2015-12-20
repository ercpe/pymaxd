# -*- coding: utf-8 -*-
import collections
import logging

try:
	from ConfigParser import ConfigParser
except ImportError: # pragma: no cover
	from configparser import ConfigParser

logger = logging.getLogger(__name__)

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
		self.reload()

	def reload(self):
		self.cfg_parser = ConfigParser()
		if not self.cfg_parser.read(self.path) == [self.path]:
			raise Exception("Failed to read configuration file %s" % self.path)

	def get_option(self, section, option, default=None):
		return self.cfg_parser.get(section, option) if self.cfg_parser.has_option(section, option) else default

	@property
	def calendar(self):
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
