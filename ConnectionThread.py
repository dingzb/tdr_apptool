import paramiko
from PyQt4 import QtCore

__version__ = '0.1'


class Connection:

    def __init__(self, ssh_client, signal_msg_handler, signal_err_handler, signal_std_handler):
        """

        :param ssh_client:
        :param signal_msg_handler: normal str
        :param signal_err_handler: error str
        :param signal_std_handler: stdout, stderr str
        """
        self.__ssh_client = ssh_client
        self.__signal_msg_handler = signal_msg_handler
        self.__signal_err_handler = signal_err_handler
        self.__signal_std_handler = signal_std_handler

    def __set_base_signal(self, target):
        target.signal_msg.connect(self.__signal_msg_handler)
        target.signal_err.connect(self.__signal_err_handler)
        target.signal_std.connect(self.__signal_std_handler)

    def open(self, signal_success_handler, hostname, port, username, password):
        self.__openThread = Open(self.__ssh_client, hostname, port, username, password)
        self.__set_base_signal(self.__openThread)
        self.__openThread.signal_success.connect(signal_success_handler)
        self.__openThread.start()


class Base(QtCore.QThread):
    signal_msg = QtCore.pyqtSignal(str)
    signal_err = QtCore.pyqtSignal(str)
    signal_std = QtCore.pyqtSignal(str)
    sshClient = paramiko.SSHClient()

    def __init__(self, ssh_client):
        QtCore.QThread.__init__(self)
        self.ssh_client = ssh_client


class Open(Base):
    signal_success = QtCore.pyqtSignal(bool)

    def __init__(self, ssh_client, hostname, port, username, password):
        Base.__init__(self, ssh_client)
        self.__hostname = hostname
        self.__port = port
        self.__username = username
        self.__password = password

    def run(self):
        self.signal_msg.emit(str.format('Connect to {:s}:{:d}...', str(self.__hostname), int(self.__port)))
        try:
            self.ssh_client.connect(self.__hostname, self.__port, self.__username, self.__password)
            self.signal_msg.emit('Connect success.')
            self.signal_success.emit(True)
        except Exception, e:
            self.signal_err.emit(str(e))
            self.signal_success.emit(False)
