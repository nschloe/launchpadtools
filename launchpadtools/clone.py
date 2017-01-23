# -*- coding: utf-8 -*-
#
from __future__ import print_function

import appdirs
import git
import hglib
import os
import subprocess
import shutil

from . import helpers


def _sanitize_directory_name(string):
    return string \
        .replace('\n', '-') \
        .replace(' ', '-') \
        .replace(':', '-') \
        .replace('/', '-')


def _get_dir_from_git(git_url):
    repo_dir = os.path.join(
        appdirs.user_cache_dir('launchpadtools', 'Nico Schlömer'),
        _sanitize_directory_name(git_url)
        )
    if os.path.isdir(repo_dir):
        print(' (using repo cache at %s)' % repo_dir)
        repo = git.Repo(repo_dir)
        origin = repo.remotes.origin
        origin.pull()
    else:
        git.Repo.clone_from(git_url, repo_dir, recursive=True)

    return repo_dir


def _get_dir_from_mercurial(url):
    repo_dir = os.path.join(
        appdirs.user_cache_dir('launchpadtools', 'Nico Schlömer'),
        _sanitize_directory_name(url)
        )
    if os.path.isdir(repo_dir):
        print(' (using repo cache at %s)' % repo_dir)
        client = hglib.open(repo_dir)
        client.pull()
    else:
        hglib.clone(url, repo_dir)

    return repo_dir


def _get_dir_from_svn(url):
    repo_dir = os.path.join(
        appdirs.user_cache_dir('launchpadtools', 'Nico Schlömer'),
        _sanitize_directory_name(url)
        )
    if os.path.isdir(repo_dir):
        print(' (using repo cache at %s)' % repo_dir)
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


def clone(source, out, subdirectory=None, ignore_hidden=True):
    print('Cloning %s to %s...' % (source, out), end='')
    if os.path.exists(out):
        if not os.path.isdir(out):
            raise RuntimeError('Destination is not a directory.')

        if os.listdir(out) == []:
            shutil.rmtree(out)
        else:
            raise RuntimeError('Destination directory is not empty.')

    is_git = False
    if os.path.isdir(source):
        orig_dir = source
    else:
        orig_dir = None

        if not orig_dir:
            try:
                orig_dir = _get_dir_from_git(source)
                is_git = True
            except (
                    git.exc.GitCommandError,
                    git.exc.InvalidGitRepositoryError
                    ):
                pass

        if not orig_dir:
            try:
                orig_dir = _get_dir_from_mercurial(source)
            except (hglib.error.ServerError, hglib.error.CommandError):
                pass

        if not orig_dir:
            try:
                orig_dir = _get_dir_from_svn(source)
            except subprocess.CalledProcessError:
                pass

        if not orig_dir:
            raise RuntimeError('Couldn\'t handle source %s. Abort.' % source)

    if subdirectory is None:
        if is_git:
            git.Repo.clone_from(
                orig_dir, out, recursive=True, shared=True
                )
        else:
            helpers.copytree(
                orig_dir, out, ignore_hidden=ignore_hidden
                )
    else:
        helpers.copytree(
            os.path.join(orig_dir, subdirectory),
            out,
            ignore_hidden=ignore_hidden
            )

    return
