"""
tds.py
------

Test Data Server(s) utilities checking and updating server and path names
e.g. if running on HPC.

Features:
  - checking if running on HPC client
  - checking if the server is available
  - changing server name in list of strings

On HPC there is a fast connection server in parallel to the test data server LIFS010,
if the script runs on HPC the fast one should be used
to prevent that HPC clients wait for file transfer.

The provided functions can be used to update e.g. pathnames, server names etc.
"""
# pylint: disable=E1101,E0611
# - import Python modules ----------------------------------------------------------------------------------------------
from __future__ import print_function
from sys import platform, modules
from os import sep, altsep, getenv
from os.path import join
from datetime import datetime
from re import search, match, sub
from subprocess import PIPE, STDOUT, call
from socket import gethostname, gethostbyname_ex, create_connection, socket, AF_INET, SOCK_STREAM
from random import randrange
from requests import get as reqget, post as reqpost
from six import PY2
# try:
from cx_Oracle import connect as cxconnect
# ISCX = True
# except ImportError:
#     from oracledb import connect as cxconnect
#     ISCX = False
if PY2:
    from types import StringTypes
    from urllib import quote
else:  # pragma: no cover
    StringTypes = (str,)
    from urllib.parse import quote
try:
    from numba import cuda
    CC_CORES_PER_SM = {(2, 0): 32, (2, 1): 48, (3, 0): 192, (3, 5): 192, (3, 7): 192, (5, 0): 128, (5, 2): 128,
                       (6, 0): 64, (6, 1): 128, (7, 0): 64, (7, 5): 64, (8, 0): 64, (8, 6): 128}
except Exception:
    cuda = CC_CORES_PER_SM = None  # pylint: disable=C0103

# - import HPC modules -------------------------------------------------------------------------------------------------
from .dicts import DefDict
from ..sched.sched_defs import LOCAL_NET_PATH
from ..core.logger import suppress_warnings
from ..rdb.app_srv import connect as asconnect

# - defines ------------------------------------------------------------------------------------------------------------
MSWIN = platform == "win32"

MAX_TASKS = 25000
# Sven, Joachim, Mohan, Cedrik, HPC_Services, Jenkins_Environment
DEVS = ["uidv7805", "uidv8815", "uidp2898", "uie61052", "uia70156", "uie30182", "uie30184"]

EXC_PRJ_NAMES = ("Admin", "INFRGTS",)

# https://mtsgoesblobstoragetest.blob.core.windows.net/mtsblobcontainer/2020.10.17_at_15.43.11_radar-mi_5174.rrec
AZR_BLOB_STX = r"(?P<epp>\w+)://(?P<account>[a-zA-Z0-9]+)\.[a-z]+\.(?P<suffix>[a-zA-Z0-9\.]+)/" \
               r"(?P<container>[a-zA-Z0-9]+)/(?P<blob>.*)"
AZR_CONN_STR = "DefaultEndpointsProtocol={};AccountName={};AccountKey={};EndpointSuffix={}"
AZR_ACC_KEYS = {
    "ewears540bw11prj1": "IA1Jsz4YnMI+J+vyyBlbayNOVnFHKmjN2cQwGuKEIh+XV3xoyVkZRTW9BHF1oPyy7/+ZPrulyDEuk1tK5eDzgw==",
    "ewears540bw11prj2": "0rM0WyXP/MPVKUpaXm7aGDv0XrBYXKXWt2oH+S7bz1An8KOIfNxTHhgWSR43dHqd/6TCpy8xOk8b8AGmyfBLhg==",
    "ewears540bw11prj3": "lxjLTnu126Kq7wBIVBhS1W6/dzWfV32ZpBRMK/NV767P5fKOemgZW6M06Vv8RzaKqnrLiM7DE5CB4OrgmINiWA=="
}

VALID_PYVER = ["2.7.12 (default, Dec  4 2017, 14:50:18) \n[GCC 5.4.0 20160609]",  # e.g. on lu00126vmx (hpcportal)
               "2.7.17 (default, Oct 28 2019, 21:35:07) [MSC v.1500 64 bit (AMD64)]",
               "3.6.10 |Anaconda, Inc.| (default, Jan  7 2020, 15:18:16) [MSC v.1916 64 bit (AMD64)]",
               "3.6.10 (default, Mar  5 2020, 10:17:47) [MSC v.1900 64 bit (AMD64)]",
               "3.8.5 (default, Sep  3 2020, 21:29:08) [MSC v.1916 64 bit (AMD64)]",
               "3.10.10 | packaged by conda-forge | (main, Mar 24 2023, 20:00:38) [MSC v.1934 64 bit (AMD64)]"]

