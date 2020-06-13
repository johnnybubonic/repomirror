import copy
import datetime
import os
import logging
import re
import shutil
##
import requests
import requests.auth
from lxml import etree


_logger = logging.getLogger()


def create_default_cfg():
    # Create a stripped sample config.
    ws_re = re.compile(r'^\s*$')
    cur_dir = os.path.dirname(os.path.abspath(os.path.expanduser(__file__)))
    samplexml = os.path.abspath(os.path.join(cur_dir, '..', 'example.config.xml'))
    with open(samplexml, 'rb') as fh:
        xml = etree.fromstring(fh.read())
    # Create a stripped sample config.
    # First we strip comments (and fix the ensuing whitespace).
    # etree has a .canonicalize(), but it chokes on a default namespace.
    # https://bugs.launchpad.net/lxml/+bug/1869455
    # So everything we do is kind of a hack.
    # for c in xml.xpath("//comment()"):
    #    parent = c.getparent()
    #    parent.remove(c)
    xmlstr = etree.tostring(xml, with_comments = False, method = 'c14n', pretty_print = True).decode('utf-8')
    newstr = []
    for line in xmlstr.splitlines():
        r = ws_re.search(line)
        if not r:
            newstr.append(line.strip())
    xml = etree.fromstring(''.join(newstr).encode('utf-8'))
    # Remove text and attr text.
    xpathq = "descendant-or-self::*[namespace-uri()!='']"
    for e in xml.xpath(xpathq):
        if e.tag == '{{{0}}}mirror'.format(xml.nsmap[None]):
            continue
        if e.text is not None and e.text.strip() != '':
            e.text = ''
        for k, v in e.attrib.items():
            if v is not None:
                e.attrib[k] = ''
    # Remove multiple children of same type to simplify.
    for e in xml.xpath(xpathq):
        if e.tag == '{{{0}}}mirror'.format(xml.nsmap[None]):
            continue
        parent = e.getparent()
        try:
            for idx, child in enumerate(parent.findall(e.tag)):
                if idx == 0:
                    continue
                parent.remove(child)
        except AttributeError:
            pass
    # And add a comment pointing them to the fully commented config.
    xml.insert(0, etree.Comment(('\n  Please reference the fully commented example.config.xml found either '
                                 'at:\n  '
                                 '  * {0}\n    * https://git.square-r00t.net/RepoMirror/tree/'
                                 'example.config.xml\n  and then configure this according to those '
                                 'instructions.\n  ').format(samplexml)))
    return(etree.tostring(xml,
                          pretty_print = True,
                          with_comments = True,
                          with_tail = True,
                          encoding = 'UTF-8',
                          xml_declaration = True))


class Config(object):
    default_xsd = 'http://schema.xml.r00t2.io/projects/repomirror.xsd'
    default_xml_path = '~/.config/repomirror.xml'

    def __init__(self, xml_path, *args, **kwargs):
        if not xml_path:
            xml_path = self.default_xml_path
        self.xml_path = os.path.abspath(os.path.expanduser(xml_path))
        if not os.path.isfile(self.xml_path):
            with open(self.xml_path, 'wb') as fh:
                fh.write(create_default_cfg())
            _logger.error(('{0} does not exist so a sample configuration file has been created in its place. '
                           'Be sure to configure it appropriately.').format(self.default_xml_path))
            raise ValueError('Config does not exist')
        else:
            with open(xml_path, 'rb') as fh:
                self.raw = fh.read()
        self.xml = None
        self.xsd = None
        self.ns_xml = None
        self.tree = None
        self.ns_tree = None
        self.defaults_parser = None
        self.parse_xml()
        _logger.info('Instantiated {0}.'.format(type(self).__name__))

    def get_xsd(self):
        raw_xsd = None
        base_url = None
        xsi = self.xml.nsmap.get('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        schemaLocation = '{{{0}}}schemaLocation'.format(xsi)
        schemaURL = self.xml.attrib.get(schemaLocation, self.default_xsd)
        split_url = schemaURL.split()
        if len(split_url) == 2:  # a properly defined schemaLocation
            schemaURL = split_url[1]
        else:
            schemaURL = split_url[0]  # a LAZY schemaLocation
        if schemaURL.startswith('file://'):
            schemaURL = re.sub(r'^file://', r'', schemaURL)
            with open(schemaURL, 'rb') as fh:
                raw_xsd = fh.read()
            base_url = os.path.dirname(schemaURL) + '/'
        else:
            req = requests.get(schemaURL)
            if not req.ok:
                raise RuntimeError('Could not download XSD')
            raw_xsd = req.content
            base_url = os.path.split(req.url)[0] + '/'  # This makes me feel dirty.
        self.xsd = etree.XMLSchema(etree.XML(raw_xsd, base_url = base_url))
        return(None)

    def parse_xml(self):
        self.parse_raw()
        self.get_xsd()
        self.populate_defaults()
        self.validate()
        return(None)

    def parse_raw(self, parser = None):
        self.xml = etree.fromstring(self.raw, parser = parser)
        self.ns_xml = etree.fromstring(self.raw, parser = parser)
        self.tree = self.xml.getroottree()
        self.ns_tree = self.ns_xml.getroottree()
        self.tree.xinclude()
        self.ns_tree.xinclude()
        self.strip_ns()
        return(None)

    def populate_defaults(self):
        if not self.xsd:
            self.get_xsd()
        if not self.defaults_parser:
            self.defaults_parser = etree.XMLParser(schema = self.xsd, attribute_defaults = True)
        self.parse_raw(parser = self.defaults_parser)
        return(None)

    def remove_defaults(self):
        self.parse_raw()
        return(None)

    def strip_ns(self, obj = None):
        # https://stackoverflow.com/questions/30232031/how-can-i-strip-namespaces-out-of-an-lxml-tree/30233635#30233635
        xpathq = "descendant-or-self::*[namespace-uri()!='']"
        if not obj:
            for x in (self.tree, self.xml):
                for e in x.xpath(xpathq):
                    e.tag = etree.QName(e).localname
        elif isinstance(obj, (etree._Element, etree._ElementTree)):
            obj = copy.deepcopy(obj)
            for e in obj.xpath(xpathq):
                e.tag = etree.QName(e).localname
            return(obj)
        else:
            raise ValueError('Did not know how to parse obj parameter')
        return(None)

    def validate(self):
        if not self.xsd:
            self.get_xsd()
        self.xsd.assertValid(self.ns_tree)
        return(None)
