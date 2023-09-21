#!/usr/bin/env python
from distutils.core import setup
import os
import re
import shutil


# Check system dependecy zstd
if not shutil.which("zstd"):
    raise Exception("zstd must be installed.")


def get_version():
    app_dir = os.path.dirname(__file__)
    with open(os.path.join(app_dir, "src", "zfq.py")) as reader:
        for line in reader:
            if line.startswith("__version__"):
                version = re.search(r"^__version__\s*=\s*\'(.+)\'", line).groups()[0]  # Example: "__version__ = '1.7.0'"
    return version


setup(
    name='zfq',
    version=get_version(),
    description='FastQ file compressor',
    author='Frederic Escudie',
    license='GNU GPL v3',
    url='https://github.com/bialimed/zfq',
    python_requires='>=3.7',
    keywords='bioinformatics compression fastq',
    scripts=['src/zfq.py']
)
