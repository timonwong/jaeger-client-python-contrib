from __future__ import absolute_import

import sys

# This is because thrift for python doesn't have 'package_prefix'.
# The thrift compiled libraries refer to each other relative to their subdir.
import jaeger_client.thrift_gen as modpath
sys.path.append(modpath.__path__[0])

__version__ = '0.1.1'

from .tracer import Tracer  # noqa
from .config import Config  # noqa
from .sampler import ProbabilisticSampler  # noqa
