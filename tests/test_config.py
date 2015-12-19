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
