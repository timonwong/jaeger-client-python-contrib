#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re

from setuptools import setup, find_packages

version = None
with open('jaeger_client_contrib/__init__.py', 'r') as f:
    for line in f:
        m = re.match(r'^__version__\s*=\s*(["\'])([^"\']+)\1', line)
        if m:
            version = m.group(2)
            break

assert version is not None, \
    'Could not determine version number from jaeger_client_contrib/__init__.py'


long_description = ''
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()


setup(
    name='jaeger-client-contrib',
    version=version,
    url='https://github.com/timonwong/jaeger-client-python-contrib',
    description='Jaeger Python Client with Zipkin',
    long_description=long_description,
    author='Timon Wong',
    author_email='timon86.wang@gmail.com',
    packages=find_packages(exclude=['tests', 'example', 'tests.*']),
    include_package_data=True,
    license="MIT",
    zip_safe=False,
    keywords='jaeger tracing opentracing',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
    ],
    install_requires=[
        'jaeger-client',
        # we want thrift>=0.9.2.post1,<0.9.3, but we let the users pin to that
        'thrift',
        'tornado>=4.3,<5',
    ],
    test_suite='tests',
    extras_require={
        'tests': [
            'mock==1.0.1',
            'pytest>=2.7,<3',
            'pytest-cov',
            'coverage',
            'pytest-timeout',
            'pytest-tornado',
            'pytest-benchmark[histogram]>=3.0.0rc1',
            'flake8',
            'flake8-quotes',
            'codecov',
        ]
    },
)
