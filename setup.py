#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

import finance


def readme():
    try:
        with open('README.rst') as f:
            return f.read()
    except:
        return '(Could not read from README.rst)'


setup(
    name='sb-finance',
    version=finance.__version__,
    description='Personal Finance Project',
    long_description=readme(),
    author=finance.__author__,
    author_email=finance.__email__,
    url='https://github.com/suminb/finance',
    license='BSD',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'finance = finance.__main__:cli'
        ]
    },
)
