#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

VERSION="0.1"

setup(
    name='pymaxd',
    version=VERSION,
    description='Daemon for the MAX Cube',
    author='Johann Schmitz',
    author_email='johann@j-schmitz.net',
    url='https://ercpe.de/projects/pymaxd',
    download_url='https://code.not-your-server.de/pymaxd.git/tags/%s.tar.gz' % VERSION,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    license='GPL-3',
)
