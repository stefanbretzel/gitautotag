from setuptools import setup
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_version():
    with os.popen("git describe") as f:
        version = f.read()
    if version:
        with open("GIT_RELEASE", "w") as f:
            f.write(version)
        return version
    elif os.path.exists("GIT_RELEASE"):
        with open("GIT_RELEASE") as f:
            return f.readline().strip()



install_requires = ('GitPython>=2.1.5', 'six')

setup(name='git-autotag',
      version=get_version(),
      description='Automatically create git tags.',
      author='Stefan Bretzel',
      author_email='stefan.bretzel@googlemail.com   ',
      packages=['gitautotag'],
      long_description=read('README.rst'),
      license='GPL',
      keywords = 'development git',
      platforms='any',
      entry_points = {
        'console_scripts': ['git-autotag=gitautotag:autotag',
                            'git-major=gitautotag:create_major_version_tag',
                            'git-minor=gitautotag:create_minor_version_tag',
                            'git-patchtag=gitautotag:create_patch_version_tag'
                            ],
        },
      install_requires=install_requires,
      test_suite = 'gitautotag.tests'
      
     )