from git import Repo, InvalidGitRepositoryError
import os
import argparse
import re
from six import string_types, iteritems


class ConfigDescriptor(object):
    """
    Descriptor class used in conjunction with the object class

    This class will provide read-only access to configuration
    values. Values are looked up in the following order:

    1) in the parsed command line arguments
    2) in the git configuration
    3) default value
    """

    def __init__(self,
                 fieldname,
                 sectionname="autotag",
                 default=None,
                 validator=None):
        self.fieldname = fieldname
        self.sectionname = sectionname
        self.default = default
        self.validator = validator

    def __get_raw__(self, obj):
        """
        Look up the field value and return it.

        The values are looked up in the
        parsed command line values contained
        in obj.parsed_args. If they are not found there,
        then the value provided from the git config
        is returned. Failing that, the configured
        default value is returned
        """
        pargs = obj.parsed_args
        if self.fieldname in pargs:
            return getattr(pargs, self.fieldname)
        with obj.repo.config_reader() as gitconf:
            if(gitconf.has_section(self.sectionname) and
               gitconf.has_option(self.sectionname, self.fieldname)):
                return gitconf.get(self.sectionname, self.fieldname)
        return self.default

    def __get__(self, obj, objtype):
        """
        Return the value of configuration setting
        provided by self.fieldname.

        If a validator routine is provided, it is called
        with the value found and its return value returned.
        """
        val = self.__get_raw__(obj)
        if self.validator:
            val = self.validator(val)
        return val


def tobool(value):
    """
    Convert a value to bool.

    The following values (irrespective of their case)
    is considered to be True: true, 1, yes, y
    All other values are considered to be False.
    """
    if type(value) is bool:
        return value
    if not isinstance(value, string_types):
        return False
    return value.strip().lower() in ('true', '1', 'yes', 'y')


def tagname_template_validator(value):
    """
    Make sure that the provided value is a valid
    template string for a tag.

    The following conditions must be met:
    1) The string must not be empty
    2) The string must only contain letters, digits,
       ., ;, _, - and comma.
    3) Placeholders for the versions are {major}, {minor} and {patch}
    4) If {patch} is provided, then {minor}
       and {major} must be present.
    5) If {minor} is provided, {major} must be provided.
    6) {major} is required.
    """
    reg = re.compile('([a-zA-Z\d.:,_-])')
    tval = value
    matches = {'{patch}': False, '{minor}': False, '{major}': False}
    if not tval:
        raise ValueError('Empty tag template provided.')
    while tval:
        for p in ('{patch}', '{minor}', '{major}'):
            if tval.startswith(p):
                tval = tval[len(p):]
                matches[p] = True
        if not tval:
            break
        c = tval[0]
        if not reg.match(c):
            raise ValueError("Illegal character {0} "
                             "found in template string: {1}".format(c, value))
        tval = tval[1:]
    if not all(matches.values()):
        if matches['{patch}']:
            raise ValueError(
                '{patch} provided but {major} or {minor} missing.')
        elif matches['{minor}'] and not matches['{major}']:
            raise ValueError('{minor} provided but {major} missing.')
    return value


