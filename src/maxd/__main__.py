# -*- coding: utf-8 -*-
import logging
import signal
from argparse import ArgumentParser
from logging.handlers import SysLogHandler

logger = logging.getLogger(__name__)

from maxd.daemon import Daemon

if __name__ == "__main__":  # pragma: nocover
	parser = ArgumentParser()
	parser.add_argument('-c', '--config', default='/etc/maxd.cfg', help="Config file to use (default: %(default)s)")
	parser.add_argument('-v', '--verbose', action="count", default=1)

	parser.add_argument('--log-target', default='syslog')

	args = parser.parse_args()

	if args.log_target == 'syslog':
		logging.basicConfig(level=logging.FATAL - (10 * args.verbose), format='maxd: [%(levelname)s] %(message)s',
							handlers=(SysLogHandler('/dev/log', facility=SysLogHandler.LOG_DAEMON), ))
	else:
		logging.basicConfig(level=logging.FATAL - (10 * args.verbose), format='%(asctime)s %(levelname)-7s %(message)s')

	daemon = None

	def stop_daemon(signum, frame):
		if daemon:
			logger.debug("Stopping daemon")
			daemon.stop()

	signal.signal(signal.SIGTERM, stop_daemon)
	signal.signal(signal.SIGINT, stop_daemon)

	daemon = Daemon(args.config)
	daemon.run()
