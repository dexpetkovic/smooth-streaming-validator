'''
Created on 9 Oct 2014

@author: dpetkovic

Logging: http://stackoverflow.com/questions/12260503/how-to-choose-log-level


'''
import logging
import threading
import time
import configparser

from smoothStreamingValidator import playlist,streamURL, threadedRequest
from smoothStreamingValidator.counter import Counter
from datetime import datetime, timedelta

def main():
    
    # Initialize configuration
    config = configparser.ConfigParser()
    config.sections()
    config.read('config.ini')
    
    # Configuration section 
    numberOfIterations = config['DEFAULT']['numberOfIterations']
    numberOfThreads = config['DEFAULT']['numberOfThreads']
    interval = config['DEFAULT']['interval']
    queryOrigin = False
    
    currentPlaylists = []
    counter = Counter()
    
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='smoothStreamingValidator.log', level=logging.INFO)
    logging.info('\n\n Started \n\n')
    
    threadedPlaylistQuery = threadedRequest.ThreadedRequest(numberOfThreads, numberOfIterations)
    logging.debug('%s: Created threadedPlaylistQuery at %s', threading.current_thread().name, time.ctime())
    
    
    with open("urlList.txt","r") as inputList:
        for line in inputList:
            currentPlaylist = playlist.Playlist(line, queryOrigin, origins)
            currentPlaylists.append(currentPlaylist)
            logging.debug('%s: Instantiated playlist %s', threading.current_thread().name, currentPlaylist.playlistUrl)
            # First, parse the current playlist and populate Playlist object with streamURL object
    
    inputList.close()
    
    now = datetime.now()
    end_time = now + timedelta(seconds=interval)
    
    while(end_time >= datetime.now()):
        for currentPlaylist in currentPlaylists:
            threadedPlaylistQuery.makeThreadedRequest(currentPlaylist, queryOrigin, counter)
            logging.debug('%s: Added playlist in thread queue %s', threading.current_thread().name, currentPlaylist.playlistUrl)
            logging.info('%s: Added playlist in thread queue %s', threading.current_thread().name, currentPlaylist.playlistUrl)
        
        threadedPlaylistQuery.q.join()
            
        # Go through the streamUrls extracted from the playlist and make query
        #
        #currentPlaylist.__str__()
        for currentPlaylist in currentPlaylists:
            iterator = iter(currentPlaylist.playlistStreamUrls)
            for playlistStreamUrl in iterator:
                threadedPlaylistQuery.makeThreadedRequest(playlistStreamUrl, queryOrigin, counter)
                          
        time.sleep(5)
    print("Waiting for threads to complete")    
    threadedPlaylistQuery.q.join()
        
    logging.info('The number of response codes from Delivery Appliances not including Origin responses are:\n %s', counter.__str__())
    logging.info('\n\n Completed \n\n')

if __name__ == '__main__':
    main()