class BaseConfig(object):
    """
    Class to hold the configuration used in creating
    tags.
    """

    tagname_template = ConfigDescriptor("tagname_template",
                                        default="{major}.{minor}.{patch}",
                                        validator=tagname_template_validator)
    tagmessage_template = ConfigDescriptor("tagmessage_template",
                                           default="Release {tagname}.")
    posttagaction = ConfigDescriptor("posttagaction")
    pull_before_tagging = ConfigDescriptor("pull_before_tagging",
                                           default=False,
                                           validator=tobool)
    push_after_tagging = ConfigDescriptor("push_after_tagging",
                                          default=False,
                                          validator=tobool)
    remote_name = ConfigDescriptor("remote_name", default="origin")

    def __init__(self):
        self._parsed_args = None

    def getcwd(self):
        """Return the current working directory."""
        return os.getcwd()

    @property
    def rootdir(self):
        """
        Determine the root directory of the repository.

        If the path to the repository is not explicitely
        provided via command line, the search for the
        repository's root directory starts at the
        current working directory and the search continues
        upwards up to the root directory.
        """
        if self._parsed_args is None:
            self.parse_args()
        if getattr(self._parsed_args, 'repo', None) is None:
            rdir = self.getcwd()
            while True:
                try:
                    Repo(rdir).git_dir
                    return rdir
                except InvalidGitRepositoryError:
                    pass
                ndir = os.path.abspath(
                    os.path.join(rdir, os.pardir))
                if rdir == ndir:
                    raise ValueError("Neither the current "
                                     "working directory nor"
                                     " its parents are a git"
                                     " repository.")
                rdir = ndir
        else:
            try:
                Repo(self._parsed_args.repo).git_dir
            except InvalidGitRepositoryError:
                raise ValueError(
                    "Path {0} does not point to a git"
                    " repository.".format(self._parsed_args.repo))
            return self._parsed_args.repo

    @property
    def repo(self):
        """Return the repository object."""
        if not hasattr(self, '_repo') or self._repo is None:
            self._repo = Repo(self.rootdir)
        return self._repo

    @property
    def parsed_args(self):
        """Return the parsed command line arguments."""
        if not hasattr(self, '_parsed_args') or self._parsed_args is None:
            self.parse_args()
        return self._parsed_args

    def get_argparser(self):
        """
        Return an instance of ArgumentParser
        to parse command line options.
        """
        argparobj = argparse.ArgumentParser(
            description="Create git tags automatically.")
        argparobj.add_argument("--repo",
                               default=None,
                               dest="repo",
                               help="Path to the repository")
        argparobj.add_argument("--message",
                               default=None,
                               dest="message",
                               help="Set the message for the tag.")
        return argparobj

    def parse_args(self, params=None):
        """
        Parse the command line arguments
        and store the result in self._parsed_args
        """
        argparser = self.get_argparser()
        if params is None:
            self._parsed_args = argparser.parse_args()
        else:
            self._parsed_args = argparser.parse_args(params)

    @property
    def tag_regex(self):
        """
        Return a regular expression for the
        tags created from the template
        for the tagname.
        """
        tmpl = self.tagname_template
        tmpl = tmpl.replace('.', '\.')
        for p in ('minor', 'patch', 'major'):
            tmpl = tmpl.replace('{{{0}}}'.format(p), '(?P<{0}>\d+)'.format(p))
        return re.compile(tmpl)


class Config(BaseConfig):
    """
    Config class that allows to set the kind
    of tag via command line.
    """

    step = ConfigDescriptor("step", default="minor")

    def get_argparser(self):
        """
        Return an ArgumentParser instance.

        An additional option to set the tag kind
        to create is provided.
        """
        argparser = super(Config, self).get_argparser()
        argparser.add_argument("step", nargs="?",
                               choices=["major", "minor", "patch"],
                               help="Explicitely specify whether to "
                                    "create a new major, minor or patch"
                                    " version (choices: major, minor, patch)")
        return argparser


class MajorVersionConfig(BaseConfig):
    """Config class creating major version tags."""
    step = "major"


class MinorVersionConfig(BaseConfig):
    """Config class creating minor version tags."""
    step = "minor"


class PatchVersionConfig(BaseConfig):
    """Config class creating patch version tags."""
    step = "patch"


class CannotParseTagError(Exception):
    pass


