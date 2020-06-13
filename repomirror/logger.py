import logging
import logging.handlers
import os
try:
    # https://www.freedesktop.org/software/systemd/python-systemd/journal.html#journalhandler-class
    from systemd import journal
    _has_journald = True
except ImportError:
    _has_journald = False


def preplog(logfile = None):
    if not logfile:
        if os.geteuid() == 0:
            logfile = '/var/log/repo/main.log'
        else:
            logfile = '~/.cache/repo.log'
    # Prep the log file.
    logfile = os.path.abspath(os.path.expanduser(logfile))
    os.makedirs(os.path.dirname(logfile), exist_ok = True, mode = 0o0700)
    if not os.path.isfile(logfile):
        with open(logfile, 'w') as fh:
            fh.write('')
    os.chmod(logfile, 0o0600)
    return(logfile)


# And set up logging.
_cfg_args = {'handlers': [],
             'level': logging.DEBUG}
if _has_journald:
    # There were some weird changes somewhere along the line.
    try:
        # But it's *probably* this one.
        h = journal.JournalHandler()
    except AttributeError:
        h = journal.JournaldLogHandler()
    # Systemd includes times, so we don't need to.
    h.setFormatter(logging.Formatter(style = '{',
                                     fmt = ('{name}:{levelname}:{name}:{filename}:'
                                            '{funcName}:{lineno}: {message}')))
    _cfg_args['handlers'].append(h)

filehandler = logging.handlers.RotatingFileHandler(preplog(),
                                                   encoding = 'utf8',
                                                   # Disable rotating for now.
                                                   # maxBytes = 50000000000,
                                                   # backupCount = 30
                                                   )
filehandler.setFormatter(logging.Formatter(style = '{',
                                           fmt = ('{asctime}:'
                                                  '{levelname}:{name}:{filename}:'
                                                  '{funcName}:{lineno}: {message}')))
_cfg_args['handlers'].append(filehandler)
logging.basicConfig(**_cfg_args)
logger = logging.getLogger('Repo Mirror')
logger.info('Logging initialized.')
