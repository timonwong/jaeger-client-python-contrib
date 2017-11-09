import random

import pytest
from jaeger_client_contrib import ProbabilisticSampler

MAX_INT = 1 << 63


def get_tags(type, param):
    return {
        'sampler.type': type,
        'sampler.param': param,
    }


def test_probabilistic_sampler_errors():
    with pytest.raises(AssertionError):
        ProbabilisticSampler(-0.1)
    with pytest.raises(AssertionError):
        ProbabilisticSampler(1.1)


def test_probabilistic_sampler():
    # 64bit ids
    sampler = ProbabilisticSampler(0.5)
    assert MAX_INT == 0x8000000000000000
    sampled, tags = sampler.is_sampled(MAX_INT - 10)
    assert sampled
    assert tags == get_tags('probabilistic', 0.5)

    sampled, _ = sampler.is_sampled(MAX_INT + 10)
    assert not sampled
    sampler.close()
    assert '%s' % sampler == 'ProbabilisticSampler(0.5)'

    # 128bit ids
    hi = random.randint(0, 0xffffffffffffffff) << 64
    sampled, tags = sampler.is_sampled(hi + MAX_INT - 10)
    assert sampled
    assert tags == get_tags('probabilistic', 0.5)

    sampled, _ = sampler.is_sampled(hi + MAX_INT + 10)
    assert not sampled
    sampler.close()
    assert '%s' % sampler == 'ProbabilisticSampler(0.5)'


def test_sampler_equality():
    prob1 = ProbabilisticSampler(rate=0.01)
    prob2 = ProbabilisticSampler(rate=0.01)
    prob3 = ProbabilisticSampler(rate=0.02)
    assert prob1 == prob2
    assert prob1 != prob3
