'''
Created on 16.07.2017

@author: stefan
'''
from gitautotag.tests import GitRepoTestCase, GitRepoWithRemoteTestCase
import unittest
import os
from git import Repo
from gitautotag import ConfigDescriptor, tagname_template_validator, BaseConfig, tobool, Tag, Config


class TestConfigDescriptor(GitRepoTestCase):
    
    def test___get_raw___from_parsed(self):
        """
        Test that the value set in obj.parsed_args has precedence
        over the git setting and the default.
        """
        cls = type('TestClass',(object,),{'parsed_args': dict(),'repo': self.repo})
        desc = ConfigDescriptor('test',default="foo")
        with self.repo.config_writer() as wr:
            wr.set_value('gitautotagtest','test','bar')
        obj = cls()
        obj.parsed_args['test']='somedata'
        self.assertEqual(desc.__get_raw__(obj),'somedata')
    
    def test__get_raw___from_gitconfig(self):
        """
        Test that the git config gets returned if no value provided
        in the parsed args.
        """
        cls = type('TestClass',(object,),{'parsed_args': dict(),'repo': self.repo})
        desc = ConfigDescriptor('test',default="foo",sectionname='autotagtest')
        with self.repo.config_writer() as wr:
            wr.set_value('autotagtest','test','bar')
        obj = cls()
        self.assertEqual(desc.__get_raw__(obj),'bar')
    
    def test__get_raw___default(self):
        """
        Test that the default gets returned if no value provided
        by parsed_args or the git config
        """
        cls = type('TestClass',(object,),{'parsed_args': dict(),'repo': self.repo})
        desc = ConfigDescriptor('test',default="foo")
        obj = cls()
        self.assertEqual(desc.__get_raw__(obj),'foo')
    
    def test___get__(self):
        cls = type('TestClass',(object,),{'parsed_args': dict(),'repo': self.repo})
        desc = ConfigDescriptor('test',default="foo")
        obj = cls()
        self.assertEqual(desc.__get__(obj,None),'foo')
    
    def dummy_validator(self,value):
        if not value=="BAZBAZ":
            raise ValueError()
        return value
    
    def test___get___with_validator(self):
        """
        Test that the validator gets called when set
        """
        cls = type('TestClass',(object,),{'parsed_args': dict(),'repo': self.repo})
        obj = cls()
        desc = ConfigDescriptor('test',default="foo",validator=self.dummy_validator)
        
        # first test, should raise a ValueError as
        # the value does not match the required one
        self.assertRaises(ValueError,desc.__get__,obj,None)
    
        # now set the value to the required one,
        # get should just simply return it
        obj.parsed_args['test'] = 'BAZBAZ'
        self.assertEqual(desc.__get__(obj,None),'BAZBAZ')
        
class Test_tobool(unittest.TestCase):
    
    def test_true(self):
        for x in ('tRue','True','true','1','yes','YeS'):
            self.assertTrue(tobool(x))
        
class Test_tagname_template_validator(unittest.TestCase):
    
    def test_legal(self):
        for s in ('{major}.{minor}','V{major}.{minor}.{patch}:_,ab'):
            try:
                tagname_template_validator(s)
            except ValueError:
                self.fail('Unexpectedly raised ValueError on {0}'.format(s))
    
    def test_illegal(self):
        for s in ('a   b','','a{something}',',;'):
            self.assertRaises(ValueError, tagname_template_validator, s)

class TestBaseConfig(GitRepoTestCase):

    class DummyBaseConfig(BaseConfig):
        
        def __init__(self,testcwd):
            self.testcwd=testcwd
            self._parsed_args = dict()
        
        def getcwd(self):
            return self.testcwd
    
    def test_rootdir__from_cwd(self):
        bc = self.DummyBaseConfig(self.tempdir)
        
        with self.assertRaises(ValueError):
            bc.rootdir
        os.makedirs(os.path.join(self.tempdir,'local','foo','bar','baz'))
        bc.testcwd = os.path.join(self.tempdir,'local','foo','bar','baz')
        self.assertEqual(bc.rootdir,os.path.join(self.tempdir,'local'))
    
    def test_rootdir__repo_arg(self):
        bc = BaseConfig()
        bc._parsed_args = {'repo': os.path.join(self.tempdir,'local')}
        self.assertEqual(bc.rootdir,os.path.join(self.tempdir,'local'))
        
        bc._parsed_args['repo'] = self.tempdir
        with self.assertRaises(ValueError):
            bc.rootdir
    
    def test_repo(self):
        bc = BaseConfig()
        bc._parsed_args = {'repo': os.path.join(self.tempdir,'local')}
        repo = bc.repo
        self.assertTrue(type(repo) is Repo)
        self.assertEqual(repo.git_dir, os.path.join(self.tempdir,'local','.git') )
    
    def test_parsed_args(self):
        self.fail('TODO')
    
    def test_get_argparser(self):
        self.fail('TODO')
    
    def test_tag_regex(self):
        self.fail('TODO')

class TestConfig(GitRepoTestCase):
    
    def test_get_argparser(self):
        self.fail('TODO')
    
class TestTag(GitRepoWithRemoteTestCase):
    
    def test_validate(self):
        self.fail('TODO')
    
    def test_get_incremented(self):
        cfg = Config()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir,'local')}
        tag = Tag(cfg)
        for s, ma, mi, patch in (('major',1,0,0),('minor',1,1,0),('patch',1,1,1)):
            tag.config._parsed_args['step'] = s
            tag = tag.get_incremented()
            self.assertDictEqual(tag.versiondict,{'major': ma, 'minor': mi,'patch':patch})
    
    def test_get_from_string(self):
        cfg = BaseConfig()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir,'local')}
        for ts, td in (('0.0.1',{'major':0,'minor':0,'patch':1}),):
            tag = Tag.get_from_string(ts, cfg)
            self.assertDictEqual(tag.versiondict, td)
            
    def test_get_tags(self):
        self.fail('TODO')
    
    def test___gen_comp__(self):
        self.fail('TODO')
        
    def test_versiondict(self):
        for t in ({'major': 1},{'major':1,'minor': 2},{'major':1,'minor':2,'patch':2}):
            vdict = Tag(None,**t).versiondict
            for k in ('major','minor','patch'):
                if k not in t:
                    t[k] = 0
            self.assertDictEqual(vdict, t)
        
    def test_name(self):
        cfg = BaseConfig()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir,'local')}
        tag = Tag(cfg,major=1,minor=2,patch=3)
        self.assertEqual(tag.name,'1.2.3')
        
    def test_message(self):
        cfg = BaseConfig()
        cfg._parsed_args = {'repo': os.path.join(self.tempdir,'local')}
        tag = Tag(cfg,major=1,minor=2,patch=3)
        self.assertEqual(tag.message,'Release 1.2.3.')

    def test_create__no_push_and_pull(self):
        self.fail('TODO')
        
    def test_create__push_and_pull(self):
        self.fail('TODO')


