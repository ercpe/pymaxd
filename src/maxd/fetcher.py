# -*- coding: utf-8 -*-
from icalendar import Calendar
from cachecontrol import CacheControl
import requests
from requests.auth import HTTPBasicAuth

class EventFetcher(object):

    def fetch(self, calendar_config):
        raise NotImplementedError  # pragma: nocover


class LocalCalendarEventFetcher(EventFetcher):

    def fetch(self, calendar_config):
        with open(calendar_config.url, 'r') as f:
            calendar = Calendar.from_ical(f.read())
            for item in calendar.walk():
                if item.name != "VEVENT":
                    continue

                yield item


class HTTPCalendarEventFetcher(EventFetcher):

    def __init__(self):
        self.session = CacheControl(requests.session())

    def fetch(self, calendar_config):
        req_kwargs = {
            'headers': {
                'Accept': 'text/calendar'
            }
        }
        if calendar_config.auth:
            req_kwargs['auth'] = HTTPBasicAuth(calendar_config.username, calendar_config.password)

        response = self.session.get(calendar_config.url, **req_kwargs)
        response.raise_for_status()

        calendar = Calendar.from_ical(response.content)
        for item in calendar.walk():
            if item.name != "VEVENT":
                continue

            yield item
