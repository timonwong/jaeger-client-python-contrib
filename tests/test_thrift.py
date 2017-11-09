from future import standard_library  # isort:skip
standard_library.install_aliases()  # isort:skip
from io import BytesIO  # isort:skip

import os
from builtins import int

from jaeger_client import Span, SpanContext
from jaeger_client.thrift_gen.agent import Agent
from jaeger_client_contrib import thrift
from opentracing import child_of
from thrift.protocol.TCompactProtocol import TCompactProtocol
from thrift.transport.TTransport import TMemoryBuffer


def test_submit_batch(tracer):
    span = tracer.start_span("test-span")
    # add both types of annotations
    span.set_tag('bender', 'is great')
    span.set_tag('peer.ipv4', 123123)
    span.log_event('kiss-my-shiny-metal-...')
    span.finish()  # to get the duration defined
    # verify that we can serialize the span
    _marshall_span(span)


def _marshall_span(span):
    class TestTrans(TMemoryBuffer):
        def now_reading(self):
            """
            Thrift TMemoryBuffer is not read-able AND write-able,
            it's one or the other (really? yes.). This will convert
            us from write-able to read-able.
            """
            self._buffer = BytesIO(self.getvalue())

    spans = thrift.make_zipkin_spans([span])

    # write and read them to test encoding
    args = Agent.emitZipkinBatch_args(spans)
    t = TestTrans()
    prot = TCompactProtocol(t)
    args.write(prot)
    t.now_reading()
    args.read(prot)


def test_trace_ids(tracer):

    def serialize(trace_id):
        parent_ctx = SpanContext(trace_id=trace_id, span_id=int.from_bytes(os.urandom(8)),
                                 parent_id=0, flags=1)
        parent = Span(context=parent_ctx, operation_name='x', tracer=tracer)
        span = tracer.start_span(operation_name='x',
                                 references=child_of(parent.context))
        span.finish()
        _marshall_span(span)

    # 64bit ids
    trace_id = 0
    serialize(trace_id)
    hi, lo = thrift.extract_from_trace_id(trace_id)
    assert thrift.id_to_int(hi) == 0
    assert thrift.id_to_int(lo) == 0

    trace_id = 0x77fd53dc6b437681
    serialize(trace_id)
    hi, lo = thrift.extract_from_trace_id(trace_id)
    assert thrift.id_to_int(hi) == 0
    assert thrift.id_to_int(lo) == 0x77fd53dc6b437681

    trace_id = 0x7fffffffffffffff
    serialize(trace_id)
    hi, lo = thrift.extract_from_trace_id(trace_id)
    assert thrift.id_to_int(hi) == 0
    assert thrift.id_to_int(lo) != 0

    trace_id = 0x8000000000000000
    serialize(trace_id)
    hi, lo = thrift.extract_from_trace_id(trace_id)
    assert thrift.id_to_int(hi) == 0
    assert thrift.id_to_int(lo) == -0x8000000000000000

    trace_id = 0x97fd53dc6b437681
    serialize(trace_id)
    hi, lo = thrift.extract_from_trace_id(trace_id)
    assert thrift.id_to_int(hi) == 0
    assert thrift.id_to_int(lo) != 0

    trace_id = (1 << 64) - 1
    assert trace_id == 0xffffffffffffffff
    serialize(trace_id)
    assert thrift.id_to_int(trace_id) == -1

    # 128bit ids
    trace_id = (1 << 128) - 1
    serialize(trace_id)
    hi, lo = thrift.extract_from_trace_id(trace_id)
    assert thrift.id_to_int(hi) == -1
    assert thrift.id_to_int(lo) == -1

    trace_id = 0x8000000000000000 << 64
    serialize(trace_id)
    hi, lo = thrift.extract_from_trace_id(trace_id)
    assert thrift.id_to_int(hi) == -0x8000000000000000
    assert thrift.id_to_int(lo) == 0
