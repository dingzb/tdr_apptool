# -*- coding: utf-8 -*-
import binascii
import os

import sys
import re

reload(sys)
import json
import paramiko
from ui import *

target_user = 'root'
target_port = 22
target_passwd = 't0d7r19tdr'


class MyApp(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.ConnectButton.clicked.connect(self.connect_dev)
        self.connectStat = False
        self.pushButtonSaveServer.clicked.connect(self.set_server)
        self.pushButtonRefreshServer.clicked.connect(self.get_server_cfg)
        self.pushButtonRefreshInfo.clicked.connect(self.get_info)
        self.pushButtonWanRefresh.clicked.connect(self.get_network_wan_cfg)
        self.pushButtonWanSave.clicked.connect(self.set_network_wan_cfg)
        self.radioButtonWanStatic.toggled.connect(self.set_network_wan_static_enable)
        self.pushButtonLanRefresh.clicked.connect(self.get_network_lan_cfg)
        self.pushButtonLanSave.clicked.connect(self.set_network_lan_cfg)
        self.cmdlineEdit.returnPressed.connect(self.run_cmd)
        self.sshClient = paramiko.SSHClient()
        self.sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        with open('shell.json') as jsonFile:
            self.shellJson = json.load(jsonFile, encoding='utf8')

    def run_cmd(self):
        cmd = self.cmdlineEdit.text()
        stdin, stdout, stderr = self.exe_cmd(str(cmd))
        self.log_append(u''.join(stderr.readlines()))
        self.log_append(u''.join(stdout.readlines()))
        self.cmdlineEdit.setText('')

    def connect_enable(self, stat):
        self.tabWidget.setEnabled(True)
        self.cmdlineEdit.setEnabled(True)
        pass

    def connect_dev(self):
        self.log_append(str.format('Connect to {:s}:{:d} ...', str(self.lineEditIp.text()), int(self.lineEditPort.text())))
        try:
            self.sshClient.connect(str(self.lineEditIp.text()), int(self.lineEditPort.text()), str(self.lineEditUsername.text()), str(self.lineEditPassword.text()))
            self.log_append(str.format('Connected.'))
            self.setWindowTitle(str(self.lineEditIp.text()))
            self.connect_enable(stat=True)
        except Exception, e:
            print(str(e))

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

    def validate_server_cfg(self):
        """校验服务器配置有效性"""
        o_ip = self.LineEditOperationIp.text()
        o_port = self.LineEditOperationPort.text()
        u_ip =self.LineEditUpdateIp.text()
        u_port = self.LineEditUpdatePort.text()
        i_ip = self.LineEditIdCardIp.text()
        i_port = self.LineEditIdCardPort.text()
        l_url  = self.LineEditLogURL.text()
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

    def log_append(self, log):
        self.logEdit.append(log)

    def exe_cmd(self, cmd):
        self.log_append('===> ' + cmd)
        return self.sshClient.exec_command(cmd)

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
    ###############################################################################################

    def show_warning(self, warn):
        warn_dialog = QtGui.QErrorMessage()
        warn_dialog.showMessage(warn)
        warn_dialog.setWindowTitle(u"错误")
        warn_dialog.exec_()

    def GetInfo(self):
        # enable ssh is cancelled
        # if self.EnableSshThread.stopped == True:
        #     return

        # get a ssh client
        # self.sshClient = paramiko.SSHClient()
        # self.sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # target_port = 22
        # try:
        #     self.sshClient.connect(str(self.lineEditIp.text()), int(self.lineEditPort.text()), str(self.lineEditUsername.text()), str(self.lineEditPassword.text()))
        # except Exception, e:
        #     print(str(e))
        #     pass
            # target_port = 22122
            # self.sshClient.connect(str(self.targetIp), target_port, target_user, target_passwd)

        # self.logEdit.append('SSH Connect %s:%d!' % (str(self.lineEditIp.text()), int(self.lineEditPort.text())))
        # self.ConnectButton.setText(u'已连接')
        # self.setWindowTitle(str(self.lineEditIp.text()))
        # self.connectStat = True
        # self.ButtonEnble(stat=True)

        # get firmware version
        cmd = 'cat /etc/openwrt_version'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stdout.read()
        self.logEdit.append(outstr)
        self.FwVersionlineEdit.setText(outstr)

        # get device config, such as SN
        cmd = 'cat /etc/wifiroute.conf'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stdout.read()
        self.logEdit.append(outstr)
        find_sn = outstr.find('sn=')
        outstr = outstr[find_sn:]
        find_sn = outstr.find('\n')
        outstr = outstr[3:find_sn]
        self.sn = outstr
        self.SnlineEdit.setText(outstr)

        cmd = 'uci show wireless'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stdout.read()
        self.logEdit.append(outstr)
        # find ap & sta interface
        find_sn = outstr.find('.mode=ap')
        self.iface = outstr[outstr[:find_sn].rfind('\n') + 1: find_sn]
        find_sn = outstr.find('.mode=sta')
        self.ifaceWan = outstr[outstr[:find_sn].rfind('\n') + 1: find_sn]

        targetStr = self.iface + '.ssid='
        find_sn = outstr.find(targetStr)
        self.ssid = outstr[find_sn + len(targetStr): outstr.find('\n', find_sn)]
        self.SSIDlineEdit.setText(self.ssid)
        targetStr = self.ifaceWan + '.ssid='
        find_sn = outstr.find(targetStr)
        self.ssid = outstr[find_sn + len(targetStr): outstr.find('\n', find_sn)]
        self.WanSSIDlineEdit.setText(self.ssid)
        # find encryption
        targetStr = self.iface + '.encryption='
        find_sn = outstr.find(targetStr)
        self.encryption = outstr[find_sn + len(targetStr): outstr.find('\n', find_sn)]
        # find passwd
        if self.encryption != 'none':
            targetStr = self.iface + '.key='
            find_sn = outstr.find(targetStr)
            if find_sn < 0:
                self.password = ''
            else:
                self.password = outstr[find_sn + len(targetStr): outstr.find('\n', find_sn)]
        else:
            self.password = ''
        self.PasswdlineEdit.setText(self.password)

        cmd = 'fw_printenv'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stdout.read()
        self.logEdit.append(outstr)
        find_sn = outstr.find('tdrsn=')
        if find_sn > 0:  # there is tdrsn in u-boot-env
            outstr = outstr[find_sn:]
            find_sn = outstr.find('\n')
            self.resetSn = outstr[6:find_sn]
            self.ResetSnlineEdit.setText(self.resetSn)
        else:
            cmd = 'cat /rom/etc/wifiroute.conf'
            self.logEdit.append('==>' + cmd)
            stdin, stdout, stderr = self.sshClient.exec_command(cmd)
            outstr = stdout.read()
            self.logEdit.append(outstr)
            find_sn = outstr.find('sn=')
            outstr = outstr[find_sn:]
            find_sn = outstr.find('\n')
            outstr = outstr[3:find_sn]
            self.resetSn = outstr
            self.ResetSnlineEdit.setText(outstr)

        cmd = 'cat /mnt/USBDisk/AppleIPK/etc/appList.json'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        jsstr = stdout.read()
        if len(jsstr) > 0:
            jsobj = json.loads(jsstr)
            osstr = ['IOS', 'Android']
            for js in jsobj:
                self.logEdit.append(
                    '系统:' + osstr[int(js['os'])] + '\t' + js['name'] + '\t版本:' + js['version'] + '\tID:' + str(
                        js['id']))
        else:
            self.logEdit.append('applist.json is empty')

        cmd = 'ifconfig | grep HWaddr'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        for outstr in stdout.readlines():
            if outstr.find('ath0') > -1 and outstr.find('ath01') < 0:
                self.AthMac = outstr[outstr.find('HWaddr ') + 7: outstr.find('\n') - 2].replace(':', '')
                self.AthMaclineEdit.setText(self.AthMac)
            if outstr.find('eth0') > -1:
                self.WanMac = outstr[outstr.find('HWaddr ') + 7: outstr.find('\n') - 2].replace(':', '')
                self.WanMaclineEdit.setText(self.WanMac)
            if outstr.find('eth1') > -1:
                self.LanMac = outstr[outstr.find('HWaddr ') + 7: outstr.find('\n') - 2].replace(':', '')
                self.LanMaclineEdit.setText(self.LanMac)

        cmd = 'cat /etc/log.conf | grep DEBUG'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stdout.read()
        if outstr.find('|off|') > 0:
            self.debugEnable = False
            self.DebugStatButton.setText('DEBUG Off')
        else:
            self.debugEnable = True
            self.DebugStatButton.setText('DEBUG On')

        cmd = 'uci show system.initdone'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stdout.read()
        # self.initDone = int(outstr[outstr.find('=') + 1:])
        # if self.initDone == 1:
        #     self.InitDoneButton.setText(u'跳过快速设置')
        # if self.initDone == 0:
        #     self.InitDoneButton.setText(u'快速设置必须')


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MyApp()
    window.setWindowTitle(u'天地融智能下载器工具 V2.4')
    window.show()
    sys.exit(app.exec_())