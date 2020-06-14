#!/usr/bin/env python3

import datetime
import re
##
import iso3166
##
import classes


_strip_re = re.compile(r'^\s*(?P<num>[0-9.]+).*$')


class Ranker(classes.Ranker):
    mirrorlist_url = 'https://www.archlinux.org/mirrors/status/tier/1/'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_mirrors()
        self.mycountry = iso3166.countries_by_alpha2[self.my_info['country']].name

    def extract_mirrors(self):
        # Limit to only successful mirrors.
        mirrors = self.bs.find('table', {'id': 'successful_mirrors'})
        # Ayyy, thanks dude.
        # Modified from https://stackoverflow.com/a/56835562/733214.
        header = mirrors.find('thead').find('tr')
        headers = [h.text if h.text != '' else 'details' for h in header.find_all('th')]
        raw_rows = mirrors.find_all('tr')
        # rows = [{headers[i]: cell.text for i, cell in enumerate(row.find_all('td'))} for row in raw_rows]
        rows = [{headers[i]: cell for i, cell in enumerate(row.find_all('td'))} for row in raw_rows]
        for r in rows:
            for k, v in r.items():
                print(v)
                if k in ('Completion %', 'Mirror Score', 'μ Duration (s)', 'σ Duration (s)'):
                    r[k] = float(_strip_re.sub(r'\g<num>', v.text).strip())
                elif k == 'μ Delay (hh:mm)':
                    # HOO boy. Wish they just did it in seconds.
                # elif k == 'Country':
            self.raw_mirrors.append(r)
        # for row in rows:
        #     if not row:
        #         continue
        #     for k in ('Completion %', 'Mirror Score', 'μ Duration (s)', 'σ Duration (s)'):
        #         row[k] = float(_strip_re.sub(r'\g<num>', row[k]).strip())

        return(None)


def main():
    r = Ranker()
    r.extract_mirrors()
    import pprint
    pprint.pprint(r.raw_mirrors)
    return(None)


if __name__ == '__main__':
    main()
