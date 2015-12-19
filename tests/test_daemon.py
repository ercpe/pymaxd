# -*- coding: utf-8 -*-
from maxd.__main__ import Daemon


class TestDaemon(object):

	def test_constructor(self):
		d = Daemon()

	def test_run(self):
		d = Daemon()
		d.run()