HPC_SHARES = {"win32": [r"\\lufs009x.li.de.conti.de", r"\\lufs003x.li.de.conti.de", r"\\lifs010.cw01.contiwan.com",
                        r"\\ozfs110.oz.in.conti.de", r"\\ozfs120.oz.in.conti.de",
                        r"\\lsfs001x.ls.de.conti.de", r"\\lsfs002x.ls.de.conti.de",
                        r"\\qhfs004x.qh.us.conti.de",
                        r"\\itfs001x.it.cn.conti.de", r"\\itfs002x.it.cn.conti.de",
                        r"https://ewears540bw11sim3.blob.core.windows.net",
                        r"https://ewears540bw11sim4.blob.core.windows.net",
                        r"https://ewears540bw11sim5.blob.core.windows.net",
                        r"https://ewears540bw11prj1.blob.core.windows.net",
                        r"https://ewears540bw11prj2.blob.core.windows.net",
                        r"https://ewears540bw11prj3.blob.core.windows.net",
                        r"https://ewears540bw11dev1.blob.core.windows.net",
                        r"https://ewears540bw11dev2.blob.core.windows.net",
                        r"\\lsfs050x.ls.de.conti.de",
                        ],
              "linux": [r"/datac/lufs009x", r"/datac/lufs003x", r"/datac/lifs010", "/datac/ozfs110", "/datac/ozfs120",
                        "/datac/lsfs001x", "/datac/lsfs002x", r"/datac/qhfs004x", "/datac/itfs001x", "/datac/itfs002x",
                        r"/datac/azure/ewears540bw11sim3", r"/datac/azure/ewears540bw11sim4",
                        r"/datac/azure/ewears540bw11sim5",
                        r"/datac/azure/ewears540bw11prj1", r"/datac/azure/ewears540bw11prj2",
                        r"/datac/azure/ewears540bw11prj3",
                        r"/datac/azure/ewears540bw11dev1", r"/datac/azure/ewears540bw11dev2",
                        r"/datac/lsfs050x",
                        ]}

if getenv("HPC_STORE"):
    HPC_SHARES = {"win32": [getenv("HPC_STORE")] * len(HPC_SHARES["win32"]),
                  "linux": ["/mnt/" + getenv("HPC_STORE").strip('\\').split('.')[0]] * len(HPC_SHARES["linux"])}

if MSWIN:
    REPLACEMENTS = ((r"(?i)(\\\\)(lifs010)(s?(\.cw01\.contiwan\.com)?)(\\.*)", r"\1\2s.cw01.contiwan.com\5"),
                    (r"(?i)(\\\\)(mdm-adas-hub1-lu\.conti\.de)(\\.*)", r"\1lifs010s.cw01.contiwan.com\3"),
                    (r"(?i)(\\\\)(lufs00[39]x)(\.li\.de\.conti\.de)?(\\.*)", r"\1\2.li.de.conti.de\4"),
                    (r"(?i)(\\\\)(mdm-adas-hub2-lu\.conti\.de)(\\.*)", r"\1lufs003x.li.de.conti.de\3"),
                    (r"(?i)(\\\\)(mdm-adas-hub3-lu\.conti\.de)(\\.*)", r"\1lufs009x.li.de.conti.de\3"),
                    (r"(?i)(\\\\)(qhfs004x)(\.qh\.us\.conti\.de)?(\\.*)", r"\1qhsimu.qh.us.conti.de\4"),
                    (r"(?i)(\\\\)(mdm-adas-hub1-qh\.conti\.de)(\\.*)", r"\1qhsimu.qh.us.conti.de\3"),
                    (r"(?i)(\\\\)(ozfs1[12]0)h?(\.oz\.in\.conti\.de)?(\\.*)", r"\1\2h.oz.in.conti.de\4"),
                    (r"(?i)(\\\\)(mdm-adas-hub1-oz\.conti\.de)(\\.*)", r"\1ozfs110h.oz.in.conti.de\3"),
                    (r"(?i)(\\\\)(mdm-adas-hub2-m8\.conti\.de)(\\.*)", r"\1ozfs120h.oz.in.conti.de\3"),
                    (r"(?i)(\\\\)(lsfs001)[xh](\.ls\.de\.conti\.de)?(\\.*)", r"\1\2h.ls.de.conti.de\4"),
                    (r"(?i)(\\\\)(mdm-adas-hub1-ls\.conti\.de)(\\.*)", r"\1lsfs001h.ls.de.conti.de\3"),
                    (r"(?i)(\\\\)(lsfs002x)(\.ls\.de\.conti\.de)?(\\.*)", r"\1\2.ls.de.conti.de\4"),
                    (r"(?i)(\\\\)mdm-adas-hub2-ls\.conti\.de(\\.*)", r"\1lsfs002x.ls.de.conti.de\2"),
                    (r"(?i)(\\\\)(itfs001)[xh](\.it\.cn\.conti\.de)?(\\.*)", r"\1\2h.it.cn.conti.de\4"),
                    (r"(?i)(\\\\)(itfs002x)(\.it\.cn\.conti\.de)?(\\.*)", r"\1\2.it.cn.conti.de\4"),
                    (r"(?i)(\\\\)mdm-adas-hub1-it\.conti\.de(\\.*)", r"\1itfs001h.it.cn.conti.de\2"),
                    (r"(?i)(\\\\)mdm-adas-hub2-it\.conti\.de(\\.*)", r"\1itfs002x.it.cn.conti.de\2"),
                    (r"(?i)\\\\enedatareprocessingsa000\.blob\.core\.windows\.net\\enedatareprocessingsa000", r"S:"),)