class Tag(object):
    """
    Class representing a tag.
    """

    def __init__(self, config, major=None, minor=None, patch=None):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.config = config

    def validate(self):
        """
        Validates the provided information for a tag.
        """
        if self.minor is not None and self.major is None:
            raise ValueError("When providing a minor version, "
                             "you also have to provide a major version.")
        if (self.patch is not None and
                (self.minor is None or self.major is None)):
            raise ValueError("When providing a patch version, you "
                             "also have to provide a major and minor version.")

    def get_incremented(self):
        """
        Return a tag object where the version is incremented
        with respect to the object.

        The increment of the version is determined
        from the configuration
        """
        step = self.config.step
        kwargs = self.versiondict
        if step not in ("major", "minor", "patch"):
            raise ValueError("step must be one of major, minor or patch.")
        if kwargs[step] is None:
            kwargs[step] = 0
        kwargs[step] += 1
        if step == 'major':
            kwargs['minor'] = 0
            kwargs['patch'] = 0
        elif step == 'minor':
            kwargs['patch'] = 0
        return self.__class__(self.config, **kwargs)

    @property
    def versiondict(self):
        """
        Return a dictionary containing version
        information (keys major, minor and patch).

        Missing version attributes are filled
        with a default of 0.
        """
        dct = dict()
        for k in ('minor', 'major', 'patch'):
            v = getattr(self, k, None)
            if v is not None:
                dct[k] = v
            else:
                dct[k] = 0
        return dct

    @property
    def name(self):
        """
        Return the tag name formatted
        according to the template provided
        by the config.
        """
        return self.config.tagname_template.format(**self.versiondict)

    @property
    def message(self):
        """Return a formatted commit message for the tag."""
        vdict = self.versiondict
        vdict['tagname'] = self.name
        return self.config.tagmessage_template.format(**vdict)

    def create(self):
        """Create a tag in the git repository."""
        msg = self.message
        name = self.name
        if name in [t.name for t in self.config.repo.tags]:
            raise Exception()
        newtag = self.config.repo.create_tag(name, message=msg)
        if self.config.push_after_tagging:
            self.config.repo.remote(name=self.config.remote_name).push(newtag)

    @classmethod
    def get_from_string(cls, tagstring, config):
        """
        Create a tag object from the passed in string and config.

        :param tagstring: the string containing the tag name
        :param config: configuration object
        """
        m = config.tag_regex.match(tagstring)
        if not m:
            raise Exception("Tagstring {0} did not match"
                            " template.".format(tagstring))
        kwargs = dict([(k, int(v)) for k, v in iteritems(m.groupdict())])
        return cls(config, **kwargs)

    @classmethod
    def get_tags(cls, config, sorted=True, raise_exception=True):
        """
        Get all tags from the repository.
        """
        alltags = []
        for t in config.repo.tags:
            try:
                alltags.append(cls.get_from_string(t.name, config))
            except Exception as e:
                if raise_exception:
                    raise CannotParseTagError(e)
        if sorted:
            alltags.sort()
        return alltags

    def __gen_comp__(self, other):
        """
        Helper function for comparing tags
        with each other.
        """
        for f in ('major', 'minor', 'patch'):
            sf = getattr(self, f, None)
            of = getattr(other, f, None)
            if sf is not None and of is not None:
                if sf > of:
                    return 1
                elif sf < of:
                    return -1
            elif sf is not None:
                return 1
            elif of is not None:
                return -1
        return 0

    def __lt__(self, other):
        return self.__gen_comp__(other) < 0

    def __le__(self, other):
        return self.__gen_comp__(other) <= 0

    def __eq__(self, other):
        return self.__gen_comp__(other) == 0

    def __ne__(self, other):
        return self.__gen_comp__(other) != 0

    def __gt__(self, other):
        return self.__gen_comp__(other) > 0

    def __ge__(self, other):
        return self.__gen_comp__(other) >= 0


def create_tag(config):
    """
    Create a tag

    :param config: instance of Configuration to use
    """
    if config.pull_before_tagging:
        config.repo.remote(name=config.remote_name).pull()
    tags = Tag.get_tags(config)
    latest_tag = tags[-1]
    new_tag = latest_tag.get_incremented()
    new_tag.create()


def create_major_version_tag():
    """Create a major version tag"""
    create_tag(MajorVersionConfig())


def autotag():
    """Create a tag with user specified increment"""
    create_tag(Config())


def create_minor_version_tag():
    """Create a minor version tag"""
    create_tag(MinorVersionConfig())


def create_patch_version_tag():
    """Create a patch version tag"""
    create_tag(PatchVersionConfig())


if __name__ == '__main__':
    create_tag()
