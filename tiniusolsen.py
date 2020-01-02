#!/usr/bin/python3

# We want to live in Python 3 but...
from __future__ import division

# Import from Python Standard Library
from threading import RLock

# Import from third party libraries
from serial import Serial


class TiniusOlsen:
    '''
    A class for communicating with Tinius Olsen load frames

    A number of, at this time, older Tinius Olsen load frames include a
    control module with an RS232 port which can be connected to a computer
    which can then control the apparatus. This class implements the text
    over serial communication protocol used by these machines exposing
    exposing methods for scripts to use to control such machines.
    
    License
    --------
    Apache 2.0 License (See Also LICENSE file)
    
    Author
    --------
    Tom Egan <tegan@bucknell.edu> for Bucknell University 
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
        self.communication_port = None  # insures theat the attribute exists...
                                        # useful if the next line raises an error
        self.communication_port = Serial(communication_port_name, 19200, timeout=1)
        self.__lock = RLock()


    def __del__(self):
        if self.communication_port:
            self.stop_moving()
            self.communication_port.close()


    def __read(self):
        buffer = bytearray()
        with self.__lock:
            while True:
                b = self.communication_port.read()
                if 1 > len(b) or 13 == b[0] or 0 == b[0]:
                    break
                else:
                    buffer.append(b[0])
            
            #print(buffer.decode('utf-8'))
            return buffer


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
        with self.__lock:
            self.communication_port.write(b'RP\r')
            return int(self.__read())


    def read_load(self):
        '''
        Get the current load as fraction of the full range -1.0 < x < 1.0

        To get the load in Netwons multiply the value returned by this method
        by the value returned from get_load_cell_range
        '''
        with self.__lock:
            self.communication_port.write(b'RL\r')
            return int(self.__read()) / 0x7FFF


    def read_load_cell_type(self):
        '''
        Get the type of the currently installed load cell.

        Returns
        --------
        str - which should be one of the predefined keys in range_lookup_table 
        '''
        with self.__lock:
            self.communication_port.write(b'RC\r')
            return self.__read().decode('utf-8')


    def set_run_rate(self, rate):
        with self.__lock:
            self.communication_port.write(b'WV')
            self.communication_port.write(bytes("{:.1f}".format(rate), 'utf-8'))
            self.communication_port.write(b'\r')
            self.__read() # purge the \r


    def start_moving_up(self):
        with self.__lock:
            self.communication_port.write(b'WF\r')
            self.__read() # purge the \r


    def start_moving_down(self):
        with self.__lock:
            self.communication_port.write(b'WR\r')
            self.__read() # purge the \r


    def stop_moving(self):
        with self.__lock:
            self.communication_port.write(b'WS\r')
            self.__read() # purge the \r


    def zero_extension(self):
        with self.__lock:
            self.communication_port.write(b'WP\r')
            self.__read() # purge the \r


    def zero_load(self):
        with self.__lock:
            self.communication_port.write(b'WL\r')
            self.__read() # purge the \r
