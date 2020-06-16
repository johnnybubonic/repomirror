import datetime
import logging
import pwd
import grp
import os
import socket
##
from . import config
from . import constants
from . import fetcher


_logger = logging.getLogger()


def get_owner(owner_xml):
    owner = {}
    user = owner_xml.find('user')
    if user:
        user = user.text
    group = owner_xml.find('group')
    if group:
        group = group.text
    if user:
        user_obj = pwd.getpwnam(user)
    else:
        user_obj = pwd.getpwuid(os.geteuid())
    owner['uid'] = user_obj.pw_uid
    if group:
        group_obj = grp.getgrnam(group)
    else:
        group_obj = grp.getgrgid(pwd.getpwuid(os.geteuid()).pw_gid)
    owner['gid'] = group_obj.gr_gid
    _logger.debug('Resolved owner xml to {0}'.format(owner))
    return(owner)


class Args(object):
    def __init__(self, args_xml):
        self.xml = args_xml
        self.args = []
        self._parse_xml()

    def _parse_xml(self):
        self.args = []
        for arg_xml in self.xml.xpath('(short|long)'):
            val = arg_xml.attrib.get('value')
            if arg_xml.tag == 'short':
                prefix = '-'
            # elif arg_xml.tag == 'long':
            else:
                prefix = '--'
            arg = '{0}{1}'.format(prefix, arg_xml.text)
            if val:
                arg += '={0}'.format(val)
            self.args.append(arg)
        _logger.debug('Generated args list: {0}'.format(self.args))
        return(None)


class Mount(object):
    def __init__(self, mpchk_xml):
        self.path = os.path.abspath(os.path.expanduser(mpchk_xml))
        self.is_mounted = None
        self._check_mount()

    def _check_mount(self):
        _logger.debug('Getting mount status for {0}'.format(self.path))
        with open('/proc/mounts', 'r') as fh:
            raw = fh.read()
        for line in raw.splitlines():
            l = line.split()
            mp = l[1]
            if mp == self.path:
                _logger.debug('{0} is mounted.'.format(self.path))
                self.is_mounted = True
                return(None)
        self.is_mounted = False
        _logger.debug('{0} is not mounted.'.format(self.path))
        return(None)


class TimestampFile(object):
    def __init__(self, ts_xml, owner_xml = None):
        self.fmt = ts_xml.attrib.get('timeFormat', 'UNIX_EPOCH')
        if self.fmt == 'UNIX_EPOCH':
            self.fmt = '%s'
        elif self.fmt == 'MICROSECOND_EPOCH':
            self.fmt = '%s.%f'
        _logger.debug('Set timestamp format string to {0}'.format(self.fmt))
        self.owner_xml = owner_xml
        self.owner = {}
        if self.owner_xml:
            self.owner = get_owner(self.owner_xml)
        _logger.debug('Owner set is {0}'.format(self.owner))
        self.path = os.path.abspath(os.path.expanduser(ts_xml.text))
        _logger.debug('Path resolved to {0}'.format(self.path))

    def read(self, parentdir = None):
        if parentdir:
            path = os.path.join(os.path.abspath(os.path.expanduser(parentdir)),
                                self.path.lstrip('/'))
        else:
            path = self.path
        with open(path, 'r') as fh:
            timestamp = datetime.datetime.strptime(fh.read().strip(), self.fmt)
        _logger.debug('Read timestamp {0} from {1}'.format(str(timestamp), self.path))
        return(timestamp)

    def write(self):
        dname = os.path.dirname(self.path)
        if not os.path.isdir(dname):
            os.makedirs(dname, mode = 0o0755)
            if self.owner:
                os.chown(dname, **self.owner)
            _logger.debug('Created {0}'.format(dname))
        with open(self.path, 'w') as fh:
            fh.write(datetime.datetime.utcnow().strftime(self.fmt))
            fh.write('\n')
        os.chmod(self.path, mode = 0o0644)
        if self.owner:
            os.chown(self.path, **self.owner)
        _logger.debug('Wrote timestamp to {0}'.format(self.path))
        return(None)


