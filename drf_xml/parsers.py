"""
Provides XML parsing support.
"""
from __future__ import unicode_literals
import datetime
import decimal
import json

from django.conf import settings
from django.utils import six
from pip._vendor.html5lib.filters.sanitizer import allowed_attributes
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser

from .compat import etree


class XMLParser(BaseParser):
    """
    XML parser.
    """

    DRF_XML = getattr(settings, 'DRF_XML', {})

    media_type = DRF_XML.get('MEDIA_TYPE', 'application/xml')
    attribute_prefix = DRF_XML.get('ATTRIBUTE_PREFIX', '@')
    is_list_attribute = DRF_XML.get('IS_LIST_ATTRIBUTE', '_is_list')
    if not is_list_attribute:
        is_list_attribute = '_is_list'
    allow_attributes = DRF_XML.get('ALLOW_ATTRIBUTES', False)
    semi_allow_attributes = DRF_XML.get('SEMI_ALLOW_ATTRIBUTES', False)
    text_prefix = DRF_XML.get('TEXT_PREFIX', '#')
    text = DRF_XML.get('TEXT_NAME', 'text')
    if not text:
        text = 'text'
    TEXT_ATTRIBUTE = "%s%s" % (text_prefix, text)

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as XML and returns the resulting data.
        """
        assert etree, 'XMLParser requires defusedxml to be installed'
        json_data = {}

        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        parser = etree.DefusedXMLParser(encoding=encoding)
        try:
            tree = etree.parse(stream, parser=parser, forbid_dtd=True)
        except (etree.ParseError, ValueError) as exc:
            raise ParseError('XML parse error - %s' % six.text_type(exc))

        json_data[tree.getroot().tag], is_list = self.get_attrib_and_text_dict(tree.getroot())

        return json_data

    def _xml_convert(self, element, data):
        """
        convert the xml `element` into the corresponding python object
        """
        children = list(element)

        if len(children) == 0:
            if self.allow_attributes:
                return {self.TEXT_ATTRIBUTE : self._type_convert(element.text)}
            else:
                return self._type_convert(element.text)
        else:
            for child in children:
                child_dict, is_list = self.get_attrib_and_text_dict(child)

                """
                Make list if `_is_list` attribute is present
                or `.LIST` is present at the end of the tag name
                """
                if (is_list or str(child.tag).upper().endswith('.LIST')) \
                        and child.tag not in data:
                    data[child.tag] = []
                if child.tag in data:
                    if type(data[child.tag]) is list:
                        data[child.tag].append(child_dict)
                    else:
                        jdict = data[child.tag]
                        data[child.tag] = [jdict, child_dict, ]
                else:
                    data[child.tag] = child_dict

            return data

    def _type_convert(self, value):
        """
        Convert XML value into corresponding python type
        """
        if value is None:
            return value

        try:
            return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            pass

        return value

    def get_attrib_and_text_dict(self, element):
        if self.allow_attributes:
            element_attr, is_list = self.get_attrib_dict(self.attribute_prefix, element)
            element_text = self._xml_convert(element, {})
            return self.merge_two_dicts(element_attr, element_text), is_list
        elif self.semi_allow_attributes and not len(list(element)) == 0:
            element_attr, is_list = self.get_attrib_dict("", element)
            element_text = self._xml_convert(element, {})
            return self.merge_two_dicts(element_attr, element_text), is_list
        else:
            return self._xml_convert(element, {}), False

    def get_attrib_dict(self, prefix, element):
        '''Addiing attribute_prefix to attribute values'''
        attr = {}
        is_list = False
        for k, v in element.attrib.iteritems():
            if k == is_list_attribute:
                is_list = True
            else:
                attr[prefix + k] = v
        return attr, is_list

    def merge_two_dicts(self, x, y):
        '''Given two dicts, merge them into a new dict as a shallow copy.'''
        z = x.copy()
        z.update(y)
        return z
