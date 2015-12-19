# -*- coding: utf-8 -*-
import threading

import time


class Worker(threading.Thread):

	def __init__(self, config, *args, **kwargs):
		super(Worker, self).__init__(*args, **kwargs)
		self.config = config

	def run(self):  # pragma: nocover
		self.execute()

	def execute(self):
		pass