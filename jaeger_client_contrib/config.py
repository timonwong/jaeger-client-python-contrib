from __future__ import absolute_import

import logging

from jaeger_client import config as base_config
from jaeger_client import ConstSampler
from jaeger_client.reporter import CompositeReporter, LoggingReporter
from opentracing import Format

from . import Tracer
from .zipkin.codecs import B3Codec
from .zipkin.reporter import ZipkinReporter

logger = logging.getLogger('jaeger_tracing')


class Config(base_config.Config):
    def initialize_tracer(self, transport_handler=None, io_loop=None):  # pragma: nocover
        """
        Initialize Jaeger Tracer based on the passed `jaeger_client.Config`.
        Save it to `opentracing.tracer` global variable.
        Only the first call to this method has any effect.
        """

        with Config._initialized_lock:
            if Config._initialized:
                logger.warn('Jaeger tracer already initialized, skipping')
                return
            Config._initialized = True

        sampler = self.sampler
        if sampler is None:
            sampler = ConstSampler(True)
        logger.info('Using sampler %s', sampler)

        reporter = ZipkinReporter(
            transport_handler=transport_handler,
            io_loop=io_loop,
            queue_capacity=self.reporter_queue_size,
            batch_size=self.reporter_batch_size,
            flush_interval=self.reporter_flush_interval,
            logger=logger,
            metrics_factory=self._metrics_factory,
            error_reporter=self.error_reporter
        )

        if self.logging:
            reporter = CompositeReporter(reporter, LoggingReporter(logger))

        tracer = self.create_tracer(reporter=reporter, sampler=sampler,)
        self._initialize_global_tracer(tracer=tracer)
        return tracer

    def create_tracer(self, reporter, sampler):  # pragma: nocover
        extra_codecs = {
            Format.HTTP_HEADERS: B3Codec(),
        }
        return Tracer(
            service_name=self.service_name,
            reporter=reporter,
            sampler=sampler,
            metrics_factory=self._metrics_factory,
            trace_id_header=self.trace_id_header,
            baggage_header_prefix=self.baggage_header_prefix,
            debug_id_header=self.debug_id_header,
            extra_codecs=extra_codecs,
            tags=self.tags,
        )
