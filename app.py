# -*- coding: utf-8 -*-
import sys
import re
import json

import time

import os
from PyQt4 import QtGui, QtCore
import paramiko
from PyQt4.QtGui import QFileDialog
from enum import Enum

import SerialThread
import androidutil
from ui import Ui_MainWindow
import _cffi_backend
import ConnectionThread

import sys

reload(sys)
sys.setdefaultencoding('utf-8')


# TODO 全选
# TODO 刷机失败时提示
# TODO 返回信息不全（没有预期的 finished 语句返回）导致进度显示失败

class MyApp(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.pushButtonOpenSerial.clicked.connect(self.open_serial)
        self.pushButtonCloseSerial.clicked.connect(self.close_serial)
        self.pushButtonReboot.clicked.connect(self.reboot_dev)
        self.pushButton2Fastboot.clicked.connect(self.adb2fastboot)
        self.pushButtonFirmwareDir.clicked.connect(self.select_firmware_dir)
        self.pushButtonFirmwareRefresh.clicked.connect(self.refresh_firmwares)
        self.pushButtonRefreshSerial.clicked.connect(self.init_serial)
        self.pushButtonCheckSum.clicked.connect(self.get_checked)
        self.pushButtonSelectAll.clicked.connect(self.check_all_y)
        self.pushButtonSelectAllCancell.clicked.connect(self.check_all_n)
        self.pushButtonFlash.clicked.connect(self.flash_firmware_start)
        self.cmdlineEdit.returnPressed.connect(self.run_cmd)
        self.actionExit.triggered.connect(self.close)
        self.text_browser_context_menu()
        self.serial_conn = SerialThread.Connection(self.log_append_msg, self.log_append_err, self.log_append_std)
        # json_file = open('shell.json')
        # self.shellJson = json.load(json_file, encoding='utf8')
        # json_file.close()
        self.flash = Flash()
        self.flash.signal_flash.connect(self.flash_firmware_info)
        self.init_serial()
        self.monitor_dev()
        self.init_table()

    def init_table(self):
        self.tableWidget.setColumnWidth(0, 20)
        self.tableWidget.setColumnWidth(1, 80)
        self.tableWidget.setColumnWidth(2, 300)
        self.tableWidget.setColumnWidth(3, 80)
        self.tableWidget.setColumnWidth(4, 80)
        self.tableWidget.setColumnWidth(5, 180)
        self.tableWidget.setColumnWidth(6, 80)

    def init_serial(self):
        ports, baudrates, parities, bytesizes, stopbits, flowcontrols = self.serial_conn.get_serial_cfg_available()
        self.comboBoxPorts.clear()
        self.comboBoxPorts.addItems(ports)
        self.comboBoxBaudrates.clear()
        self.comboBoxBaudrates.addItems(baudrates)
        self.comboBoxParities.clear()
        self.comboBoxParities.addItems(parities)
        self.comboBoxBytesizes.clear()
        self.comboBoxBytesizes.addItems(bytesizes)
        self.comboBoxStopbits.clear()
        self.comboBoxStopbits.addItems(stopbits)
        self.comboBoxFlowCtrl.clear()
        self.comboBoxFlowCtrl.addItems(flowcontrols)

    def run_cmd(self):
        cmd = self.cmdlineEdit.text()
        self.serial_conn.exe_cmd(cmd)
        self.cmdlineEdit.setText('')

    def connect_enable(self, stat):
        if stat:
            self.pushButtonCloseSerial.setEnabled(True)
        else:
            self.pushButtonOpenSerial.setEnabled(True)
            self.pushButtonCloseSerial.setEnabled(False)
        self.cmdlineEdit.setEnabled(stat)

    def open_serial(self):
        self.serial_conn.set_serial_cfg(self.comboBoxPorts.currentText(),
                                        self.comboBoxBaudrates.currentText(),
                                        self.comboBoxParities.currentText(),
                                        self.comboBoxBytesizes.currentText(),
                                        self.comboBoxStopbits.currentText(),
                                        self.comboBoxFlowCtrl.currentText())
        self.pushButtonOpenSerial.setEnabled(False)
        self.serial_conn.open(self.connect_enable)

    def close_serial(self):
        self.log_append_msg('Close...')
        self.serial_conn.close()
        self.log_append_msg('Closed.')
        self.pushButtonOpenSerial.setEnabled(True)
        self.pushButtonCloseSerial.setEnabled(False)
        self.cmdlineEdit.setEnabled(False)

    def init_devices(self):
        adbs = androidutil.list_adb()
        fastboots = androidutil.list_fastboot()
        self.comboBoxDevList.clear()
        self.comboBoxDevList.addItems(adbs)
        self.comboBoxDevList.addItems(fastboots)
        mode = self.get_dev_mode(adbs, fastboots)
        if 'adb' == mode:
            self.mode_adb_dis()
        elif 'fastboot' == mode:
            self.mode_fastboot_dis()
        else:
            self.mode_none()

    def get_dev_mode(self, adbs=None, fastboots=None):
        if adbs is None:
            adbs = androidutil.list_adb()
        if fastboots is None:
            fastboots = androidutil.list_fastboot()
        return androidutil.dev_mode(str(self.comboBoxDevList.currentText()), adbs, fastboots)

    def reboot_dev(self):
        mode = self.get_dev_mode()
        if mode == 'adb':
            androidutil.adb_reboot()

        elif mode == 'fastboot':
            androidutil.fastboot_reboot()
        else:
            self.show_warning(u'设备连接错误')

    def adb2fastboot(self):
        androidutil.adb2fastboot()

    def monitor_dev(self):
        self.monitor = DevMonitor()
        self.monitor.signal_refresh_dev.connect(self.init_devices)
        self.monitor.start()

    def mode_adb_dis(self):
        self.checkBoxAdb.setChecked(True)
        self.checkBoxFastboot.setChecked(False)
        self.pushButton2Fastboot.setEnabled(True)
        self.pushButtonFlash.setEnabled(False)
        self.pushButtonReboot.setEnabled(True)

    def mode_fastboot_dis(self):
        self.checkBoxAdb.setChecked(False)
        self.checkBoxFastboot.setChecked(True)
        self.pushButton2Fastboot.setEnabled(False)
        self.pushButtonFlash.setEnabled(True)
        self.pushButtonReboot.setEnabled(True)

    def mode_none(self):
        self.checkBoxAdb.setChecked(False)
        self.checkBoxFastboot.setChecked(False)
        self.pushButton2Fastboot.setEnabled(False)
        self.pushButtonFlash.setEnabled(False)
        self.pushButtonReboot.setEnabled(False)

    def mode_flash(self, flash):
        self.pushButtonFirmwareDir.setEnabled(not flash)
        self.pushButtonFirmwareRefresh.setEnabled(not flash)
        self.pushButtonCheckSum.setEnabled(not flash)

    def select_firmware_dir(self):
        self.lineEditFirmwareDir.setText(QFileDialog.getExistingDirectory(QtGui.QFileDialog(), u'选择固件位置', u'D:\work\GoFun\刷机\oem_sec_images'))
        self.refresh_firmwares()

    def get_firmware_list(self):
        rs = []
        dir = self.lineEditFirmwareDir.text()
        if not dir:
            return rs
        if not os.path.isfile(dir + os.path.sep  + 'list.txt'):
            return rs
        f = open(dir + os.path.sep  + 'list.txt')
        for l in iter(f):
            if l:
                la = l.strip().split()
                la[1] = dir + os.path.sep + la[1]
                rs.append(la)
        return rs

    def refresh_firmwares(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.clearContents()
        for r in self.get_firmware_list():
            rc = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rc)
            item = QtGui.QTableWidgetItem()
            item.setCheckState(QtCore.Qt.Unchecked)
            self.tableWidget.setItem(rc, 0, item)
            self.tableWidget.setItem(rc, 1, QtGui.QTableWidgetItem(unicode(str(r[0]))))
            self.tableWidget.setItem(rc, 2, QtGui.QTableWidgetItem(unicode(str(r[1]))))
            self.tableWidget.setItem(rc, 3, QtGui.QTableWidgetItem(unicode(str(r[2]))))

    def check_all_y(self):
        self.check_all(True)

    def check_all_n(self):
        self.check_all(False)

    def check_all(self, s):
        for i in range(0, self.tableWidget.rowCount()):
            self.tableWidget.item(i, 0).setCheckState(QtCore.Qt.Checked if s else QtCore.Qt.Unchecked)

    def get_checked(self):
        checkeds = []
        for i in range(0, self.tableWidget.rowCount()):
            item_ck = self.tableWidget.item(i, 0)
            if item_ck.checkState() == QtCore.Qt.Checked:
                checkeds.append((i, str(self.tableWidget.item(i, 1).text()), str(self.tableWidget.item(i, 2).text())))
        return checkeds

    def flash_firmware_start(self):
        checkeds = self.get_checked()
        if len(checkeds) == 0:
            self.show_warning(u'请至少选择一项')
            return
        for checked in checkeds:
            progress = QtGui.QProgressBar(self)
            progress.setAlignment(QtCore.Qt.AlignHCenter)
            progress.setMinimum(0)
            self.tableWidget.setCellWidget(checked[0], 5, progress)
        self.mode_flash(True)
        self.flash.set_checkeds(checkeds)
        self.flash.start()

    def flash_firmware_stop(self):
        self.flash.stop = True

    def flash_firmware_info(self, stage, status, msg):
        """
        :param stage: -1: unlock failed. other: index of firmware in the table.
        :param status: 0:normal, 1:success, -1:failed
        :param msg:
        :return:
        """
        if stage == -1:
            self.show_warning(u'解锁失败。')
            return
        if status == 1: # flash finished.
            self.mode_flash(False)
            self.flash_firmware_status(stage, True)
        elif status == -1:
            self.flash_firmware_status(stage, False)
        if not msg:
            return
        self.textBrowserFlash.append('<div>' + msg + '</div>')
        progress = self.tableWidget.cellWidget(stage, 5)
        if re.match(r'^target reported', msg):
            progress.setValue(0)
        elif re.match(r'^erasing', msg):
            progress.setValue(5)
        elif re.match(r'^sending sparse \'.*\' 1/3', msg):
            progress.setValue(10)
        elif re.match(r'^writing \'.*\' 1/3', msg):
            progress.setValue(25)
        elif re.match(r'^sending sparse \'.*\' 2/3', msg):
            progress.setValue(40)
        elif re.match(r'^writing \'.*\' 2/3', msg):
            progress.setValue(55)
        elif re.match(r'^sending sparse \'.*\' 3/3', msg):
            progress.setValue(70)
        elif re.match(r'^writing \'.*\' 3/3', msg):
            progress.setValue(85)
        elif re.match(r'^finished. total time', msg):
            progress.setValue(100)

    def flash_firmware_status(self, stage, s):
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignHCenter)
        if s:
            item.setText(u'成功')
            item.setBackgroundColor(QtCore.Qt.green)
        else:
            item.setText(u'失败')
            item.setBackgroundColor(QtCore.Qt.red)
        self.tableWidget.setItem(stage, 6, item)