else:  # pragma: nocover
    REPLACEMENTS = ((r"(?i)(\\\\)(lifs010)(s?(\.cw01\.contiwan\.com)?)(\\.*)", r"/mnt/\2\5"),
                    (r"(?i)(\\\\)(mdm-adas-hub1-lu\.conti\.de)(\\.*)", r"/mnt/lifs010\3"),
                    (r"(?i)(\\\\)(lufs00[39]x)(\.li\.de\.conti\.de)?(\\.*)", r"/mnt/\2\4"),
                    (r"(?i)(\\\\)(mdm-adas-hub2-lu\.conti\.de)(\\.*)", r"/mnt/lufs003x\3"),
                    (r"(?i)(\\\\)(mdm-adas-hub3-lu\.conti\.de)(\\.*)", r"/mnt/lufs009x\3"),
                    (r"(?i)(\\\\)(qhfs00[48]x)(\.qh\.us\.conti\.de)?(\\.*)", r"/mnt/\2\4"),
                    (r"(?i)(\\\\)(mdm-adas-hub1-qh\.conti\.de)(\\.*)", r"/mnt/qhfs004x\3"),
                    (r"(?i)(\\\\)(ozfs1[12]0)(h?(\.oz\.in\.conti\.de)?)(\\.*)", r"/mnt/\2\5"),
                    (r"(?i)(\\\\)(mdm-adas-hub1-oz\.conti\.de)(\\.*)", r"/mnt/ozfs110\3"),
                    (r"(?i)(\\\\)(mdm-adas-hub2-m8\.conti\.de)(\\.*)", r"/mnt/ozfs120\3"),
                    (r"(?i)(\\\\)(lsfs00[12])[xh](\.ls\.de\.conti\.de)?(\\.*)", r"/mnt/\2x\4"),
                    (r"(?i)(\\\\)(mdm-adas-hub([12])-ls\.conti\.de)(\\.*)", r"/mnt/lsfs00\3x\4"),
                    (r"(?i)(\\\\)(itfs00)([12])[xh](\.it\.cn\.conti\.de)?(\\.*)", r"/mnt/\2\3x\5"),
                    (r"(?i)(\\\\)mdm-adas-hub([12])-it\.conti\.de(\\.*)", r"/mnt/itfs00\2x\3"),)

REVPLACMENTS = ((r"(?i)(\\\\)(lifs010)s?(\.cw01\.contiwan\.com)?(\\.*)", r"\1\2.cw01.contiwan.com\4"),
                (r"(?i)(\\\\)(mdm-adas-hub1-lu\.conti\.de)(\\.*)", r"\1lifs010.cw01.contiwan.com\3"),
                (r"(?i)(\\\\)(lufs00[39]x)(\.li\.de\.conti\.de)?(\\.*)", r"\1\2.li.de.conti.de\4"),
                (r"(?i)(\\\\)(mdm-adas-hub2-lu\.conti\.de)(\\.*)", r"\1lufs003x.li.de.conti.de\3"),
                (r"(?i)(\\\\)(mdm-adas-hub3-lu\.conti\.de)(\\.*)", r"\1lufs009x.li.de.conti.de\3"),
                (r"(?i)(\\\\)(qhsimu)(\.qh\.us\.conti\.de)?(\\.*)", r"\1qhfs004x.qh.us.conti.de\4"),
                (r"(?i)(\\\\)(mdm-adas-hub1-qh\.conti\.de)(\\.*)", r"\1qhfs004x.qh.us.conti.de\3"),
                (r"(?i)(\\\\)(ozfs1[12]0)h?(\.oz\.in\.conti\.de)?(\\.*)", r"\1\2.oz.in.conti.de\4"),
                (r"(?i)(\\\\)(mdm-adas-hub1-oz\.conti\.de)(\\.*)", r"\1ozfs110.oz.in.conti.de\3"),
                (r"(?i)(\\\\)(mdm-adas-hub2-m8\.conti\.de)(\\.*)", r"\1ozfs120.oz.in.conti.de\3"),
                (r"(?i)(\\\\)(lsfs00[12])[xh](\.ls\.de\.conti\.de)?(\\.*)", r"\1\2x.ls.de.conti.de\4"),
                (r"(?i)(\\\\)(mdm-adas-hub([12])-ls\.conti\.de)(\\.*)", r"\1lsfs00\3x.ls.de.conti.de\4"),
                (r"(?i)(\\\\)(itfs00[12])[xh](\.it.cn\.conti\.de)?(\\.*)", r"\1\2x.it.cn.conti.de\4"),
                (r"(?i)(\\\\)mdm-adas-hub([12])[xh]-it\.conti\.de(\\.*)", r"\1itfs00\2x.ls.de.conti.de\3"),)

# connections for Oracle, postgres, etc: [(arg0, arg1, ...), connect_func, type_of_db]
# ORACONN = ('(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST={})))'
#            '(CONNECT_DATA=(SERVER=DEDICATED)(SERVICE_NAME={}))'
#            '(TRANSPORT_CONNECT_TIMEOUT=600)(CONNECT_TIMEOUT=600)(RETRY_COUNT=3))')
# EVAL_HPC = ORACONN.format("ludb004s.lu.de.conti.de", "sMISCLU_1_P_PDB.lu.de.conti.de")
HPC_USR, DEV_USR = ("hpc_user", "Baba1234", "racadmpe",), ("dev_hpc_user", "Pikachu20", "racadmpe",)
SHB_USR = ("hpc_user", "Baba1234", "testdm19p",)  # test dbq: testdm19p, normal: testdm-jd
STD_VGA, SHB_VGA = ("VAL_GLOBAL_USER", "PWD4VAL_GLBL", "racadmpe",), ("VAL_GLOBAL_USER", "PWD4VAL_GLBL", "testdm19p",)
DEFAULT_DB_CONN = {"args": (), "kwargs": {}, "conn_func": cxconnect, "db_type": 1,
                   "exec": ["ALTER SESSION SET current_schema = HPC_ADMIN", "ALTER SESSION SET time_zone = 'UTC'"],
                   "repr": "HPC@oracle", "copy": ["autocommit"]}
