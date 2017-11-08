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

import six
from jaeger_client import SpanContext
from jaeger_client.codecs import Codec


TRACE_ID_NAME = 'X-B3-TraceId'
SPAN_ID_NAME = 'X-B3-SpanId'
PARENT_SPAN_ID_NAME = 'X-B3-ParentSpanId'
SAMPLED_NAME = 'X-B3-Sampled'
FLAGS_NAME = 'X-B3-Flags'
# NOTE: uber's flags aren't the same as B3/Finagle ones
SAMPLED_FLAG = 1
DEBUG_FLAG = 2


def to_lower_hex(v):
    if (v >> 64) == 0:
        return '{:016x}'.format(v)
    return '{:032x}'.format(v)


def from_lower_hex(v):
    return int(v, 16)


def _extract_trace_id(v, span_context):
    span_context.trace_id = from_lower_hex(v)


def _extract_span_id(v, span_context):
    span_context.span_id = from_lower_hex(v)


def _extract_parent_span_id(v, span_context):
    span_context.parent_id = from_lower_hex(v)


def _extract_sampled(v, span_context):
    if v == '1' or v == 'true':
        span_context.flags |= SAMPLED_FLAG


def _extract_flags(v, span_context):
    if v == '1':
        span_context.flags |= DEBUG_FLAG


class B3Codec(Codec):
    _extractors = {
        TRACE_ID_NAME.lower(): _extract_trace_id,
        SPAN_ID_NAME.lower(): _extract_span_id,
        PARENT_SPAN_ID_NAME.lower(): _extract_parent_span_id,
        SAMPLED_NAME.lower(): _extract_sampled,
        FLAGS_NAME.lower(): _extract_flags,
    }

    def inject(self, span_context, carrier):
        carrier[TRACE_ID_NAME] = to_lower_hex(span_context.trace_id)
        if span_context.parent_id:
            carrier[PARENT_SPAN_ID_NAME] = to_lower_hex(
                span_context.parent_id)
        carrier[SPAN_ID_NAME] = to_lower_hex(span_context.span_id)
        if span_context.flags & SAMPLED_FLAG == SAMPLED_FLAG:
            carrier[SAMPLED_NAME] = '1'
        if span_context.flags & DEBUG_FLAG == DEBUG_FLAG:
            carrier[FLAGS_NAME] = '1'

    def extract(self, carrier):
        span_context = SpanContext(trace_id=None, span_id=None,
                                   parent_id=None, flags=0)
        for k, v in six.iteritems(carrier):
            k = k.lower()
            extractor = self._extractors.get(k)
            if six.callable(extractor) and v is not None:
                extractor(v, span_context)

        if span_context.trace_id is None or span_context.span_id is None:
            return None
        return span_context
