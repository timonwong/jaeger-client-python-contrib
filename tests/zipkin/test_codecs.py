from __future__ import absolute_import

import unittest

from jaeger_client import SpanContext
from jaeger_client_contrib.zipkin import codecs


class TestB3Codec(unittest.TestCase):
    def test_to_lower_hex(self):
        assert '0' * 16 == codecs.to_lower_hex(0)
        assert ('0' * 15) + ('f' * 17) == \
            codecs.to_lower_hex(0xfffffffffffffffffL)

    def test_from_lower_hex(self):
        assert 1 == codecs.from_lower_hex(('0' * 15) + '1')
        assert 0x80000000000000000L == \
            codecs.from_lower_hex(('0' * 15) + '8' + ('0' * 16))

    def test_extract_root_span(self):
        codec = codecs.B3Codec()
        carrier = self._make_b3_carrier(trace_id=1, span_id=1, parent_id=0,
                                        flags=codecs.SAMPLED_FLAG)
        context = codec.extract(carrier)
        assert 1 == context.trace_id
        assert 0 == context.parent_id
        assert 1 == context.span_id
        assert 1 == context.flags  # sampled

    def test_extract_child_span(self):
        codec = codecs.B3Codec()
        carrier = self._make_b3_carrier(trace_id=1, span_id=2, parent_id=1,
                                        flags=codecs.SAMPLED_FLAG)
        context = codec.extract(carrier)
        assert 1 == context.trace_id
        assert 1 == context.parent_id
        assert 2 == context.span_id
        assert 1 == context.flags  # sampled

    def test_extract_unsampled(self):
        codec = codecs.B3Codec()
        carrier = self._make_b3_carrier(trace_id=None, span_id=None,
                                        parent_id=None, flags=None)
        context = codec.extract(carrier)
        assert context is None

    def test_inject_root_span(self):
        codec = codecs.B3Codec()
        span_context = SpanContext(trace_id=1, span_id=1, parent_id=0,
                                   flags=codecs.SAMPLED_FLAG)
        carrier = {}
        codec.inject(span_context, carrier)
        assert codecs.to_lower_hex(1) == carrier[codecs.TRACE_ID_NAME]
        assert codecs.to_lower_hex(1) == carrier[codecs.SPAN_ID_NAME]
        assert codecs.PARENT_SPAN_ID_NAME not in carrier
        assert '1' == carrier[codecs.SAMPLED_NAME]

    def test_inject_child_span(self):
        codec = codecs.B3Codec()
        span_context = SpanContext(trace_id=1, span_id=2, parent_id=1,
                                   flags=codecs.SAMPLED_FLAG)
        carrier = {}
        codec.inject(span_context, carrier)
        assert codecs.to_lower_hex(1) == carrier[codecs.TRACE_ID_NAME]
        assert codecs.to_lower_hex(2) == carrier[codecs.SPAN_ID_NAME]
        assert codecs.to_lower_hex(1) == carrier[codecs.PARENT_SPAN_ID_NAME]
        assert '1' == carrier[codecs.SAMPLED_NAME]

    def test_inject_unsampled(self):
        codec = codecs.B3Codec()
        span_context = SpanContext(trace_id=1, span_id=1, parent_id=0, flags=0)
        carrier = {}
        codec.inject(span_context, carrier)
        assert '1' != carrier.get(codecs.SAMPLED_FLAG)

    def _make_b3_carrier(self, trace_id, span_id, parent_id, flags):
        carrier = {}
        if trace_id is not None:
            carrier[codecs.TRACE_ID_NAME] = codecs.to_lower_hex(trace_id)
        if span_id is not None:
            carrier[codecs.SPAN_ID_NAME] = codecs.to_lower_hex(span_id)
        if parent_id is not None:
            carrier[codecs.PARENT_SPAN_ID_NAME] = \
                codecs.to_lower_hex(parent_id)
        if flags:
            if flags & codecs.SAMPLED_FLAG:
                carrier[codecs.SAMPLED_NAME] = '1'
            if flags & codecs.DEBUG_FLAG:
                carrier[codecs.FLAGS_NAME] = '1'
        return carrier
