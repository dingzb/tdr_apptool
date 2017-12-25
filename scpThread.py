# -*- coding: utf-8 -*-
import urllib2
import time
import os
import struct
from hashlib import md5
from contextlib import closing
from scpclient import *

from PyQt4 import QtCore

class fileItem:
    def __init__(self):
        self.commonPath = '' # appleIPK以后的路径+文件名
        self.name = ''      # 文件名
        self.size = ''      # 文件大小
        self.pcPath = ''
        self.devPath = ''   # 设备上的路径
        self.devFullPath = '' # 设备上的路径+文件名
        self.pcMd5 = ''
        self.devMd5 = ''
        self.applistMd5 = ''
        self.match = False # 设备上存在此文件，MD5也一致
        self.exist = False # 是否存在此文件
        self.checked = 0 # 校验通过的次数


class CheckAppFile(QtCore.QThread):
    infoSignal = QtCore.pyqtSignal(str)
    cntSignal = QtCore.pyqtSignal(int)
    doneSignal = QtCore.pyqtSignal(bool, str)
    logSignal = QtCore.pyqtSignal(str)
    def __init__(self,args):
        super(CheckAppFile,self).__init__()
        self.sshClient = args[0]
        self.fileList = args[1]
        self.errorFile = ''  # 有错误的文件
        self.stopped = False

    def run(self):
        cnt = 0
        total = len(self.fileList)
        for item in self.fileList:
            if self.stopped:
                return
            md5 = item.split(' ')[0]
            file = item.split(' ')[1].strip('\n')
            file = file[file[1:].find('/') + 1:]
            file = '/mnt/USBDisk'+ file
            cmd = 'md5sum '+ file
            self.infoSignal.emit(file)
            stdin, stdout, stderr = self.sshClient.exec_command(cmd)
            err = stderr.read()
            if len(err) > 0:
                print err
                self.logSignal.emit(u"%s,请检查U盘" %(err))
                break
            else:
                remoteMd5 = stdout.read().split(' ')[0]
                if remoteMd5 == md5:
                    cnt += 1
                    self.logSignal.emit(u"%s校验通过：%s" % (file, remoteMd5))
                    self.cntSignal.emit(100 * cnt / total)
                    continue
                else:
                    print file + ' error'
                    self.errorFile += file + ' '
                    self.logSignal.emit(u"%s校验错误：当前(%s) != 正确(%s)" %(file, remoteMd5, md5))
                    continue
        self.doneSignal.emit(cnt == total, self.errorFile)
        return

    def UserCancel(self):
        self.stopped = True

class scpFile(QtCore.QThread):
    doSignal = QtCore.pyqtSignal(int)
    def __init__(self,args):
        super(scpFile,self).__init__()
        self.sshClient = args[0]
        self.localFile = args[1]
        self.remoteFile = args[2]

    def myProgress(self,remote_filename, size, file_pos):
        percent = 100 * file_pos / size
        self.doSignal.emit(percent)
        #print("Copy %s %d %d of %d" %(remote_filename,percent, file_pos, size))

        return 0

    def run(self):
        find_sn = self.remoteFile.rfind('/')
        remoteName = self.remoteFile[find_sn + 1:]
        remotePath = self.remoteFile[:find_sn + 1]
        with closing(Write(self.sshClient.get_transport(), remotePath)) as scp:
            scp.send_file(local_filename=self.localFile, remote_filename=remoteName, progress=self.myProgress)

class scpDir(QtCore.QThread):
    percSignal = QtCore.pyqtSignal(int)
    fileSignal = QtCore.pyqtSignal(str)
    def __init__(self,args):
        super(scpDir,self).__init__()
        self.sshClient = args[0]
        self.localFile = args[1]
        self.remoteFile = args[2]

    def myProgress(self,remote_filename, size, file_pos):
        percent = 100 * file_pos / size
        self.percSignal.emit(percent)
        self.fileSignal.emit(remote_filename)
        #print("Copy %s %d %d of %d" %(remote_filename,percent, file_pos, size))

    def run(self):
        with closing(WriteDir(self.sshClient.get_transport(), self.remoteFile)) as scp:
            scp.send_dir(self.localFile, self.remoteFile, progress=self.myProgress)

