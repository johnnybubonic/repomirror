#!/usr/bin/env python3

import os
import shutil
##
import logger
import fetcher

dest = '/tmp/ipxe_ftp'
path = 'ipxe'


def main():
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    f = fetcher.FTP('10.11.12.12', 21, path, dest)
    f.fetch()


if __name__ == '__main__':
    main()

