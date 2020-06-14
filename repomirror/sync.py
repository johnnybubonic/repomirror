import datetime
import logging
import os
##
from . import config


_logger = logging.getLogger()


class Args(object):
    def __init__(self, args_xml):
        self.xml = args_xml
        self.args = []
        self._parse_xml()

    def _parse_xml(self):
        for arg_xml in self.xml.xpath('(short|long)'):



class Mount(object):
    def __init__(self, mpchk_xml):
        self.path = os.path.abspath(os.path.expanduser(mpchk_xml))
        self.is_mounted = None
        self._check_mount()

    def _check_mount(self):
        with open('/proc/mounts', 'r') as fh:
            raw = fh.read()
        for line in raw.splitlines():
            l = line.split()
            mp = l[1]
            if mp == self.path:
                self.is_mounted = True
                return(None)
        self.is_mounted = False
        return(None)


class TimestampFile(object):
    def __init__(self, ts_xml):
        self.fmt = ts_xml.attrib.get('timeFormat', 'UNIX_EPOCH')
        if self.fmt == 'UNIX_EPOCH':
            self.fmt = '%s'
        elif self.fmt == 'MICROSECOND_EPOCH':
            self.fmt = '%s.%f'
        self.path = os.path.abspath(os.path.expanduser(ts_xml.text))


class Upstream(object):
    def __init__(self, upstream_xml):
        pass


class Sync(object):
    def __init__(self, cfg = None, dummy = False, distro = None, logdir = None, *args, **kwargs):
        _args = dict(locals())
        del(_args['self'])
        _logger.debug('Sync class instantiated with args: {0}'.format(_args))
        self.cfg = config.Config(cfg)
