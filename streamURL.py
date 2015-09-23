'''
Created on 25 Nov 2014

@author: dpetkovic

Classes design done with help with:

http://stackoverflow.com/questions/18137941/difference-between-assigning-values-to-attributes-in-child-class-and-parent-clas
http://stackoverflow.com/questions/8270092/python-remove-all-whitespace-in-a-string
http://stackoverflow.com/questions/16789840/python-requests-cant-send-multiple-headers-with-same-key

'''
import sys
import traceback
import logging
import urllib.request
import threading
import re
import hashlib

from urllib.parse import urljoin 
from urllib.error import URLError
from urllib.error import HTTPError
from http.client import HTTPResponse
from pymongo import MongoClient
from pip._vendor.requests.models import Response
from smoothStreamingValidator.streamResource import StreamResource
#from smoothStreamingValidator.playlist import ThreadedRequest

class StreamURL(StreamResource):
    
    '''Definition of normal response
        
        A normal response:
        - 200 OK
        - does not have null content-length and also does not have more than 10MB content-length
        - has cache-control headers in range configured on the CDN / origin
        - If (Age) then
            Age < cache-control:max-age
        - has content-type set to video/mp4
        - Last-Modified < Date   
        
        To do:
        
        - has the following caching logic in place:
        - if X-Cache is HIT from d.cdn.upclabs.com then
            if (Age) && (Age < cache-control:max-age) then
                correct
        - Check if this applies:
            expires = Date + cache-control:max-age
    '''
    
    def __init__(self, baseUrl, playlist):
        super(StreamURL, self).__init__()
        self.baseUrl = baseUrl
        self.streamUrls = []
        self.playlist = playlist
        
    def analyzeResponse(self, streamUrl, response, counter, queryOrigin):
        #
        # Get headers and create dictionary from the headers list tuple
        # http://stackoverflow.com/questions/3783530/python-tuple-to-dict
        #
        if (isinstance(response, HTTPResponse)):
             
                if (response.getcode() == 200):
                  
                    # Check if class implementation is done correctly
                    #print(isinstance(currentResponse, Response))
                    print(threading.current_thread().name, " Request ", streamUrl.rstrip(), response.getcode())
                    headers = self.normalize(response.getheaders())
                    hasher = hashlib.md5()
                    # Read from n bytes http://stackoverflow.com/questions/18019150/best-way-to-remove-first-6-bytes-and-very-last-byte-python
                    hasher.update(response.read()[1536:])
                    #print(hasher.hexdigest(), hasher.digest())
                    
                    logging.info('%s: %s %d %s %s', threading.current_thread().name, streamUrl.rstrip(), response.getcode(), headers['Content-Length'], hasher.hexdigest())
                    logging.debug('%s: Body of response to %s : %d\n %s', threading.current_thread().name, streamUrl, response.getcode(), response.info())
                    
                    self.analyzeResponseCode(streamUrl, response, counter)
                    self.analyzeResponseContentLength(streamUrl, response, headers)
                    self.analyzeResponseContentType(streamUrl, headers)
                    self.compareManifestAndChunkOrigins(response)
                else:
                    logging.error('%s: Request %s got response: %d %s', threading.current_thread().name, streamUrl, response.getcode(), response.info())
                    self.analyzeResponseCode(streamUrl, response, counter)
        #elif(isinstance(response, URLError)):
        else:
            logging.error('%s: Request %s got response: %s', threading.current_thread().name, streamUrl, response.code)
            self.analyzeResponseCode(streamUrl, response, counter)
            if (queryOrigin == True):
                
                for origin in self.playlist.getOrigins():
                    #print(origin)
                    originStreamUrl = re.sub('http://.*(com|tv)', ('http://' + origin), streamUrl).strip()
                    originResponse = self.getResource(originStreamUrl)
                    self.compareResponse(streamUrl, response, originStreamUrl, originResponse, counter)
              
        logging.debug('%s: Completed response analysis', threading.current_thread().name) 
            
            
    
    def analyzeResponseCode(self, streamUrl, response, counter):
        
        #
        # Response code analysis
        #
        if (response.getcode() == 200):
            #print("200 OK: ", response.getcode())
            counter.increment(response.getcode())
        else:
            #print("Response code:", response.code)
            counter.increment(response.code)
            self.compareManifestAndChunkOrigins(response)
        #counter.__str__() 
      
        
    def analyzeResponseContentLength(self, streamUrl, response, headers):
        #
        # Content-Length analysis
        #
        #logging.info("%s %s", threading.current_thread().name, streamUrl, headers['Content-Length'])
        if ((headers['Content-Length'] > 0) & (headers['Content-Length'] < 1000)):
            logging.error('%s: Content-Length is too low %s. This is suspicious', threading.current_thread().name, headers['Content-Length'])
        elif (headers['Content-Length'] > 100000000):
            logging.error('%s: Content-Length is too high %s. Is this expected?', threading.current_thread().name, headers['Content-Length'])
        else:
            logging.debug('%s: OK. Content-Length: %s', threading.current_thread().name, headers['Content-Length'])
        #
        # Age & cache-control analysis
        #
        if (('X-Cache' in headers)):
            if (headers['X-Cache'] == "HIT"):
                logging.debug('%s: Cache hit', threading.current_thread().name)
                if (('Age' in headers) & (('Cache-Control' in headers) | ('cache-control' in headers))):
                    if ((headers['Age'] > headers['Cache-Control']) | (headers['Age'] > headers['cache-control'])):
                        #print('Age = ', headers['Age'], ' is higher than cache-control:max-age = ', headers['cache-control'])
                        logging.error('%s: Age = %d is higher than cache-control:max-age = %d.\n%s', threading.current_thread().name, headers['Age'], headers['Cache-Control'], response.info())
                        #raise ResponseException(threading.current_thread().name, headers['Age'], headers['cache-control'], self.response.info())
                    else:
                        logging.debug('%s: OK. Age = %d is lower than cache-control:max-age = %d', threading.current_thread().name, headers['Age'], headers['Cache-Control'])
                else:
                    logging.error('%s: Age header or Cache-Control headers not present, while X-Cache was HIT. This could be FATAL. %s', threading.current_thread().name, response.info())
                    
            else:        
                #print(headers['X-Cache'])
                logging.debug('%s: Cache missed', threading.current_thread().name)
        else:
            logging.error('%s: X-Cache header not present', threading.current_thread().name)
        
    def analyzeResponseContentType(self, streamUrl, headers):
        #    
        # Content-Type analysis
        # http://stackoverflow.com/questions/1602934/check-if-a-given-key-already-exists-in-a-dictionary
        if 'Content-Type' in headers:
            if (headers['Content-Type'] == "video/mp4"):
                logging.debug('%s: OK. Content-Type header has value %s', threading.current_thread().name, headers['Content-Type'])
            elif (headers['Content-Type'] == "video/MP2T"):
                logging.debug('%s: OK. Content-Type header has value %s', threading.current_thread().name, headers['Content-Type'])
            elif (headers['Content-Type'] == "video/mp2t"):
                logging.debug('%s: OK. Content-Type header has value %s', threading.current_thread().name, headers['Content-Type'])
            else:
                logging.error('%s: Content-Type header has WRONG value %s', threading.current_thread().name, headers['Content-Type'])
        else:
            logging.error('%s: Content-Type header is not present in the header', threading.current_thread().name)
        
    def makeQuery(self, queryOrigin, counter):               
        #try:
        iterator = iter(self.streamUrls)
        # Make the actual request
        for streamUrl in iterator:
            response = self.getResource(streamUrl)
            #print("CHECKPOINT", response.getcode(), response.info())
            self.analyzeResponse(streamUrl, response, counter, queryOrigin)
    
    def compareResponse(self, streamUrl, response, originStreamUrl, originResponse, counter):
        # We already know that Response is not of type HTTPResponse.
               
        if (isinstance(originResponse, HTTPResponse)):
            if (response.code != originResponse.getcode()):
                logging.error('%s: MISMATCH: Origin request %s got response: %s\nOriginal request %s got response: %s', threading.current_thread().name, originStreamUrl, originResponse.getcode(), streamUrl.rstrip(), response.code)
                self.compareManifestAndChunkOrigins(response)
            else:
                logging.info('%s: Origin  : %s %s\n%s: Original: %s %s', threading.current_thread().name, originStreamUrl, originResponse.getcode(), streamUrl.rstrip(), response.getcode())
        
        elif (isinstance(originResponse, URLError)):
            logging.error('%s: Origin request %s got response: %s', threading.current_thread().name, originStreamUrl, originResponse.code)
        
        else:
            # Now originResponse is HTTPError
            if (response.code != originResponse.code):
                logging.error('%s: MISMATCH: Origin request %s got response: %s\nOriginal request %s got response: %s', threading.current_thread().name, originStreamUrl, originResponse.getcode(), streamUrl.rstrip(), response.code)
            else:
                logging.debug('%s: WARNING Origin request %s got response: %s\nOriginal request %s got response: %s', threading.current_thread().name, originStreamUrl, originResponse.reason, streamUrl, response.reason)
    
    def compareManifestAndChunkOrigins(self, response):
        self.setCDNServerSourceIpPort(response)
        self.setOriginSourceServerHost(response)        
        
        #if (self.getOriginSourceServerHost != self.getOriginSourceServerHost):
        #    logging.error('%s: MISMATCH: Different origin served the Manifest and chunk.\nManifest: %s\nChunk: %s', threading.current_thread().name, self.OriginSourceServerIp, chunkOriginServerSourceIP)
        #else:
        #    logging.info('%s: Same origin served the Manifest and chunk.\nManifest: %s\nChunk: %s', threading.current_thread().name, self.OriginSourceServerIp, chunkOriginServerSourceIP)
    
    def __str__(self):
        
        response = "\n".join(self.streamUrls)
        logging.debug('StreamURL:\n %s', response)
        #iterator = iter(self.streamUrls)
        #for i in iterator:
            #print(i)
            
