PROTO_DEF_PORTS = {'ftp': 21,
                   'rsync': 873}

RSYNC_DEF_ARGS = ['--recursive',
                  '--times',
                  '--links',
                  '--hard-links',
                  '--delete-after',
                  '--perms',
                  '--delay-updates',
                  '--safe-links',
                  '--delete-excluded',
                  '--exclude=".*"']

# These are needed to convert years/months to timedeltas.
# The following are averaged definitions for time units *in days* according to Google Calculator.
YEAR = 365.2422
MONTH = 30.4167
# The following are approximations based on ISO 8601 defintions *in days*.
# https://webspace.science.uu.nl/~gent0113/calendar/isocalendar.htm
# YEAR = 365.25
# MONTH = 30.6

# We no longer do this by default.
# # How many days an upstream should have last synced by before it's considered stale.
# DAYS_WARN = 2
VERSION = '1.1.0'
