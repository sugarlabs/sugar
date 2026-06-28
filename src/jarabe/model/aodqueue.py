# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import queue
import threading


_MAX_QUEUED_JOBS = 64


class AODJobQueue:
    """Small local worker queue for Activity-on-Demand jobs."""

    def __init__(self, runner, worker_count=1, max_queued=_MAX_QUEUED_JOBS):
        self._runner = runner
        self._worker_count = max(1, worker_count)
        self._queue = queue.Queue(maxsize=max_queued)
        self._workers = []
        self._shutdown = threading.Event()
        self._lock = threading.Lock()

    def submit(self, job):
        self.start()
        try:
            self._queue.put_nowait(job)
        except queue.Full:
            raise RuntimeError(
                'Activity-on-Demand job queue is full (%d pending). '
                'Wait for running jobs to finish before submitting more.'
                % self._queue.maxsize
            )

    def start(self):
        with self._lock:
            if self._workers:
                return
            self._shutdown.clear()
            for index in range(self._worker_count):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name='AODWorker-%d' % (index + 1),
                    daemon=True,
                )
                self._workers.append(worker)
                worker.start()

    def join(self):
        self._queue.join()

    def shutdown(self, wait=True):
        with self._lock:
            if not self._workers:
                return
            self._shutdown.set()
            for unused in self._workers:
                self._queue.put(None)
            workers = list(self._workers)
            self._workers = []

        if wait:
            for worker in workers:
                worker.join(timeout=2)

    def _worker_loop(self):
        while not self._shutdown.is_set():
            job = self._queue.get()
            try:
                if job is None:
                    return
                self._runner(job)
            except Exception:
                logging.exception('Activity-on-Demand worker crashed')
            finally:
                self._queue.task_done()
