#!/usr/bin/env python

from distutils.core import setup
from pkg_resources import parse_requirements
from setuptools import find_packages

import finance


def readme():
    try:
        with open("README.rst") as f:
            return f.read()
    except:
        return "(Could not read from README.rst)"


with open("requirements.txt") as f:
    install_requires = [str(x) for x in parse_requirements(f.read())]

setup(
    name="sb-finance",
    version=finance.__version__,
    description="Personal Finance Project",
    long_description=readme(),
    author=finance.__author__,
    author_email=finance.__email__,
    url="https://github.com/suminb/finance",
    license="BSD",
    packages=find_packages(),
    package_data={"": ["requirements.txt"]},
    include_package_data=True,
    install_requires=install_requires,
    entry_points={"console_scripts": ["finance = finance.__main__:cli"]},
)
