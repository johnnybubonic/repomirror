import socket
import time
##
import requests
from bs4 import BeautifulSoup
##
import constants


class Ranker(object):
    mirrorlist_url = None  # This is replaced by subclasses

    def __init__(self, parser = 'lxml', *args, **kwargs):
        self.my_info = {}
        self.raw_html = None
        self.parser = parser
        self.bs = None
        self.get_myinfo()
        self.raw_mirrors = []

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
        self.raw_html = req.content.decode('utf-8')
        self.bs = BeautifulSoup(self.raw_html, self.parser)
        return(None)
