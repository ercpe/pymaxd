# -*- coding: utf-8 -*-
from maxd.__main__ import Daemon


class TestDaemon(object):

	def test_constructor(self):
		d = Daemon('tests/fixtures/config/basic.cfg')

