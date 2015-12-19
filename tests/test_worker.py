# -*- coding: utf-8 -*-
from maxd.config import Configuration
from maxd.worker import Worker


class TestWorker(object):

	def test_execute(self):
		config = Configuration('tests/fixtures/config/basic.cfg')
		w = Worker(config)
		w.execute()