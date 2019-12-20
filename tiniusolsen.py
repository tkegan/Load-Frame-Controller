#!/usr/bin/python3

# Import from third party libraries
from serial import Serial


class TiniusOlsen:
    '''
    A class for communicating with Tinius Olsen Load Frames which expose a
    RS232 serial port for control.
    
    License: Apache 2.0 License (See Also LICENSE file included in the git
    repository where this file is found)
    
    @author Tom Egan <tegan@bucknell.edu> for Bucknell University 
    '''

    def __init__(self, communication_port_name):
        '''
        @throws 
        '''
        self.communication_port = Serial(communication_port_name, 19200, timeout=1)


    def _read(self):
        buffer = bytearray()
        while True:
            b = self.communication_port.read()
            if 1 > len(b) or 13 == b or 0 == b:
                break
            else:
                buffer.append(b)
        return str(buffer)


    def read_extension(self):
        self.communication_port.write(b'RP\r')
        return self._read()


    def read_load(self):
        self.communication_port.write(b'RL\r')
        return self._read()


    def read_load_cell_type(self):
        self.communication_port.write(b'RC\r')
        return self._read()


    def start_moving_up(self):
        self.communication_port.write(b'WF\r')


    def start_moving_down(self):
        self.communication_port.write(b'WR\r')


    def stop_moving(self):
        self.communication_port.write(b'WS\r')


    def zero_extension(self):
        self.communication_port.write(b'WP\r')


    def zero_load(self):
        self.communication_port.write(b'WL\r')