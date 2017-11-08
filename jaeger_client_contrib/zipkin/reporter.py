# Copyright (c) 2016 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import logging

import six
import tornado.gen
import tornado.ioloop
import tornado.queues
from jaeger_client import ioloop_util
from jaeger_client.constants import DEFAULT_FLUSH_INTERVAL
from jaeger_client.metrics import LegacyMetricsFactory, Metrics
from jaeger_client.reporter import NullReporter, ReporterMetrics
from jaeger_client.utils import ErrorReporter

from ..thrift import make_zipkin_spans, thrift_objs_in_bytes


default_logger = logging.getLogger('jaeger_tracing')


class ZipkinReporter(NullReporter):
    """Receives completed spans from Tracer and submits them out of process."""

    def __init__(self, transport_handler, queue_capacity=100, batch_size=10,
                 flush_interval=DEFAULT_FLUSH_INTERVAL, io_loop=None,
                 error_reporter=None, metrics_factory=None,
                 **kwargs):
        """
        :param transport_handler: Callback function that takes a message
            parameter and handles logging it
        :param queue_capacity: how many spans we can hold in memory before
            starting to drop spans
        :param batch_size: how many spans we can submit at once to Collector
        :param flush_interval: how often the auto-flush is called (in seconds)
        :param io_loop: which IOLoop to use.
        :param error_reporter:
        :param metrics_factory: an instance of MetricsFactory class, or None.
        :param kwargs:
            'logger'
        :return:
        """
        from threading import Lock

        self.transport_handler = transport_handler
        self.queue_capacity = queue_capacity
        self.batch_size = batch_size
        self.metrics_factory = metrics_factory or \
            LegacyMetricsFactory(Metrics())
        self.metrics = ReporterMetrics(self.metrics_factory)
        self.error_reporter = error_reporter or ErrorReporter(Metrics())
        self.logger = kwargs.get('logger', default_logger)

        if queue_capacity < batch_size:
            raise ValueError('Queue capacity cannot be less than batch size')

        self.io_loop = io_loop
        if self.io_loop is None:
            self.logger.error('Zipkin Reporter has no IOLoop')
        elif not six.callable(self.transport_handler):
            self.logger.error('Zipkin Reporter has no transport handler')
        else:
            self.queue = tornado.queues.Queue(maxsize=queue_capacity)
            self.stop = object()
            self.stopped = False
            self.stop_lock = Lock()
            self.flush_interval = flush_interval or None

            self.io_loop.spawn_callback(self._consume_queue)

    def report_span(self, span):
        # We should not be calling `queue.put_nowait()` from random threads,
        # only from the same IOLoop where the queue is consumed (T333431).
        if tornado.ioloop.IOLoop.current(instance=False) == self.io_loop:
            self._report_span_from_ioloop(span)
        else:
            self.io_loop.add_callback(self._report_span_from_ioloop, span)

    def _report_span_from_ioloop(self, span):
        try:
            with self.stop_lock:
                stopped = self.stopped
            if stopped:
                self.metrics.reporter_dropped(1)
            else:
                self.queue.put_nowait(span)
        except tornado.queues.QueueFull:
            self.metrics.reporter_dropped(1)

    @tornado.gen.coroutine
    def _consume_queue(self):
        spans = []
        stopped = False
        while not stopped:
            while len(spans) < self.batch_size:
                try:
                    # using timeout allows periodic flush with smaller packet
                    timeout = self.flush_interval + self.io_loop.time() \
                        if self.flush_interval and spans else None
                    span = yield self.queue.get(timeout=timeout)
                except tornado.gen.TimeoutError:
                    break
                else:
                    if span == self.stop:
                        stopped = True
                        self.queue.task_done()
                        # don't return yet, submit accumulated spans first
                        break
                    else:
                        spans.append(span)
            if spans:
                yield self._submit(spans)
                for _ in spans:
                    self.queue.task_done()
                spans = spans[:0]
        self.logger.info('Span publisher exists')

    @tornado.gen.coroutine
    def _submit(self, spans):
        if not spans:
            return
        try:
            spans = make_zipkin_spans(spans)
            yield self._send(spans)
            self.metrics.reporter_success(len(spans))
        except Exception as e:
            self.metrics.reporter_failure(len(spans))
            self.error_reporter.error(
                'Failed to submit trace to transport: %s', e)

    @tornado.gen.coroutine
    def _send(self, spans):
        """Send spans out.

        Any exceptions thrown will be caught above in the _submit exception
        handler.'''

        :param spans:
        :return:
        """
        message = thrift_objs_in_bytes(spans)
        self.transport_handler(message)

    def close(self):
        """
        Ensure that all spans from the queue are submitted.
        Returns Future that will be completed once the queue is empty.
        """
        with self.stop_lock:
            self.stopped = True

        return ioloop_util.submit(self._flush, io_loop=self.io_loop)

    @tornado.gen.coroutine
    def _flush(self):
        yield self.queue.put(self.stop)
        yield self.queue.join()
