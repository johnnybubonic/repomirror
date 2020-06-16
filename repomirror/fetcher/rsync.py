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
            self.rsync_args = rsync_args
        else:
            self.rsync_args = constants.RSYNC_DEF_ARGS
        _logger.debug('RSync args given: {0}'.format(self.rsync_args))
        if log:
            # Do I want to do this in subprocess + logging module? Or keep this?
            # It looks a little ugly in the log but it makes more sense than doing it via subprocess just to write it
            # back out.
            _log_path = None
            for h in _logger.handlers:
                if isinstance(h, logging.handlers.RotatingFileHandler):
                    _log_path = h.baseFileName
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
        cmd = subprocess.run(cmd_str,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE)
        stdout = cmd.stdout.read().decode('utf-8').strip()
        stderr = cmd.stderr.read().decode('utf-8').strip()
        if stdout != '':
            _logger.debug('STDOUT: {0}'.format(stdout))
        if stderr != '' or cmd.returncode != 0:
            _logger.error('Rsync to {0}:{1} returned exit status {2}'.format(self.domain, self.port, cmd.returncode))
            _logger.debug('STDERR: {0}'.format(stderr))
            warnings.warn('Rsync process returned non-zero')
        return(None)

    def fetch_content(self, remote_filepath):
        tf = tempfile.mkstemp()[1]
        url = os.path.join(self.url.rstrip('/'),remote_filepath.lstrip('/'))
        cmd_str = ['rsync',
                   *self.rsync_args,
                   url,
                   tf]
        cmd = subprocess.run(cmd_str,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE)
        stdout = cmd.stdout.read().decode('utf-8').strip()
        stderr = cmd.stderr.read().decode('utf-8').strip()
        if stdout != '':
            _logger.debug('STDOUT: {0}'.format(stdout))
        if stderr != '' or cmd.returncode != 0:
            _logger.error('Rsync to {0}:{1} returned exit status {2}'.format(self.domain, self.port, cmd.returncode))
            _logger.debug('STDERR: {0}'.format(stderr))
            warnings.warn('Rsync process returned non-zero')
        with open(tf, 'rb') as fh:
            raw_content = fh.read()
        os.remove(tf)
        return(raw_content)

