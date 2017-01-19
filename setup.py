"""A setuptools based setup module."""

import codecs
from os import path

from setuptools import find_packages, setup

HERE = path.abspath(path.dirname(__file__))

with codecs.open(path.join(HERE, 'README.rst'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setup(
    name='swarm',
    version='1.1.0',
    description='A simple Python project to upload data to the Wattics API',
    long_description=LONG_DESCRIPTION,
    url='https://github.com/Wattics/Swarm',
    author='Michele Delle Vergini',
    author_email='michele.dellevergini@wattics.com',
    license='BSD',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'requests',
        'tqdm'
    ],
    entry_points={
        'console_scripts': [
            'swarm=swarm.app:main',
        ],
    }
)
