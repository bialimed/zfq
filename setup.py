#!/usr/bin/env python

from distutils.core import setup

setup(
    name='zfq',
    version='1.0.0',
    description='FastQ file compressor',
    author='Frederic Escudie',
    license='GNU GPL v3',
    url='https://github.com/bialimed/zfq',
    python_requires='>=3.7',
    keywords='bioinformatics compression fastq',
    scripts=['src/zfq.py']
)