#############################################################################################

    def dis_connect_dev(self):
        self.ssh_client.close()
        self.log_append_msg(u'Disconnected.')

    def log_append(self, log, color=None):
        if color:
            __log = '<div style="color: ' + str(color) + ';">' + log + '</div>'
        else:
            __log = log
        self.textBrowserLog.append(__log)

    def log_clear(self):
        self.textBrowserLog.clear()

    def log_append_msg(self, msg):
        self.log_append(msg, 'blue')

    def log_append_err(self, err):
        self.log_append(err, 'red')

    def log_append_std(self, std):
        self.log_append(std)

    def exe_cmd(self, cmd):
        self.log_append('> ' + cmd, 'green')
        return self.ssh_client.exec_command(cmd)

    def show_warning(self, warn):
        warn_dialog = QtGui.QErrorMessage()
        warn_dialog.showMessage(warn)
        warn_dialog.setWindowTitle(u"错误")
        warn_dialog.exec_()

    def text_browser_context_menu(self):
        """
        设置日志窗口右键菜单
        :return:
        """
        action_clear = QtGui.QAction(self)
        action_clear.setText(u'清空')
        action_clear.triggered.connect(self.log_clear)
        action_dump = QtGui.QAction(self)
        action_dump.setText(u'导出日志记录')
        action_dump.triggered.connect(self.log_dump)
        self.textBrowserLog.addAction(action_clear)
        # self.textBrowserLog.addAction(action_dump)

    def log_dump(self):
        file_path = QtGui.QFileDialog.getSaveFileName(self, u'导出文件', 'log', '(*.*)')
        log_file = open(file_path, 'w')


