from . import logger
##
import logging
##
from . import config
from . import constants


_logger = logging.getLogger()


class Sync(object):
    def __init__(self, cfg = None, dummy = False, distro = None, logdir = None, *args, **kwargs):
        _args = dict(locals())
        del(_args['self'])
        _logger.debug('Sync class instantiated with args: {0}'.format(_args))
        self.cfg = config.Config(cfg)

