import socket
import time
from urllib import parse as urlparse
##
import requests
from bs4 import BeautifulSoup
from lxml import etree
##
import constants


class Ranker(object):
    mirrorlist_url = None  # This is replaced by subclasses
    distro_name = None

    def __init__(self, parser = 'lxml', *args, **kwargs):
        self.my_info = {}
        self.raw_html = None
        self.parser = parser
        self.bs = None
        self.req = None
        self.get_myinfo()
        # The native collection of mirror information.
        self.raw_mirrors = []
        # The list of URLs only of the above.
        self.mirror_candidates = []
        self.ranked_mirrors = {}
        self.ranked_urls = {}

    def extract_mirrors(self):
        # A dummy func. This should be overridden by subclasses.
        pass
        return(None)

    def get_myinfo(self):
        req = requests.get(constants.MYINFO_URL)
        if not req.ok:
            raise RuntimeError('Could not contact information gatherer')
        self.my_info = req.json()
        return(None)

    def get_mirrors(self):
        req = requests.get(self.mirrorlist_url)
        if not req.ok:
            raise RuntimeError('Could not contact information gatherer')
        self.req = req
        self.raw_html = self.req.content.decode('utf-8')
        self.bs = BeautifulSoup(self.raw_html, self.parser)
        return(None)

    def speedcheck(self):
        if not self.mirror_candidates:
            self.extract_mirrors()
        for url in self.mirror_candidates:
            u = urlparse.urlparse(url)
            sock = socket.socket()
            sock.settimeout(7)
            port = u.port
            if not port:
                port = constants.DEF_PORTS[u.scheme.lower()]
            try:
                start = time.perf_counter()
                sock.connect((u.hostname, port))
                conntime = time.perf_counter() - start  # in seconds
                sock.close()
                del(sock)
            except (socket.timeout, socket.error):
                continue
            # Skip the mirror if it has an exact time in the mirrors already.
            # Sure, it's *very* unlikely, but best practice to do this.
            if conntime in self.ranked_mirrors:
                continue
            mirror = {}
            for a in ('path', 'port'):
                mirror[a] = getattr(u, a, None)
            mirror['domain'] = u.hostname.lower()
            mirror['syncType'] = u.scheme.lower()
            if not mirror['port']:
                mirror['port'] = constants.DEF_PORTS[mirror['syncType']]
            if mirror['path'] == '':
                mirror['path'] = '/'
            self.ranked_mirrors[conntime] = mirror
            self.ranked_urls[conntime] = url
        return(None)

    def print(self):
        if not self.ranked_mirrors:
            self.speedcheck()
        print('Mirrors in order of speed:\n')
        for m in sorted(list(self.ranked_urls.keys())):
            print('{0}  # ({1} seconds to connect)'.format(self.ranked_urls[m], m))
        return(None)

    def gen_xml(self):
        if not self.distro_name:
            raise ValueError('This class must be subclassed to be useful')
        if not self.ranked_mirrors:
            self.speedcheck()
        s = ('<?xml version="1.0" encoding="UTF-8" ?>'
             '<mirror xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                     'xmlns="https://git.square-r00t.net/RepoMirror/" '
                     'xsi:schemaLocation="https://git.square-r00t.net/RepoMirror/ '
                                         'http://schema.xml.r00t2.io/projects/repomirror.xsd">'
             '</mirror>')
        xml = etree.fromstring(s.encode('utf-8'))
        distro = etree.Element('distro')
        distro.attrib['name'] = self.distro_name
        for m in sorted(list(self.ranked_mirrors.keys())):
            mirror = self.ranked_mirrors[m]
            distro.append(etree.Comment(' ({0} seconds to connect) '.format(m)))
            u = etree.SubElement(distro, 'upstream')
            for k, v in mirror.items():
                e = etree.SubElement(u, k)
                e.text = str(v)
        xml.append(distro)
        return(etree.tostring(xml,
                              pretty_print = True,
                              with_comments = True,
                              with_tail = True,
                              encoding = 'UTF-8',
                              xml_declaration = True).decode('utf-8'))
