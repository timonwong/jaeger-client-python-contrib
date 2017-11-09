import functools

from jaeger_client import ProbabilisticSampler

__all__ = ('ProbabilisticSampler',)


@functools.wraps(ProbabilisticSampler.is_sampled)
def _is_sampled(self, trace_id, operation=''):
    trace_id &= 0xffffffffffffffff
    return trace_id < self.boundary, self._tags


# Ugly, but instead of sub-classing all related sampler classes, it should be OK.
ProbabilisticSampler.is_sampled = _is_sampled
