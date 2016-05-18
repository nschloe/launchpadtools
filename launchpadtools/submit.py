# -*- coding: utf-8 -*-
#
import git
from launchpadlib.launchpad import Launchpad
import os
import re
import shutil
import subprocess
import tarfile
import tempfile

from . import clone
from . import helpers


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


def _parse_package_version(version):
    '''Dissect version in upstream, debian/ubuntu parts.
    '''
    m = re.match('(([0-9]+):)?(.*)', version)
    if m:
        epoch = m.group(2)
        version = m.group(3)
    else:
        epoch = None

    parts = version.split('-')
    m = re.match('([0-9\.]*)[a-z]*([0-9\.]*)', parts[-1])
    if len(parts) > 1 and m:
        upstream = '-'.join(parts[:-1])
        debian = m.group(1)
        ubuntu = m.group(2)
    else:
        upstream = version
        debian = None
        ubuntu = None

    return epoch, upstream, debian, ubuntu


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


def submit(
        orig,
        debian,
        ubuntu_releases,
        dry,
        ppa_string,
        debfullname,
        debemail,
        debuild_params='',
        version_override=None,
        version_append_hash=False,
        force=False,
        do_update_patches=False
        ):
    repo_dir = tempfile.mkdtemp()
    clone.clone(orig, repo_dir)
    if debian:
        # Create debian/ folder in a temporary directory
        debian_dir = tempfile.mkdtemp()
        clone.clone(debian, debian_dir)
    else:
        debian_dir = os.path.join(repo_dir, 'debian')
        assert os.path.isdir(debian_dir)

    name, version = _get_info_from_changelog(
            os.path.join(debian_dir, 'changelog')
            )

    # Dissect version in upstream, debian/ubuntu parts.
    epoch, upstream_version, debian_version, ubuntu_version = \
        _parse_package_version(version)

    if version_override:
        upstream_version = version_override

    # Create git repo.
    # Remove git-related entities to ensure a smooth creation of the repo below
    try:
        for dot_git in _find_all_dirs('.git', repo_dir):
            shutil.rmtree(dot_git)
        for dot_gitignore in _find_all_files('.gitignore', repo_dir):
            os.remove(dot_gitignore)
    except FileNotFoundError:
        pass
    repo = git.Repo.init(repo_dir)
    repo.index.add('*')
    repo.index.commit('import orig')

    # Create the orig tarball.
    orig_tarball = os.path.join('/tmp/', name + '.tar.gz')
    prefix = name + '-' + upstream_version
    with open(orig_tarball, 'wb') as fh:
        repo.archive(fh, prefix=prefix + '/', format='tar.gz')

    if debian:
        # Add the debian/ folder
        helpers.copytree(debian_dir, repo_dir)
        repo.git.add('debian/')
        repo.index.commit('add ./debian')

        if do_update_patches:
            _update_patches(repo_dir)
            repo.git.add(update=True)
            repo.index.commit('updated patches')

    lp = Launchpad.login_anonymously('foo', 'production', None)
    ppa_owner, ppa_name = tuple(ppa_string.split('/'))

    owner = lp.people[ppa_owner]
    ppa = owner.getPPAByName(name=ppa_name)
    sources = ppa.getPublishedSources()

    published_sources = [
            d for d in sources.entries if d['status'] == 'Published'
            ]

    tree_hash_short = repo.tree().hexsha[:8]
    # Use the `-` as a separator (instead of `~` as it's often used) to
    # make sure that ${UBUNTU_RELEASE}x isn't part of the name. This makes
    # it possible to increment `x` and have launchpad recognize it as a new
    # version.
    if version_append_hash:
        upstream_version += '-%s' % tree_hash_short

    # check which ubuntu series we need to submit to
    submit_releases = []
    for ubuntu_release in ubuntu_releases:
        # Check if this version has already been published.
        published_in_series = [
                d for d in published_sources
                if d['distro_series_link'] ==
                'https://api.launchpad.net/1.0/ubuntu/%s' % ubuntu_release
                ]
        parts = published_in_series[0]['source_package_version'].split('-')
        already_published = len(parts) == 3 and parts[1] == tree_hash_short
        if force or not already_published:
            submit_releases.append(ubuntu_release)
        else:
            # Expect a package version of the form
            # 2.1.0~20160504184836-01b3a567-trusty1
            print('Same version already published for %s.' % ubuntu_release)

    _submit(
        orig_tarball,
        debian,
        name,
        upstream_version,
        debian_version,
        ubuntu_version,
        submit_releases,
        epoch,
        dry,
        ppa_string,
        debfullname,
        debemail,
        debuild_params='',
        force=False
        )
    return


def submit_dsc(
        dsc,
        ubuntu_releases,
        dry,
        ppa_string,
        debfullname,
        debemail,
        debuild_params='',
        force=False
        ):
    orig_tarball, debian_dir = _get_items_from_dsc(dsc)

    if not debian_dir:
        tmp_dir = tempfile.mkdtemp()
        os.chdir(tmp_dir)
        tar = tarfile.open(orig_tarball)
        tar.extractall()
        tar.close()

        # Find the debian subdirectory
        subdir = None
        for item in os.listdir(tmp_dir):
                if os.path.isdir(item):
                        subdir = os.path.join(tmp_dir, item)
                        break
        debian_dir = os.path.join(tmp_dir, subdir, 'debian')

    name, version = _get_info_from_changelog(
            os.path.join(debian_dir, 'changelog')
            )
    epoch, upstream_version, debian_version, ubuntu_version = \
        _parse_package_version(version)

    _submit(
        orig_tarball,
        debian_dir,
        name,
        upstream_version,
        debian_version,
        ubuntu_version,
        ubuntu_releases,
        epoch,
        dry,
        ppa_string,
        debfullname,
        debemail,
        debuild_params='',
        force=False
        )
    return


