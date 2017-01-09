# -*- coding: utf-8 -*-
#
import subprocess
import sys


def copytree(source, dest, ignore_hidden=False):
    '''Workaround until Python 3.5, fixing
    <https://bugs.python.org/issue21697>, is available.
    '''
    if ignore_hidden:
        command = (
            'rsync -av --progress --exclude=".*" --exclude=".*/" %s/* %s'
            % (source, dest)
            )
    else:
        command = 'cp -ar %s %s' % (source, dest)

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
        sys.exit('\nERROR: The command \n\n%s\n\nreturned a nonzero '
                 'exit status. The error message is \n\n%s\n\n'
                 'Abort.\n' %
                 (command, process.stderr.read()[:-1])
                 )

    return
