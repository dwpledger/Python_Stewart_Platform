#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Functions and classes for generating FESTO EasyIP Packets

Packet is the main class which is the most important
Flags and Operands are enum classes just to keep track of various constants
"""
__autor__ = "Peter Magnusson"
__copyright__ = "Copyright 2009-2010, Peter Magnusson <peter@birchroad.net>"
__version__ = "1.0.0"
__all__ = ['Flags', 'Operands', 'Factory', 'PayloadEncodingException', 'PayloadDecodingException', 'Packet']

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


from struct import pack, unpack, calcsize
import logging
import sys

EASYIP_PORT=995

class Flags():
    """
    EasyIP flag enum
    """
    EMPTY = 0
    BIT_OR=0x2
    BIT_AND=0x4
    NO_ACK=0x40
    RESPONSE=0x80

class Operands():
    """
    EasyIP Operands enum
    """
    EMPTY=0
    FLAG_WORD=1
    INPUT_WORD=2
    OUTPUT_WORD=3
    REGISTERS=4
    STRINGS=11

class Factory():
    """
    A simple protocol factory to help generate valid packets for common use-cases
    """
    @classmethod
    def send_string(cls, counter, string, string_no):
        """
        Send a single string to be stored at string_no
        """
        packet = Packet(counter=counter,
                        senddata_type=Operands.STRINGS,
                        senddata_offset = string_no)
       
        count = packet.encode_payload(string, packet.DIRECTION_SEND)
        packet.senddata_size = count
        assert count
        return packet
    
    @classmethod
    def send_flagword(cls, counter, words, offset=0):
        """
        Send flagword(s) to be stored starting att Flagword offset
        """
        packet = Packet()
        packet.counter = counter
        packet.senddata_type = Operands.FLAG_WORD
        
        packet.senddata_offset = offset
        count = packet.encode_payload(words, packet.DIRECTION_SEND)
        packet.senddata_size = count
        assert count
        return packet
    
    @classmethod
    def req_flagword(cls, counter, count, offset=0):
        """
        Request 'count' flagwords starting at flagword 'offset'
        """
        packet = Packet()
        packet.counter=counter
        packet.error=0
        packet.reqdata_type=Operands.FLAG_WORD
        packet.reqdata_size=count
        packet.reqdata_offset_server = offset
        return packet
    
    @classmethod
    def req_string(cls, counter, string_no):
        """
        Request string at 'string_no'
        """
        packet = Packet()
        packet.counter=counter
        packet.reqdata_type=Operands.STRINGS
        packet.reqdata_size=1
        packet.reqdata_offset_server = string_no
        return packet
    
    @classmethod
    def response(cls, in_packet, error=0):
        """
        Create a base response packet matching 'in_packet'
        Payload has to be done manually
        """
        packet = Packet()
        packet.counter = in_packet.counter
        packet.error=error
        packet.flags = Flags.RESPONSE
        return packet

class PayloadEncodingException(Exception):
    pass

class PayloadDecodingException(Exception):
    pass

class Packet(object):
    """Class for managing EasyIP packet
    """
    #L/H
    HEADER_FORMAT='<B B H H B B H H B B H H H'
    _FIELDS=['flags', 'error', 'counter', 'index1', 'spare1', 
        'senddata_type', 'senddata_size', 'senddata_offset', 
        'spare2', 'reqdata_type', 'reqdata_size', 'reqdata_offset_server',
        'reqdata_offset_client']
    DIRECTION_SEND=1
    DIRECTION_REQ=2
   
    def __init__(self, data=None, **kwargs):
        self.logger = logging.getLogger('fstlib.easyip')
        self.payload = None
        for f in self._FIELDS:
            setattr(self, f, 0)
        
        if data:
            self.logger.debug("len(data)=%d" % len(data))
            self.unpack(data);
            self.payload=data[calcsize(self.HEADER_FORMAT):]
        else:
            for key in kwargs:
                if key in Packet._FIELDS:
                    setattr(self,key, kwargs[key])

    def unpack(self, data):
        """Unpacks a packet comming in a string buffer"""
        self.logger.debug("Unpacking data")
        data = unpack(self.HEADER_FORMAT, data[0:calcsize(self.HEADER_FORMAT)])
        header=list(data)
        index = 0
        for f in self._FIELDS:
            setattr(self, f, header[index])
            index +=1
            
        self.logger.debug(self.__str__())
        return header
    
    def pack(self):
        header = []
        for f in self._FIELDS:
            header.append(getattr(self, f, 0))
            
        packed_header = pack(self.HEADER_FORMAT, *header)
        if self.payload and len(self.payload)>0:
            return packed_header + self.payload
        else:
            return packed_header
    
    
    def __str__(self):
        return "Packet(flags=%i error=%i counter=%i send_type=%i request_type=%i)" %  (
            self.flags, self.error, self.counter,
            self.senddata_type, self.reqdata_type)

    def encode_payload(self, data, direction):
        count = None
        type = None
        if direction==self.DIRECTION_SEND:
            type = self.senddata_type
        
        if not type:
            self.payload = None
        elif type == Operands.STRINGS:
            if isinstance(data, list):
                raise PayloadEncodingException("String payload can not be a list object!")
            elif isinstance(data, str) or isinstance(data, unicode):
                #all strings must be zero terminated
                self.payload = str(data) + "\x00"
                count = 1
            else:
                self.payload = None
        else:
            if not isinstance(data, list):
                data = [data,]
            for d in data:
                if d>65535 or d<0: raise PayloadEncodingException("Word must be within 0 - 65535")
            count = len(data)
            payload_format = '<' + "H "*count
            self.payload = pack(payload_format, *data)
        return count
    
    def decode_payload(self, direction):
        count = 0
        type = Operands.EMPTY
        if direction==self.DIRECTION_SEND:
            count = self.senddata_size
            type = self.senddata_type
        else:
            count = self.reqdata_size
            type = self.reqdata_type
        
        if type == Operands.STRINGS:
            strings = self.payload.split("\0",count)
            strings.pop()
            return strings
        else:
            payload_format = '<' + ("H " * count)
            try:
                return unpack(payload_format, self.payload[:count*2])
            except Exception as e:
                raise PayloadDecodingException("Failed to decode payload with format='%s'" % payload_format, e), None, sys.exc_info()[2]
                
    
    
    def response_errors(self, response):
        errors = []
        if response.flags != Flags.RESPONSE:
            errors.append('not a response packet')
            
        if response.counter != self.counter:
            errors.append('bad counter')
            
        if len(errors)>0:
            return errors
        else:
            return None