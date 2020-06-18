import re
from setuptools import setup
from repomirror import constants


_req_re = re.compile(r'(<|=|>)')
with open('README', 'r') as fh:
    long_desc = fh.read().strip()
with open('requirements.txt', 'r') as fh:
    reqs = [_req_re.split(i.strip())[0] for i in fh.read().strip().splitlines()
            if not i.startswith('#')
            and i.strip() != '']


setup(
        author_email = 'bts@square-r00t.net',
        author = 'Brent S.',
        classifiers = [
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
            'Operating System :: POSIX :: BSD',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3 :: Only',
            'Topic :: Internet',
            'Topic :: Software Development :: Build Tools',
            'Topic :: System :: Archiving :: Mirroring',
            'Topic :: System :: Installation/Setup',
            'Topic :: System :: Software Distribution',
            'Topic :: System :: Systems Administration'
            ],
        description = 'Clone/mirror multiple Linux distro/BSD flavor/etc. repositories to a local server',
        long_description = long_desc,
        long_description_content_type = 'text/plain',
        name = 'repomirror',
        packages = ['repomirror', 'repomirror.fetcher', 'repomirror.utils'],
        project_urls = {
            'Documentation': 'https://git.square-r00t.net/RepoMirror/tree/README',
            'Source': 'https://git.square-r00t.net/RepoMirror/',
            'Tracker': 'https://bugs.square-r00t.net/index.php?project=14'
            },
        install_requires = reqs,
        python_requires = '>=3.7',
        scripts = [
            'reposync'
            ],
        url = 'https://git.square-r00t.net/RepoMirror/',
        version = str(constants.VERSION)
        )
