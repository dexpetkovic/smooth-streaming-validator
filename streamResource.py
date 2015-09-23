'''
Created on 16 Mar 2015

@author: dpetkovic
'''

import logging
import urllib.request
import threading
import re
import socket

from socket import fromfd
from socket import AF_INET
from socket import SOCK_STREAM

from urllib.error import URLError
from urllib.error import HTTPError
from http.client import HTTPResponse

class StreamResource():
    '''
    classdocs
    '''
    

    def __init__(self):
        self.OriginSourceServerIp = ''
        self.OriginSourceServerHost = ''
        self.CDNSourceServerIp = ''
        self.CDNSourceServerPort = ''
    
    def setCDNServerSourceIpPort(self, response):
        # http://stackoverflow.com/questions/8919627/how-to-determine-the-ip-address-of-the-server-after-connecting-with-urllib2
        # Analyze the source IP of the server that served the request
        try:
            mysockno = response.fileno()
            mysock = fromfd( mysockno, AF_INET, SOCK_STREAM)
            (ip, port) = mysock.getpeername()
            self.CDNSourceServerIp = ip
            self.CDNSourceServerPort = port
        except:
            #peer = response.fp._sock.fp._sock.getpeername()
            #logging.error("Peer is %s", str(peer))
            pass
    
    def getCDNServerSourceIpPort(self):
        return (self.CDNSourceServerIp, self.CDNSourceServerPort)
        
    def getOriginSourceServerIp(self):
        return self.OriginSourceServerIp
                                              
    def setOriginSourceServerIp(self,OriginSourceServerIp):
        self.OriginSourceServerIp = OriginSourceServerIp
        
    def getOriginSourceServerHost(self):
        return self.OriginSourceServerHost
    
    def setOriginSourceServerHost(self, response):
        headers = self.normalize(response.getheaders())
        #print("Served by:",headers['server'])
        if ('server' in headers):
            self.OriginSourceServerHost = headers['server']
            return headers['server']
        #else:
        #    return headers['server']
    
    def getResource(self, urlLocation):
        req = urllib.request.Request(urlLocation)
        try: 
            response = urllib.request.urlopen(req)
            return response
        except HTTPError as httperror:
            return httperror
        except URLError as urlerror:
            return urlerror
        except:
            logging.error('%s: Error in getResource %s %s',threading.current_thread().name, urlLocation, URLError.reason)
    
    def normalize(self, headers):
        '''
        Normalize function that is used to properly parse http header and cast values to correct type        
        '''
        headers = dict((x, y) for x, y in headers)
        # Prior to header check, do the normalization of values in dictionary and cast them into correct typee
        
        logging.debug('%s: Starting normalization', threading.current_thread().name)
        headers['Content-Length'] = int(headers['Content-Length'])
        logging.debug('%s: Content-Length header normalized', threading.current_thread().name)
        
        if 'X-Cache' in headers:
            headers['X-Cache'] = re.sub(r"( from d.cdn.*$)",'',headers['X-Cache']).strip()
            #print("X-Cache posle normalizacije", headers['X-Cache'])
            logging.debug('%s: X-Cache header normalized', threading.current_thread().name)
        else:
            logging.debug('%s: X-Cache header not present', threading.current_thread().name)
            headers['X-Cache'] = 'Undefined'
        
        
        if 'Age' in headers:
            headers['Age'] = int(headers['Age'])
            logging.debug('%s: Age header normalized', threading.current_thread().name)
        elif (('Age' not in headers) & (headers['X-Cache'] == "MISS")):
            logging.debug('%s: Age header not present due to missed cache', threading.current_thread().name)
        elif (('Age' not in headers) & (headers['X-Cache'] == "HIT")):
            logging.error('%s: Age header not present despite cache hit ', threading.current_thread().name)

        if ('Cache-Control' in headers) :
            # Normalize cache-control header and leave only int in the field instead of string
            # "max-age=xxx"
            # http://stackoverflow.com/questions/8270092/python-remove-all-whitespace-in-a-string
            # http://stackoverflow.com/questions/16789840/python-requests-cant-send-multiple-headers-with-same-key
            #
            maxage = re.sub('max-age=','',headers['Cache-Control']).strip()
            maxage = re.sub(',.*','', maxage).strip()
            maxage = int(maxage)
            headers['cache-control'] = maxage
            headers['Cache-Control'] = maxage
            #print(maxage)
            logging.debug('%s: Cache-Control header normalized', threading.current_thread().name)
            
        elif ('cache-control' in headers):
            maxage = re.sub('max-age=','',headers['cache-control']).strip()
            maxage = re.sub(',.*','', maxage).strip()
            maxage = int(maxage)
            headers['cache-control'] = maxage
            headers['Cache-Control'] = maxage
            #print(maxage)
            logging.debug('%s: cache-control header normalized', threading.current_thread().name)
        else:
            logging.debug('%s: cache-control header not present', threading.current_thread().name)
        
        #if ('server' in headers):       
        
        logging.debug('%s: Normalization completed', threading.current_thread().name)
        return headers
    
    def __str__(self):
        iterator = iter(self.streamUrls)
        for i in iterator:
            print(i)