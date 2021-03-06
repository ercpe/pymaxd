# -*- coding: utf-8 -*-
import datetime
import pytest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from maxd.config import Configuration, timediff, max_value, min_value, time_range


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

        cals = cfg.calendars
        assert cals == []  # first access => initialize
        assert id(cals) == id(cfg.calendars)  # second access => cached value

    def test_calendar_property_missing_values(self):
        cfg = Configuration('tests/fixtures/config/missing_values.cfg')
        assert len(cfg.calendars) == 0  # missing url

    def test_calendar_property(self):
        cfg = Configuration('tests/fixtures/config/basic2.cfg')
        assert len(cfg.calendars) == 2

        assert cfg.calendars[0].name == 'testcal1'
        assert cfg.calendars[0].url == 'http://localhost/test.ics'
        assert not cfg.calendars[0].auth
        assert cfg.calendars[0].username == cfg.calendars[0].password == None

        assert cfg.calendars[1].name == 'testcal2'
        assert cfg.calendars[1].url == 'http://localhost/test.ics'
        assert cfg.calendars[1].auth
        assert cfg.calendars[1].username == 'foo'
        assert cfg.calendars[1].password == 'bar'

    def test_basic_config(self):
        cfg = Configuration('tests/fixtures/config/basic.cfg')
        assert cfg.cfg_parser is not None

    def test_get_option(self):
        cfg = Configuration('tests/fixtures/config/basic2.cfg')
        assert cfg.get_option('GENERAL', 'calendars') == 'testcal1, testcal2'

    def test_get_option_default(self):
        cfg = Configuration('tests/fixtures/config/basic2.cfg')
        assert cfg.get_option('GENERAL', 'foo') is None
        assert cfg.get_option('GENERAL', 'foo', 'bar') == 'bar'
        assert cfg.get_option('does not exist', 'foo') is None
        assert cfg.get_option('does not exist', 'foo', 'bar') == 'bar'

    def test_get_option_default(self):
        cfg = Configuration('tests/fixtures/config/basic2.cfg')
        assert cfg.get_int('GENERAL', 'foo', 'bar') == 'bar'
        assert cfg.get_int('does not exist', 'foo', 'bar') == 'bar'

    def test_timediff_decorator(self):
        for s, td in [
            (10, datetime.timedelta(minutes=10)),
            (360, datetime.timedelta(minutes=360)),
            ("20", datetime.timedelta(minutes=20)),
            ("02:30", datetime.timedelta(hours=2, minutes=30)),
            ("2:3", datetime.timedelta(hours=2, minutes=3)),
            (datetime.timedelta(minutes=1), datetime.timedelta(minutes=1))
        ]:
            assert timediff(lambda: s)() == td, "'%s' does not parse into %s" % (s, td)

    def test_timediff_decorator_unparsable(self):
        with pytest.raises(ValueError):
            assert timediff(lambda: "lalala")()

    def test_warmup_duration(self):
        cfg = Configuration('tests/fixtures/config/basic2.cfg')
        assert cfg.warmup_duration == datetime.timedelta(minutes=30) # default value

    def test_max_value_decorator(self):
        @max_value(20)
        def test():
            return 10
        assert test() == 10

    def test_max_value_decorator_limit_to_max(self):
        @max_value(10)
        def test():
            return 20
        assert test() == 10

    def test_max_value_decorator_allow_none(self):
        @max_value(10)
        def test():
            return None
        assert test() is None

        @max_value(10, allow_none=False)
        def test():
            return None
        assert test() == 10

    def test_min_value_decorator(self):
        @min_value(5)
        def test():
            return 10
        assert test() == 10

    def test_min_value_decorator_limit_to_min(self):
        @min_value(10)
        def test():
            return 5
        assert test() == 10

    def test_min_value_decorator_none(self):
        @min_value(5)
        def test():
            return None
        assert test() is None

        @min_value(5, allow_none=False)
        def test2():
            return None
        assert test2() == 5

    def test_get_high_temperature_not_set(self):
        cfg = Configuration('/dev/null')
        assert cfg.high_temperature == 24

    def test_get_high_temperature_limited(self):
        cfg1 = Configuration('tests/fixtures/config/temperatures_high.cfg')
        assert cfg1.high_temperature is 30

        cfg2 = Configuration('tests/fixtures/config/temperatures_low.cfg')
        assert cfg2.high_temperature == 5

    def test_get_low_temperature_limited(self):
        cfg1 = Configuration('tests/fixtures/config/temperatures_high.cfg')
        assert cfg1.low_temperature is 30

        cfg2 = Configuration('tests/fixtures/config/temperatures_low.cfg')
        assert cfg2.low_temperature == 5

    def test_get_static_schedule_not_set(self):
        cfg1 = Configuration('/dev/null')
        assert cfg1.static_schedule == { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], }

        cfg2 = Configuration('/dev/null')
        cfg2.cfg_parser.readfp(StringIO("""
[static]
monday =
tuesday =
wednesday =
thursday =
friday =
saturday =
sunday =
"""))
        assert cfg2.static_schedule == { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], }

    def test_get_static_schedule(self):
        cfg1 = Configuration('/dev/null')
        cfg1.cfg_parser.readfp(StringIO("""
[static]
monday = 08:00 - 10:00
"""))
        assert cfg1.static_schedule == { 0: [
            (datetime.time(8, 0), datetime.time(10, 0)),
        ], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], }

    def test_time_range(self):
        assert list(time_range('')) == []
        assert list(time_range(None)) == []

        for bad in ('foobar', 'ab:cd', '123:456', '123:456 789:012', '1 2', '12:34 56:78'):
            with pytest.raises(ValueError):
                list(time_range(bad))

        assert list(time_range('10:00-11:00')) == [(10, 00, 11, 00)]
        assert list(time_range('10:00 - 11:00')) == [(10, 00, 11, 00)]
        assert list(time_range('77:88-99:00')) == [(77, 88, 99, 00)]

        assert list(time_range('08:30 - 09:00, 05:15-17:00')) == [
            (8, 30, 9, 0),
            (5, 15, 17, 00),
        ]

        assert list(time_range('08:30 - 09:00,')) == [(8, 30, 9, 0)]
