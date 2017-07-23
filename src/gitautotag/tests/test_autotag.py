'''
Created on 16.07.2017

@author: stefan
'''
from gitautotag.tests import GitRepoTestCase, GitRepoWithRemoteTestCase
import unittest
import os
from git import Repo
from gitautotag import ConfigDescriptor, tagname_template_validator,\
    BaseConfig, tobool, Tag, Config


class TestConfigDescriptor(GitRepoTestCase):

    def test___get_raw___from_parsed(self):
        """
        Test that the value set in obj.parsed_args has precedence
        over the git setting and the default.
        """
        cls = type('TestClass', (object, ),
                   {'parsed_args': dict(), 'repo': self.repo})
        desc = ConfigDescriptor('test', default="foo")
        with self.repo.config_writer() as wr:
            wr.set_value('gitautotagtest', 'test', 'bar')
        obj = cls()
        obj.parsed_args['test'] = 'somedata'
        self.assertEqual(desc.__get_raw__(obj), 'somedata')

    def test__get_raw___from_gitconfig(self):
        """
        Test that the git config gets returned if no value provided
        in the parsed args.
        """
        cls = type('TestClass', (object, ),
                   {'parsed_args': dict(), 'repo': self.repo})
        desc = ConfigDescriptor('test',
                                default="foo",
                                sectionname='autotagtest')
        with self.repo.config_writer() as wr:
            wr.set_value('autotagtest', 'test', 'bar')
        obj = cls()
        self.assertEqual(desc.__get_raw__(obj), 'bar')

    def test__get_raw___default(self):
        """
        Test that the default gets returned if no value provided
        by parsed_args or the git config
        """
        cls = type('TestClass', (object, ),
                   {'parsed_args': dict(), 'repo': self.repo})
        desc = ConfigDescriptor('test', default="foo")
        obj = cls()
        self.assertEqual(desc.__get_raw__(obj), 'foo')

    def test___get__(self):
        cls = type('TestClass', (object, ),
                   {'parsed_args': dict(), 'repo': self.repo})
        desc = ConfigDescriptor('test', default="foo")
        obj = cls()
        self.assertEqual(desc.__get__(obj, None), 'foo')

    def dummy_validator(self, value):
        if not value == "BAZBAZ":
            raise ValueError()
        return value

    def test___get___with_validator(self):
        """
        Test that the validator gets called when set
        """
        cls = type('TestClass', (object, ),
                   {'parsed_args': dict(), 'repo': self.repo})
        obj = cls()
        desc = ConfigDescriptor('test', default="foo",
                                validator=self.dummy_validator)

        # first test, should raise a ValueError as
        # the value does not match the required one
        self.assertRaises(ValueError, desc.__get__, obj, None)

        # now set the value to the required one,
        # get should just simply return it
        obj.parsed_args['test'] = 'BAZBAZ'
        self.assertEqual(desc.__get__(obj, None), 'BAZBAZ')


class Test_tobool(unittest.TestCase):

    def test_true(self):
        for x in ('tRue', 'True', 'true', '1', 'yes', 'YeS', True):
            self.assertTrue(tobool(x))

    def test_false(self):
        for x in (None, "foobar", 1, False, 3.145926, 'yesandno'):
            self.assertFalse(tobool(x))


class Test_tagname_template_validator(unittest.TestCase):

    def test_legal(self):
        for s in ('{major}.{minor}', 'V{major}.{minor}.{patch}:_,ab'):
            try:
                tagname_template_validator(s)
            except ValueError:
                self.fail('Unexpectedly raised ValueError on {0}'.format(s))

    def test_illegal(self):
        for s in ('a   b', '', 'a{something}', ',;'):
            self.assertRaises(ValueError, tagname_template_validator, s)

    def test_required_fields(self):
        """
        Make sure that {patch} in the template also
        means that {major} and {minor} need to be present, that the presence of
        {major} is required.
        """
        for s in ('{patch}', 'V{major}.{patch}', '{minor}.{patch}'):
            self.assertRaises(ValueError, tagname_template_validator, s)
        for s in ('{major}.{minor}.{patch}', '{major}', '{major}.{minor}'):
            self.assertEqual(s, tagname_template_validator(s))


