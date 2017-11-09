import mock
import pytest
from jaeger_client import ConstSampler, Tracer


@pytest.fixture(scope='function')
def tracer():
    reporter = mock.MagicMock()
    sampler = ConstSampler(True)
    return Tracer(
        service_name='test_service_1', reporter=reporter, sampler=sampler)
