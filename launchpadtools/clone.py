# -*- coding: utf-8 -*-
#
import git
import os
import subprocess
import tempfile

from . import helpers


def _sanitize_directory_name(string):
    return string \
        .replace('\n', '-') \
        .replace(' ', '-') \
        .replace(':', '-') \
        .replace('/', '-')


def _get_dir_from_git(git_url):
    repo_dir = os.path.join('/tmp', _sanitize_directory_name(git_url))
    if os.path.isdir(repo_dir):
        repo = git.Repo(repo_dir)
        origin = repo.remotes.origin
        origin.pull()
    else:
        git.Repo.clone_from(git_url, repo_dir)

    return repo_dir


def _get_dir_from_svn(url):
    repo_dir = os.path.join('/tmp', _sanitize_directory_name(url))
    if os.path.isdir(repo_dir):
        os.chdir(repo_dir)
        # Call `svn info` first since `svn up` returns exit code 0 even if the
        # directory is not a repository.
        subprocess.check_call(
                'svn info',
                shell=True
                )
        subprocess.check_call(
                'svn up',
                shell=True
                )
    else:
        subprocess.check_call(
                'svn checkout %s %s' % (url, repo_dir),
                shell=True
                )

    return repo_dir


def clone(source, out):
    if os.path.isdir(source):
        orig_dir = source
    else:
        try:
            orig_dir = _get_dir_from_git(source)
        except git.exc.GitCommandError:
            pass
        except git.exc.InvalidGitRepositoryError:
            pass

        try:
            orig_dir = _get_dir_from_svn(source)
        except subprocess.CalledProcessError:
            pass

        raise RuntimeError('Couldn\'t handle source %s. Abort.' % source)

    helpers.copytree(os.path.join(orig_dir, '*'), out)
    return