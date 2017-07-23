#!/usr/bin/env python

from distutils.core import setup
import os
import subprocess

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_version():
    pass

setup(name='git-autotag',
      version=get_version(),
      description='Automatically create git tags.',
      author='Stefan Bretzel',
      author_email='stefan.bretzel@googlemail.com   ',
      packages=['gitautotag'],
      long_description=read('README.rst'),
      license='GPL',
      keywords = 'development git',
      entry_points = {
        'console_scripts': ['git-autotag=gitautotag:create_tag',
                            'git-major=gitautotag:create_major_version_tag',
                            'git-minor=gitautotag:create_minor_version_tag',
                            'git-patchtag=gitautotag:create_patch_version_tag'
                            ],
        }
     )