class CopyAndCheckFiles(QtCore.QThread):
    cntSignal = QtCore.pyqtSignal(int)
    fileSingal = QtCore.pyqtSignal(str)
    errorSignal = QtCore.pyqtSignal(str)
    logSignal = QtCore.pyqtSignal(str)
    def __init__(self,args):
        super(CopyAndCheckFiles, self).__init__()
        self.localAppDir = args[0]
        self.remoteAppDir = args[1]
        self.md5Check = args[2]
        self.sshClient = args[3]
        self.cnt = 0            # 已经拷贝的文件大小
        self.number = 0         # 已经拷贝的文件数量
        self.copySize = 0      # 需要更新的文件数量
        self.copyNum = 0       # 需要更新的文件大小总和
        self.totalNum = 0       # 所有文件数量
        self.stopped = False
        self.lastSize = 0
        self.lastTime = 0
        self.fileList = []
        self.checkCnt = 0
        self.pcappmd5 = ''  # PC下app的md5值
        self.devapplist = []


    def run(self):
        try:
            # Get file list and md5 from applist.md5
            self.localAppDir = self.localAppDir.replace('\\', '/')
            applistMd5File = self.localAppDir + '/applist.md5'

            if not os.path.exists(applistMd5File):
                self.errorSignal.emit("%s not exist" %(applistMd5File))
                return
            else:
                applistFp = open(applistMd5File)
                applist = applistFp.read().split('\n')
                applistFp.close()

            # 添加applist.md5文件到文件列表
            localMd5 = md5()
            localMd5.update(open(applistMd5File, 'rb').read())
            applistMd5FileMd5 = localMd5.hexdigest()

            applistMd5File = applist[0].split(' ')[1].split('/AppleIPK/')[0] + '/AppleIPK/applist.md5'
            applist.append(str(applistMd5FileMd5) + ' ' + applistMd5File)

            # 建立本地检索list
            for line in applist:
                    if self.stopped:
                        return
                    eachFile = fileItem()
                    if len(line) < 32:  # maybe the last line
                        continue
                    lineList = line.split(' ')
                    eachFile.applistMd5 = lineList[0]
                    self.pcappmd5 += str(lineList[0] + ' ')
                    eachFile.commonPath = lineList[len(lineList)-1].split('/AppleIPK/')[1]
                    eachFile.name = eachFile.commonPath[eachFile.commonPath.rfind('/') + 1:]
                    eachFile.pcPath = self.localAppDir + '/' + eachFile.commonPath
                    eachFile.devFullPath = self.remoteAppDir + eachFile.commonPath
                    eachFile.devPath = eachFile.devFullPath.rstrip(eachFile.name)
                    eachFile.size = os.path.getsize(eachFile.pcPath)
                    self.fileList.append(eachFile)

            # 判断applist.md5是否存在
            cmd = 'ls /mnt/USBDisk/AppleIPK/applist.md5'
            stdin, stdout, stderr = self.sshClient.exec_command(cmd)
            if stderr.read().find('No such file or directory') > 0:
                print u'dev下applist.md5不存在'
            else:
                print u'applist.md5存在'
                cmd = 'cat /mnt/USBDisk/AppleIPK/applist.md5'
                stdin, stdout, stderr = self.sshClient.exec_command(cmd)
                self.devmd5file = stdout.read()
                # Dev下各文件MD5+devPath
                devmd5file = str(self.devmd5file).split('\n')
                for line in devmd5file:
                    if self.stopped:
                        return
                    if len(line) < 32:  # maybe the last line
                        continue
                    filemd5 = line.split(' ')[0]
                    devapppath = '/mnt/USBDisk/AppleIPK/' + line.split('/AppleIPK/')[1]
                    self.devapplist.append(filemd5 + ' ' + devapppath)
                # dev下applist.md5文件md5+path
                cmd = 'md5sum ' + '/mnt/USBDisk/AppleIPK/applist.md5'
                stdin, stdout, stderr = self.sshClient.exec_command(cmd)
                filemd5 = stdout.read()
                filemd5 = str(filemd5).split(' ')[0]
                info = filemd5 + ' ' + '/mnt/USBDisk/AppleIPK/applist.md5'
                self.devapplist.append(info)
                # 遍历dev下各文件MD5值  若不存出在于self.pcappmd5则删除对应Dev下文件
                for line in self.devapplist:
                    devapppath = str(line).split()[1]
                    filemd5 = str(line).split()[0]
                    print filemd5, devapppath
                    if self.pcappmd5.find(filemd5) == -1:
                        cmd = 'rm' + ' ' + devapppath
                        self.sshClient.exec_command(cmd)
                        print u'不存在'
                    else:
                        print u'存在'



            self.totalNum = len(self.fileList)
            # 校验并更新
            maxTry = 5
            for it in range(1, maxTry, 1):
                self.copyNum = 0
                self.copySize = 0
                self.checkCnt = 0
                # 整体校验一轮
                self.logSignal.emit(u'开始校验')
                for eachFile in self.fileList:
                    if self.stopped:
                        return
                    # 校验通过2遍则不再校验
                    self.checkCnt += 1
                    self.fileSingal.emit(u'校验文件中 %d/%d'%(self.checkCnt, self.totalNum))
                    self.cntSignal.emit(self.checkCnt * 100 / self.totalNum)
                    if eachFile.checked > 1:
                        continue
                    cmd = 'md5sum ' + eachFile.devFullPath
                    stdin, stdout, stderr = self.sshClient.exec_command(cmd)
                    result = stdout.read()
                    if len(result) > 0:
                        eachFile.exist = True
                        eachFile.devMd5 = result.split()[0]
                        if eachFile.devMd5 == eachFile.applistMd5:
                            eachFile.match = True
                            eachFile.checked += 1
                            self.logSignal.emit(u"%s 存在且一致" % (eachFile.commonPath))
                        else:
                            eachFile.match = False
                            self.copyNum += 1
                            self.copySize += eachFile.size
                            self.logSignal.emit(u"%s 存在但不一致" % (eachFile.commonPath))
                    else:
                        eachFile.exist = False
                        eachFile.devMd5 = 0
                        eachFile.match = False
                        self.copyNum += 1
                        self.copySize += eachFile.size
                        self.logSignal.emit(u"%s 不存在" % (eachFile.commonPath))

                if self.copyNum == 0:
                    self.logSignal.emit(u'一共%d文件,全部存在无需更新'%(self.totalNum))
                    return
                else:
                    self.logSignal.emit(u"一共%d文件，需要更新%d个，大小%dKB" % (self.totalNum, self.copyNum, self.copySize / 1024))

                # 更新一轮
                def myProgress(file, size, file_pos):
                        self.cntSignal.emit((self.cnt + file_pos) * 100 / self.copySize)
                        now = time.clock()
                        incrTime = now - self.lastTime
                        if incrTime < 1:
                            return
                        self.lastTime = now
                        incrSize = self.cnt + file_pos - self.lastSize
                        self.lastSize = self.cnt + file_pos
                        self.fileSingal.emit(u'%s\n大小:%dKB %d%% 速度:%dKB/s 总数:%d/%d' % (
                            file, size / 1024, file_pos * 100 / size, incrSize / incrTime / 1024, self.number + 1,
                            self.copyNum))

                self.logSignal.emit(u'开始更新文件')
                self.number = 0
                self.cnt = 0
                for file in self.fileList:
                    if self.stopped:
                        return
                    if file.match == True:
                        continue
                    else:
                        self.logSignal.emit(u"#copy#%d:%s" %(self.number, file.commonPath))
                        cmd = 'ls ' + file.devPath
                        stdin, stdout, stderr = self.sshClient.exec_command(cmd)
                        if stderr.read().find(u'No such file or directory') > 0:
                            cmd = 'mkdir -p ' + file.devPath
                            self.sshClient.exec_command(cmd)
                            time.sleep(2)
                        with closing(Write(self.sshClient.get_transport(), file.devPath)) as scp:
                            scp.send_file(local_filename=file.pcPath, remote_filename=file.name,
                                          progress=myProgress)
                        cmd = 'fsync ' + file.devPath + file.name
                        self.sshClient.exec_command(cmd)
                        self.cnt += file.size
                        self.number += 1

            # maxTry 循环后依然没有完成
            self.errorSignal.emit(u'%d轮更新后依然有问题，请联系工程师'%(maxTry))

        except Exception, e:
            print Exception, ":", e
            self.error('Exception:' + e.message)

    def error(self, file):
        self.errorSignal.emit(file)
        self.stopped = True
        return

    def userCancel(self):
        if self.cnt < self.copySize:
            self.errorSignal.emit('User Cancel')
            self.stopped = True

class EnableSSH(QtCore.QThread):
    percSignal = QtCore.pyqtSignal(int)
    def __init__(self,args):
        super(EnableSSH, self).__init__()
        IP = args
        self.targetUrlOld = str('http://' + IP + ':8008/api/bkdprivi.lua?act=put&bkdon=1')
        self.targetUrlNew = str('http://' + IP + ':38008/api/bkdprivi.lua?act=put&bkdon=1')
        self.stopped = False

    def stop(self):
        self.stopped = True

    def run(self):
        self.stopped = False
        # enable ssh service of target
        ssh_max_try = 100
        cnt = 1
        while self.stopped == False:
            self.percSignal.emit(cnt)
            try:
                urllib2.urlopen(self.targetUrlOld, timeout=3)
                break
            except urllib2.URLError, e:
                print e,'8008'

                time.sleep(3)
                cnt = cnt + 1
                if cnt == ssh_max_try:
                    break
            try:
                urllib2.urlopen(self.targetUrlNew, timeout=3)
                break
            except urllib2.URLError, e:
                print e,'38008'
                time.sleep(3)
                cnt = cnt + 1
                if cnt == ssh_max_try:
                    break
                else:
                    continue
        time.sleep(2)
        self.percSignal.emit(100)





