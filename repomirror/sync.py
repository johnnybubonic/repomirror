import datetime
import logging
import pwd
import grp
import os
import re
import socket
import sys
import warnings
##
import psutil
##
from . import config
from . import constants
from . import fetcher
from . import logger


_logger = logging.getLogger()


if os.isatty(sys.stdin.fileno()):
    _is_cron = False
else:
    _is_cron = True

_duration_re = re.compile(('^P'
                           '((?P<years>[0-9]+(\.[0-9]+)?)Y)?'
                           '((?P<months>[0-9]+(\.[0-9]+)?)M)?'
                           '((?P<days>[0-9]+(\.[0-9]+)?)D)?'
                           'T?'
                           '((?P<hours>[0-9]+(\.[0-9]+)?)H)?'
                           '((?P<minutes>[0-9]+(\.[0-9]+)?)M)?'
                           '((?P<seconds>[0-9]+(\.[0-9]+)?)S)?'
                           '$'))


def get_owner(owner_xml):
    owner = {}
    user = owner_xml.find('user')
    if user is not None:
        user = user.text
    group = owner_xml.find('group')
    if group is not None:
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
        self.path = os.path.abspath(os.path.expanduser(mpchk_xml.text))
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
        if self.owner_xml is not None:
            self.owner = get_owner(self.owner_xml)
        _logger.debug('Owner set is {0}'.format(self.owner))
        self.path = os.path.abspath(os.path.expanduser(ts_xml.text))
        _logger.debug('Path resolved to {0}'.format(self.path))

    def read(self, parentdir = None):
        timestamp = None
        if parentdir:
            path = os.path.join(os.path.abspath(os.path.expanduser(parentdir)),
                                self.path.lstrip('/'))
        else:
            path = self.path
        if os.path.isfile(path):
            with open(path, 'r') as fh:
                ts_raw = fh.read().strip()
            if '%s' in self.fmt:
                timestamp = datetime.datetime.fromtimestamp(float(ts_raw))
            else:
                timestamp = datetime.datetime.strptime(ts_raw, self.fmt)
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
    def __init__(self, upstream_xml, dest, rsync_args = None, owner = None, filechecks = None, rsync_ignores = None):
        self.xml = upstream_xml
        # These are required for all upstreams.
        self.sync_type = self.xml.find('syncType').text.lower()
        self.domain = self.xml.find('domain').text
        self.path = self.xml.find('path').text
        self.dest = os.path.abspath(os.path.expanduser(dest))
        self.delay = None
        self.owner = owner
        self.filechecks = filechecks
        self._get_delaychk()
        self.has_new = False
        # These are optional.
        port = self.xml.find('port')
        if port is not None:
            self.port = int(port.text)
        else:
            self.port = constants.PROTO_DEF_PORTS[self.sync_type]
        self.available = None
        if self.sync_type == 'rsync':
            self.fetcher = fetcher.RSync(self.domain,
                                         self.port,
                                         self.path,
                                         self.dest,
                                         rsync_args = rsync_args,
                                         rsync_ignores = rsync_ignores,
                                         filechecks = self.filechecks,
                                         owner = self.owner)
        else:
            self.fetcher = fetcher.FTP(self.domain, self.port, self.path, self.dest, owner = self.owner)
        self._check_conn()

    def _get_delaychk(self):
        delay = self.xml.attrib.get('delayCheck')
        if not delay:
            return(None)
        r = _duration_re.search(delay)
        times = {k: (float(v) if v else 0.0) for k, v in r.groupdict().items()}
        years = float(times.pop('years'))
        months = float(times.pop('months'))
        times['days'] = (times['days'] + (years * constants.YEAR) + (months * constants.MONTH))
        self.delay = datetime.timedelta(**times)
        return(None)

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
        self.name = self.xml.attrib['name']
        self.dest = os.path.abspath(os.path.expanduser(self.xml.find('dest').text))
        self.mount = Mount(self.xml.find('mountCheck'))
        self.filechecks = {'local': {'check': None,
                                     'sync': None},
                           'remote': {'update': None,
                                      'sync': None}}
        self.timestamps = {}
        self.rsync_args = None
        self.rsync_ignores = None
        self.owner = None
        self.upstreams = []
        self.lockfile = '/var/run/repomirror/{0}.lck'.format(self.name)
        # These are optional.
        self.owner_xml = self.xml.find('owner')
        if self.owner_xml is not None:
            self.owner = get_owner(self.owner_xml)
        self.rsync_xml = self.xml.find('rsyncArgs')
        if self.rsync_xml is not None:
            self.rsync_args = Args(self.rsync_xml)
        for i in ('Check', 'Sync'):
            e = self.xml.find('lastLocal{0}'.format(i))
            if e is not None:
                self.filechecks['local'][i.lower()] = TimestampFile(e)
        for i in ('Sync', 'Update'):
            e = self.xml.find('lastRemote{0}'.format(i))
            if e is not None:
                self.filechecks['remote'][i.lower()] = TimestampFile(e)
        self.rsync_ignores = []
        rsyncig_xml = self.xml.find('rsyncIgnore')
        if rsyncig_xml is not None:
            self.rsync_ignores = [int(i.strip()) for i in rsyncig_xml.attrib['returns'].split()]
        for u in self.xml.findall('upstream'):
            self.upstreams.append(Upstream(u,
                                           self.dest,
                                           rsync_args = self.rsync_args,
                                           owner = self.owner,
                                           filechecks = self.filechecks,
                                           rsync_ignores = self.rsync_ignores))

    def check(self):
        for k, v in self.filechecks['local'].items():
            if v:
                tstmp = v.read()
                self.timestamps[k] = tstmp
        _logger.debug('Updated local timestamps: {0}'.format(self.timestamps))
        local_checks = sorted([i for i in self.timestamps.values() if i])
        if local_checks:
            _logger.info('Local timestamps: {0}'.format(', '.join([str(t) for t in local_checks])))
        for u in self.upstreams:
            if not u.available:
                continue
            u.fetcher.check()
            remote_checks = sorted([i for i in u.fetcher.timestamps.values() if i])
            if remote_checks:
                _logger.info('Remote timestamps for {0}: {1}'.format(u.domain, ', '.join([str(t)
                                                                                           for t in remote_checks])))
            if not any((local_checks, remote_checks)) or not remote_checks:
                _logger.info('There are no reliable timestamp comparisons; syncing.')
                u.has_new = True
            else:
                update = u.fetcher.timestamps.get('update')
                sync = u.fetcher.timestamps.get('sync')
                if update:
                    if local_checks and (local_checks[-1] < update):
                        _logger.info('Newest local timestamp is older than the remote update; syncing.')
                        u.has_new = True
                    elif not local_checks:
                        _logger.info('No local timestamps; syncing.')
                        u.has_new = True
                    else:
                        _logger.info('Local checks are newer than upstream.')
                else:
                    _logger.info('No remote update timestamp; syncing.')
                    u.has_new = True
                if sync and u.delay:
                    td = datetime.datetime.utcnow() - sync
                    if td.days > u.delay:
                        _logger.warning(('Upstream {0} has not synced for {1} or longer; this '
                                         'repository may be out of date.').format(u.fetcher.url, u.delay))
                        warnings.warn('Upstream may be out of date')
        return(None)

    def sync(self):
        self.check()
        my_pid = os.getpid()
        if os.path.isfile(self.lockfile):
            with open(self.lockfile, 'r') as fh:
                pid = int(fh.read().strip())
            if my_pid == pid:  # This logically should not happen, but something might have gone stupid.
                _logger.warning('Someone call the Ghostbusters because this machine is haunted.')
                return(False)
            else:
                warnmsg = 'The sync process for {0} is locked with file {1} and PID {2}'.format(self.name,
                                                                                                self.lockfile,
                                                                                                pid)
                try:
                    proc = psutil.Process(pid)
                    warnmsg += '.'
                except (psutil.NoSuchProcess, FileNotFoundError, AttributeError):
                    proc = None
                    warnmsg += ' but that PID no longer exists.'
                _logger.warning(warnmsg)
                if proc:
                    _logger.warning('PID information: {0}'.format(vars(proc)))
                # This is *really* annoying if you're running from cron and get emailed output.
                # So we suppress it if in cron.
                if not _is_cron:
                    warnings.warn(warnmsg)
                    if proc:
                        proc_info = {k.lstrip('_'):v for k, v in vars(proc) if k not in ('_lock', '_proc')}
                        import pprint
                        print('Process information:')
                        pprint.pprint(proc_info)
                return(False)
        if not self.mount.is_mounted:
            _logger.error(('The mountpoint {0} for distro {1} is not mounted; '
                           'refusing to sync').format(self.mount.path, self.name))
            return(False)
        os.makedirs(os.path.dirname(self.lockfile), mode = 0o0755, exist_ok = True)
        with open(self.lockfile, 'w') as fh:
            fh.write('{0}\n'.format(str(my_pid)))
        for u in self.upstreams:
            if not u.available:
                _logger.debug('Upstream {0} is not available; skipping.'.format(u.domain))
                continue
            if u.has_new:
                _logger.info('Initiating syncing upstream {0}.'.format(u.domain))
                u.sync()
                _logger.debug('Sync for upstream {0} complete.'.format(u.domain))
                if self.filechecks['local']['sync']:
                    self.filechecks['local']['sync'].write()
                break
            else:
                _logger.debug('Upstream {0} is not new; not syncing.'.format(u.domain))
        if self.filechecks['local']['check']:
            self.filechecks['local']['check'].write()
        os.remove(self.lockfile)
        return(True)


