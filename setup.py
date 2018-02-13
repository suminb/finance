#!/usr/bin/env python

from distutils.core import setup
import finance


def readme():
    try:
        with open('README.rst') as f:
            return f.read()
    except:
        return '(Could not read from README.rst)'


setup(
    name='finance',
    py_modules=[
        'finance', 'finance.__main__', 'finance.models', 'finance.importers',
        'finance.utils', 'finance.exceptions', 'finance.providers.google',
    ],
    version=finance.__version__,
    description='Personal Finance Project',
    long_description=readme(),
    author=finance.__author__,
    author_email=finance.__email__,
    url='http://github.com/suminb/finance',
    license='BSD',
    packages=[],
    entry_points={
        'console_scripts': [
            'finance = finance.__main__:cli'
        ]
    },
)