DEV_DB_CONN = {"args": (), "kwargs": {}, "conn_func": cxconnect, "db_type": 1,
               "exec": ["ALTER SESSION SET current_schema = DEV_HPC_ADMIN", "ALTER SESSION SET time_zone = 'UTC'"],
               "repr": "DEV_HPC@oracle", "copy": ["autocommit"]}
CHINA_DB_CONN = dict(DEFAULT_DB_CONN)
VGA_DB_CONN = {"args": (), "kwargs": {}, "conn_func": cxconnect,
               "db_type": 1, "repr": "VGA@oracle", "exec": ["ALTER SESSION SET current_schema = VAL_GLOBAL_ADMIN"],
               "copy": ["autocommit"]}
CHINA_VGA_CONN = dict(VGA_DB_CONN)

for conn, cusr in [[DEFAULT_DB_CONN, HPC_USR], [DEV_DB_CONN, DEV_USR], [CHINA_DB_CONN, SHB_USR],
                   [VGA_DB_CONN, STD_VGA], [CHINA_VGA_CONN, SHB_VGA]]:
    # if ISCX:
    conn["args"] = cusr
    # else:
    #     conn["kwargs"] = dict(zip(("user", "password", "service_name",), cusr))


# postgres could look like this:
# DEFAULT_DB_CONN = {"args": (,), "kwargs": {"host": '<host>.lu.de.conti.de', "dbname": 'HPC', "user": 'hpc_user',
#                    "password": 'hpc_user'}, "conn_func": pgconnect, "db_type": 1,
#                    "exec": ["ALTER SESSION SET current_schema = HPC_ADMIN", "ALTER SESSION SET time_zone = 'UTC'"],
#                    "repr": "HPC@oracle", "copy": ["autocommit"]}
PORTAL_URL = "hpcportal.conti.de"
APPSRV_DB_CONN = {"args": ('http://' + PORTAL_URL, 'HPC',), "kwargs": {},
                  "conn_func": asconnect, "db_type": 2, "repr": "HPC@appserver",
                  "set": [("autocommit", True)], "copy": ["autocommit"]}
APP_SERVER = "localhost" if 'nose' in modules else PORTAL_URL

LND_HEAD = "LU00156VMA"
LND_LOC = "LND"
POC_HEAD = "LUAS003A"
POC_LOC = "POC"
DEV_HEAD = "LUAS004A"
DEV_LOC = "DEV"
# AZR_LOC = "AZR"
DUB_LOC = "DUB"
DUB_HEAD = "LSAS002A"
SHARES = r"(prj|legacy|sim|hpc)"
LND_SERVERS = (r"LIFS010S?(\.CW01\.CONTIWAN\.COM)?\\(prj|sim|testdata|data)",
               r"LUFS00[39]X(\.LI\.DE\.CONTI\.DE)?\\(prj|legacy|sim|hpc|landing)",
               r"mdm-adas-hub[123]-lu\.conti\.de\\" + SHARES,
               r"cw01(\.contiwan\.com)?\\Root\\Loc\\lndp\\did[a-z]\d{4}",)
MAZ_SERVERS = list(LND_SERVERS) + [AZR_BLOB_STX] + [r"LSFS00[12][XH](\.LS\.DE\.CONTI\.DE)?\\" + SHARES]
ABH_HEAD = "QHS6U5DA"
ABH_LOC = "ABH"
ABH_SERVERS = (r"QH(FS004X|SIMU)(\.QH\.US\.CONTI\.DE)?\\" + SHARES, r"mdm-adas-hub1-qh\.conti\.de\\" + SHARES,)
BLR_HEAD = "OZAS012A"
BLR_LOC = "BLR"
BLR_SERVERS = (r"OZFS1[12]0H?(\.OZ\.IN\.CONTI\.DE)?\\" + SHARES, r"mdm-adas-hub(1-oz|2-m8)\.conti\.de\\" + SHARES,)
SHB_HEAD = "ITAS004A"
SHB_LOC = "SHB"
SHB_SERVERS = (r"ITFS00[12][XH](\.IT\.CN\.CONTI\.DE)?\\" + SHARES, r"mdm-adas-hub[12]-it\.conti\.de\\" + SHARES,)
FFM_HEAD = "LSAS095A"
FFM_LOC = "FFM"
FFM_SERVERS = (r"LSFS00[12][HX](\.LS\.DE\.CONTI\.DE)?\\" + SHARES, r"mdm-adas-hub[12]-ls\.conti\.de\\" + SHARES,
               r"auto(\.contiwan\.com)?\\CAS\\Loc\\ffm2\\did[a-z]\d{4}",)

DUB_SERVERS = (r"LSFS00[12][HX](\.LS\.DE\.CONTI\.DE)?\\" + SHARES, r".*\.blob\.core\.windows\.net",)
DEV_SERVERS = list(LND_SERVERS) + list(FFM_SERVERS)
POC_SERVERS = [r"FRFS010x(\.FR\.GE\.CONTI\.DE)?\\transfer"] + list(FFM_SERVERS)