class Sync(object):
    def __init__(self, cfg = None, dummy = False, distro = None, logdir = None, *args, **kwargs):
        if logdir:
            self.logdir = logdir
        else:
            self.logdir = os.path.dirname(logger.filehandler.baseFilename)
        self._orig_log_old = logger.filehandler.baseFilename
        self._orig_log = logger.preplog(os.path.join(self.logdir, '_main.log'))
        logger.filehandler.close()
        logger.filehandler.baseFilename = self._orig_log
        try:
            _args = dict(locals())
            del(_args['self'])
            _logger.debug('Sync class instantiated with args: {0}'.format(_args))
            self.dummy = dummy
            if distro:
                self.distro = distro
            else:
                self.distro = []
            self.cfg = config.Config(cfg)
        except Exception as e:
            _logger.error('FATAL ERROR. Stacktrace follows.', exc_info = True)
            raise e

    def sync(self):
        if self.distro:
            for d in self.distro:
                e = self.cfg.xml.xpath('//distro[@name="{0}"]'.format(d))
                if e is None:
                    _logger.error('Could not find specified distro {0}; skipping'.format(d))
                    continue
                e = e[0]
                logger.filehandler.close()
                logger.filehandler.baseFilename = os.path.join(self.logdir, '{0}.log'.format(e.attrib['name']))
                distro = Distro(e)
                distro.sync()
        else:
            for e in self.cfg.xml.findall('distro'):
                logger.filehandler.close()
                logger.filehandler.baseFilename = os.path.join(self.logdir, '{0}.log'.format(e.attrib['name']))
                distro = Distro(e)
                distro.sync()
        logger.filehandler.close()
        logger.filehandler.baseFilename = self._orig_log
        return(None)
