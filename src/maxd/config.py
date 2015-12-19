# -*- coding: utf-8 -*-

try:
	from ConfigParser import ConfigParser
except ImportError: # pragma: no cover
	from configparser import ConfigParser

class Configuration(object):

	def __init__(self, config_path):
		self.path = config_path
		self.cfg_parser = None
		self.reload()

	def reload(self):
		self.cfg_parser = ConfigParser()
		if not self.cfg_parser.read(self.path) == [self.path]:
			raise Exception("Failed to read configuration file %s" % self.path)
