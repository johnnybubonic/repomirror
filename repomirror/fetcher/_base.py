import datetime
import logging
import os


_logger = logging.getLogger()


class BaseFetcher(object):
    type = None

    def __init__(self,
                 domain,
                 port,
                 path,
                 dest,
                 owner = None,
                 filechecks = None,
                 mtime = False,
                 offset = None,
                 *args,
                 **kwargs):
        self.domain = domain
        self.port = int(port)
        self.path = path
        self.dest = os.path.abspath(os.path.expanduser(dest))
        self.mtime = mtime
        self.offset = offset
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
                if self.mtime:
                    self.timestamps[k] = datetime.datetime.fromtimestamp(float(self.fetch_content(v.path, mtime_only = True)))
                else:
                    tstmp_raw = self.fetch_content(v.path).decode('utf-8').strip()
                    if '%s' in v.fmt:
                        tstmp = datetime.datetime.fromtimestamp(float(tstmp_raw))
                    else:
                        tstmp = datetime.datetime.strptime(tstmp_raw, v.fmt)
                    self.timestamps[k] = tstmp
                if self.offset:
                    if self.offset.mod == '+' or not self.offset.mod:
                        newval = self.timestamps[k] + self.offset.offset
                    elif self.offset.mod == '-':
                        newval = self.timestamps[k] - self.offset.offset
                    self.timestamps[k] = newval
        _logger.debug('Updated upstream timestamps: {0}'.format(self.timestamps))
        return(None)

    def fetch_content(self, path, mtime_only = False):
        # Dummy func.
        return(b'')
