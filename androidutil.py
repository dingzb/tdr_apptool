# coding=utf-8
import os
import subprocess
import locale

adb_cmd = 'adb\\adb.exe '
fastboot_cmd = 'adb\\fastboot.exe '

def exe_cmd(cmd):
    p = os.popen(cmd)
    rs = ''
    line = p.readline()
    while line:
        rs += line
        line = p.readline()
    return rs

def exe_cmd2(cmd, stdout_fn = None):
    p = subprocess.Popen(cmd.encode(locale.getdefaultlocale()[1]), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    rs = ''
    while p.poll():
        return p.stdout
    while p.poll() is None:
        line = p.stdout.readline()
        if p.stdout:
            if stdout_fn:
                stdout_fn(line)
            rs += line
    return p.pid, rs

def exe_adb(cmd):
    return exe_cmd(adb_cmd + cmd)

def exe_fastboot(cmd, stdout_fn=None):
    return exe_cmd2(fastboot_cmd + cmd, stdout_fn)[1]

def list_adb():
    rs_str = exe_adb('devices')
    rs = []
    if rs_str:
        ds = rs_str.split('\n')
        for d in ds:
            kv = d.split('\t')
            if len(kv) > 1:
                rs.append(kv[0])
    return rs

def list_fastboot():
    rs_str = exe_fastboot('devices')
    rs = []
    if rs_str:
        ds = rs_str.split('\n')
        for d in ds:
            kv = d.split('\t')
            if len(kv) > 1:
                rs.append(kv[0])
    return rs

def dev_mode(serial_num, adbs, fastboots):
    if serial_num in adbs:
        return 'adb'
    elif serial_num in fastboots:
        return 'fastboot'
    else:
        return ''

def adb2fastboot():
    exe_adb('reboot bootloader')

def fastboot_reboot():
    exe_fastboot('reboot')

def adb_reboot():
    exe_adb('reboot')

def flash(type, path, msg_fn):
    exe_fastboot('--unbuffered flash ' + str(type) + ' "' + str(path) + '"', msg_fn)