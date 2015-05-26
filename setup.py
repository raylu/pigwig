#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='pigwig',
    version='0.0.0',
    description='A sample Python project',
    long_description='pigs with wigs',
    url='https://github.com/raylu/pigwig',
    author='raylu',
    classifiers=[ # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Programming Language :: Python :: 3.4',
    ],
    packages=find_packages(exclude=['docs', 'tests*', 'blogwig']),
)
