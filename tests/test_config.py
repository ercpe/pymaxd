# -*- coding: utf-8 -*-
import pytest

from maxd.config import Configuration

class TestConfig(object):

	def test_missing_file(self):
		with pytest.raises(Exception):
			Configuration('/file/does/not/exist')

	def test_reload(self):
		cfg = Configuration('/dev/null')
		old_id = id(cfg.cfg_parser)
		cfg.reload()

		assert old_id != id(cfg.cfg_parser), "Configuration did not reload"
		assert cfg._calendar is None, "Calendar property not cleared on reload"

	def test_calendar_property_init(self):
		cfg = Configuration('tests/fixtures/config/basic.cfg')

		cals = cfg.calendar
		assert cals == []  # first access => initialize
		assert id(cals) == id(cfg.calendar)  # second access => cached value

	def test_calendar_property_missing_values(self):
		cfg = Configuration('tests/fixtures/config/missing_values.cfg')
		assert len(cfg.calendar) == 0  # missing url

	def test_calendar_property(self):
		cfg = Configuration('tests/fixtures/config/basic2.cfg')
		assert len(cfg.calendar) == 2

		assert cfg.calendar[0].name == 'testcal1'
		assert cfg.calendar[0].url == 'http://localhost/test.ics'
		assert not cfg.calendar[0].auth
		assert cfg.calendar[0].username == cfg.calendar[0].password == None

		assert cfg.calendar[1].name == 'testcal2'
		assert cfg.calendar[1].url == 'http://localhost/test.ics'
		assert cfg.calendar[1].auth
		assert cfg.calendar[1].username == 'foo'
		assert cfg.calendar[1].password == 'bar'

	def test_basic_config(self):
		cfg = Configuration('tests/fixtures/config/basic.cfg')
		assert cfg.cfg_parser is not None