PORTALS = ["http://{}".format(PORTAL_URL), "http://{}:8000".format(PORTAL_URL), "http://{}:8100".format(PORTAL_URL)]
SPARCS_URL = "https://statusportal.adas.conti.de:8005"

# values of HPC_STORAGE_MAP explained:
# [0]: server shares belonging to same head node,
# [1]: hpc network share,
# [2]: which version of HPC pack is being used,
# [3]: related DB connection to be used,
# [4]: location
HPC_STORAGE_MAP = \
    DefDict((["OTHER"], LOCAL_NET_PATH, "localhost", DEFAULT_DB_CONN, None, "localhost"),
            **{
                DEV_HEAD: (DEV_SERVERS, HPC_SHARES[platform][0], "2019", DEV_DB_CONN, DEV_LOC, PORTALS[2],),
                # "LU00190VMA": (LND_SERVERS, HPC_SHARES[platform][0], None, DEV_DB_CONN, DEV_LOC, PORTALS[2],),
                # LND => 156VMA: SIL, 003A: CC
                LND_HEAD: (LND_SERVERS, HPC_SHARES[platform][0], "2016", DEFAULT_DB_CONN, LND_LOC, PORTALS[0],),
                POC_HEAD: (POC_SERVERS, HPC_SHARES[platform][6], "2019", DEFAULT_DB_CONN, LND_LOC, PORTALS[0],),
                "LU00160VMA": (LND_SERVERS, HPC_SHARES[platform][0], "2019", DEFAULT_DB_CONN, LND_LOC, PORTALS[0],),
                "LU00199VMA": (LND_SERVERS, HPC_SHARES[platform][0], "2019", DEFAULT_DB_CONN, LND_LOC, PORTALS[0],),
                "LU00200VMA": (LND_SERVERS, HPC_SHARES[platform][0], "2019", DEFAULT_DB_CONN, LND_LOC, PORTALS[0],),
                # ABH => 5CA: SIL, 5BA: CC
                "QHS6U5CA": (ABH_SERVERS, HPC_SHARES[platform][7], "2016", DEFAULT_DB_CONN, ABH_LOC, PORTALS[0],),
                "QHS6U5BA": (ABH_SERVERS, HPC_SHARES[platform][7], "2016", DEFAULT_DB_CONN, ABH_LOC, PORTALS[0],),
                # new ABH head nodes:
                ABH_HEAD: (ABH_SERVERS, HPC_SHARES[platform][7], "2019", DEFAULT_DB_CONN, ABH_LOC, PORTALS[0],),
                "QHS6U5FA": (ABH_SERVERS, HPC_SHARES[platform][7], "2019", DEFAULT_DB_CONN, ABH_LOC, PORTALS[0],),
                # BLR => 012A: SIL, 013A: CC
                BLR_HEAD: (BLR_SERVERS, HPC_SHARES[platform][3], "2016", DEFAULT_DB_CONN, BLR_LOC, PORTALS[0],),
                "OZAS013A": (BLR_SERVERS, HPC_SHARES[platform][3], "2016", DEFAULT_DB_CONN, BLR_LOC, PORTALS[0],),
                # FFM => 003A: SIL, 002A: CC
                FFM_HEAD: (FFM_SERVERS, HPC_SHARES[platform][6], "2019", DEFAULT_DB_CONN, FFM_LOC, PORTALS[0],),
                DUB_HEAD: (DUB_SERVERS, HPC_SHARES[platform][6], "2019", DEFAULT_DB_CONN, FFM_LOC, PORTALS[0],),
                "LSAS003A": (FFM_SERVERS, HPC_SHARES[platform][6], "2019", DEFAULT_DB_CONN, FFM_LOC, PORTALS[0],),
                # JIT => 06: SIL, 07: CC
                SHB_HEAD: (SHB_SERVERS, HPC_SHARES[platform][9], "2016", CHINA_DB_CONN, SHB_LOC, PORTALS[1],),
                "ITAS004A_CSCT": (SHB_SERVERS, HPC_SHARES[platform][9], "2016", CHINA_DB_CONN, SHB_LOC, PORTALS[1],),
                "ITAS005A": (SHB_SERVERS, HPC_SHARES[platform][9], "2016", CHINA_DB_CONN, SHB_LOC, PORTALS[1],),
            })

LOC_HEAD_MAP = {LND_LOC: [LND_HEAD, "LU00160VMA", "LU00199VMA", "LU00200VMA"],
                BLR_LOC: [BLR_HEAD, "OZAS013A"],
                ABH_LOC: [ABH_HEAD, "QHS6U5FA", "QHS6U5CA", "QHS6U5BA"],
                FFM_LOC: [FFM_HEAD],
                POC_LOC: [POC_HEAD],
                SHB_LOC: [SHB_HEAD, "ITAS004A_CSCT", "ITAS005A"],
                # AZR_LOC: [AZR_HEAD, AZR_HEAD],
                DEV_LOC: [DEV_HEAD],
                DUB_LOC: [DUB_HEAD],
                }
X_SUBMIT_EXC = {FFM_LOC: LND_LOC, LND_LOC: FFM_LOC, FFM_LOC: DUB_LOC, DUB_LOC: FFM_LOC}

PRODUCTION_HEADS = [LND_HEAD, ABH_HEAD, BLR_HEAD, FFM_HEAD]

PRJ_EXC = "Admin|Short_Test|CI|INFRGTS"