class OrionHSSStreamUrl(StreamURL):
    def __init__(self, playlist, baseUrl, time, deltaArray, length, qualityLevels):
        super(OrionHSSStreamUrl, self).__init__(baseUrl, playlist)
        self.time = time
        self.deltaArray = deltaArray
        self.length = length
        self.qualityLevels = qualityLevels
        
    def getStreamURLs(self):
        time = self.time
        logging.debug('%s: Starting update of streamURL array', threading.current_thread().name)
        for i in range(0, self.length):
            if(re.findall(r"(^.*Helios-HSS.*$)", self.playlist.getPlaylistUrl())):
                url = urljoin(self.baseUrl,'IRDETO-HSS-H/QualityLevels(' + str(self.qualityLevels) + ')/Fragments(video=' + str(int(time)) + ')')
                #print(self.baseUrl, "IS Helios VOD")
            elif(re.findall(r"(^.*\.vod.*$)", self.baseUrl)):
                url = urljoin(self.baseUrl,'IRDETO-HSS-O/QualityLevels(' + str(self.qualityLevels) + ')/Fragments(video=' + str(int(time)) + ')')
                #print(self.baseUrl, "IS Orion VOD")
            else:
                url = urljoin(self.baseUrl,'QualityLevels(' + str(self.qualityLevels) + ')/Fragments(video=' + str(int(time)) + ')')
                #print(self.baseUrl, "IS LIVE")
            self.streamUrls.append(url)
            time = time + int(self.deltaArray[i])
            #print(self.streamUrls[i], 'index : ', i)
        logging.debug('%s: Completed updating streamURL array', threading.current_thread().name)
        return self
    
    def __str__(self):
        logging.debug('base URL: %s\nStart time: %s\nDelta: %s\nLength: %s\nStreamURLs: %s\n', self.baseUrl, self.time, self.deltaArray, self.length, "\n".join(self.streamUrls))
        
        #print ('base URL: ', self.baseUrl)
        #print ('Start time: ', self.time)
        #print ('Delta: ', self.deltaArray)
        #print ('Length: ', self.length)
        #iterator = iter(self.streamUrls)
        #for i in iterator:
        #    print(i)
            
