#!/usr/bin/python3

#####################################################################
# Copyright 2020 Tom Egan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#####################################################################

# We want to live in Python 3 but...
from __future__ import division

# Import from Python Standard Library
from abc import ABC, abstractmethod
from threading import RLock
from time import sleep

# Import from third party libraries
from serial import Serial

'''
Classes for communicating with Tinius Olsen load frames

A number of, at this time, older Tinius Olsen load frames include a control
module with an RS232 port which can be connected to a computer which can then
control the apparatus. This module provides implementations of the text over
serial communication protocols used by some of these machines.

License
--------
Apache 2.0 License (See Also LICENSE file)

Author
--------
Tom Egan <tegan@bucknell.edu> for Bucknell University 
'''

class TiniusOlsen(ABC):
    '''
    An abstract base class that implements some core functionality shared
    by all supported Tinius Olsen load frames 
    '''

    def __init__(self):
        self.communication_port = None  # insures that the attribute exists...
        self._lock = RLock()


    def __del__(self):
        if self.communication_port:
            self.stop_moving()
            self.communication_port.close()


    def _read(self):
        buffer = bytearray()
        with self._lock:
            while True:
                b = self.communication_port.read()
                if 1 > len(b) or 13 == b[0] or 0 == b[0]:
                    break
                else:
                    buffer.append(b[0])
            
            #print(buffer.decode('utf-8'))
            return buffer


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


class TiniusOlsenH5KSeries(TiniusOlsen):
    '''
    An implementation of the serial Communication protocol used with Tinius
    Olsen H5K series load frame controllers
    '''

    range_lookup_table = {
        "5": 5,
        "17": 10,
        "18": 20,
        "19": 25,
        "20": 30,
        "21": 50,
        "33": 100,
        "34": 200,
        "35": 250,
        "36": 300,
        "37": 500,
        "49": 1000,
        "50": 2000,
        "51": 2500,
        "52": 3000,
        "53": 5000,
        "65": 10000,
        "66": 20000,
        "67": 25000,
        "68": 30000,
        "69": 50000,
        "81": 100000,
        "82": 200000,
        "83": 250000
    }


    def __init__(self, communication_port_name):
        '''
        Parameters
        --------
        communication_port_name : str
            the name of the serial port by which a compatible Tinius Olsen
            load frame is connected to the PC running your script

        Raises
        --------
        IOError - if the serial port can not be opened
        '''
        super().__init__()
        self.communication_port = Serial(communication_port_name, 19200, timeout=1)
        self.range = self.get_load_cell_range()


    def get_load_cell_range(self):
        '''
        Get the rated range for the load cell in Newtons (N)

        Raises
        --------
        LookupError if the machine reports a load cell of an unknown type
            is in use or does not respond to request to read configuration
        '''
        load_cell_type = self.read_load_cell_type()
        try:
            return self.range_lookup_table[load_cell_type]
        except KeyError as ke:
            raise LookupError("Machine reports unknown load cell is in use") from ke


    def read_extension(self):
        '''
        Get the current extension in millimeters (mm)
        '''
        with self._lock:
            self.communication_port.write(b'RP\r')
            return 0.001 * int(self._read())


    def read_load(self):
        '''
        Get the current load in Newtons (N)
        '''
        with self._lock:
            self.communication_port.write(b'RL\r')
            # 0X7FFF seems like a logical conversion constant but
            # the machines do not seem to have binary number ranges
            # d30000 works better
            return int(self._read()) / 30000


    def read_load_cell_type(self):
        '''
        Get the type of the currently installed load cell.

        Returns
        --------
        str - which should be one of the predefined keys in range_lookup_table 
        '''
        with self._lock:
            self.communication_port.write(b'RC\r')
            return self._read().decode('utf-8')


    def set_run_rate(self, rate):
        with self._lock:
            self.communication_port.write(b'WV')
            self.communication_port.write(bytes("{:.1f}".format(rate), 'utf-8'))
            self.communication_port.write(b'\r')
            self._read() # purge the \r


    def start_moving_up(self):
        with self._lock:
            self.communication_port.write(b'WF\r')
            self._read() # purge the \r


    def start_moving_down(self):
        with self._lock:
            self.communication_port.write(b'WR\r')
            self._read() # purge the \r


    def stop_moving(self):
        with self._lock:
            self.communication_port.write(b'WS\r')
            self._read() # purge the \r


    def zero_extension(self):
        with self._lock:
            self.communication_port.write(b'WP\r')
            self._read() # purge the \r


    def zero_load(self):
        with self._lock:
            self.communication_port.write(b'WZ\r')
            self._read() # purge the \r