# - function -
def location(default=None):
    """
    find out location of you, if not found, falls back to def_head

    :param str default: default thing to return if AD cannot resolve properly
    :return: hpc headnode
    :rtype: str
    """
    host = gethostname().upper()
    # # the LDAP values are not always set correctly,
    # # e.g. for FFM there is some faster conn. to LND, so they use 'delnd11'
    # if platform == "win32":
    #     loc_lookup = {"delnd": LND_LOC, "deuu": LND_LOC, "inblr": BLR_LOC, "usabh": ABH_LOC,
    #                   "defrhub": FFM_LOC, "defr": FFM_LOC, "cnj": SHB_LOC, "sgsgpl": SHB_LOC}
    #     if host in ['UUL5S7DW']:
    #         loc_lookup["deuu"] = LND_LOC
    #     elif host in ["LU00209VMA"]:
    #         loc_lookup["deuu"] = DEV_LOC
    #
    #     srvn = None
    #     try:
    #         root = GetObject('LDAP://rootDSE')
    #         srvn = 'LDAP://' + root.Get('dsServiceName')
    #         ntds = GetObject(srvn)
    #         site = GetObject(GetObject(GetObject(ntds.Parent).Parent).Parent)
    #         loc = match(r"(cnj|[a-z]*)\d*", site.Get('cn').lower()).group(1)
    #         if default is not None:
    #             return loc_lookup.get(loc, default)
    #         return loc
    #     except Exception as ex:  # lookup error as user is locked out???
    #         print("unable to lookup LDAP: %s" % (str(ex) if srvn is None else srvn))
    #         return default
    # else:
    loc_lookup = {"LU": LND_LOC, "OZ": BLR_LOC, "AN": ABH_LOC, "FR": FFM_LOC, "UU": LND_LOC, "IT": SHB_LOC,
                  # additional Windows names at the sites:
                  "QH": ABH_LOC, "LS": FFM_LOC, "JD": SHB_LOC}
    if host in ['UULBM6GW']:
        loc_lookup["UU"] = LND_LOC
    elif host in ["LU00209VMA"]:
        loc_lookup["deuu"] = DEV_LOC

    return loc_lookup.get(host[:2], default)


# - continue defines -
# find out our actual location of current computer
LOCATION = location(LND_LOC)
DEFAULT_HEAD_NODE = {ABH_LOC: ABH_HEAD, BLR_LOC: BLR_HEAD, SHB_LOC: SHB_HEAD, FFM_LOC: FFM_HEAD,
                     LND_LOC: LND_HEAD, DEV_LOC: DEV_HEAD}.get(LOCATION, LND_HEAD)
JENKINS_NODES = ["LU00142VMA", "QHS6U6BA", "OZAS016A"]

# ww submit service provided for now by Jenkins monitoring servers
# listing all possible locations so rec files at locations not supported won't break the submit
# but only cause a deployment error for that files
# this table needs to be synchronised with server list in has.views.WW_LOC !!!
WW_SUBMIT_SRV_MAP = {LND_LOC: "LU00179VMA", ABH_LOC: "QHS6U5AA", BLR_LOC: "OZAS021A", FFM_LOC: "LSAS092A",
                     DEV_LOC: "LU00209VMA"}

PY_2_EXE = r"C:\LegacyApp\Python27_64\python.exe"
PY_36_EXE = r"C:\LegacyApp\Python36\python.exe"
PY_38_EXE = PY_3_EXE = r"C:\LegacyApp\Python38\python.exe"
PY_310_EXE = r"C:\LegacyApp\Python310\python.exe"
LIN_EXE = "/usr/bin/python"
LIN_3_EXE = "/usr/bin/python3"
# take care to check the hpcreq_....txt files for each supported version
SHORT_VER = {PY_2_EXE: "2.7", PY_36_EXE: "3.6", PY_38_EXE: "3.8", PY_310_EXE: "3.10"}

HPC_SUPPORTED_CLASSES = ["DEV", "EVA", "ADM", "CIT", "SHT", "AZR"]
HPC_SUPPORTED_TYPES = ['AJS', 'AL2', 'ALL', 'AS2', 'ASL', 'CVT', 'EFS', 'FSI', 'FUS', 'IEX', 'OTH', 'SIM', 'TSF', 'VFR']
HPC_SUPPORTED_FUNCTIONS = ["ACC", "ALN", "ARS", "AWV", "BLD", "CB", "CC", "CCAL", "CD", "CEM", "CIPP", "COD", "CRLS",
                           "DAP", "EBA", "EC", "ECM", "EM", "EMO", "EO", "FB", "FCA", "FPS", "FSD", "GA", "GDR", "GEN",
                           "GFRS", "GP", "GS", "HEAD", "HLA", "HRE", "HVF", "KCM", "LCA", "LD", "LDW", "LKA", "LMK",
                           "LR", "MAC", "MAP", "MCAL", "MFC", "MFL", "MFS", "MLL", "MOS", "OD", "OFC", "OFCF", "OOC",
                           "OT", "PCC", "PD", "PED", "PMD", "PV", "RC", "RCTA", "RDI", "RDT", "RHC", "RIC", "RMHT",
                           "RMP", "RPM", "RSP", "SAC", "SCAL", "SCT", "SDC", "SEP", "SFOD", "SI", "SIB", "SIR", "SLE",
                           "SOD", "SPOD", "SR", "SRL", "SRP", "TLR", "TSA", "UDW", "VC", "VCL", "VDY", "VL", "VOD"]

