#!/usr/bin/env python

from setuptools import setup
import unittest
#from distutils.core import setup
import os
import subprocess

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_version():
    pass

def get_test_suite():
    test_loader = unittest.TestLoader()
    return test_loader.discover('src', pattern='test_*.py')

install_requires = ('GitPython>=2.1.5', 'six')

setup(name='git-autotag',
      version=get_version(),
      description='Automatically create git tags.',
      author='Stefan Bretzel',
      author_email='stefan.bretzel@googlemail.com   ',
      packages=['gitautotag'],
      long_description=read('README.rst'),
      package_dir={'':'src'},
      license='GPL',
      keywords = 'development git',
      entry_points = {
        'console_scripts': ['git-autotag=gitautotag:autotag',
                            'git-major=gitautotag:create_major_version_tag',
                            'git-minor=gitautotag:create_minor_version_tag',
                            'git-patchtag=gitautotag:create_patch_version_tag'
                            ],
        },
      install_requires=install_requires,
      test_suite = 'setup.get_test_suite'
      
     )
