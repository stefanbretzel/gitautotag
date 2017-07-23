import unittest
import tempfile
import os
import shutil
from git import Repo, InvalidGitRepositoryError
from git.exc import RepositoryDirtyError

class GitRepoTestCase(unittest.TestCase):
    """
    A subclass of unittest.TestCase that
    creates a temporary directory which contains
    a git repo
    """
    
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.repo = Repo.init(os.path.join(self.tempdir,'local'), bare=False)
        
    def tearDown(self):
        if os.path.exists(self.tempdir):
            if not os.path.isdir(self.tempdir):
                raise Exception('Expected {0} to be a directory.'.format(self.tempdir))
            shutil.rmtree(self.tempdir, ignore_errors=False)
            
class GitRepoWithRemoteTestCase(GitRepoTestCase):
    """
    A subclass providing a git repo and associated
    remote repository
    """
    
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.remote_tempdir = os.path.join(self.tempdir,'remote')
        self.local_tempdir = os.path.join(self.tempdir,'local')
        self.remote_repo = Repo.init(self.remote_tempdir, bare=True)
        self.local_repo = Repo.clone_from(self.remote_tempdir,self.local_tempdir)
        
