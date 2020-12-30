#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
	name='pigwig',
	version='0.7.0',
	description='a python3.4+ WSGI framework',
	long_description='pigs with wigs',
	url='https://github.com/raylu/pigwig',
	author='raylu',
	classifiers=[ # https://pypi.python.org/pypi?%3Aaction=list_classifiers
		'Programming Language :: Python :: 3.4',
		'Topic :: Internet :: WWW/HTTP :: WSGI',
	],
	packages=find_packages(exclude=['docs', 'pigwig.tests', 'blogwig']),
)
