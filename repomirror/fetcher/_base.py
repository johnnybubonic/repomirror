import datetime
import logging
import os


_logger = logging.getLogger()


class BaseFetcher(object):
    type = None

    def __init__(self, domain, port, path, dest, owner = None, filechecks = None, *args, **kwargs):
        self.domain = domain
        self.port = int(port)
        self.path = path
        self.dest = os.path.abspath(os.path.expanduser(dest))
        self.url = '{0}://{1}:{2}/{3}'.format(self.type, self.domain, self.port, self.path.lstrip('/'))
        self.owner = owner
        self.filechecks = filechecks
        self.timestamps = {}
        os.makedirs(self.dest, mode = 0o0755, exist_ok = True)
        if self.owner:
            os.chown(self.dest, **self.owner)

    def check(self):
        for k, v in self.filechecks['remote'].items():
            if v:
                tstmp_raw = self.fetch_content(v.path).decode('utf-8').strip()
                if '%s' in v.fmt:
                    tstmp = datetime.datetime.fromtimestamp(int(tstmp_raw))
                else:
                    tstmp = datetime.datetime.strptime(tstmp_raw, v.fmt)
                self.timestamps[k] = tstmp
        _logger.debug('Updated timestamps: {0}'.format(self.timestamps))
        return(None)

    def fetch_content(self, path):
        # Dummy func.
        return(b'')