VALID_NAME = r"(ADM|DMI?)_.+|((%s)_(%s)|0\d{6})_(%s)(_.+)" \
             % ("|".join(HPC_SUPPORTED_CLASSES), "|".join(HPC_SUPPORTED_TYPES), "|".join(HPC_SUPPORTED_FUNCTIONS))

DATA_PATH = r"D:\data" if MSWIN else "/var/hpc"


# - functions ----------------------------------------------------------------------------------------------------------
def validate_name(head, name):  # pylint: disable=R0916
    r"""
    validate name of job (internal)

    **The job name must follow these rules:**

        CCC_TTT_FFF_xxxxxxIxx_shrt_dscr

    .. productionlist::
       job_name: (job_class '_' job_type | ims_issue) '_' job_func '_' sw_version '_' shrt_dscr
       job_class: ['DEV'|'EVA'|'CIT'|'SHT'|'ADM']
       job_type: ["AJS"|"AL2"|"ALL"|"AS2"|"ASL"|"CVT"|"EFS"|"FSI"|"FUS"|"IEX"|"OTH"|"SIM"|"TSF"|"VFR"]
       job_func: ["ARS"|"MFS"|"SRL"|"MFC"|"MFL"|"ACC"|"ALN"|"AWV"|"CB"|"CD"|"CEM"|"CCAL"|"CIPP"|
               :  "COD"|"CRLS"|"EM"|"EBA"|"ECM"|"EMO"|"EO"|"FB"|"FCA"|"FSD"|"GEN"|"HEAD"|"HLA"|
               :  "HRE"|"HVF"|"KCM"|"LCA"|"LD"|"LKA"|"LMK"|"LR"|"MAP"|"MCAL"|"OFC"|"OFCF"|"OT"|"PED"|
               :  "PV"|"RCTA"|"RHC"|"RSP"|"SAC"|"SCT"|"SDC"|"SFOD"|"SI"|"SIB"|"SIR"|"SLE"|"SPOD"|
               :  "SR"|"TLR"|"TSA"|"UDW"|"VCL"|"VDY"|"VL"|"VOD"|"LDW"|"MAC"|"OD"|"SOD"|"GDR"|
               :  "SCAL"|"BLD"|"PMD"]
       sw_version: ['xxxxxxIxx'|'######I##']
       #: [0..9]
       shtr_dscr: [a..z|A..Z|0..9|_]
       ims_issue: [0..9]{6}

    max len: 128 char, no spaces and only ascii char, using following definitions:

    supported classes CCC:

    ===  ===========
    DEV  development, job to develop a function or test
    EVA  evaluation, job for final test reports
    CIT  continuous integration test, automatic submit from Jenkins et.al.
    SHT  short test, job with short run time, result can be deleted early in case of memory problems
    ADM  administration job
    ===  ===========

    supported type names TTT:

    ALL, AL2, SIM, EFS, AJS, FUS, FSI, VFR, IEX, CVT, OTH, ASL, AS2

    supported functions FFF:

    ARS, MFS, SRL, MFC, MFL, ACC, ALN, AWV, CB, CD, CEM, CCAL, CIPP,
    COD, CRLS, EM, EBA, ECM, EMO, EO, FB, FCA, FSD, GEN, HEAD, HLA,
    HRE, HVF, KCM, LCA, LD, LKA, LR, MAP, MCAL, OFC, OFCF, OT, PED,
    PV, RCTA, RHC, RSP, SAC, SCT, SDC, SFOD, SI, SIB, SIR, SLE, SPOD,
    SR, TLR, TSA, UDW, VCL, VDY, VL, VOD, LDW, MAC, OD, SOD, GDR,
    SCAL, BLD, PMD

    version number of SW under test:

    xxxxxxIxx for release and Integration build number, or just that string for testing

    **valid names**::

        EVA_FUS_EBA_123456I02_all_recs
        SHT_SIM_SRL_xxxxxxIxx_test_ped

    this method 'validate_name' is used internally to check the job name:

    :param str head: head node name
    :param str name: name of job to validate
    :return: boolean whether the name follows rules
    :rtype: bool
    """
    try:
        # care about file/folder names: https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
        # pylint: disable=R0916
        if "\\x" in str(name.encode()) or len(name) != len(name.strip()) or len(name) > 128 \
                or search(r"\\|/|:|\*|\?|\"|<|>|\||\.\.|\s", name) or not all(20 < ord(i) < 128 for i in name):
            return False
    except Exception:
        return False

    if head and head in PRODUCTION_HEADS and match(r"^{}$".format(VALID_NAME), name) is None:
        return False

    return True


@suppress_warnings
def validate_project(name):
    """
    validate the project name
    docu: https://confluence.auto.continental.cloud/pages/viewpage.action?spaceKey=ASP&title=HPC+CLUSTER+Team

    :param str name: name of project
    :return: message from SPARCS of what's wrong (in case)
    :rtype: str
    """
    if search(PRJ_EXC, name):
        return -1

    try:
        res = reqget("{}/project/{}".format(SPARCS_URL, quote(name)),
                     proxies={"no_proxy": ".conti.de"}, allow_redirects=True, verify=False)
        return res.json()["id"] if res.status_code == 200 else res.text
    except Exception as _ex:
        return 0


