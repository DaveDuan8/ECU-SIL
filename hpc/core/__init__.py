"""
hpc.core
--------

Interface Module for Hpc.

Subpackage which contains the needed interfaces to:

**Internal-API Interfaces**

"""
__all__ = ["DOMAINNAME", "LOGINNAME", "UID_NAME"]


# - import Python modules ----------------------------------------------------------------------------------------------
from sys import platform

if platform == "win32":
    from win32api import GetUserNameEx
    DOMAINNAME, LOGINNAME = GetUserNameEx(2).split('\\')
    LOGINNAME = LOGINNAME.lower()
    DOMAINNAME = DOMAINNAME.upper()
    UID_NAME = "{}\\{}".format(DOMAINNAME, LOGINNAME)
else:
    from getpass import getuser
    UID_NAME = LOGINNAME = getuser()
    DOMAINNAME = ""
