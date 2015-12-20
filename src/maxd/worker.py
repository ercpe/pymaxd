# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)

class Worker(object):

	def __init__(self, config):
		self.config = config
		self.exception = None

	def execute(self):
		logger.info("Running...")

	def fetch_events(self, calendar_config):
		pass