class TestBaseConfig(GitRepoTestCase):

    class DummyBaseConfig(BaseConfig):

        def __init__(self, testcwd):
            self.testcwd = testcwd
            self._parsed_args = dict()

        def getcwd(self):
            return self.testcwd

    def test_rootdir__from_cwd(self):
        bc = self.DummyBaseConfig(self.tempdir)

        with self.assertRaises(ValueError):
            bc.rootdir
        os.makedirs(os.path.join(self.tempdir, 'local', 'foo', 'bar', 'baz'))
        bc.testcwd = os.path.join(self.tempdir, 'local', 'foo', 'bar', 'baz')
        self.assertEqual(bc.rootdir, os.path.join(self.tempdir, 'local'))

    def test_rootdir__repo_arg(self):
        bc = BaseConfig()
        bc._parsed_args = {'repo': os.path.join(self.tempdir, 'local')}
        self.assertEqual(bc.rootdir, os.path.join(self.tempdir, 'local'))

        bc._parsed_args['repo'] = self.tempdir
        with self.assertRaises(ValueError):
            bc.rootdir

    def test_repo(self):
        bc = BaseConfig()
        bc._parsed_args = {'repo': os.path.join(self.tempdir, 'local')}
        repo = bc.repo
        self.assertTrue(type(repo) is Repo)
        self.assertEqual(repo.git_dir,
                         os.path.join(self.tempdir, 'local', '.git'))

    def test_parse_args(self):
        bc = BaseConfig()
        self.assertTrue(bc._parsed_args is None)
        bc.parse_args(params=["--repo", "test", "--message", "SSSSS"])
        self.assertTrue(hasattr(bc, '_parsed_args'))
        self.assertEqual(bc._parsed_args.repo, "test")
        self.assertEqual(bc._parsed_args.message, "SSSSS")

    def test_get_argparser(self):
        config = BaseConfig()
        parser = config.get_argparser()
        parsed = parser.parse_args(["--repo", "test", "--message", "SSSSS"])
        self.assertEqual(parsed.repo, "test")
        self.assertEqual(parsed.message, "SSSSS")

    def test_tag_regex(self):
        config = BaseConfig()

        for t, teststr, versiondict in (
                ("{major}.{minor}.{patch}", "0.1.2",
                 {"major": "0", "minor": "1", "patch": "2"}),
                ("V{major}.{minor}.{patch}", "V0.1.2",
                 {"major": "0", "minor": "1", "patch": "2"}),
                ("{major}_{minor}:{patch}", "0_1:2",
                 {"major": "0", "minor": "1", "patch": "2"}),
                ("version {major}.{minor}", "version 0.1",
                 {"major": "0", "minor": "1"})
                ):
            config.tagname_template = t
            reg = config.tag_regex
            m = reg.match(teststr)
            self.assertTrue(m is not None)
            got = {}
            for k in versiondict:
                got[k] = m.group(k)
            self.assertDictEqual(got, versiondict)


class TestConfig(GitRepoTestCase):

    def test_get_argparser(self):
        config = Config()
        ap = config.get_argparser()
        prsed = ap.parse_args(["patch"])
        self.assertEqual(prsed.step, "patch")


class TestTag(GitRepoWithRemoteTestCase):

    def test_validate(self):
        config = BaseConfig()
        for major, minor, patch in (
                (None, 1, 0),  # minor/patch provided but major missing
                (1, None, 0),  # major/patch provided but minor missing
                (None, None, 1),  # no major/minor but patch
                ):
            tag = Tag(config, major=major, minor=minor, patch=patch)
            self.assertRaises(ValueError, tag.validate)

        for major, minor, patch in ((1, 0, 1),  # all explicetely set
                                    (1, None, None),  # only major given
                                    (1, 1, None),  # all but patch given
                                    ):
            tag = Tag(config, major=major, minor=minor, patch=patch)
            try:
                tag.validate()
            except ValueError:
                self.fail("ValueError unexpectedly raised.")

    def test_get_incremented(self):
        cfg = Config()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir, 'local')}
        tag = Tag(cfg)
        for s, ma, mi, patch in (('major', 1, 0, 0), ('minor', 1, 1, 0),
                                 ('patch', 1, 1, 1)):
            tag.config._parsed_args['step'] = s
            tag = tag.get_incremented()
            self.assertDictEqual(tag.versiondict,
                                 {'major': ma, 'minor': mi, 'patch': patch})

    def test_get_from_string(self):
        cfg = BaseConfig()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir, 'local')}
        for ts, td in (('0.0.1', {'major': 0, 'minor': 0, 'patch': 1}), ):
            tag = Tag.get_from_string(ts, cfg)
            self.assertDictEqual(tag.versiondict, td)

    def test_get_tags(self):
        self.fail('TODO')

    def test___gen_comp__(self):
        config = BaseConfig()
        tag100 = Tag(config, major=1, minor=0, patch=0)
        tag110 = Tag(config, major=1, minor=1, patch=0)
        tag010 = Tag(config, major=0, minor=1, patch=0)
        tag001 = Tag(config, major=0, minor=0, patch=0)
        tag211 = Tag(config, major=2, minor=1, patch=1)
        tag101 = Tag(config, major=1, minor=0, patch=1)

        # tags are the same to themselves
        for t in (tag100, tag010, tag001, tag211, tag110):
            self.assertEqual(t.__gen_comp__(t), 0)

        # the highest version is higher than all other
        for t in (tag100, tag010, tag001, tag110):
            self.assertEqual(tag211.__gen_comp__(t), 1)
            self.assertEqual(t.__gen_comp__(tag211), -1)

        # the lowest version is lower than any other
        for t in (tag211, tag010, tag100, tag110):
            self.assertEqual(t.__gen_comp__(tag001), 1)
            self.assertEqual(tag001.__gen_comp__(t), -1)

        self.assertEqual(tag100.__gen_comp__(tag110), -1)
        self.assertEqual(tag110.__gen_comp__(tag100), 1)
        self.assertEqual(tag101.__gen_comp__(tag100), 1)
        self.assertEqual(tag100.__gen_comp__(tag101), -1)

    def test_versiondict(self):
        for t in ({'major': 1}, {'major': 1, 'minor': 2},
                  {'major': 1, 'minor': 2, 'patch': 2}):
            vdict = Tag(None, **t).versiondict
            for k in ('major', 'minor', 'patch'):
                if k not in t:
                    t[k] = 0
            self.assertDictEqual(vdict, t)

    def test_name(self):
        cfg = BaseConfig()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir, 'local')}
        tag = Tag(cfg, major=1, minor=2, patch=3)
        self.assertEqual(tag.name, '1.2.3')

    def test_message(self):
        cfg = BaseConfig()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir, 'local')}
        tag = Tag(cfg, major=1, minor=2, patch=3)
        self.assertEqual(tag.message, 'Release 1.2.3.')

    def test_create__no_push_and_pull(self):
        self.fail('TODO')

    def test_create__push_and_pull(self):
        self.fail('TODO')
