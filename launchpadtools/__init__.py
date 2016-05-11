#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Automatically create tarball and submit it to launchpad.
'''
import git
from launchpadlib.launchpad import Launchpad
import os
import re
import shutil
import subprocess
import tarfile
import tempfile


def _get_info_from_changelog(changelog):
    with open(changelog, 'r') as f:
        first_line = f.readline()
        search = re.search(
                '^( *[^ ]+) *\(([^\)]+)\).*',
                first_line,
                re.IGNORECASE
                )
        if search:
            return search.group(1), search.group(2)
        else:
            raise RuntimeError('Could not extract name from changelog.')


def submit(
        directory,
        ubuntu_releases,
        resubmission,
        slot,
        dry,
        ppa_string,
        debfullname,
        debemail,
        debuild_params='',
        version_override=None,
        version_append_hash=False,
        force=False
        ):
    name, version = _get_info_from_changelog(
            os.path.join(directory, 'debian', 'changelog')
            )

    repo = git.Repo(directory)

    if version_override:
        version = version_override

    # Create the tarball.
    tarball_path = os.path.join('/tmp/', name + '.tar.gz')
    prefix = name + '-' + version
    print('Creating new archive %s...' % tarball_path)
    with open(tarball_path, 'wb') as fh:
        repo.archive(fh, prefix=prefix + '/', format='tar.gz')
    print('done.')

    lp = Launchpad.login_anonymously('foo', 'production', None)
    ppa_owner, ppa_name = tuple(ppa_string.split('/'))

    owner = lp.people[ppa_owner]
    ppa = owner.getPPAByName(name=ppa_name)
    sources = ppa.getPublishedSources()

    published_sources = [
            d for d in sources.entries if d['status'] == 'Published'
            ]

    tree_hash_short = repo.tree().hexsha[:8]
    if version_append_hash:
        version += '-%s' % tree_hash_short

    for ubuntu_release in ubuntu_releases:
        # Check if this version has already been published.
        published_in_series = [
                d for d in published_sources
                if d['distro_series_link'] ==
                'https://api.launchpad.net/1.0/ubuntu/%s' % ubuntu_release
                ]
        if not force and published_in_series:
            # Expect a package version of the form
            # 2.1.0~20160504184836-01b3a567-trusty1
            parts = published_in_series[0]['source_package_version'].split('-')
            if len(parts) == 3 and parts[1] == tree_hash_short:
                print('Same version already published for %s. Abort.' %
                      ubuntu_release)
                continue

        # Create empty directory of the form
        #     /tmp/trilinos/trusty/
        release_dir = os.path.join('/tmp', name, ubuntu_release)
        if os.path.exists(release_dir):
            shutil.rmtree(release_dir)
        # Use Python3's makedirs for recursive creation
        os.makedirs(release_dir, exist_ok=True)

        # Copy source tarball to
        #     /tmp/trilinos/trusty/trilinos_4.3.1.2~20121123-01b3a567.tar.gz
        tarball_dest = '%s_%s.orig.tar.gz' % (name, version)

        shutil.copy2(tarball_path, os.path.join(release_dir, tarball_dest))
        # Unpack the tarball
        os.chdir(release_dir)
        tar = tarfile.open(tarball_dest)
        tar.extractall()
        tar.close()

        os.chdir(release_dir)

        # Use the `-` as a separator (instead of `~` as it's often used) to
        # make sure that ${UBUNTU_RELEASE}x isn't part of the name. This makes
        # it possible to increment `x` and have launchpad recognize it as a new
        # version.
        full_version = '%s-%s%d' % (version, ubuntu_release, resubmission)
        if slot:
            chlog_version = slot + ':' + full_version
        else:
            chlog_version = full_version

        # Override changelog
        os.chdir(os.path.join(release_dir, prefix))
        env = {}
        if debfullname:
            env['DEBFULLNAME'] = debfullname
        if debemail:
            env['DEBEMAIL'] = debemail
        subprocess.check_call([
                 'dch',
                 '-b',  # force
                 '-v', chlog_version,
                 '--distribution', ubuntu_release,
                 'launchpad-submit update'
                ],
                env=env
                )

        # Call debuild, the actual workhorse
        os.chdir(os.path.join(release_dir, prefix))
        subprocess.check_call(
                ['debuild',
                 debuild_params,
                 '-S',  # build source package only
                 '--lintian-opts', '-EvIL', '+pedantic'
                 ]
                )

        # Submit to launchpad.
        os.chdir(os.pardir)
        if not dry:
            print()
            print('Uploading to PPA %s...' % ppa_string)
            print()
            subprocess.check_call([
                'dput',
                'ppa:%s' % ppa_string,
                '%s_%s_source.changes' % (name, full_version)
                ])
            # Remove the upload file so we can upload again to another ppa
            os.remove('%s_%s_source.ppa.upload'
                      % (name, full_version)
                      )

    return


def update_patches(directory):
    '''debuild's patch apply doesn't allow fuzz, but fuzz is often what happens
    when applying a Debian patch to the master branch. `patch` itself is more
    robust, so use that here to update the Debian patches.
    '''
    debian_dir = os.path.join(directory, 'debian')
    if os.path.isfile(os.path.join(debian_dir, 'patches', 'ubuntu.series')):
        series = os.path.join(debian_dir, 'patches', 'ubuntu.series')
    elif os.path.isfile(os.path.join(debian_dir, 'patches', 'series')):
        series = os.path.join(debian_dir, 'patches', 'series')
    else:
        return

    with open(series, 'r') as f:
        content = f.readlines()

    if content:
        try:
            repo = git.Repo(directory)
        except git.exc.InvalidGitRepositoryError:
            raise RuntimeError('Directory %s is not Git-managed.' % directory)

        repo.git.checkout('.')

        tmp_dir = tempfile.mkdtemp()
        filenames = []
        for line in content:
            filename = line.strip()
            if filename[0] == '#':
                # skip commented-out lines
                continue

            repo.git.checkout('.')
            # apply the patch
            patch_path = os.path.join(debian_dir, 'patches', filename)
            try:
                # Don't use git.apply here: It doesn't understand fuzz.
                os.chdir(directory)
                subprocess.check_call(
                    'patch -f -p 1 < %s' % patch_path,
                    shell=True
                    )
            except subprocess.CalledProcessError:
                # Patch cannot be applied properly. That happens, just pass on
                # this one then.
                print('\n  Patch NOT properly applied. Skipping.\n')
                continue

            filenames.append(filename)
            # write diff to temporary file
            with open(os.path.join(tmp_dir, filename), 'w') as f:
                f.write(repo.git.diff())
                f.write('\n')

        # move the files back over to debian/patches
        repo.git.checkout('.')
        for filename in filenames:
            shutil.move(
                    os.path.join(tmp_dir, filename),
                    os.path.join(debian_dir, 'patches', filename)
                    )

        # shutil.rmtree(tmp_dir)
    return


def undo_patches(directory):
    debian_dir = os.path.join(directory, 'debian')
    if os.path.isfile(os.path.join(debian_dir, 'patches', 'ubuntu.series')):
        series = os.path.join(debian_dir, 'patches', 'ubuntu.series')
    elif os.path.isfile(os.path.join(debian_dir, 'patches', 'series')):
        series = os.path.join(debian_dir, 'patches', 'series')
    else:
        return

    with open(series, 'r') as f:
        content = f.readlines()

    for line in content:
        filename = line.strip()
        if filename[0] == '#':
            # skip commented-out lines
            continue

        # unapply the patch
        patch_path = os.path.join(debian_dir, 'patches', filename)
        os.chdir(directory)
        subprocess.check_call(
            'patch -R -p 1 < %s' % patch_path,
            shell=True
            )
    return


def _copytree(source, dest):
    '''Workaround until Python 3.5, fixing
    <https://bugs.python.org/issue21697>, is available.
    '''
    import subprocess
    command = 'cp -r %s %s' % (source, dest)
    process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True
            )
    process.stdout.read()[:-1]
    ret = process.wait()

    if ret != 0:
        import sys
        sys.exit( "\nERROR: The command \n\n%s\n\nreturned a nonzero " \
                  "exit status. The error message is \n\n%s\n\n" \
                  "Abort.\n" % \
                  ( command, process.stderr.read()[:-1] )
                )

    return


def _find_all_dirs(name, path):
    # From http://stackoverflow.com/a/1724723/353337
    result = []
    for root, dirs, files in os.walk(path):
        if name in dirs:
            result.append(os.path.join(root, name))
    return result


def _find_all_files(name, path):
    # From http://stackoverflow.com/a/1724723/353337
    result = []
    for root, dirs, files in os.walk(path):
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
    undo_patches(directory)

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


def create_repo(orig, debian, out, do_update_patches):
    orig_dir = _get_dir(orig)
    _copytree(os.path.join(orig_dir, '*'), out)

    if debian:
        assert not os.path.isdir(os.path.join(out, 'debian'))
        debian_dir = _get_dir(debian)
        _copytree(os.path.join(debian_dir, 'debian'), out)

    assert os.path.isdir(os.path.join(out, 'debian'))

    # Remove git-related entities to ensure a smooth creation of the repo below
    try:
        for dot_git in _find_all_dirs('.git', out):
            shutil.rmtree(dot_git)
        for dot_gitignore in _find_all_files('.gitignore', out):
            os.remove(dot_gitignore)
    except FileNotFoundError:
        pass

    repo = git.Repo.init(out)
    repo.index.add('*')
    repo.index.commit('import orig, debian')

    if do_update_patches:
        update_patches(out)
        repo.git.add(update=True)
        repo.index.commit('updated patches')

    return
