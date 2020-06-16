import ftplib
import logging
import io
import os
import pathlib
##
from . import _base


_logger = logging.getLogger()


class FTP(_base.BaseFetcher):
    type = 'ftp'

    def __init__(self, domain, port, path, dest, owner = None, *args, **kwargs):
        super().__init__(domain, port, path, dest, owner = owner, *args, **kwargs)
        _logger.debug('Instantiated FTP fetcher')
        self.handler = ftplib.FTP(self.domain)
        _logger.debug('Configured handler for {0}'.format(self.domain))
        self.handler.port = self.port
        _logger.debug('Set port for {0} to {1}'.format(self.domain, self.port))
        self.connected = None

    def _connect(self):
        if not self.connected:
            self.handler.login()
            _logger.debug('Connected to {0}:{1} as Anonymous'.format(self.domain, self.port))
        self.connected = True
        return(None)

    def _disconnect(self):
        if self.connected:
            self.handler.quit()
            _logger.debug('Disconnected from {0}:{1} as Anonymous'.format(self.domain, self.port))
        self.connected = False
        return(None)

    def _pathtuple(self, path):
        relpath = path.lstrip('/')
        relpath_stripped = str(pathlib.Path(relpath).relative_to(self.path))
        destdir = os.path.join(self.dest, os.path.dirname(relpath_stripped))
        destpath = os.path.join(self.dest, relpath_stripped)
        return((relpath, destdir, destpath))

    def _prepdir(self, destdir):
        os.makedirs(destdir, mode = 0o0755, exist_ok = True)
        _logger.debug('Created directory {0} (if it did not exist)'.format(destdir))
        if self.owner:
            os.chown(destdir, **self.owner)
            _logger.debug('Chowned {0} to {uid}:{gid}'.format(destdir, **self.owner))
        return()

    def fetch(self):
        def getter(path, relroot):
            _logger.debug('getter invoked with path={0}, relroot={1}'.format(path, relroot))
            if relroot == path:
                parentdir = path
                _logger.debug('relroot and path are the same')
            else:
                parentdir = relroot
                _logger.debug('relroot and path are not the same')
            _logger.debug('parentdir set to {0}'.format(parentdir))
            _logger.debug('Executing LS on {0}'.format(parentdir))
            for itemspec in self.handler.mlsd(parentdir):
                relpath, spec = itemspec
                if relpath in ('.', '..'):
                    continue
                _logger.debug(('Parsing path ('
                               'relroot: {0}, '
                               'path: {1}, '
                               'relpath: {2}) with spec {3}').format(relroot, path, relpath, itemspec))
                ptype = spec['type']
                newpath = os.path.join(parentdir, relpath)
                itemspec = (newpath, itemspec[1])
                if ptype.startswith('OS.unix=slink'):
                    _logger.debug('Fetching symlink {0}'.format(parentdir))
                    self.fetch_symlink(itemspec)
                elif ptype == 'dir':
                    _logger.debug('Fetching dir {0}'.format(parentdir))
                    self.fetch_dir(itemspec)
                    _logger.debug('Recursing getter with relpath={0}, parentdir={1}'.format(relpath, parentdir))
                    getter(relpath, newpath)
                elif ptype == 'file':
                    _logger.debug('Fetching file {0}'.format(parentdir))
                    self.fetch_file(itemspec)
            return(None)
        self._connect()
        getter(self.path, self.path)
        self._disconnect()
        return(None)

    def fetch_content(self, remote_filepath):
        self._connect()
        buf = io.BytesIO()
        self.handler.retrbinary('RETR {0}'.format(remote_filepath), buf.write)
        self._disconnect()
        buf.seek(0, 0)
        return(buf.read())

    def fetch_dir(self, pathspec):
        self._connect()
        # Relative to FTP root.
        relpath, destdir, destpath = self._pathtuple(pathspec[0])
        mode = int(pathspec[1]['unix.mode'], 8)
        os.makedirs(destpath, mode = mode, exist_ok = True)
        _logger.debug('Created directory {0} with mode {1} (if it did not exist)'.format(destpath, oct(mode)))
        if self.owner:
            os.chown(destpath, **self.owner)
            _logger.debug('Chowned {0} to {uid}:{gid}'.format(destpath, **self.owner))
        return(None)

    def fetch_file(self, pathspec):
        self._connect()
        relpath, destdir, destpath = self._pathtuple(pathspec[0])
        self._prepdir(destdir)
        with open(destpath, 'wb') as fh:
            self.handler.retrbinary('RETR {0}'.format(relpath), fh.write)
        _logger.debug('Created file {0}'.format(destpath))
        mode = int(pathspec[1]['unix.mode'], 8)
        os.chmod(destpath, mode)
        _logger.debug('Chmodded {0} to {1}'.format(destpath, oct(mode)))
        if self.owner:
            os.chown(destpath, **self.owner)
            _logger.debug('Chowned {0} to {uid}:{gid}'.format(destpath, **self.owner))
        return(None)

    def fetch_symlink(self, pathspec):
        relpath, destdir, destpath = self._pathtuple(pathspec[0])
        self._prepdir(destdir)
        # For symlinks, this is something like: OS.unix=slink:path/to/target
        target = pathspec[1]['type'].split(':', 1)[1]
        # We don't care if the target exists.
        os.symlink(target, destpath)
        _logger.debug('Created symlink {0} -> {1}'.format(destpath, target))
        return(None)
