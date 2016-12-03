#!/usr/bin/env python

import sys
import os
import codecs
import re
from setuptools import setup, find_packages
import setuptools.command.test


HERE = os.path.abspath(os.path.dirname(__file__))
META_PATH = os.path.join('rezina', '__init__.py')


def read(name):
    with codecs.open(os.path.join(HERE, name), "rb", "utf-8") as f:
        return f.read()

META_FILE = read(META_PATH)


def find_meta(meta):
    meta_match = re.search(
        r"^__{meta}__ = ['\"]([^'\"]*)['\"]".format(meta=meta),
        META_FILE, re.M
    )
    if meta_match:
        return meta_match.group(1)
    raise RuntimeError("Unable to find __{meta}__ string.".format(meta=meta))


class PyTest(setuptools.command.test.test):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        setuptools.command.test.test.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.pytest_args))


setup(name='rezina',
      version=find_meta('version'),
      description='a scalable, distributed task execution system',
      long_description=read('README.rst'),
      scripts=['bin/rezina-cli'],
      author=find_meta('author'),
      author_email='fujiaoliu@gmail.com',
      maintainer='Fujiao Liu',
      url='https://rezina.readthedocs.org',
      packages=find_packages(),
      install_requires=['pyzmq>=16.0.0'],
      license='BSD',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: POSIX :: Linux',
          "Topic :: System :: Distributed Computing",
          "Topic :: Software Development :: Object Brokering",
          'Programming Language :: Python',
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.5",
          ],
      tests_require=['pytest'],
      cmdclass={'test': PyTest},
      include_package_data=True
      )