class TiniusOlsen1000Series(TiniusOlsen):
    '''
    An implementation of the serial Communication protocol used with Tinius
    Olsen 1000 series load frame controllers.
    
    These machines assume that software will manipulate data to provide
    zeroing in software always reporting an absolute value over the serial
    protocol 
    '''

    range_lookup_table = {
        "0": 1000,
        "1": 100,
        "2": 10,
        "3": 1,
        "6": 10000
    }


    def __init__(self, communication_port_name):
        '''
        Parameters
        --------
        communication_port_name : str
            the name of the serial port by which a compatible Tinius Olsen
            load frame is connected to the PC running your script

        Raises
        --------
        IOError - if the serial port can not be opened
        '''
        super().__init__()
        self.communication_port = Serial(communication_port_name, 9600, timeout=1)
        self.zero_load_offset = 0
        self.zero_extension_offset = 0


    def get_load_cell_range(self):
        '''
        Get the rated range for the load cell in Newtons (N)

        Raises
        --------
        LookupError if the machine reports a load cell of an unknown type
            is in use or does not respond to request to read configuration
        '''
        load_cell_type = self.read_load_cell_type()
        try:
            return self.range_lookup_table[load_cell_type]
        except KeyError as ke:
            raise LookupError("Machine reports unknown load cell is in use") from ke


    def read_extension(self):
        '''
        Get the current extension as a multiple of 0.001mm e.g. 6859 is 6.859mm
        '''
        with self._lock:
            self.communication_port.write(b'R2\r')
            return int(self._read()) - self.zero_extension_offset


    def read_load(self):
        '''
        Get the current load as fraction of the full range -1.0 < x < 1.0

        To get the load in Netwons multiply the value returned by this method
        by the value returned from get_load_cell_range
        '''
        with self._lock:
            self.communication_port.write(b'R1\r')
            return (int(self._read()) - self.zero_load_offset) / 2000


    def read_load_cell_type(self):
        '''
        Get the type of the currently installed load cell.

        Returns
        --------
        str - which should be one of the predefined keys in range_lookup_table 
        '''
        with self._lock:
            self.communication_port.write(b'RC\r')
            return self._read().decode('utf-8')


    def set_run_rate(self, rate):
        with self._lock:
            self.communication_port.write(b'WV')
            self.communication_port.write(bytes("{:.1f}".format(rate), 'utf-8'))
            self.communication_port.write(b'\r')
            self._read() # purge the \r


    def start_moving_up(self):
        with self._lock:
            self.communication_port.write(b'WF\r')
            self._read() # purge the \r


    def start_moving_down(self):
        with self._lock:
            self.communication_port.write(b'WR\r')
            self._read() # purge the \r


    def stop_moving(self):
        with self._lock:
            self.communication_port.write(b'WS\r')
            self._read() # purge the \r


    def zero_extension(self):
        with self._lock:
            self.communication_port.write(b'WE\r')
            self._read() # purge the \r
            sleep(15)
            self.communication_port.write(b'R2\r')
            self.zero_extension_offset = int(self._read())


    def zero_load(self):
        with self._lock:
            self.communication_port.write(b'WZ\r')
            self._read() # purge the \r
            sleep(15)
            self.communication_port.write(b'R1\r')
            self.zero_load_offset = int(self._read())
