# -*- coding: utf-8 -*-
#
from __future__ import print_function

import appdirs
import git
import hglib
import os
import subprocess


def _sanitize_directory_name(string):
    return string \
        .replace('\n', '-') \
        .replace(' ', '-') \
        .replace(':', '-') \
        .replace('/', '-')


def _git(git_url, repo_dir):
    if os.path.isdir(repo_dir):
        repo = git.Repo(repo_dir)
        origin = repo.remotes.origin
        origin.pull()
    else:
        git.Repo.clone_from(git_url, repo_dir, recursive=True)
    return


def _mercurial(url, repo_dir):
    if os.path.isdir(repo_dir):
        client = hglib.open(repo_dir)
        client.pull()
    else:
        hglib.clone(url, repo_dir)
    return


def _svn(url, repo_dir):
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
    return


def cclone(source):
    print('Cloning %s...' % source, end='')

    repo_dir = os.path.join(
        appdirs.user_cache_dir('launchpadtools', 'Nico Schlömer'),
        _sanitize_directory_name(source)
        )

    try:
        _git(source, repo_dir)
        return repo_dir
    except (git.exc.GitCommandError, git.exc.InvalidGitRepositoryError):
        pass

    try:
        _mercurial(source, repo_dir)
        return repo_dir
    except (hglib.error.ServerError, hglib.error.CommandError):
        pass

    try:
        _svn(source, repo_dir)
        return repo_dir
    except subprocess.CalledProcessError:
        pass

    raise RuntimeError('Couldn\'t handle source %s. Abort.' % source)

    return repo_dir