class DawnStreamUrl(StreamURL):
    def __init__(self, playlist, baseUrl):
        super(DawnStreamUrl, self).__init__(baseUrl)
    
    def getStreamURLs(self):
        #print("Getting Dawn URL")
        response = self.getResource(self.baseUrl)
        chunks = re.findall(r"(^.*Segment.*$)", response.read().decode('utf-8'), re.MULTILINE)
        for chunk in chunks:
            playlistUrl = re.sub(r"(Level.*)", chunk, self.baseUrl)
            #print(playlistUrl)            
            #logging.debug('%s Instantiated DawnStreamUrl object with the parameters: %s ', threading.current_thread().name, playlistUrl)
            self.streamUrls.append(playlistUrl)
        return self
    
    def __str__(self):
        logging.DEBUG('base URL: %s\nStreamUrls: %s\n', self.baseUrl, "\n".join(self.streamUrls))
        #print ('base URL: ', self.baseUrl)
        #iterator = iter(self.streamUrls)
        #for i in iterator:
        #    print(i)
            
class OrionLiveHLSStreamUrl(StreamURL):
    def __init__(self, playlist, baseUrl):
        super(OrionLiveHLSStreamUrl, self).__init__(baseUrl)
    
    def getStreamURLs(self):
        #print("Getting Orion Live HLS URL")
        response = self.getResource(self.baseUrl)
        #print(self.baseUrl)
        chunks = re.findall(r"(.*\.ts)", response.read().decode('utf-8'), re.MULTILINE)
        for chunk in chunks:
            playlistUrl = re.sub(r"([0-9]{2}\.m3u8)", chunk, self.baseUrl)
            #print(chunk, playlistUrl)
            if (playlistUrl not in self.streamUrls):            
                logging.debug('%s Instantiated Orion Live HLS URL object with the parameters: %s ', threading.current_thread().name, playlistUrl)
                #print(threading.current_thread().name, " Added to the list ", playlistUrl)
                self.streamUrls.append(playlistUrl)
        return self