import logging
import os
import subprocess
import sys
import tempfile
import warnings
##
_cur_dir = os.path.dirname(os.path.abspath(os.path.expanduser(__file__)))
sys.path.append(os.path.abspath(os.path.join(_cur_dir, '..')))
import constants
# import logger
from . import _base
from . import rsync_returns


_logger = logging.getLogger()


class RSync(_base.BaseFetcher):
    type = 'rsync'

    def __init__(self,
                 domain,
                 port,
                 path,
                 dest,
                 rsync_args = None,
                 owner = None,
                 log = True,
                 filechecks = None,
                 *args,
                 **kwargs):
        super().__init__(domain, port, path, dest, owner = owner, filechecks = filechecks, *args, **kwargs)
        _logger.debug('Instantiated RSync fetcher')
        if rsync_args:
            self.rsync_args = rsync_args.args[:]
        else:
            self.rsync_args = constants.RSYNC_DEF_ARGS[:]
        _logger.debug('RSync args given: {0}'.format(self.rsync_args))
        if log:
            # Do I want to do this in subprocess + logging module? Or keep this?
            # It looks a little ugly in the log but it makes more sense than doing it via subprocess just to write it
            # back out.
            _log_path = None
            for h in _logger.handlers:
                if isinstance(h, logging.handlers.RotatingFileHandler):
                    _log_path = h.baseFilename
                    break
            self.rsync_args.extend(['--verbose',
                                    '--log-file-format="[RSYNC {0}:{1}]:%l:%f%L"'.format(self.domain, self.port),
                                    '--log-file={0}'.format(_log_path)])

    def fetch(self):
        path = self.url.rstrip('/')
        if not path.endswith('/.'):
            path += '/.'
        dest = self.dest
        if not dest.endswith('/.'):
            dest += '/.'
        # Yes, I know it's named "cmd_*str*". Yes, I know it's a *list*.
        cmd_str = ['rsync',
                   *self.rsync_args,
                   path,
                   dest]
        _logger.debug('Running command: {0}'.format(' '.join(cmd_str)))
        cmd = subprocess.run(cmd_str,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE)
        stdout = cmd.stdout.decode('utf-8').strip()
        stderr = cmd.stderr.decode('utf-8').strip()
        if stdout != '':
            _logger.debug('STDOUT: {0}'.format(stdout))
        if stderr != '' or cmd.returncode != 0:
            rtrn = cmd.returncode
            err = rsync_returns.returns[rtrn]
            errmsg = 'Rsync to {0}:{1} returned'.format(self.domain, self.port)
            debugmsg = 'Rsync command {0} returned'.format(' '.join(cmd_str))
            if stderr != '':
                errmsg += ' an error message: {0}'.format(stderr)
                debugmsg += ' an error message: {0}'.format(stderr)
            if rtrn != 0:
                errmsg += ' with exit status {0} ({1})'.format(rtrn, err)
                debugmsg += ' with exit status {0} ({1})'.format(rtrn, err)
            errmsg += '.'
            _logger.error(errmsg)
            _logger.debug(debugmsg)
            warnings.warn(errmsg)
        return(None)

    def fetch_content(self, remote_filepath):
        tf = tempfile.mkstemp()[1]
        url = os.path.join(self.url.rstrip('/'),remote_filepath.lstrip('/'))
        cmd_str = ['rsync',
                   *self.rsync_args,
                   url,
                   tf]
        _logger.debug('Running command: {0}'.format(' '.join(cmd_str)))
        cmd = subprocess.run(cmd_str,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE)
        stdout = cmd.stdout.decode('utf-8').strip()
        stderr = cmd.stderr.decode('utf-8').strip()
        if stdout != '':
            _logger.debug('STDOUT: {0}'.format(stdout))
        if stderr != '' or cmd.returncode != 0:
            rtrn = cmd.returncode
            err = rsync_returns.returns[rtrn]
            errmsg = 'Rsync to {0}:{1} returned'.format(self.domain, self.port)
            debugmsg = 'Rsync command {0} returned'.format(' '.join(cmd_str))
            if stderr != '':
                errmsg += ' an error message: {0}'.format(stderr)
                debugmsg += ' an error message: {0}'.format(stderr)
            if rtrn != 0:
                errmsg += ' with exit status {0} ({1})'.format(rtrn, err)
                debugmsg += ' with exit status {0} ({1})'.format(rtrn, err)
            errmsg += '.'
            _logger.error(errmsg)
            _logger.debug(debugmsg)
            warnings.warn(errmsg)
        with open(tf, 'rb') as fh:
            raw_content = fh.read()
        os.remove(tf)
        return(raw_content)

