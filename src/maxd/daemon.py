# -*- coding: utf-8 -*-
import logging
import threading

import time

from maxd.config import Configuration
from maxd.worker import Worker

logger = logging.getLogger(__name__)

class WorkerThread(threading.Thread):

    def __init__(self, config_file, *args, **kwargs):
        super(WorkerThread, self).__init__(*args, **kwargs)
        self.config_file = config_file
        self.timer = None
        self.exit = threading.Event()

    def run(self):
        worker = Worker(Configuration(self.config_file))

        def _exec():
            try:
                worker.execute()
            except:
                logger.exception("Worker failure")

        _exec()
        while not self.exit.wait(10):
            _exec()

        logger.info("worker thread exiting")


class Daemon(object):

    def __init__(self, config_file, *args, **kwargs):
        super(Daemon, self).__init__(*args, **kwargs)
        self.config_file = config_file
        self.worker_thread = None

    def run(self):
        logger.info("Starting worker thread")
        self.worker_thread = WorkerThread(self.config_file)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        while True:
            time.sleep(1)
            if self.worker_thread.exit.is_set():
                logger.debug("Waiting for worker thread to exit..")
                self.worker_thread.join()
                break

    def stop(self):
        logger.debug("Stopping worker thread")
        self.worker_thread.exit.set()
        self.worker_thread.join()
        logger.debug("Worker Thread join()ed")
