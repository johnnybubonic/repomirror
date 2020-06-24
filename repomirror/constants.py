PROTO_DEF_PORTS = {'ftp': 21,
                   'rsync': 873}
RSYNC_DEF_ARGS = ['--recursive',
                  '--times',
                  '--links',
                  '--hard-links',
                  '--delete-after',
                  '--delay-updates',
                  '--copy-links',
                  '--safe-links',
                  '--delete-excluded',
                  '--exclude=.*']
# How many days an upstream should have last synced by before it's considered stale.
DAYS_WARN = 2
VERSION = '1.0.2'
