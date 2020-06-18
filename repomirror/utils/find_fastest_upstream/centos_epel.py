#!/usr/bin/env python3

import argparse
import re
##
import classes


_proto_re = re.compile(r'^(?P<proto>https?)(?P<uri>.*)')


class Ranker(classes.Ranker):
    # No CSV, JSON, or XML that I could find, unfortunately.
    # There's apparently? an API to mirrormanager2 but I can't seem to find a public endpoint nor an endpoint that
    # would return the mirrors.
    mirrorlist_url = 'https://admin.fedoraproject.org/mirrormanager/mirrors/EPEL'
    distro_name = 'EPEL'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_mirrors()

    def extract_mirrors(self, preferred_proto = 'rsync'):
        preferred_proto = preferred_proto.lower()
        if preferred_proto not in ('rsync', 'ftp'):
            raise ValueError('Invalid preferred_proto; must be one of rsync or ftp')
        non_preferred = ('rsync' if preferred_proto == 'ftp' else 'ftp')
        print(('Fedora (who maintains EPEL) do their mirroring in an extremely weird way.\n'
               'See https://fedoraproject.org/wiki/Infrastructure/Mirroring and '
               'https://fedoraproject.org/wiki/Infrastructure/Mirroring/Tiering#Tier_1_Mirrors for which mirrors and '
               'how to sync.'))
        return(None)
        # mirror_section = self.bs.find('h2', string = 'Public active mirrors')
        # mirror_table = mirror_section.find_next('table')
        # if mirror_table is None:
        #     return(None)
        # # https://stackoverflow.com/a/56835562/733214
        # headers = [h.text for h in mirror_table.find_all('th')]
        # rows = [m for m in mirror_table.find_all('tr')][1:]
        # for row in rows:
        #     mirror = {}
        #     do_skip = False
        #     for idx, cell in enumerate(row.find_all('td')):
        #         k = headers[idx]
        #         v = cell.text.strip()
        #         if k == 'Country' and v != self.my_info['country']:
        #             do_skip = True
        #             continue
        #         if k == 'Categories' and not do_skip:
        #             # TODO: DO THIS BETTER! Their mirrorlist sucks and is not easily parsed at all.
        #             # I need to check and try to grab the specific URL that contains "epel".
        #             if 'EPEL' not in v:
        #                 do_skip = True
        #                 continue
        #             pref_proto = cell.find('a', attrs = {
        #                 'href': re.compile(r'^{0}://'.format(preferred_proto), re.IGNORECASE)})
        #             non_pref = cell.find('a', attrs = {
        #                 'href': re.compile(r'^{0}://'.format(non_preferred), re.IGNORECASE)})
        #             if pref_proto is not None:
        #                 v = pref_proto['href']
        #             elif non_pref is not None:
        #                 v = non_pref['href']
        #             else:
        #                 v = None
        #             mirror['url'] = v
        #         # Fedora team can't spell.
        #         elif k in ('Bandwidth', 'Bandwith'):
        #             mirror['bw'] = int(v)
        #     if do_skip:
        #         continue
        #     if not mirror['url']:
        #         continue
        #     self.raw_mirrors.append(mirror)
        #     self.mirror_candidates.append(mirror['url'])
        # return(None)


def parseArgs():
    args = argparse.ArgumentParser(description = 'Generate a list of suitable EPEL upstream mirrors in order of '
                                                 'speed.')
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
