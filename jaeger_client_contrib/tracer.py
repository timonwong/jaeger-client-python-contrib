from __future__ import absolute_import

import os
import uuid
from builtins import int

import jaeger_client
import six
from jaeger_client import Span, SpanContext
from jaeger_client.span import DEBUG_FLAG, SAMPLED_FLAG
from opentracing.ext import tags as ext_tags


class Tracer(jaeger_client.Tracer):
    def random_trace_id(self):
        return uuid.uuid1().int

    def random_id(self):
        return int.from_bytes(os.urandom(8))

    def start_span(self,
                   operation_name=None,
                   child_of=None,
                   references=None,
                   tags=None,
                   start_time=None):
        """
        Start and return a new Span representing a unit of work.

        :param operation_name: name of the operation represented by the new
            span from the perspective of the current service.
        :param child_of: shortcut for 'child_of' reference
        :param references: (optional) either a single Reference object or a
            list of Reference objects that identify one or more parent
            SpanContexts. (See the Reference documentation for detail)
        :param tags: optional dictionary of Span Tags. The caller gives up
            ownership of that dictionary, because the Tracer may use it as-is
            to avoid extra data copying.
        :param start_time: an explicit Span start time as a unix timestamp per
            time.time()

        :return: Returns an already-started Span instance.
        """
        parent = child_of
        if references:
            if isinstance(references, list):
                # TODO(XXX) only the first reference is currently used
                references = references[0]
            parent = references.referenced_context

        # allow Span to be passed as reference, not just SpanContext
        if isinstance(parent, Span):
            parent = parent.context

        rpc_server = tags and \
            tags.get(ext_tags.SPAN_KIND) == ext_tags.SPAN_KIND_RPC_SERVER

        if parent is None or parent.is_debug_id_container_only:
            trace_id = self.random_trace_id()
            span_id = self.random_id()
            parent_id = None
            flags = 0
            baggage = None
            if parent is None:
                sampled, sampler_tags = \
                    self.sampler.is_sampled(trace_id, operation_name)
                if sampled:
                    flags = SAMPLED_FLAG
                    tags = tags or {}
                    for k, v in six.iteritems(sampler_tags):
                        tags[k] = v
            else:  # have debug id
                flags = SAMPLED_FLAG | DEBUG_FLAG
                tags = tags or {}
                tags[self.debug_id_header] = parent.debug_id
        else:
            trace_id = parent.trace_id
            if rpc_server and self.one_span_per_rpc:
                # Zipkin-style one-span-per-RPC
                span_id = parent.span_id
                parent_id = parent.parent_id
            else:
                span_id = self.random_id()
                parent_id = parent.span_id
            flags = parent.flags
            baggage = dict(parent.baggage)

        span_ctx = SpanContext(trace_id=trace_id, span_id=span_id,
                               parent_id=parent_id, flags=flags,
                               baggage=baggage)
        span = Span(context=span_ctx, tracer=self,
                    operation_name=operation_name,
                    tags=tags, start_time=start_time)

        if (rpc_server or not parent_id) and (flags & SAMPLED_FLAG):
            # this is a first-in-process span, and is sampled
            for k, v in six.iteritems(self.tags):
                span.set_tag(k, v)

        self._emit_span_metrics(span=span, join=rpc_server)

        return span
