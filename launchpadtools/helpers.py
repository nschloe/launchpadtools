# -*- coding: utf-8 -*-
#
import subprocess
import sys


def copytree(source, dest):
    '''Workaround until Python 3.5, fixing
    <https://bugs.python.org/issue21697>, is available.
    '''
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
        sys.exit('\nERROR: The command \n\n%s\n\nreturned a nonzero '
                 'exit status. The error message is \n\n%s\n\n'
                 'Abort.\n' %
                 (command, process.stderr.read()[:-1])
                 )

    return
