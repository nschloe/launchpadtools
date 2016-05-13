# -*- coding: utf-8 -*-
#
import git
import os
import shutil
import subprocess

from . import helpers


def _find_all_dirs(name, path):
    # From http://stackoverflow.com/a/1724723/353337
    result = []
    for root, dirs, _ in os.walk(path):
        if name in dirs:
            result.append(os.path.join(root, name))
    return result


def _find_all_files(name, path):
    # From http://stackoverflow.com/a/1724723/353337
    result = []
    for root, _, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result


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


def _get_dir_from_dsc(url):
    repo_dir = os.path.join('/tmp', _sanitize_directory_name(url))
    if os.path.isdir(repo_dir):
        shutil.rmtree(repo_dir)
    os.mkdir(repo_dir)
    os.chdir(repo_dir)
    subprocess.check_call(
            'dget %s' % url,
            shell=True
            )
    # Find the appropriate subdirectory
    directory = None
    for item in os.listdir(repo_dir):
        if os.path.isdir(item):
            directory = os.path.join(repo_dir, item)
            break

    assert directory

    # dget applies patches. Undo that.
    os.chdir(directory)
    subprocess.check_call(['quilt', 'pop',  '-a'])

    return directory



def _get_dir(source):
    try:
        return _get_dir_from_git(source)
    except git.exc.GitCommandError:
        pass
    except git.exc.InvalidGitRepositoryError:
        pass

    try:
        return _get_dir_from_svn(source)
    except subprocess.CalledProcessError:
        pass

    try:
        return _get_dir_from_dsc(source)
    except subprocess.CalledProcessError:
        pass

    raise RuntimeError('Couldn\'t handle source %s. Abort.' % source)


def clone(source, out):
    if os.path.isdir(source):
        orig_dir = source
    else:
        orig_dir = _get_dir(source)

    helpers.copytree(os.path.join(orig_dir, '*'), out)
    return
