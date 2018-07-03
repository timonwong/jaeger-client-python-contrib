from __future__ import absolute_import

import socket
import struct

import jaeger_client.thrift_gen.zipkincore.ZipkinCollector as zipkin_collector
import six

from .thrift_gen.zipkincore.constants import (CLIENT_ADDR, CLIENT_RECV,
                                              CLIENT_SEND, LOCAL_COMPONENT,
                                              SERVER_ADDR, SERVER_RECV,
                                              SERVER_SEND)

_max_signed_port = (1 << 15) - 1
_max_unsigned_port = (1 << 16)
_max_signed_id = (1 << 63) - 1
_max_unsigned_id = (1 << 64)

if six.PY3:
    long = int


def make_event(timestamp, name):
    return zipkin_collector.Annotation(
        timestamp=timestamp_micros(timestamp), value=name, host=None)


def timestamp_micros(ts):
    """
    Convert a float Unix timestamp from time.time() into a long value
    in microseconds, as required by Zipkin protocol.
    :param ts:
    :return:
    """
    return long(ts * 1000000)


def ipv4_to_int(ipv4):
    if ipv4 == 'localhost':
        ipv4 = '127.0.0.1'
    elif ipv4 == '::1':
        ipv4 = '127.0.0.1'
    try:
        return struct.unpack('!i', socket.inet_aton(ipv4))[0]
    except:
        return 0


def port_to_int(port):
    if type(port) is str:
        if port.isdigit():
            port = int(port)
    if type(port) is int:
        # zipkincore.thrift defines port as i16, which is signed,
        # therefore we convert ephemeral ports as negative ints
        if port > _max_signed_port:
            port -= _max_unsigned_port
        return port
    return None


def id_to_int(big_id):
    if big_id is None:
        return None
    # zipkincore.thrift defines ID fields as i64, which is signed,
    # therefore we convert large IDs (> 2^63) to negative longs
    if big_id > _max_signed_id:
        big_id -= _max_unsigned_id
    return big_id


def make_endpoint(ipv4, port, service_name):
    if isinstance(ipv4, basestring):
        ipv4 = ipv4_to_int(ipv4)
    port = port_to_int(port)
    if port is None:
        port = 0
    return zipkin_collector.Endpoint(ipv4, port, service_name.lower())


def make_peer_address_tag(key, host):
    """
    Used for Zipkin binary annotations like CA/SA (client/server address).
    They are modeled as Boolean type with '0x01' as the value.
    :param key:
    :param host:
    """
    return zipkin_collector.BinaryAnnotation(
        key, '0x01', zipkin_collector.AnnotationType.BOOL, host)


def make_local_component_tag(component_name, endpoint):
    """
    Used for Zipkin binary annotation LOCAL_COMPONENT.
    :param component_name:
    :param endpoint:
    """
    return zipkin_collector.BinaryAnnotation(
        key=LOCAL_COMPONENT, value=component_name,
        annotation_type=zipkin_collector.AnnotationType.STRING,
        host=endpoint)


def add_zipkin_annotations(span, endpoint):
    if span.is_rpc():
        is_client = span.is_rpc_client()

        end_event = CLIENT_RECV if is_client else SERVER_SEND
        end_event = make_event(timestamp=span.end_time, name=end_event)
        end_event.host = endpoint
        span.logs.append(end_event)

        start_event = CLIENT_SEND if is_client else SERVER_RECV
        start_event = make_event(timestamp=span.start_time, name=start_event)
        start_event.host = endpoint
        span.logs.append(start_event)

        if span.peer:
            host = make_endpoint(
                ipv4=span.peer.get('ipv4', 0),
                port=span.peer.get('port', 0),
                service_name=span.peer.get('service_name', ''))
            key = SERVER_ADDR if is_client else CLIENT_ADDR
            peer = make_peer_address_tag(key=key, host=host)
            span.tags.append(peer)
    else:
        lc = make_local_component_tag(
            component_name=span.component or span.tracer.service_name,
            endpoint=endpoint)
        span.tags.append(lc)
