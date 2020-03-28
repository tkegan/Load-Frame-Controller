#####################################################################
# Copyright 2020 Tom Egan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#####################################################################

# Import from Python Standard Library
from abc import ABC, abstractmethod

'''
Interface for working with load frames

License
--------
Apache 2.0 License (See Also LICENSE file)

Author
--------
Tom Egan <tom@tomegan.tech>
'''

class LoadFrame(ABC):
    '''
    An abstract base class that defines an interface we expect we can implement
    for all the load frames we wish to support 
    '''


    @abstractmethod
    def get_load_cell_range(self):
        '''
        Get the rated range for the load cell in Newtons (N)

        Raises
        --------
        LookupError if the machine reports a load cell of an unknown type
            is in use or does not respond to request to read configuration
        '''
        pass


    @abstractmethod
    def read_extension(self):
        '''
        Get the current extension in Millimeters (mm)
        '''
        pass


    @abstractmethod
    def read_load(self):
        '''
        Get the current load in Newtons (N)
        '''
        pass


    @abstractmethod
    def set_run_rate(self, rate):
        pass


    @abstractmethod
    def start_moving_up(self):
        pass


    @abstractmethod
    def start_moving_down(self):
        pass


    @abstractmethod
    def stop_moving(self):
        pass


    @abstractmethod
    def zero_extension(self):
        pass


    @abstractmethod
    def zero_load(self):
        pass