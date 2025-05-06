#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = f.read().splitlines()

setup(
    name="rigranger-server",
    version="0.1.0",
    author="RigRanger Project Contributors",
    author_email="your.email@example.com",
    description="A lightweight console application for controlling amateur radios",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YourUsername/RigRanger-Server",
    packages=find_packages(),
    package_data={
        'rigranger_server': ['public/*'],
    },
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Ham Radio",
        "Intended Audience :: End Users/Desktop",
        "Development Status :: 3 - Alpha",
    ],
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'rigranger-server=rigranger_server.rigranger_python_server:main',
        ],
    },
)
