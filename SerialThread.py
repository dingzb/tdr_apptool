# coding=utf-8
import paramiko
import serial
from PyQt4 import QtCore

__version__ = '0.1'


class Connection:
    __ports = []
    __baudrates = []
    __parities = {'None': serial.PARITY_NONE, 'Even': serial.PARITY_EVEN, 'Odd': serial.PARITY_ODD, 'Mark': serial.PARITY_MARK, 'Space': serial.PARITY_SPACE}
    __parities_names = ['None', 'Even', 'Odd', 'Mark', 'Space']
    __bytesizes = {'5': serial.FIVEBITS, '6': serial.SIXBITS, '7': serial.SEVENBITS, '8': serial.EIGHTBITS}
    __bytesizes_names = ['8' , '7' , '6', '5']
    __stopbits = {'1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE, '2': serial.STOPBITS_TWO}
    __stopbits_names = ['1', '1.5', '2']
    __flowcontrols = ['None', 'XON/XOFF', 'RTS/CTS', 'DSR/DTR']

    def __init__(self, signal_msg_handler, signal_err_handler, signal_std_handler):
        """

        :param signal_msg_handler: normal str
        :param signal_err_handler: error str
        :param signal_std_handler: stdout, stderr str
        """
        self.__serial_conn = serial.Serial()
        self.__signal_msg_handler = signal_msg_handler
        self.__signal_err_handler = signal_err_handler
        self.__signal_std_handler = signal_std_handler

    def __set_base_signal(self, target):
        target.signal_msg.connect(self.__signal_msg_handler)
        target.signal_err.connect(self.__signal_err_handler)
        target.signal_std.connect(self.__signal_std_handler)

    def open(self, signal_success_handler):
        self.__openThread = Open(self.__serial_conn)
        self.__set_base_signal(self.__openThread)
        self.__openThread.signal_success.connect(signal_success_handler)
        self.__openThread.start()

    def close(self):
        if self.__openThread:
            self.__openThread.monitor = False
        self.__serial_conn.close()

    def exe_cmd(self, cmd):
        self.__serial_conn.write((str(cmd) + '\n\n').encode())

    def __init_serial_cfg(self):
        self.__ports = []
        import serial.tools.list_ports
        # ports
        plist = list(serial.tools.list_ports.comports())
        for pc in plist:
            p = list(pc)
            self.__ports.append(p[0])
        # baudrates
        self.__baudrates = self.__serial_conn.BAUDRATES

    def get_serial_cfg_available(self):
        self.__init_serial_cfg()
        return (self.__ports, map(str, self.__baudrates), self.__parities_names, self.__bytesizes_names, self.__stopbits_names, self.__flowcontrols)

    def set_serial_cfg(self, port, baudrate, parity, bytesize, stopbits, flowcontrol):
        self.__serial_conn.port = str(port)
        self.__serial_conn.baudrate = int(baudrate)

        self.__serial_conn.parity = self.__parities.get(str(parity))
        self.__serial_conn.bytesize = self.__bytesizes.get(str(bytesize))
        self.__serial_conn.stopbits = self.__stopbits.get(str(stopbits))
        if flowcontrol == 'XON/XOFF':
            self.__serial_conn.xonxoff = True
        elif flowcontrol == 'RTS/CTS':
            self.__serial_conn.rtsct = True
        elif flowcontrol == 'DSR/DTR':
            self.__serial_conn.dsrdtr = True

class Base(QtCore.QThread):
    signal_msg = QtCore.pyqtSignal(str)
    signal_err = QtCore.pyqtSignal(str)
    signal_std = QtCore.pyqtSignal(str)

    def __init__(self, serial_conn):
        QtCore.QThread.__init__(self)
        self.serial_conn = serial_conn


class Open(Base):
    """Open and monitor the serial."""
    signal_success = QtCore.pyqtSignal(bool)
    monitor = True

    def __init__(self, serial_conn):
        Base.__init__(self, serial_conn)

    def run(self):
        self.signal_msg.emit(str.format('Open {:s}:{:d}...', str(self.serial_conn.port), int(self.serial_conn.baudrate)))
        try:
            self.serial_conn.open()
            self.serial_conn.write('\n\n')
            self.signal_msg.emit('Open success.')
            self.signal_success.emit(True)
            while self.monitor:
                str1 = self.serial_conn.readline()
                self.signal_msg.emit(str1)
        except Exception, e:
            print e
            self.signal_err.emit(str(e))
            self.signal_success.emit(False)


class Monitor(Base):
    monitor = True
    def __init__(self, serial_conn):
        Base.__init__(self, serial_conn)

    def run(self):
        try:
            while self.monitor:
                self.signal_msg.emit(self.serial_conn.readline(10))
        except Exception, e:
            print e
            self.signal_err.emit(str(e))
