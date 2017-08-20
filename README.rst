==========
gitautotag
==========

gitautotag is a library for creating git tags automatically, that is creating annotated tags based on some template and potentially existing tags
in your repository. After installing, you can create new git tags by issuing

git major
git minor
git patchtag

which will create a new major version, minor version or patch tag respectively. In doing so, gitautotag implicitely assumes you are following semantic
versioning http://semver.org/, that is your software versions follow the major.minor.patch version pattern, where major, minor and patch are non-negative
integers.

Requirements
------------

gitautotag is based on GitPython (2.1.15 or newer), which requires git (version 1.7.x or newer) to be installed. gitpython was developped and is tested with Python 2.7 and Python 3.4.

Installation
------------
If you have downloaded the source code:

python setup.py install

Configuration
-------------

The behaviour of gitautotag can be configured either by setting values in git's config or by using command line parameters when running git major, git minor, git patchtag
or git autotag. 

Via git config
~~~~~~~~~~~~~~
gitautotag can be configured by setting configuration values by running git config. The following configuration values are used by gitautotag:

- autotag.tagname_template - Template string for the tag's name (default: "{major}.{minor}.{patch}").
- autotag.tagmessate_template - Template string for the tag's message (default: "Release {tagname}").
- autotag.posttagaction - custom command after creating the tag.
- autotag.pull_before_tagging - True or False, indicate whether to pull from the remote before tagging.
- autotag.push_after_tagging - True or False, indicate whether to push the tag to the remote.
- autotag.remote_name - Name of the remote (default: "origin")
- autotag.step - major, minor or patch, to indicate which part of the version string to increment if not implied by the git command used.

Command line arguments
~~~~~~~~~~~~~~~~~~~~~~
- --repo <PATH>: path to the root of the repository (default: your current working directory)
- --step (major"|minor|patch): which part of your versioning scheme to increment (default: "minor"); only available for git autotag
- --message <MESSAGE>: custom message to use when creating this tag

Template strings
~~~~~~~~~~~~~~~~

License
-------

GPL, see the LICENSE file.
