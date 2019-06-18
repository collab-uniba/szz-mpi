import logging
import os

import pygit2
from git import Repo

from utils.utility import slug_to_folder_name

logger = logging.getLogger('SZZ')


class RepoCloner:
    @staticmethod
    def clone(slug, repos_folder):
        try:
            path = os.path.join(repos_folder, slug_to_folder_name(slug))
            owner, repo = slug.split('/')
            url = 'https://github.com/{0}/{1}.git'.format(owner, repo)

            logger.info(msg='Cloning repo {0} into {1}.'.format(slug, path))
            pygit2.clone_repository(url=url, path=path)
        except Exception as e:
            logger.error('Error cloning repo {0}: {1}'.format(slug, e))

    @staticmethod
    def update_submodules(repos_folder):
        try:
            path = os.path.join(repos_folder, '.git')

            logger.info(msg='Updating submodules of repo at {0}.'.format(path))
            repo = pygit2.Repository(path=path)
            repo.init_submodules()
            repo.update_submodules()
        except Exception as e:
            logger.error('Error updating submodules at {0}'.format(e))

    @staticmethod
    def pull(dest):
        try:
            repo = Repo(path=dest)
            o = repo.remotes.origin
            o.pull()
        except Exception as e:
            logger.error('Error pulling git repo {0} at {1}'.format(dest, e))
