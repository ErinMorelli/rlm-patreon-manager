#!/usr/bin/env python
"""
Copyright (C) 2021 Erin Morelli.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.x

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see [https://www.gnu.org/licenses/].
"""

from setuptools import setup, find_packages

setup(
    name='rlm-patreon-manager',
    version='1.0',
    author='Erin Morelli',
    author_email='me@erin.dev',
    url='https://erin.dev',
    description='A CLI tool for managing RLM Patreon exclusive content.',
    long_description=open('README.md').read(),
    include_package_data=True,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'rlm-patreon = rlm_patreon:cli'
        ]
    },
    install_requires=[
        'click',
        'cryptography',
        'feedgen',
        'passlib',
        'pyquery',
        'python-dateutil',
        'requests',
        'selenium',
        'SQLAlchemy',
        'SQLAlchemy-Utils',
        'tabulate',
        'tqdm',
        'vimeo-downloader'
    ],
)
