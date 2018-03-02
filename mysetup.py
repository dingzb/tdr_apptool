import sys
from distutils.core import setup
import py2exe
import _cffi_backend

# this allows to run it with a simple double click.
sys.argv.append('py2exe')

py2exe_options = {
    "includes": ["sip"],
    "dll_excludes": ["MSVCP90.dll", ],
    # "compressed": 1,
    "optimize": 2,
    "ascii": 0,
    "bundle_files": 1
}

setup(
    name='GoFun Tool',
    version='0.1',
    windows=['app.py', ],
    zipfile=None,
    options={'py2exe': py2exe_options},
    data_files = [('adb',['adb/adb.exe', 'adb/AdbWinApi.dll', 'adb/AdbWinUsbApi.dll', 'adb/fastboot.exe'])]
)