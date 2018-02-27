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


# TODO 刷机时传入刷机线程(firmware_path, slot)
# TODO 刷机动画

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
        self.pushButtonFlash.clicked.connect(self.flash_firmware_start)
        #######################################################################
        # self.pushButtonSaveServer.clicked.connect(self.set_server)
        # self.pushButtonRefreshServer.clicked.connect(self.get_server_cfg)
        # self.pushButtonRefreshInfo.clicked.connect(self.get_info)
        # self.pushButtonWanRefresh.clicked.connect(self.get_network_wan_cfg)
        # self.pushButtonWanSave.clicked.connect(self.set_network_wan_cfg)
        # self.radioButtonWanStatic.toggled.connect(self.set_network_wan_static_enable)
        # self.pushButtonLanRefresh.clicked.connect(self.get_network_lan_cfg)
        # self.pushButtonLanSave.clicked.connect(self.set_network_lan_cfg)
        self.cmdlineEdit.returnPressed.connect(self.run_cmd)
        # self.actionExit.triggered.connect(self.close)
        self.text_browser_context_menu()
        # self.ssh_client = paramiko.SSHClient()
        # self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # self.connection = ConnectionThread.Connection(self.ssh_client, self.log_append_msg, self.log_append_err, self.log_append_std)
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

    def select_firmware_dir(self):
        self.lineEditFirmwareDir.setText(QFileDialog.getExistingDirectory(QtGui.QFileDialog(), u'选择固件位置', u'D:\work\GoFun\刷机'))
        self.refresh_firmwares()

    def get_frimwar_list(self, dir=None):
        """这里暂时根据文件后缀筛选，后期考虑根据校验文件的固件列表获取文件并校验"""
        rs = []
        system_img = FirmwareType.SYSTEM.value
        boot_img = FirmwareType.BOOT.value
        if dir is None:
            dir = self.lineEditFirmwareDir.text()
        if not dir:
            return rs
        rs.append((system_img, 'D:\\work\\GoFun\\system.img', '1.0'))
        rs.append((boot_img, 'D:\\work\\GoFun\\boot.img', '1.0'))
        # for f_n in os.listdir(dir):
        #     if system_img in f_n:
        #         rs.append((system_img, dir + '\\' + f_n, '1.0'))
        #     elif boot_img in f_n:
        #         rs.append((boot_img, dir + '\\' + f_n, '1.0'))
        return rs

    def refresh_firmwares(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.clearContents()
        for r in self.get_frimwar_list():
            rc = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rc)
            item = QtGui.QTableWidgetItem()
            item.setCheckState(QtCore.Qt.Unchecked)
            self.tableWidget.setItem(rc, 0, item)
            self.tableWidget.setItem(rc, 1, QtGui.QTableWidgetItem(unicode(str(r[0]))))
            self.tableWidget.setItem(rc, 2, QtGui.QTableWidgetItem(unicode(str(r[1]))))
            self.tableWidget.setItem(rc, 3, QtGui.QTableWidgetItem(unicode(str(r[2]))))

    def get_checked(self):
        checkeds = []
        for i in range(0, self.tableWidget.rowCount()):
            item_ck = self.tableWidget.item(i, 0)
            if item_ck.checkState() == QtCore.Qt.Checked:
                checkeds.append((i, str(self.tableWidget.item(i, 1).text()), str(self.tableWidget.item(i, 2).text())))
        return checkeds

    def flash_firmware_start(self):
        checkeds = self.get_checked()
        for checked in checkeds:
            progress = QtGui.QProgressBar(self)
            progress.setAlignment(QtCore.Qt.AlignHCenter)
            progress.setMinimum(0)
            self.tableWidget.setCellWidget(checked[0], 5, progress)
        time.sleep(0.01) # table设置进度条和刷机都是多线程进行的，要保证进度条设置完成后在开始刷机
        self.flash.set_checkeds(checkeds)
        self.flash.start()

    def flash_firmware_stop(self):
        self.flash.stop = True

    def flash_firmware_info(self, stage, msg):
        if not msg:
            return
        self.textBrowserFlash.append('<div style="color: red;">' + msg + '</div>')
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
    ########################################################################################################

    def info_append(self, info):
        """附件内容到详情"""
        self.textBrowserInfo.append(str(info))

    def info_clear(self):
        """清空详情内容"""
        self.textBrowserInfo.clear()

    def fill_server_cfg(self, info):
        """填充服务器配置表单"""
        kvs = info.split('\n')
        for i, kv in enumerate(kvs):
            kvs[i] = kv.split('=')
        ks = self.shellJson.get('keys').get('setting').get('server')
        u_ip = self.get_cfg_f_tuple(ks.get('upgradeIp'), kvs)
        u_port = self.get_cfg_f_tuple(ks.get('upgradePort'), kvs)
        o_ip = self.get_cfg_f_tuple(ks.get('operationIp'), kvs)
        o_port = self.get_cfg_f_tuple(ks.get('operationPort'), kvs)
        i_ip = self.get_cfg_f_tuple(ks.get('idcardIp'), kvs)
        i_port = self.get_cfg_f_tuple(ks.get('idcardPort'), kvs)
        l_url = self.get_cfg_f_tuple(ks.get('logsrvUrl'), kvs)
        self.LineEditUpdateIp.setText(u_ip)
        self.LineEditUpdatePort.setText(u_port)
        self.LineEditOperationIp.setText(o_ip)
        self.LineEditOperationPort.setText(o_port)
        self.LineEditIdCardIp.setText(i_ip)
        self.LineEditIdCardPort.setText(i_port)
        self.LineEditLogURL.setText(l_url)

    def get_cfg_f_tuple(self, k, kvs):
        """
        从Tuple数组中获取服务器配置信息
        :param k: key
        :param kvs: tuple array
        :return: kv[1]
        """
        for kv in kvs:
            if kv[0] == k:
                return kv[1].replace("'", "")

    def set_server(self):
        """设置服务器配置"""
        vr = self.validate_server_cfg()
        if not vr[0]:
            self.show_warning(vr[1])
            return
        settings = vr[1]
        cmd = str(self.shellJson.get('setting').get('server').get('set'))
        ks = self.shellJson.get('keys').get('setting').get('server')
        self.exe_cmd(str.format(cmd, ks.get('operationIp'), str(settings[0])))
        self.exe_cmd(str.format(cmd, ks.get('operationPort'), str(settings[1])))
        self.exe_cmd(str.format(cmd, ks.get('upgradeIp'), str(settings[2])))
        self.exe_cmd(str.format(cmd, ks.get('upgradePort'), str(settings[3])))
        self.exe_cmd(str.format(cmd, ks.get('idcardIp'), str(settings[4])))
        self.exe_cmd(str.format(cmd, ks.get('idcardPort'), str(settings[5])))
        self.exe_cmd(str.format(cmd, ks.get('logsrvUrl'), str(settings[6])))
        self.exe_cmd(self.shellJson.get('setting').get('server').get('commit'))
        self.show_status_bar_msg(u'配置生效需要重启')

    def validate_server_cfg(self):
        """校验服务器配置有效性"""
        o_ip = self.LineEditOperationIp.text()
        o_port = self.LineEditOperationPort.text()
        u_ip = self.LineEditUpdateIp.text()
        u_port = self.LineEditUpdatePort.text()
        i_ip = self.LineEditIdCardIp.text()
        i_port = self.LineEditIdCardPort.text()
        l_url = self.LineEditLogURL.text()
        if not self.validate_ip(o_ip):
            return False, u'业务服务器IP格式错误'
        if not self.validate_port(o_port):
            return False, u'业务服务器端口格式错误'
        if not self.validate_ip(u_ip):
            return False, u'升级服务器IP格式错误'
        if not self.validate_port(u_port):
            return False, u'升级服务器端口格式错误'
        if not self.validate_ip(i_ip):
            return False, u'身份证服务器IP格式错误'
        if not self.validate_port(i_port):
            return False, u'身份证服务器端口格式错误'
        if not self.validate_url(l_url):
            return False, u'日志服务器URL格式错误'
        return True, (o_ip, o_port, u_ip, u_port, i_ip, i_port, l_url)

    def re_boot(self):
        self.exe_cmd('reboot')
        self.dis_connect_dev()
        self.connect_enable(False)

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

    def validate_ip(self, ip):
        pattern = r'^(?:(?:1[0-9][0-9]\.)|(?:2[0-4][0-9]\.)|(?:25[0-5]\.)|(?:[1-9][0-9]\.)|(?:[0-9]\.)){3}(?:(?:1[0-9][0-9])|(?:2[0-4][0-9])|(?:25[0-5])|(?:[1-9][0-9])|(?:[0-9]))$'
        return re.match(pattern, str(ip))

    def validate_port(self, port):
        pattern = r'^\d{2,5}$'
        return re.match(pattern, str(port))

    def validate_url(self, url):
        pattern = r'((https?|ftp|file)://)?[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]'
        return re.match(pattern, str(url))

    def validate_mask(self, mask):
        pattern = r'^(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])(\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])){3}$'
        return re.match(pattern, str(mask))

    def show_warning(self, warn):
        warn_dialog = QtGui.QErrorMessage()
        warn_dialog.showMessage(warn)
        warn_dialog.setWindowTitle(u"错误")
        warn_dialog.exec_()

    def show_status_bar_msg(self, msg):
        self.statusBar.showMessage(msg)

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


class Flash(QtCore.QThread):
    signal_flash = QtCore.pyqtSignal(int, str)
    stop = False
    __cur_key = 0
    def __init__(self):
        QtCore.QThread.__init__(self)

    def set_checkeds(self, checkeds):
        self.checkeds = checkeds

    def send_msg(self, msg):
        self.signal_flash.emit(self.__cur_key, msg)

    def run(self):
        self.stop = False
        self.__cur_key = 0
        for checked in self.checkeds:
            if self.stop:
                return
            self.__cur_key = checked[0]
            self.signal_flash.emit(self.__cur_key, 'Flash ' + checked[1])
            androidutil.flash(FirmwareType(checked[1]).value, checked[2], self.send_msg)


class FirmwareType(Enum):
    SYSTEM = 'system'
    BOOT = 'boot'


def main():
    app = QtGui.QApplication(sys.argv)
    window = MyApp()
    window.setWindowTitle(u'GoFun工具 V0.1')
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
