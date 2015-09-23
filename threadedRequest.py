'''
Created on 9 Jan 2015

@author: dpetkovic
'''

import queue
import threading
import logging


class ThreadedRequest():
    '''
    Implementation idea taken from:
    
    http://stackoverflow.com/questions/16199793/python-3-3-simple-threading-event-example
    http://www.troyfawkes.com/learn-python-multithreading-queues-basics/
    
    '''
    
    def __init__(self, numberOfThreads, numberOfIterations):
        self.numberOfThreads = numberOfThreads
        self.numberOfIterations = numberOfIterations
        self.q = queue.Queue()
        
        for i in range(self.numberOfThreads):
            t = threading.Thread(target=self.worker)
            logging.debug('%s: Starting thread', threading.current_thread().name)
            t.daemon = True # thread dies when main thread (only non-daemon thread) exits.cal
            t.start()
        
    def worker(self):
        while True:
            currResource, queryOrigin, counter = self.q.get()
            logging.debug('%s: Starting query on resource', threading.current_thread().name)
            currResource.makeQuery(queryOrigin, counter)
            logging.debug('%s: Completed query on thread', threading.current_thread().name)
            counter.__str__()
            self.q.task_done()
    
    def lock(self):
        return threading.Lock()
    
    def makeThreadedRequest(self, resource, queryOrigin, counter):
        for i in range(self.numberOfIterations):                    
            self.q.put((resource, queryOrigin, counter))
            logging.debug('%s: Adding to the queue: %s', threading.current_thread().name, resource.__str__())