# -*- coding: utf-8 -*-
import binascii
import os
import sys

import re

reload(sys)
sys.setdefaultencoding('utf8')
import time
import json
import paramiko
from hashlib import md5
from tools import *
from scpclient import *
from contextlib import closing

target_user = 'root'
target_port = 22
target_passwd = 't0d7r19tdr'


class MyApp(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.ConnectButton.clicked.connect(self.Connect)
        self.connectStat = False
        self.pushButtonSaveServer.clicked.connect(self.set_network)
        # self.FwUpgradeButton.clicked.connect(self.FwUpgrade)
        # self.SetSnButton.clicked.connect(self.SetSn)
        # self.SetResetSnButton.clicked.connect(self.SetResetSn)
        # self.ResetButton.clicked.connect(self.Reset)
        # self.RebootButton.clicked.connect(self.Reboot)
        # self.HaltButton.clicked.connect(self.Halt)
        # self.SetSSIDButton.clicked.connect(self.SetSSID)
        # self.SetPasswdButton.clicked.connect(self.SetPasswd)
        self.CmdlineEdit.returnPressed.connect(self.RunCmd)
        # self.UpdateUdiskButton.clicked.connect(self.UpdateApp)
        # self.RestartNetworkButton.clicked.connect(self.RestartNetWork)
        # self.ClearSqliteButton.clicked.connect(self.ClearSqlite)
        # self.CheckUDiskButton.clicked.connect(self.CheckUDisk)
        # self.SetMacButton.clicked.connect(self.SetMac)
        # self.SaveLogButton.clicked.connect(self.SaveLog)
        # self.DebugStatButton.clicked.connect(self.SetDebugStat)
        # self.FormatUDiskButton.clicked.connect(self.FormatUDisk)
        # self.InitDoneButton.clicked.connect(self.InitDoneToggle)
        # self.CheckAppButton.clicked.connect(self.CheckApp)
        # self.AppButton.clicked.connect(self.SelecApp)
        # self.DelAppButton.clicked.connect(self.DelApp)
        # self.UDiskBar.hide()
        # self.ButtonEnble(stat=False)
        # self.AppMd5CheckBox.setChecked(True)
        # self.updateAppFail = ''
        # self.CancelDlg = QtGui.QMessageBox()
        # self.CancelDlgStat = False
        # self.debugEnable = False
        # self.localAppDir = ''
        # self.IPhistory = ['192.100.10.1']
        # self.comboBox.addItems(self.IPhistory)
        self.sshClient = paramiko.SSHClient()
        self.sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        with open('shell.json') as jsonFile:
            self.shellJson = json.load(jsonFile, encoding='utf8')

    def AppendLog(self, str):
        self.logEdit.append(str)

    def CheckApp(self):
        cmd = 'cat /mnt/USBDisk/AppleIPK/applist.md5'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stderr.read()
        if len(outstr):
            QtGui.QMessageBox.warning(self, u'错误', outstr)
            return
        outstr = stdout.readlines()
        if len(outstr) == 0:
            QtGui.QMessageBox.warning(self, u'错误', u'applist.md5文件为空')
            return

        proDlg = QtGui.QProgressDialog(self)
        proDlg.setMinimum(0)
        proDlg.setMaximum(100)
        proDlg.setFixedWidth(400)
        proDlg.setWindowTitle(u'检验中')
        # proDlg.setCancelButtonText(u'取消')
        proDlg.setCancelButton(None)
        proDlg.setAutoClose(False)
        proDlg.setWindowModality(1)
        proDlg.show()

        from scpThread import CheckAppFile
        self.CheckAppThread = CheckAppFile(args=(self.sshClient, outstr))
        self.CheckAppThread.finished.connect(proDlg.close)
        self.CheckAppThread.doneSignal.connect(self.FinishCheckApp)
        self.CheckAppThread.cntSignal.connect(proDlg.setValue)
        self.CheckAppThread.infoSignal.connect(proDlg.setLabelText)
        self.CheckAppThread.logSignal.connect(self.AppendLog)
        proDlg.canceled.connect(self.CheckAppThread.UserCancel)
        self.CheckAppThread.start()

    def FinishCheckApp(self, stat, file):
        if stat:
            QtGui.QMessageBox.information(self, u'提示', u'APP包校验通过')
        else:
            QtGui.QMessageBox.warning(self, u'错误', u'%s校验出错' % (file))
        return

    def InitDoneToggle(self):
        if self.initDone == 1:
            cmd = 'uci set system.initdone=0 && uci commit && /sbin/init_iptables'
            self.initDone = 0
            self.InitDoneButton.setText(u'必须快速设置')
        else:
            cmd = 'uci set system.initdone=1 && uci commit && /sbin/init_iptables'
            self.initDone = 1
            self.InitDoneButton.setText(u'跳过快速设置')
        self.sshClient.exec_command(cmd)

    def FormatUDisk(self):

        val = QtGui.QMessageBox.question(self, u'提示', u'即将格式化U盘',
                                         QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        if val == QtGui.QMessageBox.Cancel:
            return 0

        self.KillService()

        cmd = 'umount /mnt/USBDisk -f'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stderr.read()
        if len(outstr) > 0:
            QtGui.QMessageBox.warning(self, u'错误', u'U盘卸载失败，请重试\n%s' % (outstr))
            return

        cmd = 'mkfs.vfat /dev/sda1'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        self.logEdit.append('==> ' + cmd)
        self.logEdit.append(stdout.read())

        cmd = 'mount -t vfat /dev/sda1 /mnt/USBDisk'
        self.sshClient.exec_command(cmd)
        QtGui.QMessageBox.information(self, u'提示', u'U盘格式化成功')

    def SetDebugStat(self):
        if self.debugEnable == False:
            cmd = str('sed -i s/\'DEBUG|off\'/\'DEBUG|on\'/g /etc/log.conf')
            self.sshClient.exec_command(cmd)
            self.debugEnable = True
            self.DebugStatButton.setText('DEBUG On')
        else:
            cmd = str('sed -i s/\'DEBUG|on\'/\'DEBUG|off\'/g /etc/log.conf')
            self.sshClient.exec_command(cmd)
            self.debugEnable = False
            self.DebugStatButton.setText('DEBUG Off')

    def SaveLog(self):
        path = str(self.sn)
        if not os.path.exists(path):
            os.mkdir(path)
        path += '\\' + time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
        if not os.path.exists(path):
            os.mkdir(path)

        def outputCmdToFile(cmd, saveFile):
            file = open(path + '\\' + saveFile, 'w')
            stdin, stdout, stderr = self.sshClient.exec_command(cmd)
            file.write(stdout.read())
            outstr = stderr.read()
            if len(outstr) > 0:
                file.write('=================stderr=================\n')
                file.write(outstr)
            file.close()

        def outputStrToFile(str, saveFile):
            file = open(path + '\\' + saveFile, 'w')
            file.write(str)
            file.close()

        outputStrToFile(self.logEdit.toPlainText(), 'localLog.txt')
        outputCmdToFile('uci show update', 'updateStat.txt')
        outputCmdToFile('ls /mnt/USBDisk/AppleIPK -lR', 'AppleIPK.txt')
        outputCmdToFile('ps', 'ps.txt')
        outputCmdToFile('ls -l /etc/staticList.json && cat /etc/staticList.json', 'staticList_json.txt')

        with closing(ReadDir(self.sshClient.get_transport(), '.')) as scp:
            scp.receive_dir(local_dirname=path, remote_dirname='/mnt/USBDisk/AppleIPK/etc', preserve_times=True)
        with closing(ReadDir(self.sshClient.get_transport(), '.')) as scp:
            scp.receive_dir(local_dirname=path, remote_dirname='/mnt/USBDisk/AppleIPK/log', preserve_times=True)

    def SetMac(self):
        newAthMac = self.AthMaclineEdit.text()
        newAthMac = int(str(newAthMac), 16)
        newLanMac = newAthMac + 1
        newWanMac = newAthMac + 2
        self.AthMac = ('%.12x' % (newAthMac)).upper()
        self.WanMac = ('%.12x' % (newWanMac)).upper()
        self.LanMac = ('%.12x' % (newLanMac)).upper()
        newAthMac = binascii.a2b_hex(self.AthMac)
        newWanMac = binascii.a2b_hex(self.WanMac)
        newLanMac = binascii.a2b_hex(self.LanMac)
        QtGui.QMessageBox.information(self, u'提示', u'MAC地址修改成功，重启生效。重启后LAN IP会变化，请重新确认')

        cmd = 'cat /dev/mtdblock5'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        artImg = stdout.read()
        newImg = newWanMac + newLanMac + artImg[12:4098] + newAthMac + artImg[4104:]
        imgFile = open('art.img', 'wb')
        imgFile.write(newImg)
        imgFile.close()

        with closing(Write(self.sshClient.get_transport(), '/tmp/')) as scp:
            scp.send_file('art.img', 'art.img')

        cmd = 'mtd erase art && mtd write /tmp/art.img art'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)

        self.WanMaclineEdit.setText(self.WanMac)
        self.LanMaclineEdit.setText(self.LanMac)
        os.remove('art.img')

    def KillService(self):
        cmd = 'ps  |grep runcron.sh | awk \'{printf("kill -9 %s\\n",$1)}\' |sh'
        self.sshClient.exec_command(cmd)
        cmd = 'ps  |grep runupdate.sh | awk \'{printf("kill -9 %s\\n",$1)}\' |sh'
        self.sshClient.exec_command(cmd)
        cmd = 'ps  |grep sendmsg.lua | awk \'{printf("kill -9 %s\\n",$1)}\' |sh'
        self.sshClient.exec_command(cmd)
        cmd = 'ps  |grep nginx | awk \'{printf("kill -9 %s\\n",$1)}\' |sh'
        self.sshClient.exec_command(cmd)
        cmd = 'ps  |grep recvbus.lua | awk \'{printf("kill -9 %s\\n",$1)}\' |sh'
        self.sshClient.exec_command(cmd)
        cmd = 'ps  |grep datatransfer.lua | awk \'{printf("kill -9 %s\\n",$1)}\' |sh'
        self.sshClient.exec_command(cmd)

    def SelecApp(self):
        self.localAppDir = str(
            QtGui.QFileDialog.getExistingDirectory(self, ('Select AppleIPK Dir'), 'C:', QtGui.QFileDialog.ShowDirsOnly))
        if self.localAppDir == '':  # cancelled
            return
        self.localAppDir = unicode(self.localAppDir, "utf-8")
        self.AppLineEdit.setText(self.localAppDir)

    def DelApp(self):
        val = QtGui.QMessageBox.question(self, u'提示', u'删除设备里的AppleIPK目录？',
                                         QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        if val == QtGui.QMessageBox.Cancel:
            return 0

        cmd = 'rm -rf /mnt/USBDisk/AppleIPK'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        QtGui.QMessageBox.information(self, u'提示', u'App包已经删除')

    def UpdateApp(self):
        self.UDiskStat = False
        self.CheckUDisk()
        if not self.UDiskStat:
            return
        self.updateAppFail = ''

        self.localAppDir = self.AppLineEdit.text()

        if self.localAppDir == '':
            QtGui.QMessageBox.warning(self, u'错误', u'请先选择App包')
            return

        self.remoteAppDir = '/mnt/USBDisk/AppleIPK/'
        self.logEdit.append('==> cp ' + self.localAppDir + ' to ' + self.remoteAppDir)
        self.repaint()
        self.md5Check = self.AppMd5CheckBox.isChecked()
        # kill update service
        self.KillService()

        cmd = 'mount -o remount /dev/sda1 /mnt/USBDisk'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        self.logEdit.append(stderr.read())
        # cmd = 'rm -rf /mnt/USBDisk/AppleIPK_old && mv /mnt/USBDisk/AppleIPK /mnt/USBDisk/AppleIPK_old'
        # self.sshClient.exec_command(cmd)
        # self.logEdit.append('==> ' + cmd)

        proDlg = QtGui.QProgressDialog(self)
        proDlg.setMinimum(0)
        proDlg.setMaximum(100)
        proDlg.setFixedWidth(400)
        proDlg.setWindowTitle(u'更新中')
        proDlg.setCancelButtonText(u'取消')
        proDlg.setCancelButton(None)
        proDlg.setAutoClose(False)
        proDlg.setWindowModality(1)
        proDlg.show()

        from scpThread import CopyAndCheckFiles
        self.checkFilesThread = CopyAndCheckFiles(
            args=(self.localAppDir, self.remoteAppDir, self.md5Check, self.sshClient))
        self.checkFilesThread.fileSingal.connect(proDlg.setLabelText)
        self.checkFilesThread.cntSignal.connect(proDlg.setValue)
        self.checkFilesThread.logSignal.connect(self.AppendLog)
        self.checkFilesThread.finished.connect(proDlg.close)
        self.checkFilesThread.finished.connect(self.finishUpdateApp)
        proDlg.canceled.connect(self.checkFilesThread.userCancel)

        def haltProDlg(str):
            self.updateAppFail = str

        self.checkFilesThread.errorSignal.connect(haltProDlg)
        self.checkFilesThread.start()

    def finishUpdateApp(self):
        if len(self.updateAppFail) > 0:
            if self.updateAppFail == 'User Cancel':
                self.CancelDlg.close()
                self.CancelDlgStat = False
                QtGui.QMessageBox.warning(self, u'错误', u'用户取消更新')
                self.logEdit.append(u'用户取消更新')
            elif self.updateAppFail.indexOf('Exception:') != -1:
                QtGui.QMessageBox.warning(self, u'错误', u'发生异常!%s' % (self.updateAppFail))
                self.logEdit.append(u'发生异常!%s' % (self.updateAppFail))
                self.SaveLog()
            else:
                QtGui.QMessageBox.warning(self, u'错误', u'%s' % (self.updateAppFail))
            self.logEdit.append(u'%s' % (self.updateAppFail))
            cmd = 'rm -rf /mnt/USBDisk/AppleIPK/applist.md5'
            self.sshClient.exec_command(cmd)
            self.logEdit.append('==> ' + cmd)
            return

        cmd = 'cp -f /mnt/USBDisk/AppleIPK/staticList.json /etc/ && sync'
        self.sshClient.exec_command(str(cmd))
        self.logEdit.append('==>' + cmd)
        cmd = 'uci set update.stat.app=0 && uci set update.stat.config=0 && uci set update.stat.theme=0 && uci commit'
        self.sshClient.exec_command(str(cmd))
        self.logEdit.append('==>' + cmd)
        QtGui.QMessageBox.information(self, u'提示', u'更新APP成功，下载App需重启')

    def ClearSqlite(self):
        cmd = 'rm -rf /mnt/USBDisk/sqlite3'
        self.sshClient.exec_command(str(cmd))
        self.logEdit.append('==>' + cmd)

    def RunCmd(self):
        cmd = self.CmdlineEdit.text()
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(str(cmd))
        self.logEdit.append(u''.join(stderr.readlines()))
        self.logEdit.append(u''.join(stdout.readlines()))
        self.CmdlineEdit.setText('')
        return 0

    def ButtonEnble(self, stat):
        pass
        # self.DebugStatButton.setEnabled(stat)
        # self.FwUpgradeButton.setEnabled(stat)
        # self.SetSnButton.setEnabled(stat)
        # self.SetResetSnButton.setEnabled(stat)
        # self.RebootButton.setEnabled(stat)
        # self.HaltButton.setEnabled(stat)
        # self.SetSSIDButton.setEnabled(stat)
        # self.SetPasswdButton.setEnabled(stat)
        # self.UpdateUdiskButton.setEnabled(stat)
        # self.ResetButton.setEnabled(stat)
        # self.RestartNetworkButton.setEnabled(stat)
        # self.ClearSqliteButton.setEnabled(stat)
        # self.CheckUDiskButton.setEnabled(stat)
        # self.AppMd5CheckBox.setEnabled(stat)
        # self.SetMacButton.setEnabled(stat)
        # self.SaveLogButton.setEnabled(stat)
        # self.FormatUDiskButton.setEnabled(stat)
        # self.InitDoneButton.setEnabled(stat)
        # self.CheckAppButton.setEnabled(stat)
        # self.DelAppButton.setEnabled(stat)
        # self.AppButton.setEnabled(stat)
        #
        # if not stat:
        #     self.FwVersionlineEdit.setText('')
        #     self.SnlineEdit.setText('')
        #     self.ResetSnlineEdit.setText('')
        #     self.SSIDlineEdit.setText('')
        #     self.PasswdlineEdit.setText('')
        #     self.WanSSIDlineEdit.setText('')
        #     self.AthMaclineEdit.setText('')
        #     self.LanMaclineEdit.setText('')
        #     self.WanMaclineEdit.setText('')

    def Reset(self):
        cmd = 'sync && firstboot'
        self.logEdit.append('==>' + cmd)
        self.sshClient.exec_command(cmd)
        QtGui.QMessageBox.information(self, u'提示', u'恢复出厂设置成功，重启生效')
        self.repaint()

    def Reboot(self):
        cmd = 'sync && reboot'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = ''.join(stdout.readlines())
        self.logEdit.append(outstr)
        self.ButtonEnble(stat=False)
        self.connectStat = False
        self.ConnectButton.setText(u'未连接')
        self.repaint()
        return 0

    def Halt(self):
        cmd = 'sync && halt'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = ''.join(stdout.readlines())
        self.logEdit.append(outstr)
        self.ButtonEnble(stat=False)
        self.connectStat = False
        self.ConnectButton.setText(u'未连接')
        self.repaint()
        return 0

    def SetResetSn(self):
        cmd = 'cat /proc/cmdline'
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = ''.join(stdout.readlines())
        self.logEdit.append(outstr)
        find_sn = outstr.find('64k(u-boot-env)ro')
        if find_sn > 0:
            self.ResetSnlineEdit.setText(self.resetSn)
            self.ResetSnlineEdit.setReadOnly(True)
            QtGui.QMessageBox.warning(self, u'警告', u'U-boot-env只读, 无法修改序列号')
            return 0
        else:
            newResetSn = self.ResetSnlineEdit.text()
            cmd = 'fw_setenv tdrsn ' + newResetSn + ' && fw_printenv'
            stdin, stdout, stderr = self.sshClient.exec_command(str(cmd))
            outstr = stdout.read()
            if outstr.find('tdrsn=' + newResetSn) > 0:
                QtGui.QMessageBox.information(self, u'提示', u'出厂设置序列号修改成功')
                self.ResetSnlineEdit.setText(newResetSn)
                self.resetSn = newResetSn
            else:
                QtGui.QMessageBox.warning(self, u'警告', u'出厂设置序列号修改失败')
                self.ResetSnlineEdit.setText(self.resetSn)

    def SetPasswd(self):
        newPasswd = str(self.PasswdlineEdit.text())
        if newPasswd == self.password:
            return

        if len(newPasswd) == 0:  # empty, so no passwd
            newEncryption = 'none'
        else:
            newEncryption = 'psk2'

        cmd = 'uci set %s.encryption=%s' % (self.iface, newEncryption)
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        cmd = 'uci set %s.key=%s' % (self.iface, newPasswd)
        self.logEdit.append('==>' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        cmd = 'uci commit'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        self.logEdit.append('==>' + cmd)
        self.repaint()
        self.encryption = newEncryption
        self.password = newPasswd

    def SetSSID(self):
        newSSID = self.SSIDlineEdit.text()
        cmd = 'uci set %s.ssid=%s' % (self.iface, newSSID)
        self.logEdit.append('==>' + cmd)
        self.sshClient.exec_command(cmd)
        cmd = 'uci commit'
        self.sshClient.exec_command(cmd)
        self.logEdit.append('==>' + cmd)
        self.ssid = newSSID
        self.SSIDlineEdit.setText(newSSID)

    def RestartNetWork(self):
        cmd = '/etc/init.d/network restart'
        self.logEdit.append('==> ' + cmd)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        QtGui.QMessageBox.information(self, u'提示', u'网络重启中，稍后请重新连接')

    def SetSn(self):
        newSn = self.SnlineEdit.text()
        cmd = str('sed -i s/' + self.sn + '/' + newSn + '/g /etc/wifiroute.conf')
        self.logEdit.append('Set Sn from ' + self.sn + ' to ' + newSn)
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        self.sn = newSn
        return 0

    def FwUpgrade(self):  # copy new fw file into device
        self.localFwFile = str(QtGui.QFileDialog.getOpenFileName(self, ('open file'), 'C:', ("Images (*.bin)")))
        if self.localFwFile == '':
            return
        self.localFwFile = unicode(self.localFwFile, "utf-8")
        localMd5 = md5()
        localMd5.update(open(self.localFwFile, 'rb').read())
        self.localFwMd5 = localMd5.hexdigest()
        self.remoteFwFile = '/tmp/upgrade.bin'
        self.logEdit.append('==> scp ' + self.localFwFile + ' to ' + self.remoteFwFile)

        proDlg = QtGui.QProgressDialog(self)
        proDlg.setMinimum(0)
        proDlg.setMaximum(100)
        proDlg.setFixedHeight(200)
        proDlg.setFixedWidth(400)
        proDlg.setWindowTitle(u'拷贝中')
        proDlg.setLabelText(self.remoteFwFile)
        proDlg.setCancelButtonText(u'取消')
        proDlg.setAutoClose(True)
        proDlg.setWindowModality(1)
        proDlg.show()

        from scpThread import scpFile
        self.scpFileThread = scpFile(args=(self.sshClient, self.localFwFile, self.remoteFwFile,))
        self.scpFileThread.doSignal.connect(proDlg.setValue)
        self.scpFileThread.finished.connect(self.doFwUpgrade)
        self.scpFileThread.start()

    def doFwUpgrade(self):  # actually do upgrade
        cmd = 'md5sum ' + self.remoteFwFile
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = ''.join(stdout.readlines())
        remoteMd5 = outstr[:outstr.find(' ')]
        # print remoteMd5

        if (self.localFwMd5 == remoteMd5):
            # self.logEdit.append('md5sum match, start upgrading')
            cmd = 'sysupgrade -n -F ' + self.remoteFwFile
            val = QtGui.QMessageBox.question(self, u'提示', u'即将升级,需要2-3分钟，不要关闭程序',
                                             QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            if val == QtGui.QMessageBox.Cancel:
                return 0
            self.connectStat = False
            self.ConnectButton.setText(u'未连接')
            self.ButtonEnble(stat=False)
            self.repaint()
            stdin, stdout, stderr = self.sshClient.exec_command(cmd)
            time.sleep(2)
            self.Connect(afterUpFw=True)

        else:
            self.logEdit.append('md5sum check failed, try again')
            return -1

    def CheckUDisk(self):
        cmd = 'ls /dev/sda1'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        if stdout.read().find('No such file or directory') > 0:  # No device
            QtGui.QMessageBox.warning(self, u'警告', u'U盘设备不存在')
            return

        cmd = 'df | grep sda'
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        outstr = stdout.read()
        if outstr.find('/dev/sda1') < 0:  # not mount
            QtGui.QMessageBox.warning(self, u'警告', u'U盘没有挂载')
            return
        else:
            self.UDiskStat = True
            outlist = outstr.split()
            diskSize = (float(outlist[1])) / 1000000
            usedPerc = outlist[4]
            self.UDiskBar.setFormat('%s/%.1fGB' % (usedPerc, diskSize))
            self.UDiskBar.setValue(int(usedPerc.rstrip('%')))
            self.UDiskBar.show()

    def Connect(self, afterUpFw=False):
        try:
            self.sshClient.connect(str(self.lineEditIp.text()), int(self.lineEditPort.text()), str(self.lineEditUsername.text()), str(self.lineEditPassword.text()))
            self.logEdit.append('SSH Connect %s:%d!' % (str(self.lineEditIp.text()), int(self.lineEditPort.text())))
            self.ConnectButton.setText(u'已连接')
            self.setWindowTitle(str(self.lineEditIp.text()))
            self.connectStat = True
            self.ButtonEnble(stat=True)
        except Exception, e:
            print(str(e))


        while(self.connectStat):
            self.get_info()
            break

        # self.targetIp=self.TargetIPLlineEdit.text()

        # self.targetIp = self.comboBox.currentText()
        # print IPhistory
        # if self.targetIp in self.IPhistory:
        #     print ''
        # else:
        #     self.IPhistory.append(self.targetIp)
        #     self.comboBox.insertItem(0, self.targetIp)
        #     self.comboBox.update()

        # if self.targetIp.indexOf('192.100.10.1') > -1:
        #   targetUrl=str('http://' + self.targetIp + ':8008/api/bkdprivi.lua?act=put&bkdon=1')
        # else:
        #    targetUrl = str('http://' + self.targetIp + ':38008/api/bkdprivi.lua?act=put&bkdon=1')
        # self.logEdit.append('Connecting ' + self.targetIp)
        # self.ConnectButton.setText(u'连接中')
        # self.repaint()
        #
        # proDlg = QtGui.QProgressDialog(self)
        # proDlg.setMinimum(0)
        # proDlg.setMaximum(100)
        # proDlg.setFixedWidth(400)
        # if afterUpFw == False:
        #     proDlg.setWindowTitle(u'连接中')
        #     proDlg.setCancelButtonText(u'取消')
        # else:
        #     proDlg.setWindowTitle(u'升级中')
        #     proDlg.setCancelButton(None)
        #     proDlg.setLabelText(u'正在升级，完成后会自动重启，请不要断电')
        # proDlg.setAutoClose(True)
        # proDlg.setWindowModality(1)
        # proDlg.show()
        # self.GetInfo()
        # # enable ssh service of target
        # from scpThread import EnableSSH
        # self.EnableSshThread = EnableSSH(args=self.targetIp)
        # self.EnableSshThread.finished.connect(self.GetInfo)
        # self.EnableSshThread.percSignal.connect(proDlg.setValue)
        # proDlg.canceled.connect(self.EnableSshThread.stop)
        # self.EnableSshThread.start()

    def get_info(self):
        cmd = self.shellJson.get('info').get('network')
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        n_str = stdout.read()
        self.fill_cfg_network(n_str)
        self.append_info('<================================ network =====================================>')
        self.append_info(n_str)
        cmd = self.shellJson.get('info').get('version')
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        self.append_info('<================================ version =====================================>')
        self.append_info(stdout.read())
        cmd = self.shellJson.get('info').get('usb')
        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
        self.append_info('<================================= usb ========================================>')
        self.append_info(stdout.read())

    def append_info(self, info):
        self.textBrowserInfo.append(str(info))

    def clear_info(self):
        self.textBrowserInfo.clear()

    def fill_cfg_network(self, info=None):
        kvs = info.split('\n')
        for i, kv in enumerate(kvs):
            kvs[i] = kv.split('=')
        ks = self.shellJson.get('keys').get('setting').get('network')
        u_ip = self.__get_v_f_network_info_str(ks.get('upgradeIp'), kvs)
        u_port = self.__get_v_f_network_info_str(ks.get('upgradePort'), kvs)
        o_ip = self.__get_v_f_network_info_str(ks.get('operationIp'), kvs)
        o_port = self.__get_v_f_network_info_str(ks.get('operationPort'), kvs)
        i_ip = self.__get_v_f_network_info_str(ks.get('idcardIp'), kvs)
        i_port = self.__get_v_f_network_info_str(ks.get('idcardPort'), kvs)
        l_url = self.__get_v_f_network_info_str(ks.get('logsrvUrl'), kvs)
        self.LineEditUpdateIp.setText(u_ip)
        self.LineEditUpdatePort.setText(u_port)
        self.LineEditOperationIp.setText(o_ip)
        self.LineEditOperationPort.setText(o_port)
        self.LineEditIdCardIp.setText(i_ip)
        self.LineEditIdCardPort.setText(i_port)
        self.LineEditLogURL.setText(l_url)

    def __get_v_f_network_info_str(self, k, kvs):
        """从字符串中获取网络配置信息"""
        for kv in kvs:
            if kv[0] == k:
                return kv[1].replace("'", "")

    def set_network(self):
        vr = self.__validate_network_cfg()
        if not vr[0]:
            warn_dialog = QtGui.QErrorMessage()
            warn_dialog.showMessage(vr[1])
            warn_dialog.setWindowTitle(u"错误")
            warn_dialog.exec_()
            return
        settings = vr[1]
        cmd = str(self.shellJson.get('setting').get('network').get('set'))
        ks = self.shellJson.get('keys').get('setting').get('network')
        self.__exe_cmd(str.format(cmd, ks.get('operationIp'), str(settings[0])))
        self.__exe_cmd(str.format(cmd, ks.get('operationPort'), str(settings[1])))
        self.__exe_cmd(str.format(cmd, ks.get('upgradeIp'), str(settings[2])))
        self.__exe_cmd(str.format(cmd, ks.get('upgradePort'), str(settings[3])))
        self.__exe_cmd(str.format(cmd, ks.get('idcardIp'), str(settings[4])))
        self.__exe_cmd(str.format(cmd, ks.get('idcardPort'), str(settings[5])))
        self.__exe_cmd(str.format(cmd, ks.get('logsrvUrl'), str(settings[6])))
        self.__exe_cmd(self.shellJson.get('setting').get('network').get('commit'))

    def __validate_network_cfg(self):
        o_ip = self.LineEditOperationIp.text()
        o_port = self.LineEditOperationPort.text()
        u_ip =self.LineEditUpdateIp.text()
        u_port = self.LineEditUpdatePort.text()
        i_ip = self.LineEditIdCardIp.text()
        i_port = self.LineEditIdCardPort.text()
        l_url  = self.LineEditLogURL.text()
        ip_pattern = r'^(?:(?:1[0-9][0-9]\.)|(?:2[0-4][0-9]\.)|(?:25[0-5]\.)|(?:[1-9][0-9]\.)|(?:[0-9]\.)){3}(?:(?:1[0-9][0-9])|(?:2[0-4][0-9])|(?:25[0-5])|(?:[1-9][0-9])|(?:[0-9]))$'
        port_pattern = r'^\d{2,5}$'
        url_pattern = r'((https?|ftp|file)://)?[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]'
        if not re.match(ip_pattern, str(o_ip)):
            return False, u'业务服务器IP格式错误'
        if not re.match(port_pattern, str(o_port)):
            return False, u'业务服务器端口格式错误'
        if not re.match(ip_pattern, str(u_ip)):
            return False, u'升级服务器IP格式错误'
        if not re.match(port_pattern, str(u_port)):
            return False, u'升级服务器端口格式错误'
        if not re.match(ip_pattern, str(i_ip)):
            return False, u'身份证服务器IP格式错误'
        if not re.match(port_pattern, str(i_port)):
            return False, u'身份证服务器端口格式错误'
        if not re.match(url_pattern, str(l_url)):
            return False, u'日志服务器URL格式错误'
        return True, (o_ip, o_port, u_ip, u_port, i_ip, i_port, l_url)

    def __log_append(self, log):
        self.logEdit.append(log)

    def __exe_cmd(self, cmd):
        self.__log_append('===> ' + cmd)
        self.sshClient.exec_command(cmd)

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
