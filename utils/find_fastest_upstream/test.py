#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

country = 'US'
url = 'https://www.archlinux.org/mirrors/status/tier/1/'

req = requests.get(url)
html = req.content.decode('utf-8')
bs = BeautifulSoup(html, 'lxml')

mirrors = bs.find('table', {'id': 'successful_mirrors'})
header = mirrors.find('thead').find('tr')
headers = [h.text if h.text != '' else 'details' for h in header.find_all('th')]

results = [{headers[i]: cell.text for i, cell in enumerate(row.find_all('td'))} for row in mirrors.find_all('tr')]

import pprint
pprint.pprint(results)
