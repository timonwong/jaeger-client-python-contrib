from __future__ import absolute_import

from jaeger_client.thrift import (add_zipkin_annotations, id_to_int,
                                  make_endpoint, timestamp_micros)
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.Thrift import TType
from thrift.transport.TTransport import TMemoryBuffer

from .thrift_gen.zipkincore import ttypes as zipkin_types


def extract_from_trace_id(trace_id):
    """Extract high and low 64 bit parts from trace_id"""
    hi = trace_id >> 64
    lo = trace_id & 0xffffffffffffffff
    return hi, lo


def make_zipkin_spans(spans):
    zipkin_spans = []
    for span in spans:
        endpoint = make_endpoint(ipv4=span.tracer.ip_address,
                                 port=0,  # span.port,
                                 service_name=span.tracer.service_name)
        # TODO extend Zipkin Thrift and pass endpoint once only
        for event in span.logs:
            event.host = endpoint
        with span.update_lock:
            add_zipkin_annotations(span=span, endpoint=endpoint)
            hi, lo = extract_from_trace_id(span.trace_id)
            zipkin_span = zipkin_types.Span(
                trace_id=id_to_int(lo),
                trace_id_high=id_to_int(hi),
                name=span.operation_name,
                id=id_to_int(span.span_id),
                parent_id=id_to_int(span.parent_id) or None,
                annotations=span.logs,
                binary_annotations=span.tags,
                debug=span.is_debug(),
                timestamp=timestamp_micros(span.start_time),
                duration=timestamp_micros(span.end_time - span.start_time)
            )
        zipkin_spans.append(zipkin_span)
    return zipkin_spans


def thrift_objs_in_bytes(thrift_obj_list):  # pragma: no cover
    """
    Returns TBinaryProtocol encoded Thrift objects.

    :param thrift_obj_list: thrift objects list to encode
    :returns: thrift objects in TBinaryProtocol format bytes.
    """
    transport = TMemoryBuffer()
    protocol = TBinaryProtocol(transport)
    protocol.writeListBegin(TType.STRUCT, len(thrift_obj_list))
    for thrift_obj in thrift_obj_list:
        thrift_obj.write(protocol)
    return bytes(transport.getvalue())