class DevMonitor(QtCore.QThread):
    __adbs = None
    __fastboots = None
    signal_refresh_dev = QtCore.pyqtSignal()

    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        while True:
            adbs = androidutil.list_adb()
            fastboots = androidutil.list_fastboot()
            need_refresh = False
            if self.__adbs != adbs:
                self.__adbs = adbs
                need_refresh |= True
            if self.__fastboots != fastboots:
                self.__fastboots = fastboots
                need_refresh |= True
            if need_refresh:
                self.signal_refresh_dev.emit()
            time.sleep(0.25)


class FirmwareType(object):
    """支持的类型，防止列表文件修改错误造成刷机问题"""
    SBL1 = 'sbl1'
    RPM = 'rpm'
    TZ = 'tz'
    ABOOT = 'aboot'
    SBL1BAK = 'sbl1bak'
    RPMBAK = 'rpmbak'
    TZBAK = 'tzbak'
    ABOOTBAK = 'abootbak'
    BOOT = 'boot'
    SPLASH = 'splash'
    SEC = 'sec'
    MODEM = 'modem'
    SYSTEM = 'system'
    USERDATA = 'userdata'
    PERSIST = 'persist'
    CACHE = 'cache'
    RECOVERY = 'recovery'
    PRIVDATA1 = 'privdata1'
    PRIVDATA2 = 'privdata2'

    __map = {
        'sbl1': SBL1,
        'rpm': RPM,
        'tz': TZ,
        'aboot': ABOOT,
        'sbl1bak': SBL1BAK,
        'rpmbak': RPMBAK,
        'tzbak': TZBAK,
        'abootbak': ABOOTBAK,
        'boot': BOOT,
        'splash': SPLASH,
        'sec': SEC,
        'modem': MODEM,
        'system': SYSTEM,
        'userdata': USERDATA,
        'persist': PERSIST,
        'cache': CACHE,
        'recovery': RECOVERY,
        'privdata1': PRIVDATA1,
        'privdata2': PRIVDATA2
    }

    @classmethod
    def of(cls, v):
        return cls.__map.get(v)


