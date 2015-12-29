# -*- coding: utf-8 -*-
from maxd.config import CalendarConfig
from maxd.fetcher import LocalCalendarEventFetcher, HTTPCalendarEventFetcher
import requests
import datetime
import pytz
import sys

if sys.version_info.major == 2 or (sys.version_info.major == 3 and sys.version_info.minor <= 2):
	from mock import Mock, patch
else:
	from unittest.mock import Mock, patch

class TestLocalFetcher(object):

	def test_local_fetcher(self):
		f = LocalCalendarEventFetcher()
		events = list(f.fetch(CalendarConfig(name='test', url='tests/fixtures/calendars/single_event.ics')))
		assert len(events) == 1

		event = events[0]

		assert event['SUMMARY'] == 'Test Event'
		assert event['DTSTART'].dt == datetime.datetime(2015, 12, 20, 9, 0, tzinfo=pytz.UTC)
		assert event['DTEND'].dt == datetime.datetime(2015, 12, 20, 10, 0, tzinfo=pytz.UTC)


class TestHTTPFetcher(object):

	def test_constructor(self):
		f = HTTPCalendarEventFetcher()
		assert isinstance(f.session, requests.sessions.Session)

	def test_fetch_without_auth(self):
		response_mock = Mock()
		with open('tests/fixtures/calendars/single_event.ics', 'r') as f:
			response_mock.content = f.read()

		f = HTTPCalendarEventFetcher()
		f.session = Mock()
		f.session.get = Mock(return_value=response_mock)

		response = list(f.fetch(CalendarConfig(name='test', url='http://example.com/test.ics')))
		f.session.get.assert_called_with('http://example.com/test.ics')
		assert len(response) == 1

	def test_fetch_with_auth(self):
		f = HTTPCalendarEventFetcher()
		f.session = Mock()

		def get_mock(*args, **kwargs): # stupid way to get around the not implemented __eq__ for HttpBasicAuth
			assert len(args) == 1 and args[0] == 'http://example.com/test.ics'
			assert len(kwargs) == 1 and 'auth' in kwargs and kwargs['auth'].username == 'foo' and kwargs['auth'].password == 'bar', \
					"A HTTPBasicAuth instance should be passed to requests"
			response_mock = Mock()
			with open('tests/fixtures/calendars/single_event.ics', 'r') as f:
				response_mock.content = f.read()
			return response_mock

		f.session.get = Mock(side_effect=get_mock)
		response = list(f.fetch(CalendarConfig(name='test', url='http://example.com/test.ics', username='foo', password='bar')))
		assert f.session.get.called
		assert len(response) == 1
