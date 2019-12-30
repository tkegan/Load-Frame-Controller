#!/usr/bin/python3

# Import from Python Standard Library
from threading import Lock

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
        self.communication_port = Serial(communication_port_name, 19200, timeout=1)
        self.__lock = Lock()


    def __del__(self):
        if self.communication_port:
            self.stop_moving()
            self.communication_port.close()


    def __read(self):
        buffer = bytearray()
        while True:
            b = self.communication_port.read()
            if 1 > len(b) or 13 == b or 0 == b:
                break
            else:
                buffer.append(b)
        return str(buffer)


    def read_extension(self):
        with self.__lock:
            self.communication_port.write(b'RP\r')
            return self.__read()


    def read_load(self):
        with self.__lock:
            self.communication_port.write(b'RL\r')
            return self.__read()


    def read_load_cell_type(self):
        with self.__lock:
            self.communication_port.write(b'RC\r')
            return self.__read()


    def start_moving_up(self):
        with self.__lock:
            self.communication_port.write(b'WF\r')


    def start_moving_down(self):
        with self.__lock:
            self.communication_port.write(b'WR\r')


    def stop_moving(self):
        with self.__lock:
            self.communication_port.write(b'WS\r')


    def zero_extension(self):
        with self.__lock:
            self.communication_port.write(b'WP\r')


    def zero_load(self):
        with self.__lock:
            self.communication_port.write(b'WL\r')