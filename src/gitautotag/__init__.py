from git import Repo, InvalidGitRepositoryError
import os
import argparse
import re


class ConfigDescriptor(object):
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
        pargs = obj.parsed_args
        if self.fieldname in pargs:
            return pargs[self.fieldname]
        with obj.repo.config_reader() as gitconf:
            if(gitconf.has_section(self.sectionname) and
               gitconf.has_option(self.sectionname, self.fieldname)):
                return gitconf.get(self.sectionname, self.fieldname)
        return self.default

    def __get__(self, obj, objtype):
        val = self.__get_raw__(obj)
        if self.validator:
            val = self.validator(val)
        return val


def tobool(value):
    if type(value) is bool:
        return value
    return value.strip().lower() in ('true', '1', 'yes', 'y')


def tagname_template_validator(value):
    reg = re.compile('([a-zA-Z\d.:,_-])')
    tval = value
    if not tval:
        raise ValueError('Empty tag template provided.')
    while tval:
        for p in ('{patch}', '{minor}', '{major}'):
            if tval.startswith(p):
                tval = tval[len(p):]
        if not tval:
            break
        c = tval[0]
        if not reg.match(c):
            raise ValueError("Illegal character {0} "
                             "found in template string: {1}".format(c, value))
        tval = tval[1:]
    return value


class BaseConfig(object):

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
        return os.getcwd()

    @property
    def rootdir(self):
        if self._parsed_args is None:
            self.parse_args()
        if self._parsed_args.get('repo') is None:
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
                Repo(self._parsed_args['repo']).git_dir
            except InvalidGitRepositoryError:
                raise ValueError(
                    "Path {0} does not point to a git"
                    " repository.".format(self._parsed_args['repo']))
            return self._parsed_args['repo']

    @property
    def repo(self):
        if not hasattr(self, '_repo') or self._repo is None:
            self._repo = Repo(self.rootdir)
        return self._repo

    @property
    def parsed_args(self):
        if not hasattr(self, '_parsed_args') or self._parsed_args is None:
            self.parse_args()
        return self._parsed_args

    def get_argparser(self):
        argparser = argparse.ArgumentParser(
            description="Create git tags automatically.")
        argparser.add_argument("--repo",
                               action="store_const",
                               default=None,
                               help="Path to the repository")
        argparser.add_argument("--message",
                               action="store_const",
                               default=None,
                               help="Set the message for the tag.")
        return argparser

    def parse_args(self, params=None):
        argparser = self.get_argparser()
        if params is None:
            self._parsed_args = argparser.parse_args()
        else:
            self._parsed_args = argparser.parse_args(params)

    @property
    def tag_regex(self):
        tmpl = self.tagname_template
        for p in ('minor', 'patch', 'major'):
            tmpl = tmpl.replace('{{{0}}}'.format(p), '(?P<{0}>\d+)'.format(p))
        tmpl = tmpl.replace('.', '\.')
        return re.compile(tmpl)


class Config(BaseConfig):

    step = ConfigDescriptor("step", default="minor")

    def get_argparser(self):
        argparser = super(Config, self).get_argparser()
        argparser.add_argument("step", nargs="?",
                               store="const",
                               choices=["major", "minor", "patch"],
                               help="Explicitely specify whether to "
                                    "create a new major, minor or patch"
                                    " version (choices: major, minor, patch)")
        return argparser


class MajorVersionConfig(BaseConfig):
    step = "major"


class MinorVersionConfig(BaseConfig):
    step = "minor"


class PatchVersionConfig(BaseConfig):
    step = "patch"


class Tag(object):

    def __init__(self, config, major=None, minor=None, patch=None):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.config = config

    def validate(self):
        if self.minor is not None and self.major is None:
            raise ValueError("When providing a minor version, "
                             "you also have to provide a major version.")
        if self.patch is not None and self.minor is None:
            raise ValueError("When providing a patch version, you "
                             "also have to provide a major and minor version.")

    def get_incremented(self):
        step = self.config.step
        kwargs = {'major': self.major,
                  'minor': self.minor,
                  'patch': self.patch}
        if step not in ("major", "minor", "patch"):
            raise ValueError("step must be one of major, minor or patch.")
        if kwargs[step] is None:
            kwargs[step] = 0
        kwargs[step] += 1
        return self.__class__(self.config, **kwargs)

    @property
    def versiondict(self):
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
        return self.config.tagname_template.format(**self.versiondict)

    @property
    def message(self):
        vdict = self.versiondict
        vdict['tagname'] = self.name
        return self.config.tagmessage_template.format(**vdict)

    def create(self):
        msg = self.message
        name = self.name
        if self.config.pull_before_tagging:
            self.config.repo.remote(name=self.config.remote_name).fetch()
        newtag = self.config.repo.create_tag(name, message=msg)
        if self.config.push_after_tagging:
            self.config.repo.remote(name=self.config.remote_name).push(newtag)

    @classmethod
    def get_from_string(cls, tagstring, config):
        m = config.tag_regex.match(tagstring)
        if not m:
            raise Exception("Tagstring {0} did not match"
                            " template.".format(tagstring))
        kwargs = dict([(k, int(v)) for k, v in m.groupdict().iteritems()])
        return cls(config, **kwargs)

    @classmethod
    def get_tags(cls, config, sorted=True, raise_exception=True):
        alltags = []
        for t in config.repo.tags:
            try:
                alltags.add(cls.get_from_string(t.name, config))
            except Exception, e:
                if raise_exception:
                    raise e
        if sorted:
            alltags.sort()
        return alltags

    def __gen_comp__(self, other):
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


def create_tag(config_class=Config):
    config = config_class()
    tags = Tag.get_tags(config)
    latest_tag = tags[-1]
    new_tag = latest_tag.get_incremented()
    new_tag.create()


def create_major_version_tag():
    create_tag(MajorVersionConfig)


def create_minor_version_tag():
    create_tag(MinorVersionConfig)


def create_patch_version_tag():
    create_tag(PatchVersionConfig)


if __name__ == '__main__':
    create_tag()