@suppress_warnings
def project_usage(name, resource, duration):
    """
    send resource usage to statusportal

    :param str name: name of project
    :param str resource: resource being used
    :param int duration: duration in [s} being used
    :return: usage info could be posted successfully
    :rtype: bool
    """
    try:
        json = {"project_name": quote(name), "type": resource,
                "end_data": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), "hours_used": duration / 3600}
        res = reqpost("{}/projects".format(SPARCS_URL), json=json,
                      proxies={"no_proxy": ".conti.de"}, allow_redirects=True, verify=False)

        if res.status_code == 200:
            return True
    except Exception as _ex:
        pass
    print("project usage post error!")
    return False


def head_name(default=None):
    """
    :return: head node name
    :rtype: str
    """
    return getenv("CCP_CLUSTER_NAME", getenv("CCP_SCHEDULER", default))


def resolve_alias(alias):
    """
    Resolve a given Network Alias of a machine to a real existing
    pc name inside the network.

    :param alias: Alias of the PC.
    :type alias:  sting
    :return:      real pc-name
    :rtype:       string
    """
    try:
        return gethostbyname_ex(alias)[0].split('.')[0].upper()
    except Exception:
        return alias.upper()


def resolve_ip(server):
    """resolve IP address from server name"""
    cip = gethostbyname_ex(server)[2]
    return cip[randrange(0, len(cip))]


def server_path(head_node):
    """
    **Check if a fast path to server is available**

    Usage mainly to check if we are on a Fast Network (e.g. on HPC),
    then we should be able to access server LIFS010S for fast file transfer.

    **Caution:** this function gets really slow (~4 sec) if the server is not available,
    so use it only where it is really needed!

    :return: path to related head node share folder
    :rtype:  str
    """
    # change with extreme caution!!
    # this function is used by HPC nearly everywhere and therefore an error will stop the complete cloud!
    if head_node not in HPC_STORAGE_MAP:
        return LOCAL_NET_PATH

    # check for S connection (faster)
    server = HPC_STORAGE_MAP[head_node][1]
    if MSWIN:
        fastsrv = replace_server_path(server)
        fastparts = [i for i in fastsrv.split(sep + altsep) if i]

        if call([r"ping", "-n" if MSWIN else "-c", "1", fastparts[0]], stdout=PIPE, stderr=STDOUT) == 0:
            server = fastsrv

    return join(server, "hpc", head_node)


def replace_server_path(arg_list, reverse=False):
    r"""
    replace all server name entries like \\LIFS010 entries
    with the fast connection server name like \\LIFS010s when running on HPC.

    update server names as defined in `REPLACEMENTS` if on_hpc is True

    :param arg_list: input argument list for HPC.
    :type arg_list:  list[string] | str
    :param reverse: do a reverse replace
    :type reverse: bool

    :return: modified argument list.
    :rtype:  list[string]
    """
    if arg_list is None:
        return None

    if isinstance(arg_list, StringTypes):
        arg_list = [arg_list]

        def conv(x):
            """conversation"""
            return x[0]
    else:
        def conv(x):
            """conversation"""
            return x

    clst = arg_list[:]
    for i, v in enumerate(clst):
        for k in REVPLACMENTS if reverse else REPLACEMENTS:
            clst[i] = sub(k[0], k[1], v)
            if clst[i] != v:
                break

    return conv(clst)


def resolve_mail(usr=None):
    """
    resolve email address of user

    :param str usr: user name
    :return: email address
    :rtype: str
    """
    if not usr:
        usr = "{}\\{}".format(getenv("USERDOMAIN"), getenv("USERNAME"))
    try:
        from win32com.client import GetObject, Dispatch  # pylint: disable=C0415
        nres = Dispatch(dispatch="NameTranslate")
        nres.Set(3, usr)
        return GetObject("LDAP://" + nres.Get(1)).Get("mail")
    except Exception:
        return None


def cuda_cores():
    """
    https://stackoverflow.com/questions/63823395/how-can-i-get-the-number-of-cuda-cores-in-my-gpu-using-python-and-numba

    :return: number of total cores available (cuda must be installed)
    :rtype: int
    """
    try:
        dev = cuda.get_current_device()
        return CC_CORES_PER_SM[dev.compute_capability] * getattr(dev, 'MULTIPROCESSOR_COUNT', 0)
    except Exception:
        return 0


def daemon_cmd(cmd, host="localhost", timeout=60.):
    """
    ask HPC daemon to do something

    :param str cmd: command to send to localhost's HPC daemon
    :param str host: hostname to use
    :param float timeout: timeout of connection
    :return: response from localhost's daemon
    :rtype: `data`
    """
    data = "ERR"
    sock = socket(AF_INET, SOCK_STREAM)
    try:
        sock.connect((host, 8092))
        sock.settimeout(timeout)
        if PY2:
            sock.send(cmd + "\n")
        else:
            sock.send((cmd + "\n").encode())
        data = sock.recv(4096).strip()
        sock.close()
    except Exception:
        pass
    return data


def take_offline(host=""):  # pragma: no cover
    """
    take me offline by asking headnode to do so

    :param str host: take host offline
    :return: success status: true/false
    :rtype: bool
    """
    data = "ERR"
    try:
        sock = create_connection((DEFAULT_HEAD_NODE, 8088), 5)
        sock.sendall("cluster=offline(%s)\n" % host)
        data = sock.recv(8).strip()
        sock.close()
    except Exception:
        pass

    return data == "OK"