class Upstream(object):
    def __init__(self, upstream_xml, dest, rsync_args = None, owner = None, filechecks = None):
        self.xml = upstream_xml
        # These are required for all upstreams.
        self.sync_type = self.xml.find('syncType').text.lower()
        self.domain = self.xml.find('domain').text
        self.path = self.xml.find('path').text
        self.dest = os.path.abspath(os.path.expanduser(dest))
        self.owner = owner
        self.filechecks = filechecks
        self.has_new = False
        # These are optional.
        for i in ('port', 'bwlimit'):
            e = self.xml.find(i)
            if e:
                setattr(self, i, int(e.text))
            else:
                setattr(self, i, None)
        if not getattr(self, 'port'):
            self.port = constants.PROTO_DEF_PORTS[self.sync_type]
        self.available = None
        if self.sync_type == 'rsync':
            self.fetcher = fetcher.RSync(self.domain,
                                         self.port,
                                         self.path,
                                         self.dest,
                                         rsync_args = rsync_args,
                                         filechecks = self.filechecks,
                                         owner = self.owner)
        else:
            self.fetcher = fetcher.FTP(self.domain, self.port, self.path, self.dest, owner = self.owner)
        self._check_conn()

    def _check_conn(self):
        sock = socket.socket()
        sock.settimeout(7)
        try:
            sock.connect((self.domain, self.port))
            sock.close()
            self.available = True
        except (socket.timeout, socket.error):
            self.available = False
        return(None)

    def sync(self):
        self.fetcher.fetch()
        return(None)


class Distro(object):
    def __init__(self, distro_xml):
        self.xml = distro_xml
        self.name = distro_xml.attrib['name']
        self.dest = os.path.abspath(os.path.expanduser(distro_xml.find('dest').text))
        self.mount = Mount(self.xml.find('mountCheck'))
        self.filechecks = {'local': {'check': None,
                                     'sync': None},
                           'remote': {'update': None,
                                      'sync': None}}
        self.timestamps = {}
        self.rsync_args = None
        self.owner = None
        self.upstreams = []
        # These are optional.
        self.owner_xml = self.xml.find('owner')
        if self.owner_xml:
            self.owner = get_owner(self.owner_xml)
        self.rsync_xml = self.xml.find('rsyncArgs')
        if self.rsync_xml:
            self.rsync_args = Args(self.rsync_xml)
        for i in ('Check', 'Sync'):
            e = self.xml.find('lastLocal{0}'.format(i))
            if e:
                self.filechecks['local'][i.lower()] = TimestampFile(e)
        for i in ('Sync', 'Update'):
            e = self.xml.find('lastRemote{0}'.format(i))
            if e:
                self.filechecks['remote'][i.lower()] = TimestampFile(e)
        for u in self.xml.findall('upstream'):
            self.upstreams.append(Upstream(u,
                                           self.dest,
                                           rsync_args = self.rsync_args,
                                           owner = self.owner,
                                           filechecks = self.filechecks))

    def check(self):
        for k, v in self.filechecks['local']:
            if v:
                tstmp = v.read()
                self.timestamps[k] = tstmp
        _logger.debug('Updated timestamps: {0}'.format(self.timestamps))

    def sync(self):
        self.check()
        for u in self.upstreams:
            if not u.available:
                continue
            u.fetcher.check(self.filechecks['local'])
            if u.has_new:
                u.sync()
                if self.filechecks['local']['sync']:
                    self.filechecks['local']['sync'].write()
                break
        if self.filechecks['local']['check']:
            self.filechecks['local']['check'].write()
        return(None)


class Sync(object):
    def __init__(self, cfg = None, dummy = False, distro = None, logdir = None, *args, **kwargs):
        try:
            _args = dict(locals())
            del(_args['self'])
            _logger.debug('Sync class instantiated with args: {0}'.format(_args))
            self.dummy = dummy
            if distro:
                self.distro = distro
            else:
                self.distro = []
            self._distro_objs = []
            self.logdir = logdir
            self.xml = config.Config(cfg)
            self._distro_populate()
        except Exception:
            _logger.error('FATAL ERROR. Stacktrace follows.', exc_info = True)

    def _distro_populate(self):
        pass

    def sync(self):
        for d in self._distro_objs:
            d.sync()
