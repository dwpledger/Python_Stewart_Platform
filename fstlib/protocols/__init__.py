#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Twisted protocol helper for easyip"""
__autor__ = "Peter Magnusson"
__copyright__ = "Copyright 2009-2010, Peter Magnusson <peter@birchroad.net>"
__version__ = "1.0.0"
__all__=('TwistedEasyS')

#Copyright (c) 2009-2010 Peter Magnusson.
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification,
#are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#    
#    2. Redistributions in binary form must reproduce the above copyright 
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Peter Magnusson nor the names of its contributors may be used
#       to endorse or promote products derived from this software without
#       specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from fstlib import easyip
import logging
from twisted.internet import protocol
from twisted.python import log




class LogProxy(object):
    def debug(self, msg):
        log.msg(msg, logLevel=logging.DEBUG)

class TwistedEasyS(protocol.DatagramProtocol):
    """
    Warning!!!
    This class is experimental and not tested
    """
    def __init__(self):
        #self.log = logging.getLogger('easyip.EasyS')
        self.log=LogProxy()
            
    def startProtocol(self):
        pass
    
    def sendMsg(self, packet, (host, port)):
        self.log.debug('Sending data')
        self.transport.write(packet.pack(), (host, port))
            
    def datagramReceived(self, datagram, (host,port)):
        packet = easyip.Packet(datagram)
        response = self.react(packet)
        if response:
            self.sendMsg(response, (host, port))

    def react(self, packet):
        response = easyip.Packet();
        response.counter = packet.counter
        response.flags = 128
        return response
        