#
# (C) Copyright 2003 Jacek Konieczny <jajcus@bnet.pl>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

"""Message XMPP stanza handling"""

__revision__="$Id: message.py,v 1.21 2004/09/19 16:06:28 jajcus Exp $"
__docformat__="restructuredtext en"

import libxml2
from pyxmpp.stanza import Stanza,StanzaError
from pyxmpp.utils import to_utf8,from_utf8

message_types=("normal","chat","headline","error","groupchat")

class Message(Stanza):
    """Wraper object for <message /> stanzas."""
    stanza_type="message"
    def __init__(self,node=None,from_jid=None,to_jid=None,stanza_type=None,stanza_id=None,
            subject=None, body=None, thread=None,error=None,error_cond=None):
        """Initialize a `Message` object.

        :Parameters:
            - `node`: XML node to_jid be wrapped into the `Message` object
              or other Message object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: "get", "set", "result" or "error".
            - `stanza_id`: stanza id -- value of stanza's "id" attribute. If not
              given, then unique for the session value is generated.
            - `subject`: message subject,
            - `body`: message body.
            - `thread`: message thread id.
            - `error_cond`: error condition name. Ignored if `stanza_type` is not "error".
        :Types:
            - `node`: `unicode` or `libxml2.xmlNode` or `Stanza`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `subject`: `unicode`
            - `body`: `unicode`
            - `thread`: `unicode`
            - `error_cond`: `unicode`"""

        self.node=None
        if isinstance(node,Message):
            pass
        elif isinstance(node,Stanza):
            raise TypeError,"Couldn't make Message from other Stanza"
        elif isinstance(node,libxml2.xmlNode):
            pass
        elif node is not None:
            raise TypeError,"Couldn't make Message from %r" % (type(node),)

        if stanza_type=="normal":
            stanza_type=None

        if node is None:
            node="message"

        Stanza.__init__(self,node,from_jid=from_jid,to_jid=to_jid,stanza_type=stanza_type,stanza_id=stanza_id,
                error=error, error_cond=error_cond)
        
        if subject is not None:
            self.node.newTextChild(None,"subject",to_utf8(subject))
        if body is not None:
            self.node.newTextChild(None,"body",to_utf8(body))
        if thread is not None:
            self.node.newTextChild(None,"thread",to_utf8(thread))

    def get_subject(self):
        """Get the message subject.
        
        :return: the message subject or `None` if there is no subject.
        :returntype: `unicode`"""
        n=self.xpath_eval("subject")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def get_thread(self):
        """Get the thread-id subject.
        
        :return: the thread-id or `None` if there is no thread-id.
        :returntype: `unicode`"""
        n=self.xpath_eval("thread")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def copy(self):
        """Create a deep copy of the message stanza.
        
        :returntype: `Message`"""
        return Message(self)

    def get_body(self):
        """Get the body of the message.
        
        :return: the body of the message or `None` if there is no body.
        :returntype: `unicode`"""
        n=self.xpath_eval("body")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def make_error_response(self,cond):
        """Create error response for any non-error message stanza.

        :Parameters:
            - `cond`: error condition name, as defined in XMPP specification.

        :return: new message stanza with the same "id" as self, "from" and
            "to" attributes swapped, type="error" and containing <error />
            element plus payload of `self`.
        :returntype: `unicode`"""

        if self.get_type() == "error":
            raise StanzaError,"Errors may not be generated in response to errors"

        m=Message(stanza_type="error",from_jid=self.get_to(),to_jid=self.get_from(),
            stanza_id=self.get_id(),error_cond=cond)

        if self.node.children:
            n=self.node.children
            while n:
                m.node.children.addPrevSibling(n.copyNode(1))
                n=n.next
        return m

# vi: sts=4 et sw=4
