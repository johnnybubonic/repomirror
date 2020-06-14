#!/usr/bin/env python3

import argparse
import csv
import datetime
import io
import re
##
import classes


_proto_re = re.compile(r'^(?P<proto>https?)(?P<uri>.*)')


class Ranker(classes.Ranker):
    # https://lists.centos.org/pipermail/centos-mirror/2017-March/010312.html
    mirrorlist_url = 'https://www.centos.org/download/full-mirrorlist.csv'
    distro_name = 'centos'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_mirrors()

    def extract_mirrors(self, preferred_proto = 'rsync'):
        preferred_proto = preferred_proto.lower()
        if preferred_proto not in ('rsync', 'ftp'):
            raise ValueError('Invalid preferred_proto; must be one of rsync or ftp')
        non_preferred = ('rsync' if preferred_proto == 'ftp' else 'ftp')
        c = csv.DictReader(io.StringIO(self.raw_html), )
        for row in c:
            if not row['Country'] or row['Country'].strip() == '':
                continue
            # GorRAM it, dudes. States are not countries.
            country = row['Country'].strip()
            region = row['Region'].strip()
            if region == 'US':
                country = region
            if country != self.my_info['country']:
                continue
            for k, v in row.items():
                if v.strip() == '':
                    row[k] = None
            pref_url = row['{0} mirror link'.format(preferred_proto)]
            nonpref_url = row['{0} mirror link'.format(non_preferred)]
            if pref_url:
                url = _proto_re.sub(r'{0}\g<uri>'.format(preferred_proto), pref_url)
            else:
                if not nonpref_url:
                    continue
                url = _proto_re.sub(r'{0}\g<uri>'.format(non_preferred), nonpref_url)
            self.raw_mirrors.append(row)
            self.mirror_candidates.append(url)
        return(None)


def parseArgs():
    args = argparse.ArgumentParser(description = 'Generate a list of suitable CentOS upstream mirrors in order of '
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
