#!/usr/bin/env python3

import argparse
import datetime
##
import classes


class Ranker(classes.Ranker):
    mirrorlist_url = 'https://www.archlinux.org/mirrors/status/tier/1/json/'
    distro_name = 'archlinux'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_mirrors()

    def extract_mirrors(self):
        for mirror in self.req.json()['urls']:
            if not all((mirror['active'],  # Only successful/active mirrors
                        mirror['isos'],  # Only mirrors with ISOs
                        # Only mirrors that support rsync (Arch mirrors do not support ftp)
                        (mirror['protocol'] == 'rsync'),
                        # Only mirrors in the system's country (May be buggy if both are not ISO-3166-1 Alpha-2)
                        (mirror['country_code'].upper() == self.my_info['country'].upper()),
                        # Only mirrors that are at least 100% complete.
                        (mirror['completion_pct'] >= 1.0))):
                continue
            # Convert the timestamp to python-native.
            mirror['last_sync'] = datetime.datetime.strptime(mirror['last_sync'], '%Y-%m-%dT%H:%M:%SZ')
            self.raw_mirrors.append(mirror)
            self.mirror_candidates.append(mirror['url'])
        return(None)


def parseArgs():
    args = argparse.ArgumentParser(description = 'Generate a list of suitable Arch Linux upstream mirrors in order of '
                                                 'speed')
    args.add_argument('-x', '--xml',
                      dest = 'xml',
                      action = 'store_true',
                      help = ('If specified, generate a config stub instead of a printed list of URLs'))
    return(args)


def main():
    args = parseArgs().parse_args()
    r = Ranker()
    r.extract_mirrors()
    r.speedcheck()
    if args.xml:
        print(r.gen_xml())
    else:
        r.print()
    return(None)


if __name__ == '__main__':
    main()
