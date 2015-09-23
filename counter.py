'''
Created on 8 Jan 2015

@author: dpetkovic
'''

class Counter():
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.count200 = 0
        self.count404 = 0
        self.count500 = 0
        self.countOther = 0
    
    def increment(self, responseCode):
        if (responseCode == 200):
            self.count200 = self.count200 + 1
        elif (responseCode == 404):
            self.count404 = self.count404 + 1
        elif (responseCode == 500):
            self.count500 = self.count500 + 1
        elif (responseCode == 412):
            self.count412 = self.count412 + 1
        else:
            self.countOther = self.countOther + 1
            
        return self
    
    def __str__(self):
        result = ('200: ', str(self.count200), '\n404 :', str(self.count404), '\n500 :', str(self.count500), '\nOther :', str(self.countOther))
        print(''.join(result))
        return ''.join(result)