def _submit(
        orig_tarball,
        debian_dir,
        name,
        upstream_version,
        debian_version,
        ubuntu_version,
        ubuntu_releases,
        slot,
        dry,
        ppa_string,
        debfullname,
        debemail,
        debuild_params='',
        force=False
        ):
    for ubuntu_release in ubuntu_releases:
        # Create empty directory of the form
        #     /tmp/trilinos/trusty/
        release_dir = os.path.join('/tmp', name, ubuntu_release)
        if os.path.exists(release_dir):
            shutil.rmtree(release_dir)
        # Use Python3's makedirs for recursive creation
        os.makedirs(release_dir, exist_ok=True)

        # Copy source tarball to
        #     /tmp/trilinos/trusty/trilinos_4.3.1.2~20121123-01b3a567.tar.gz
        # Preserve file type.
        _, ext = os.path.splitext(orig_tarball)
        tarball_dest = '%s_%s.orig.tar%s' % (name, upstream_version, ext)

        shutil.copy2(orig_tarball, os.path.join(release_dir, tarball_dest))
        # Unpack the tarball
        os.chdir(release_dir)
        tar = tarfile.open(tarball_dest)
        tar.extractall()
        tar.close()

        # Find the subdirectory
        prefix = None
        for item in os.listdir(release_dir):
            if os.path.isdir(item):
                prefix = os.path.join(release_dir, item)
                break
        assert os.path.isdir(prefix)

        if debian_dir:
            # copy over debian directory
            if not os.path.isdir(os.path.join(release_dir, prefix, 'debian')):
                assert os.path.isdir(debian_dir)
                helpers.copytree(
                        debian_dir,
                        os.path.join(release_dir, prefix, 'debian')
                        )

        # We cannot use "-ubuntu1" as a suffix here since we'd like to submit
        # for multiple ubuntu releases. If the version strings were exactly the
        # same, the following error is produced on upload:
        #
        #   File gmsh_2.12.1~20160512220459-ef262f68-ubuntu1.debian.tar.gz
        #   already exists in Gmsh nightly, but uploaded version has different
        #   contents.
        #
        chlog_version = upstream_version + '-'
        if debian_version:
            chlog_version += debian_version
        if ubuntu_version:
            chlog_version += '%s%s' % (ubuntu_release, ubuntu_version)
        else:
            chlog_version += '%s1' % ubuntu_release

        slot_version = chlog_version
        if slot:
            slot_version = slot + ':' + chlog_version

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
                 '-v', slot_version,
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
                '%s_%s_source.changes' % (name, chlog_version)
                ])

    return


def _update_patches(directory):
    '''debuild's patch apply doesn't allow fuzz, but fuzz is often what happens
    when applying a Debian patch to the master branch. `patch` itself is more
    robust, so use that here to update the Debian patches.
    '''
    try:
        repo = git.Repo(directory)
    except git.exc.InvalidGitRepositoryError:
        raise RuntimeError('Directory %s is not Git-managed.' % directory)

    repo.git.checkout('.')

    os.chdir(directory)
    subprocess.check_call(
        'while quilt push; do quilt refresh; done',
        shell=True,
        env={
            'QUILT_PATCHES': 'debian/patches'
            }
        )

    # undo all patches; only the changes in the debian/patches/ remain.
    subprocess.check_call(
        'quilt pop -a',
        shell=True,
        env={
            'QUILT_PATCHES': 'debian/patches'
            }
        )

    repo.index.add('*')
    repo.index.commit('update patches')

    return


def _get_items_from_dsc(url):
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)
    subprocess.check_call(
            'dget %s' % url,
            shell=True
            )

    dsc_filename = os.path.basename(url)

    # Get the orig/debian file names from the dsc file.
    with open(dsc_filename, 'r') as f:
        while f.readline().strip() != 'Files:':
            pass

        filenames = []
        while True:
            # The lines have the form
            #
            # 74c21e7d24df6f98db139... 1681868 git-buildpackage_0.7.4.tar.xz
            #
            # and we're interested in the last part, the file name.
            line = f.readline().strip()
            m = re.match(' *[a-z0-9]+ +[0-9]+ +([^ ]+).*', line)
            if m:
                filenames.append(m.group(1))
            else:
                # bail on the first line that doesn't match
                break

    if len(filenames) == 1:
        orig_tarball = os.path.join(tmp_dir, filenames[0])
        debian_dir = None
    elif len(filenames) == 2:
        # Which one is the orig and which is the debian?
        if re.search('\.orig\.', filenames[0]):
            orig_tarball = os.path.join(tmp_dir, filenames[0])
            debian = filenames[1]
        elif re.search('\.orig\.', filenames[1]):
            orig_tarball = os.path.join(tmp_dir, filenames[1])
            debian = filenames[0]
        else:
            raise RuntimeError('expected .orig. in one of the filenames')

        # Unpack the debian tarball
        tar = tarfile.open(debian)
        tar.extractall()
        tar.close()

        debian_dir = os.path.join(tmp_dir, os.path.join(tmp_dir, 'debian'))

        assert os.path.isdir(debian_dir)
    else:
        raise RuntimeError('Expected either 1 or 2 file names in DSC file.')

    return orig_tarball, debian_dir
