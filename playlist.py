'''
Created on 2 Oct 2014

@author: dpetkovic

http://stackoverflow.com/questions/11818023/python-regex-to-match-whole-line-with-a-particular-regex-pattern

'''

import re
import logging
import urllib.request
import threading
import queue
import time
import traceback

from xml.dom import minidom
from urllib.error import URLError
from urllib.error import HTTPError
from http.client import HTTPResponse
from smoothStreamingValidator.streamURL import StreamURL
from smoothStreamingValidator.streamURL import OrionHSSStreamUrl
from smoothStreamingValidator.streamURL import DawnStreamUrl
from smoothStreamingValidator.streamURL import OrionLiveHLSStreamUrl
from smoothStreamingValidator.streamResource import StreamResource

class Playlist(StreamResource):
    
    def __init__(self, playlistUrl, queryOrigin, origins):
        # The biggest quality level chunk from the playlist
        super(Playlist, self).__init__()
        self.playlistUrl = playlistUrl
        self.streamType = ''
        self.playlistStreamUrls = []
        self.queryOrigin = queryOrigin
        self.origins = origins
    
    def getOrigins(self):
        return self.origins
    
    def setOrigins(self, origins):
        self.origins = origins

    def getPlaylistUrl(self):
        return self.playlistUrl
        
    def findChildNodeByName(self, parent, name):
        for node in parent.childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.localName == name:
                return node
        return None
    
    def findChildNodesByName(self, parent, name, subname):
        nodeArray = []
        for node in parent.childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.localName == name:
                nodeArray.append(node.attributes[subname].value)
        return nodeArray

    def decideStreamType(self, playlistUrl):
        #print("Debugging decideStreamType", playlistUrl)
        if (re.search("isml", playlistUrl, re.IGNORECASE)):
            #print(playlistUrl, "Orion-HSS")
            return "Orion-HSS"
        elif (re.search("device=Dawn-HLS", playlistUrl, re.IGNORECASE)):
            #print(playlistUrl, "Dawn-HLS")
            return "Dawn-HLS"
        elif (re.search("m3u8", playlistUrl, re.IGNORECASE)):
            #print(playlistUrl, "Orion-HLS")
            return "Orion-HLS"
        elif (re.search("3.ism", playlistUrl, re.IGNORECASE)):
            #print(playlistUrl, "Orion-HSS-VOD")
            return "Orion-HSS-VOD"
        
    def parsePlaylistToGetStreamUrlParams(self):
     
        self.streamType = self.decideStreamType(self.playlistUrl)
        response = self.getResource(self.playlistUrl)
        self.setCDNServerSourceIpPort(response)
        # Update origin source server hostname in the streamResoruce
        self.setOriginSourceServerHost(response)
        print(self.CDNSourceServerIp, self.CDNSourceServerPort)
        print(self.OriginSourceServerIp)
        
        if (self.queryOrigin == True):
            #originStreamUrl = re.sub('http://.*(com|tv)',"http://172.30.65.165:5554", self.playlistUrl).strip()
            originStreamUrl = re.sub('http://.*(com|tv)',"http://172.27.66.173", self.playlistUrl).strip()
            originResponse = self.getResource(originStreamUrl)
            #print("originResponse1")
            if (isinstance(originResponse, HTTPResponse)):
                #print("originResponse2")
                if (response.code != originResponse.getcode()):
                    #print("originResponse3")
                    logging.error('%s: MISMATCH: Origin request %s got response: %s\nOriginal request %s got response: %s', threading.current_thread().name, originStreamUrl, originResponse.reason, self.playlistUrl, response.reason)
                else:
                    logging.info('%s: Origin request %s got response: %s\nOriginal request %s got response: %s', threading.current_thread().name, originStreamUrl, originResponse.getcode(), self.playlistUrl, response.getcode())
    
            else:
                # Now originResponse is HTTP/URLerror
                logging.debug('%s: WARNING Origin request %s got response: %s\nOriginal request %s got response: %s', threading.current_thread().name, originStreamUrl, originResponse.reason, self.playlistUrl, response.code)
        
        # Check the Playlist type and instantiate appropriate object
        if (isinstance(response, HTTPResponse)):
            #print("pre procene koda", response.getcode())
            if (response.getcode() == 200):
                #print (self.playlistUrl)
                if (self.streamType == "Orion-HSS"):
                    # After executing the request, parse the XML from the response
                    #print(response.read())
                    xmldoc = minidom.parse(response)      
                    return self.parseOrionHSSplaylist(xmldoc)
                elif (self.streamType == "Dawn-HLS"): 
                    # After executing the request, parse the XML from the response
                    return self.parseDawnVODHLSplaylist(response)
                elif (self.streamType == "Orion-HLS"): 
                    # After executing the request, parse the XML from the response
                    return self.parseOrionLiveHLSplaylist(response)
                elif (self.streamType == "Orion-HSS-VOD"):
                    # After executing the request, parse the XML from the response
                    xmldoc = minidom.parse(response)
                    return self.parseOrionHSSplaylist(xmldoc, 0)
        else:
            print(response.reason)
                    
    def parseOrionHSSplaylist(self, xmldoc, time=1):
        # Extract the playlistStreamList that describes audio and video streams
        playlistStreamList = xmldoc.getElementsByTagName('StreamIndex')    
        # Find the start time value and the time delta in the StreamIndex video section 
               
        for streamIndex in playlistStreamList:
            if (streamIndex.attributes['Name'].value == 'video'):
                #print (streamIndex.attributes['Name'].value)
                # Get time value, delta and number of chunks
                baseUrl = re.sub('.anifest.*','',self.playlistUrl)
                if (time == 1):    
                    time = int(self.findChildNodeByName(streamIndex,'c').attributes['t'].value)
                
                # Removed due to delta array
                # delta = int(self.findChildNodeByName(streamIndex,'c').attributes['d'].value)
                deltaArray = self.findChildNodesByName(streamIndex,'c','d')
                
                # Removed due to quality levels array
                #qualityLevels = int(self.findChildNodeByName(streamIndex,'QualityLevel').attributes['Bitrate'].value)
                qualityLevelsArray = self.findChildNodesByName(streamIndex,'QualityLevel','Bitrate')
                #print(baseUrl, deltaArray, qualityLevelsArray)
                
                # Length represents number of video chunks in current playlist
                length = len(streamIndex.getElementsByTagName('c'))
                #print(time,delta,length)
                # Instantiate streamURL
                for qualityLevels in qualityLevelsArray:
                    currentStreamURL = OrionHSSStreamUrl(self, baseUrl, time, deltaArray, length, qualityLevels)
                    #print(currentStreamURL.__str__())
                    logging.debug('%s Instantiated OrionHSSStreamUrl object with the parameters: %s %d %d %d %s', threading.current_thread().name, baseUrl, time, deltaArray, length, qualityLevels)
                    currentStreamURL.getStreamURLs()
                    self.playlistStreamUrls.append(currentStreamURL)
        return self
    
    def parseDawnVODHLSplaylist(self, response):
        #
        # http://stackoverflow.com/questions/11818023/python-regex-to-match-whole-line-with-a-particular-regex-pattern
        #
        levels = re.findall(r"(^.*m3u8.*$)", response.read().decode('utf-8'), re.MULTILINE)
        #print(type(response.read()))
        #print(levels)
        for level in levels:
            baseUrl = re.sub(r"(9.m3u8.*)", level, self.playlistUrl)
            #print(baseUrl)
            currentStreamURL = DawnStreamUrl(self, baseUrl)
            logging.debug('%s Instantiated DawnStreamUrl object with the parameters: %s ', threading.current_thread().name, baseUrl)
            currentStreamURL.getStreamURLs()
            self.playlistStreamUrls.append(currentStreamURL)
            
        return self
    
    def parseOrionLiveHLSplaylist(self, response):
        #
        # http://stackoverflow.com/questions/11818023/python-regex-to-match-whole-line-with-a-particular-regex-pattern
        #
        levels = re.findall(r"(^.*m3u8.*$)", response.read().decode('utf-8'), re.MULTILINE)
        #print(type(response.read()))
        #print(levels)
        for level in levels:
            baseUrl = re.sub(r"(index.m3u8)", level, self.playlistUrl)
            #print(baseUrl)
            currentStreamURL = OrionLiveHLSStreamUrl(self, baseUrl)
            logging.debug('%s Instantiated Orion Live HLS StreamUrl object with the parameters: %s ', threading.current_thread().name, baseUrl)
            currentStreamURL.getStreamURLs()
            self.playlistStreamUrls.append(currentStreamURL)
            
        return self
   
    def updatePlaylist(self):
        self.parsePlaylistToGetStreamUrlParams()
        
    def makeQuery(self, queryOrigin, counter):
        self.parsePlaylistToGetStreamUrlParams()
        #iterator = iter(self.playlistStreamUrls)
        ##for playlistStreamUrl in iterator:
        #    playlistStreamUrl.makeQuery(self.queryOrigin, counter, origins)           
    
    def __str__(self):
        logging.debug('Playlist URL: %s\nStreamURLs: %s\n', self.playlistUrl, "\n".join(self.playlistStreamUrls))
        #print(self.playlistUrl)
        #iterator = iter(self.playlistStreamUrls)
        #for i in iterator:
        #    i.__str__()
        #return (self.playlistUrl)
            
            