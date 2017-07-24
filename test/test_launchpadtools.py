# -*- coding: utf-8 -*-
#
import launchpadtools


def test():
    launchpadtools.submit.submit(
        work_dir='/tmp/dockergc-test-launchpadtools/',
        ubuntu_releases=['xenial'],
        ppa_string='nschloe/docker-gc-nightly',
        launchpad_login_name='johndoe',
        debuild_params='',
        version_override='1.2.3',
        version_append_hash=True,
        force=True,
        do_update_patches=True,
        dry=True
        )
    return
