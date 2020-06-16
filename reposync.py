#!/usr/bin/env python3

import argparse
import os
import pathlib
import sys
##
##
_cur_file = pathlib.Path(os.path.abspath(os.path.expanduser(__file__))).resolve()
_cur_path = os.path.dirname(_cur_file)
sys.path.insert(1, _cur_path)
import repomirror


if os.geteuid() == 0:
    _def_logdir = '/var/log/repo'
else:
    _def_logdir = '~/.cache/repologs'


def parseArgs():
    args = argparse.ArgumentParser(description = 'Sync repositories for various distributions to local paths')
    args.add_argument('-c', '--config',
                      default = '~/.config/repomirror.xml',
                      dest = 'cfg',
                      help = ('The path to the config file. If it does not exist, a bare version will be created. '
                              'Default: ~/.config/repomirror.xml'))
    # args.add_argument('-n', '--dry-run',
    #                   action = 'store_true',
    #                   dest = 'dummy',
    #                   help = ('If specified, do not actually sync anything (other than timestamp files if '
    #                           'applicable to determine logic); do not actually sync any repositories. Useful for '
    #                           'generating logs to determine potential issues before they happen'))
    args.add_argument('-d', '--distro',
                      dest = 'distro',
                      action = 'append',
                      help = ('If specified, only sync the specified distro in the config file (otherwise sync all '
                              'specified). May be given multiple times'))
    args.add_argument('-l', '--logdir',
                      default = _def_logdir,
                      dest = 'logdir',
                      help = ('The path to the directory where logs should be written. The actual log files will be '
                              'named after their respective distro names in the config file. '
                              'Defailt: {0}'.format(_def_logdir)))
    return(args)


def main():
    args = parseArgs().parse_args()
    r = repomirror.Sync(**vars(args))
    r.sync()
    return(None)


if __name__ == '__main__':
    main()
