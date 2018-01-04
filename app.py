# -*- coding: utf-8 -*-
import sys
import re
import json
from PyQt4 import QtGui
import paramiko
from ui import Ui_MainWindow
import _cffi_backend
import ConnectionThread


class MyApp(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.pushButtonConnect.clicked.connect(self.connect_dev)
        self.pushButtonReboot.clicked.connect(self.re_boot)
        self.pushButtonSaveServer.clicked.connect(self.set_server)
        self.pushButtonRefreshServer.clicked.connect(self.get_server_cfg)
        self.pushButtonRefreshInfo.clicked.connect(self.get_info)
        self.pushButtonWanRefresh.clicked.connect(self.get_network_wan_cfg)
        self.pushButtonWanSave.clicked.connect(self.set_network_wan_cfg)
        self.radioButtonWanStatic.toggled.connect(self.set_network_wan_static_enable)
        self.pushButtonLanRefresh.clicked.connect(self.get_network_lan_cfg)
        self.pushButtonLanSave.clicked.connect(self.set_network_lan_cfg)
        self.cmdlineEdit.returnPressed.connect(self.run_cmd)
        self.actionExit.triggered.connect(self.close)
        self.text_browser_context_menu()
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connection = ConnectionThread.Connection(self.ssh_client, self.log_append_msg, self.log_append_err, self.log_append_std)
        json_file = open('shell.json')
        self.shellJson = json.load(json_file, encoding='utf8')
        json_file.close()

    def run_cmd(self):
        cmd = self.cmdlineEdit.text()
        stdin, stdout, stderr = self.exe_cmd(str(cmd))
        self.log_append_std(u''.join(stderr.readlines()))
        self.log_append_std(u''.join(stdout.readlines()))
        self.cmdlineEdit.setText('')

    def connect_enable(self, stat):
        if stat:
            self.pushButtonConnect.setText(u'已连接')
        else:
            self.pushButtonConnect.setText(u'连接')
            self.pushButtonConnect.setEnabled(True)
        self.pushButtonReboot.setEnabled(stat)
        self.tabWidget.setEnabled(stat)
        self.cmdlineEdit.setEnabled(stat)
        pass

    def connect_dev(self):
        self.pushButtonConnect.setEnabled(False)
        self.pushButtonConnect.setText(u'连接...')
        self.connection.open(self.connect_enable, str(self.lineEditIp.text()), int(self.lineEditPort.text()),
                             str(self.lineEditUsername.text()), str(self.lineEditPassword.text()))

    def get_network_lan_cfg(self):
        """获取lan网络配置"""
        cmd = self.shellJson.get('setting').get('network').get('lan').get('get')
        stdin, stdout, stderr = self.exe_cmd(cmd)
        network_lan_cfg_str = stdout.read()
        self.fill_newtork_lan_cfg(network_lan_cfg_str)
        return network_lan_cfg_str

    def set_network_lan_cfg(self):
        """设置lan网络配置"""
        vn = self.validate_network_lan_cfg()
        if not vn[0]:
            self.show_warning(vn[1])
            return
        settings = vn[1]
        cmd = str(self.shellJson.get('setting').get('network').get('lan').get('set'))
        ks = self.shellJson.get('keys').get('setting').get('network').get('lan')
        self.exe_cmd(str.format(cmd, ks.get('ip'), str(settings[0])))
        self.exe_cmd(str.format(cmd, ks.get('mask'), str(settings[1])))
        self.exe_cmd(self.shellJson.get('setting').get('network').get('lan').get('commit'))

    def validate_network_lan_cfg(self):
        """校验wan网络配置有效性"""
        ip = self.lineEditLanIp.text()
        mask = self.lineEditLanMask.text()
        if not self.validate_ip(ip):
            return False, u'IP地址格式错误'
        if not self.validate_mask(mask):
            return False, u'子网掩码格式错误'
        return True, (ip, mask)

    def fill_newtork_lan_cfg(self, info):
        """填充lan网络配置"""
        kvs = info.split('\n')
        for i, kv in enumerate(kvs):
            kvs[i] = kv.split('=')
        ks = self.shellJson.get('keys').get('setting').get('network').get('lan')
        name = self.get_cfg_f_tuple(ks.get('name'), kvs)
        ip = self.get_cfg_f_tuple(ks.get('ip'), kvs)
        mask = self.get_cfg_f_tuple(ks.get('mask'), kvs)
        self.labelLanName.setText(name)
        self.lineEditLanIp.setText(str(ip))
        self.lineEditLanMask.setText(str(mask))

    def get_network_wan_cfg(self):
        """获取wan网络配置"""
        cmd = self.shellJson.get('setting').get('network').get('wan').get('get')
        stdin, stdout, stderr = self.exe_cmd(cmd)
        network_wan_cfg_str = stdout.read()
        self.fill_newtork_wan_cfg(network_wan_cfg_str)
        return network_wan_cfg_str

    def set_network_wan_cfg(self):
        """设置wan配置"""
        vn = self.validate_network_wan_cfg()
        if not vn[0]:
            self.show_warning(vn[1])
            return
        settings = vn[1]
        cmd = str(self.shellJson.get('setting').get('network').get('wan').get('set'))
        ks = self.shellJson.get('keys').get('setting').get('network').get('wan')
        self.exe_cmd(str.format(cmd, ks.get('proto'), str(settings[0])))
        if str(settings[0]) == 'static':
            self.exe_cmd(str.format(cmd, ks.get('ip'), str(settings[1])))
            self.exe_cmd(str.format(cmd, ks.get('mask'), str(settings[2])))
            self.exe_cmd(str.format(cmd, ks.get('gateway'), str(settings[3])))
        self.exe_cmd(self.shellJson.get('setting').get('network').get('wan').get('commit'))
        self.show_status_bar_msg(u'配置生效需要重启')

    def validate_network_wan_cfg(self):
        """校验wan网络配置有效性"""
        proto = 'static' if self.radioButtonWanStatic.isChecked() else 'dhcp'
        ip = self.lineEditWanIp.text()
        mask = self.lineEditWanMask.text()
        gateway = self.lineEditWanGateway.text()
        if proto == 'dhcp':
            return True, (proto,)
        else:
            if not self.validate_ip(ip):
                return False, u'IP地址格式错误'
            if not self.validate_mask(mask):
                return False, u'子网掩码格式错误'
            if not self.validate_ip(gateway):
                return False, u'网关地址格式错误'
            return True, (proto, ip, mask, gateway)

    def fill_newtork_wan_cfg(self, info):
        """填充wan网络配置"""
        kvs = info.split('\n')
        for i, kv in enumerate(kvs):
            kvs[i] = kv.split('=')
        ks = self.shellJson.get('keys').get('setting').get('network').get('wan')
        name = self.get_cfg_f_tuple(ks.get('name'), kvs)
        proto = self.get_cfg_f_tuple(ks.get('proto'), kvs)
        ip = self.get_cfg_f_tuple(ks.get('ip'), kvs)
        mask = self.get_cfg_f_tuple(ks.get('mask'), kvs)
        gateway = self.get_cfg_f_tuple(ks.get('gateway'), kvs)
        self.labelWanName.setText(name)
        self.radioButtonWanStatic.setChecked('static' == proto)
        self.radioButtonWanAuto.setChecked('dhcp' == proto)
        if 'static' == proto:
            self.lineEditWanIp.setText(str(ip))
            self.lineEditWanMask.setText(str(mask))
            self.lineEditWanGateway.setText(str(gateway))
        else:
            self.set_network_wan_static_enable(False)

    def set_network_wan_static_enable(self, enable):
        self.lineEditWanIp.setEnabled(enable)
        self.lineEditWanMask.setEnabled(enable)
        self.lineEditWanGateway.setEnabled(enable)

    def get_server_cfg(self):
        """获取服务器配置"""
        cmd = self.shellJson.get('setting').get('server').get('get')
        stdin, stdout, stderr = self.exe_cmd(cmd)
        server_cfg_str = stdout.read()
        self.fill_server_cfg(server_cfg_str)
        return server_cfg_str

    def get_info(self):
        """获取设备信息"""
        self.info_clear()
        cmd = self.shellJson.get('info').get('network')
        stdin, stdout, stderr = self.exe_cmd(cmd)
        self.info_append('<================================ network =====================================>')
        self.info_append(stdout.read())
        cmd = self.shellJson.get('info').get('version')
        stdin, stdout, stderr = self.exe_cmd(cmd)
        self.info_append('<================================ version =====================================>')
        self.info_append(stdout.read())
        cmd = self.shellJson.get('info').get('usb')
        stdin, stdout, stderr = self.exe_cmd(cmd)
        self.info_append('<================================= usb ========================================>')
        self.info_append(stdout.read())

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
        file_path = QtGui.QFileDialog.getSaveFileName(self,u'导出文件','log' ,'(*.*)')
        log_file = open(file_path, 'w')


def main():
    app = QtGui.QApplication(sys.argv)
    window = MyApp()
    window.setWindowTitle(u'门禁工具 V0.1')
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
