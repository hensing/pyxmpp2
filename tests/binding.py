#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import time
import re

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.streambase import StreamBase, XMPPEventHandler
from pyxmpp2.streamevents import *
from pyxmpp2.exceptions import StreamParseError
from pyxmpp2.jid import JID
from pyxmpp2.binding import ResourceBindingHandler

from test_util import NetworkTestCase

C2S_SERVER_STREAM_HEAD = '<stream:stream version="1.0" from="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'
C2S_CLIENT_STREAM_HEAD = '<stream:stream version="1.0" to="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'

BIND_FEATURES = """<stream:features>
     <bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'/>
</stream:features>"""

BIND_GENERATED_REQUEST = """<iq type="set" id="42">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
  </bind>
</iq>
"""

BIND_GENERATED_RESPONSE = """<iq type="result" id="{0}">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
    <jid>test@127.0.0.1/Generated</jid>
  </bind>
</iq>
"""

BIND_PROVIDED_REQUEST = """<iq type="set" id="42">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
    <resource>Provided</resource>
  </bind>
</iq>
"""

BIND_PROVIDED_RESPONSE = """<iq type="result" id="{0}">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
    <jid>test@127.0.0.1/Provided</jid>
  </bind>
</iq>
"""


STREAM_TAIL = '</stream:stream>'
        
PARSE_ERROR_RESPONSE = ('<stream:error><xml-not-well-formed'
                    '  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        '</stream:error></stream:stream>')

TIMEOUT = 1.0 # seconds

class AuthorizedEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        if isinstance(event, AuthorizedEvent):
            event.stream.close()
            return True
        return False

class IgnoreEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        return False

class TestBindingInitiator(NetworkTestCase):
    def loop(self, stream, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while stream.socket and time.time() < timeout:
            stream.loop_iter(0.1)
            if expect:
                match = expect.match(self.server.rdata)
                if match:
                    return match.group(1)

    def test_bind_no_resource(self):
        addr, port = self.start_server()
        handler = AuthorizedEventHandler()
        stream = StreamBase(u"jabber:client", [ResourceBindingHandler(), handler])
        stream.me = JID("test@127.0.0.1")
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        stream.loop_iter(1)
        self.server.write(BIND_FEATURES)
        req_id = self.loop(stream, timeout = 1, 
                    expect = re.compile(r".*<iq[^>]*id=[\"']([^\"']*)[\"']"))
        self.assertIsNotNone(req_id)
        self.server.write(BIND_GENERATED_RESPONSE.format(req_id))
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    BindingResourceEvent, AuthorizedEvent, DisconnectedEvent])
 
    def test_bind(self):
        addr, port = self.start_server()
        handler = AuthorizedEventHandler()
        stream = StreamBase(u"jabber:client", [ResourceBindingHandler(), handler])
        stream.me = JID("test@127.0.0.1/Provided")
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        stream.loop_iter(1)
        self.server.write(BIND_FEATURES)
        req_id = self.loop(stream, timeout = 1, 
                    expect = re.compile(r".*<iq[^>]*id=[\"']([^\"']*)[\"'].*<resource>Provided</resource>"))
        self.assertIsNotNone(req_id)
        self.server.write(BIND_PROVIDED_RESPONSE.format(req_id))
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    BindingResourceEvent, AuthorizedEvent, DisconnectedEvent])
   
class TestBindingReceiver(NetworkTestCase):
    def loop(self, stream, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while stream.socket and time.time() < timeout:
            stream.loop_iter(0.1)
            if expect:
                match = expect.match(self.client.rdata)
                if match:
                    return match.group(1)

    def test_bind_no_resource(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = IgnoreEventHandler()
        stream = StreamBase(u"jabber:client", [ResourceBindingHandler(), handler])
        stream.accept(sock, sock.getsockname()[0])
        stream.set_peer_authenticated(JID("test@127.0.0.1"))
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        features = self.loop(stream, timeout = 10, 
                expect = re.compile(r".*<stream:features>(.*<bind.*urn:ietf:params:xml:ns:xmpp-bind.*)</stream:features>"))
        self.assertIsNotNone(features)
        self.client.write(BIND_GENERATED_REQUEST)
        resource = self.loop(stream, timeout = 10, 
                expect = re.compile(r".*<iq.*id=(?:\"42\"|'42').*><bind.*<jid>test@127.0.0.1/(.*)</jid>.*</bind>"))
        self.assertTrue(resource)
        self.client.write(STREAM_TAIL)
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectionAcceptedEvent,
                                AuthenticatedEvent, StreamConnectedEvent,
                                    AuthorizedEvent, DisconnectedEvent])
 
    def test_bind_resource(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = IgnoreEventHandler()
        stream = StreamBase(u"jabber:client", [ResourceBindingHandler(), handler])
        stream.accept(sock, sock.getsockname()[0])
        stream.set_peer_authenticated(JID("test@127.0.0.1"))
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        features = self.loop(stream, timeout = 10, 
                expect = re.compile(r".*<stream:features>(.*<bind.*urn:ietf:params:xml:ns:xmpp-bind.*)</stream:features>"))
        self.assertIsNotNone(features)
        self.client.write(BIND_PROVIDED_REQUEST)
        resource = self.loop(stream, timeout = 10, 
                expect = re.compile(r".*<iq.*id=(?:\"42\"|'42').*><bind.*<jid>test@127.0.0.1/(.*)</jid>.*</bind>"))
        self.assertEqual(resource, u"Provided")
        self.client.write(STREAM_TAIL)
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectionAcceptedEvent, 
                                AuthenticatedEvent, StreamConnectedEvent,
                                AuthorizedEvent, DisconnectedEvent])
 
def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestBindingInitiator))
     suite.addTest(unittest.makeSuite(TestBindingReceiver))
     return suite

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4