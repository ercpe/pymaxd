# -*- coding: utf-8 -*-
import logging
from argparse import ArgumentParser

from maxd.config import Configuration
from maxd.worker import Worker

logger = logging.getLogger(__name__)

class Daemon(object):

	def __init__(self, config_file, *args, **kwargs):
		super(Daemon, self).__init__(*args, **kwargs)
		self.config_file = config_file
		self.worker = None

	def run(self):
		exit = False

		while not exit:
			config = Configuration(self.config_file)
			self.worker = Worker(config)

			try:
				self.worker.start()
				self.worker.join()
			except:
				logger.exception("")
				exit = True

if __name__ == "__main__":  # pragma: nocover

	parser = ArgumentParser()
	parser.add_argument('-c', '--config')

	args = parser.parse_args()

	d = Daemon(args.config)
	d.run()

