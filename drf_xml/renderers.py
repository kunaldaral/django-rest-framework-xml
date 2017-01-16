"""
Provides XML rendering support.
"""
from __future__ import unicode_literals

from django.utils import six
from django.utils.xmlutils import SimplerXMLGenerator
from django.utils.six.moves import StringIO
from django.utils.encoding import smart_text
from rest_framework.renderers import BaseRenderer
from django.conf import settings


class XMLRenderer(BaseRenderer):
    """
    Renderer which serializes to XML.
    """

    DRF_XML = getattr(settings, 'DRF_XML', {})

    media_type = DRF_XML.get('MEDIA_TYPE', 'application/xml')
    attribute_prefix = DRF_XML.get('ATTRIBUTE_PREFIX', '@')
    allow_attributes = DRF_XML.get('ALLOW_ATTRIBUTES', True)
    is_list_attribute = DRF_XML.get('IS_LIST_ATTRIBUTE', '_is_list')
    if not is_list_attribute:
        is_list_attribute = '_is_list'
    text_prefix = DRF_XML.get('TEXT_PREFIX', '#')
    root_tag_name = DRF_XML.get('ROOT_TAG_NAME', 'root')
    text = DRF_XML.get('TEXT_NAME', 'text')
    LIST_ATTRIBUTE = "%s%s"%(attribute_prefix,is_list_attribute)
    TEXT_ATTRIBUTE = "%s%s"%(text_prefix, text)
    if not text:
        text = 'text'
    format = 'xml'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders `data` into serialized XML.
        """
        if data is None:
            return ''

        stream = StringIO()

        xml = SimplerXMLGenerator(stream, self.charset)
        xml.startDocument()
        xml.startElement(self.root_tag_name, {})

        self._to_xml(xml, data, "item")

        xml.endElement(self.root_tag_name)
        xml.endDocument()
        return stream.getvalue()

    def _to_xml(self, xml, data, tag_name):
        if isinstance(data, (list, tuple)):
            for item in data:
                self._allow_attribute_item_update(xml, item, tag_name)
        elif isinstance(data, dict):
            for key, value in six.iteritems(data):
                if isinstance(value, (list, tuple)):
                    if len(value) == 0:
                        value = [{self.LIST_ATTRIBUTE: ""}]
                    else:
                        value[0][self.LIST_ATTRIBUTE] = ""
                    self._to_xml(xml, value, key)
                else:
                    self._allow_attribute_item_update(xml, value, key)
        elif data is None:
            # Don't output any value
            pass

        else:
            xml.characters(smart_text(data))

    def _allow_attribute_item_update(self, xml, item, tag_name):
        attributes = {}
        _is_text_key_present = False
        print item
        if self.allow_attributes and isinstance(item, (dict)):
            data = dict(item)
            for k, v in item.items():
                if k == self.TEXT_ATTRIBUTE:
                    _is_text_key_present = True
                    data = v
                elif k.startswith(self.attribute_prefix):
                    attributes[k[len(self.attribute_prefix):]] = v
                    item.pop(k)
            if _is_text_key_present:
                item = data
            elif self.attribute_prefix:
                pass
            else:
                item = data
                attributes = {}
        elif not self.allow_attributes:
            if self.LIST_ATTRIBUTE in item:
                attributes[self.is_list_attribute] = ""
                item.pop(self.LIST_ATTRIBUTE)
        xml.startElement(tag_name, attrs=attributes)
        self._to_xml(xml, item, tag_name)
        xml.endElement(tag_name)