class Flash(QtCore.QThread):
    signal_flash = QtCore.pyqtSignal(int, int, str)
    stop = False
    __cur_key = 0
    def __init__(self):
        QtCore.QThread.__init__(self)

    def set_checkeds(self, checkeds):
        self.checkeds = checkeds

    def send_msg(self, msg):
        self.signal_flash.emit(self.__cur_key, 0, msg)

    def __flash_unlock(self):
        count = 10
        while count > 0:
            count -= 1
            pass_c, pass_s = androidutil.exe_fastboot('oem passwd TdrGofun@0129')
            if pass_c == 0:
                unlock_c, unlock_s = androidutil.exe_fastboot('oem unlock-go')
                if unlock_c == 0:
                    count = -1
                    continue
            time.sleep(0.25)
        return count == -1

    def __flash_lock(self):
        count = 10
        while count > 0:
            count -= 1
            shipment_c, shipment_s = androidutil.exe_fastboot('oem shipment TdrGofun@0129')
            if shipment_c == 0:
                lock_c, lock_s = androidutil.exe_fastboot('oem lock')
                if lock_c == 0:
                    count = -1
                    continue
            time.sleep(0.25)
        return count == -1

    def run(self):
        self.stop = False
        self.__cur_key = 0
        if not self.__flash_unlock():
            self.signal_flash.emit(-1, 0, 'Unlock failed.')
            return
        for checked in self.checkeds:
            if self.stop:
                return
            self.__cur_key = checked[0]
            self.signal_flash.emit(self.__cur_key, 0, 'Flash ' + checked[1])
            tp = FirmwareType.of(checked[1])
            if tp is None:
                continue
            rc, rv = androidutil.flash(tp, checked[2], self.send_msg)
            if rc != 0:
                self.signal_flash.emit(self.__cur_key, -1, 'Flash failed.')
            else:
                self.signal_flash.emit(self.__cur_key, 1, 'Flash success.')
        if not self.__flash_lock():
            self.signal_flash.emit(-1, 0, 'Lock failed.')



def main():
    app = QtGui.QApplication(sys.argv)
    window = MyApp()
    window.setWindowTitle(u'GoFun工具 V0.1')
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
