# -*- coding: utf-8 -*-
#
import os
from distutils.core import setup
import codecs

# https://packaging.python.org/single_source_version/
base_dir = os.path.abspath(os.path.dirname(__file__))
about = {}
with open(os.path.join(base_dir, 'launchpadtools', '__about__.py')) as f:
    exec(f.read(), about)


def read(fname):
    try:
        content = codecs.open(
            os.path.join(os.path.dirname(__file__), fname),
            encoding='utf-8'
            ).read()
    except Exception:
        content = ''
    return content

setup(
    name='launchpadtools',
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    packages=['launchpadtools'],
    description='Tools for Debian/Ubuntu Launchpad',
    long_description=read('README.rst'),
    url='https://github.com/nschloe/launchpadtools',
    download_url='https://pypi.python.org/pypi/launchpadtools',
    license='License :: OSI Approved :: MIT License',
    platforms='any',
    install_requires=[
        'launchpadlib',
        ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Operating System'
        ],
    scripts=[
        'tools/launchpad-submit',
        ]
    )
