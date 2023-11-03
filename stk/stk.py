"""
STK (Scripting Tool Kit)
------------------------

Scripting Tool Kit Package for ADAS Algo Validation

This script returns the release string, date and checkpoint of the current release.

options:
  -v  return only release version as string as ##.##.##
  -c  print out content hash of all python files from stk to see if using unchanged version
  -w  write hash into stk_hash.sha1

"""
# - import Python modules ---------------------------------------------------------------------------------------------
from hashlib import sha1
from os.path import walk, isfile, dirname, exists, join, abspath
from sys import exit as sysexit
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from re import match
from threading import current_thread, Thread


# - defines -----------------------------------------------------------------------------------------------------------
RELEASE = '02.03.37'
INTVERS = 'INT-1'
RELDATE = '17.11.2017'
MKS_ID = 667032
MKS_CP = '1.59'

MIN_SQLITE_VERSION = "3.8.3"

# Jenkins | HPC Nodes
IGNORE_HOST = r"(UU(D296A|L1VAJ)G)|(LU(DS\d{3}|S\d{4})M)$"

__version__ = '_'.join([RELEASE, INTVERS])


# - functions ---------------------------------------------------------------------------------------------------------
def main():
    """info see module level
    """
    args = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter, version=RELEASE)
    args.add_argument('-i', dest='int_rel', action='store_const', const=True,
                      help='return integration release string as ##.##.##_INT-#')
    args.add_argument('-c', dest='hash', action='store_true', default=False,
                      help='calculates sha1 checksum of all python files with STK additionally')
    args.add_argument('-w', dest='writehash', action='store_true', default=False,
                      help='calculates sha1 checksum of all python files and saves it')
    opt = args.parse_args()

    if opt.int_rel:
        return __version__

    print("Scripting Tool Kit Package for ADAS Algo Validation")
    print("Release %s_%s from %s" % (RELEASE, INTVERS, RELDATE))
    print("Checkpoint: %s" % MKS_CP)
    print('')
    print("For Detailed Release Information please see: \n"
          "URL: http://ims-adas:7002/im/issues?selection=%s" % MKS_ID)

    chk_file = join(dirname(__file__), "stk_hash.sha1")
    if opt.writehash:
        with open(chk_file, 'wb') as shafp:
            chk_sum = stk_checksum()
            shafp.write(chk_sum)
            print('your checksum: %s' % chk_sum)

    if opt.hash and exists(chk_file):
        with open(chk_file, 'rb') as shafp:
            chk_sum = shafp.read().strip()
        stk_sum = stk_checksum()
        print('\nstk  checksum: %s' % chk_sum)
        print('your checksum: %s' % stk_sum)
        print("you don't have any modifications." if chk_sum == stk_sum else "you have some modifications inside STK!")


def db_update():
    """update db usage information
    """
    if current_thread().name != "DB update":
        Thread(target=db_update, name='DB update').start()
        return

    from os import environ
    if match(IGNORE_HOST, environ["COMPUTERNAME"].upper()):  # we don't want to log
        return

    try:
        dbexe = VgaDbase()
    except:  # we're unable to connect, so we're leaving it for now
        return

    username = environ["USERDOMAIN"] + "\\" + environ["USERNAME"]
    # check user
    usridx = dbexe("SELECT IID FROM LOG_ITEM WHERE NAME = :name", name=username)
    if len(usridx):
        usridx = usridx[0][0]
    else:
        try:
            # get user description ('name, surname') from ActiveDirectory
            from win32com.client import GetObject
            udesc = GetObject("WinNT://%s,user" % username.replace('\\', '/')).FullName
        except:
            udesc = None

        usridx = dbexe("INSERT INTO LOG_ITEM (NAME, DESCR) VALUES(:name, :descr) RETURNING IID INTO :id",
                       name=username, descr=udesc)

    vernfo = (RELEASE + "_" + INTVERS)[:24]
    # check this SW Version, if first usage, just update table
    veridx = dbexe("SELECT v.VER_IDX FROM APP_VERSIONS v INNER JOIN APP_APP a USING(APP_IDX) "
                   "WHERE a.NAME = 'STK' AND v.VERSION = :ver", ver=vernfo)
    if len(veridx) == 1:
        veridx = veridx[0][0]
    else:
        veridx = dbexe("INSERT INTO APP_VERSIONS (APP_IDX, VERSION) "
                       "VALUES((SELECT APP_IDX FROM APP_APP WHERE NAME = 'STK'), :ver) RETURNING VER_IDX INTO :id",
                       ver=vernfo)

    # update last usage (if none, insert)
    if 0 == dbexe("UPDATE APP_USERMAP SET LAST_USAGE = CURRENT_TIMESTAMP, USAGES = USAGES + 1 "
                  "WHERE VER_IDX = :ver AND USR_IDX = :usr", ver=veridx, usr=usridx):
        dbexe("INSERT INTO APP_USERMAP (VER_IDX, USR_IDX) VALUES(:ver, :usr)", ver=veridx, usr=usridx)


class VgaDbase(object):
    """short val_global_admin interface"""
    def __init__(self):
        """connect to DB"""
        from cx_Oracle import connect, NUMBER
        self._num = NUMBER
        self._db = connect('VAL_GLOBAL_USER', 'PWD4VAL_GLBL', 'racadmpe', threaded=True)
        self("ALTER SESSION SET current_schema = VAL_GLOBAL_ADMIN")

    def __call__(self, stmt, **kw):
        """execute given stmt

        :param stmt: sql to execute
        :return: records retrieved
        """
        cur = self._db.cursor()
        if "RETURNING" in stmt:
            rid = self._db.cursor().var(self._num)
            kw['id'] = rid
            cur.execute(stmt, kw)
            recs = int(rid.getvalue())
        else:
            cur.execute(stmt, kw)
            if stmt.startswith("SELECT"):
                recs = cur.fetchall()
            else:
                recs = cur.rowcount
        cur.close()
        return recs

    def __del__(self):
        """disconnect from DB"""
        if hasattr(self, "_db"):
            self._db.commit()
            self._db.close()


def stk_checksum(compare=False):
    """Recursively calculates a checksum representing the contents of all python files from STK.

    :param compare: compares stk's python files checksum against saved one
    :return: True if equal, False if not
    """
    def _update_checksum(checksum, dir_, filenames):
        """updates checksum, called for each directory through walk

        :param checksum: algo to use
        :param dir_: dir name
        :param filenames: list of filenames
        """
        for filename in sorted(filenames):
            path = join(dir_, filename)
            if isfile(path) and path.endswith('.py'):
                with open(path, 'rb') as fptr:
                    while 1:
                        buf = fptr.read(4096)
                        if not buf:
                            break
                        checksum.update(buf)

    chksum = sha1()
    mydir = dirname(abspath(__file__))
    walk(mydir, _update_checksum, chksum)

    if compare:
        with open(join(mydir, 'stk_hash.sha1'), 'rb') as chkf:
            saved = chkf.read()
        return saved == chksum.hexdigest()

    return chksum.hexdigest()


# - main --------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    sysexit(main())


"""
CHANGE LOG:
-----------
$Log: stk.py  $
Revision 1.97 2017/11/19 19:09:00CET Hospes, Gerd-Joachim (uidv8815) 
autocreate rel VT_STK_02.03.37_INT-1
Revision 1.96 2017/10/27 11:51:05CEST Hospes, Gerd-Joachim (uidv8815) 
prep 2.3.37
Revision 1.95 2017/10/20 17:56:02CEST Hospes, Gerd-Joachim (uidv8815)
rel 2.3.36
Revision 1.94 2017/08/25 17:47:00CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.36
Revision 1.93 2017/08/25 17:24:12CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.35_INT-2
Revision 1.92 2017/08/25 15:52:57CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.35_INT-1
Revision 1.91 2017/08/07 18:46:01CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.35
Revision 1.90 2017/08/07 12:22:36CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.34_INT-1
Revision 1.89 2017/07/21 17:55:07CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.34
Revision 1.88 2017/07/21 16:39:57CEST Hospes, Gerd-Joachim (uidv8815)
rel 2.3.33
Revision 1.86.1.2 2017/07/21 16:32:14CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.33_INT-1
Revision 1.86.1.1 2017/07/03 09:54:14CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.33
Revision 1.86 2017/02/21 22:30:19CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.32_INT-1
Revision 1.85 2016/12/20 09:33:26CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.32
Revision 1.84 2016/12/19 16:47:41CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.31_INT-2
Revision 1.83 2016/12/01 15:37:50CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.32
Revision 1.82 2016/12/01 11:38:15CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.31_INT-1
Revision 1.81 2016/11/11 17:43:07CET Hospes, Gerd-Joachim (uidv8815)
move rel.
Revision 1.80 2016/10/28 17:28:39CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.31
Revision 1.79 2016/10/28 16:39:31CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.30_INT-1
Revision 1.78 2016/10/06 18:06:44CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.30
Revision 1.77 2016/10/01 15:24:04CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.29_INT-1
Revision 1.76 2016/09/20 15:45:29CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.29
Revision 1.75 2016/09/19 18:09:37CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.28_INT-1
Revision 1.74 2016/09/14 16:55:17CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.28
Revision 1.73 2016/08/19 21:26:13CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.27_INT-2
Revision 1.72 2016/08/09 15:02:08CEST Hospes, Gerd-Joachim (uidv8815)
catch GetObject error
Revision 1.71 2016/08/08 17:54:51CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.28
Revision 1.70 2016/08/08 10:41:12CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.27_INT-1
Revision 1.69 2016/07/12 15:54:22CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.27
Revision 1.68 2016/07/08 17:15:45CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.26_INT-1
Revision 1.67 2016/06/24 16:10:16CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.26
Revision 1.66 2016/06/24 13:44:59CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.25_INT-1
Revision 1.65 2016/05/31 16:10:52CEST Hospes, Gerd-Joachim (uidv8815)
prep rel 2.3.25
Revision 1.64 2016/05/31 15:14:50CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.24_INT-1
Revision 1.63 2016/05/24 12:48:07CEST Hospes, Gerd-Joachim (uidv8815)
do not catch db error in VgaDbase init so db_update() gets the error and stops directly
Revision 1.62 2016/05/20 07:53:59CEST Mertens, Sven (uidv7805)
try on connect
Revision 1.61 2016/05/19 17:09:34CEST Hospes, Gerd-Joachim (uidv8815)
check if connected in __del__ to prevent error output
Revision 1.60 2016/05/13 17:29:49CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.24
Revision 1.59 2016/05/13 16:45:22CEST Hospes, Gerd-Joachim (uidv8815)
fix -c for rel 2.3.23
Revision 1.58 2016/05/13 16:14:41CEST Hospes, Gerd-Joachim (uidv8815)
rel 2.3.23
Revision 1.57 2016/05/13 16:11:39CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.23_INT-1
Revision 1.56 2016/04/19 10:49:59CEST Hospes, Gerd-Joachim (uidv8815)
correct rel id
Revision 1.55 2016/04/15 18:13:23CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.23
Revision 1.54 2016/04/15 17:55:16CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.22_INT-1
Revision 1.53 2016/04/04 18:42:13CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.22
Revision 1.52 2016/04/04 17:38:43CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.21_INT-1
Revision 1.51 2016/03/18 18:15:03CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.21
Revision 1.50 2016/03/18 17:00:21CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.20_INT-1
Revision 1.49 2016/02/26 17:48:37CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.20
Revision 1.48 2016/02/26 16:41:37CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.19_INT-1
Revision 1.47 2016/02/16 09:42:37CET Mertens, Sven (uidv7805)
connection should be inside try except
Revision 1.46 2016/02/11 13:46:53CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.19 - fix cp and release id
Revision 1.45 2016/02/05 19:17:02CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.19
Revision 1.44 2016/02/05 18:28:52CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.18_INT-1
Revision 1.43 2016/02/01 16:59:13CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.18
Revision 1.42 2016/02/01 08:47:12CET Mertens, Sven (uidv7805)
fix for user DB update
Revision 1.41 2016/01/26 18:20:05CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.17_INT-1
Revision 1.40 2015/12/18 15:38:29CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.17
Revision 1.37 2015/12/09 13:24:22CET Hospes, Gerd-Joachim (uidv8815)
fix rel issue id
Revision 1.36 2015/12/04 18:52:15CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.16
Revision 1.35 2015/12/04 18:22:25CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.15_INT-1
Revision 1.34 2015/11/20 17:34:34CET Hospes, Gerd-Joachim (uidv8815)
prep 2.3.15
- Added comments -  uidv8815 [Nov 20, 2015 5:34:34 PM CET]
Change Package : 398693:1 http://mks-psad:7002/im/viewissue?selection=398693
Revision 1.33 2015/11/20 15:41:09CET Hospes, Gerd-Joachim (uidv8815)
rel 2.3.14
--- Added comments ---  uidv8815 [Nov 20, 2015 3:41:09 PM CET]
Change Package : 398499:1 http://mks-psad:7002/im/viewissue?selection=398499
Revision 1.32 2015/11/06 16:45:53CET Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.13_INT-1
--- Added comments ---  uidv8815 [Nov 6, 2015 4:45:53 PM CET]
Change Package : 390002:1 http://mks-psad:7002/im/viewissue?selection=390002
Revision 1.31 2015/10/26 16:39:37CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
--- Added comments ---  uidv8815 [Oct 26, 2015 4:39:38 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.30 2015/10/24 18:41:15CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.13
--- Added comments ---  uidv8815 [Oct 24, 2015 6:41:16 PM CEST]
Change Package : 390002:1 http://ims-adas:7002/im/viewissue?selection=390002
Revision 1.29 2015/10/23 10:57:54CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.12_INT-1
--- Added comments ---  uidv8815 [Oct 23, 2015 10:57:55 AM CEST]
Change Package : 385131:1 http://ims-adas:7002/im/viewissue?selection=385131
Revision 1.28 2015/10/12 10:00:41CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.12
--- Added comments ---  uidv8815 [Oct 12, 2015 10:00:42 AM CEST]
Change Package : 385131:1 http://ims-adas:7002/im/viewissue?selection=385131
Revision 1.27 2015/10/09 18:10:30CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.11_INT-1
--- Added comments ---  uidv8815 [Oct 9, 2015 6:10:30 PM CEST]
Change Package : 380676:1 http://ims-adas:7002/im/viewissue?selection=380676
Revision 1.26 2015/09/25 16:12:52CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.11
--- Added comments ---  uidv8815 [Sep 25, 2015 4:12:52 PM CEST]
Change Package : 380676:1 http://ims-adas:7002/im/viewissue?selection=380676
Revision 1.24 2015/09/11 16:56:40CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.10
--- Added comments ---  uidv8815 [Sep 11, 2015 4:56:41 PM CEST]
Change Package : 376211:1 http://ims-adas:7002/im/viewissue?selection=376211
Revision 1.22 2015/08/31 09:54:23CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.9
--- Added comments ---  uidv8815 [Aug 31, 2015 9:54:24 AM CEST]
Change Package : 371701:1 http://ims-adas:7002/im/viewissue?selection=371701
Revision 1.21 2015/08/28 16:16:10CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.08_INT-1
--- Added comments ---  uidv8815 [Aug 28, 2015 4:16:11 PM CEST]
Change Package : 368569:1 http://ims-adas:7002/im/viewissue?selection=368569
Revision 1.20 2015/08/18 09:16:10CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.8
--- Added comments ---  uidv8815 [Aug 18, 2015 9:16:11 AM CEST]
Change Package : 368569:1 http://ims-adas:7002/im/viewissue?selection=368569
Revision 1.19 2015/08/17 16:34:22CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.07_INT-1
--- Added comments ---  uidv8815 [Aug 17, 2015 4:34:23 PM CEST]
Change Package : 363415:2 http://ims-adas:7002/im/viewissue?selection=363415
Revision 1.18 2015/08/03 10:15:55CEST Mertens, Sven (uidv7805)
adaptation to new table structure
--- Added comments ---  uidv7805 [Aug 3, 2015 10:15:56 AM CEST]
Change Package : 363417:1 http://ims-adas:7002/im/viewissue?selection=363417
Revision 1.17 2015/07/31 17:54:43CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.7
--- Added comments ---  uidv8815 [Jul 31, 2015 5:54:44 PM CEST]
Change Package : 363415:1 http://ims-adas:7002/im/viewissue?selection=363415
Revision 1.16 2015/07/31 17:25:08CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.06_INT-1
--- Added comments ---  uidv8815 [Jul 31, 2015 5:25:09 PM CEST]
Change Package : 357931:2 http://ims-adas:7002/im/viewissue?selection=357931
Revision 1.15 2015/07/17 19:07:16CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.6
--- Added comments ---  uidv8815 [Jul 17, 2015 7:07:17 PM CEST]
Change Package : 357931:1 http://ims-adas:7002/im/viewissue?selection=357931
Revision 1.14 2015/07/17 18:06:09CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.05_INT-1
--- Added comments ---  uidv8815 [Jul 17, 2015 6:06:09 PM CEST]
Change Package : 353993:1 http://ims-adas:7002/im/viewissue?selection=353993
Revision 1.13 2015/07/06 16:54:04CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.5 v2
--- Added comments ---  uidv8815 [Jul 6, 2015 4:54:04 PM CEST]
Change Package : 353993:1 http://ims-adas:7002/im/viewissue?selection=353993
Revision 1.12 2015/07/06 16:52:31CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.5
Revision 1.11 2015/07/03 16:30:27CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.04_INT-1
--- Added comments ---  uidv8815 [Jul 3, 2015 4:30:28 PM CEST]
Change Package : 349479:1 http://ims-adas:7002/im/viewissue?selection=349479
Revision 1.10 2015/06/19 15:40:15CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.4
--- Added comments ---  uidv8815 [Jun 19, 2015 3:40:15 PM CEST]
Change Package : 349479:1 http://ims-adas:7002/im/viewissue?selection=349479
Revision 1.9 2015/06/19 14:46:49CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.03_INT-1
--- Added comments ---  uidv8815 [Jun 19, 2015 2:46:50 PM CEST]
Change Package : 341328:1 http://ims-adas:7002/im/viewissue?selection=341328
Revision 1.8 2015/06/08 15:34:18CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.3 again
--- Added comments ---  uidv8815 [Jun 8, 2015 3:34:18 PM CEST]
Change Package : 341328:1 http://ims-adas:7002/im/viewissue?selection=341328
Revision 1.7 2015/06/01 14:27:11CEST Hecker, Robert (heckerr)
Preparation for upcoming cp.
--- Added comments ---  heckerr [Jun 1, 2015 2:27:11 PM CEST]
Change Package : 343765:1 http://ims-adas:7002/im/viewissue?selection=343765
Revision 1.6 2015/05/22 17:55:40CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.3
--- Added comments ---  uidv8815 [May 22, 2015 5:55:40 PM CEST]
Change Package : 341328:1 http://ims-adas:7002/im/viewissue?selection=341328
Revision 1.5 2015/05/22 14:56:19CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.02_INT-1
--- Added comments ---  uidv8815 [May 22, 2015 2:56:20 PM CEST]
Change Package : 336934:1 http://ims-adas:7002/im/viewissue?selection=336934
Revision 1.4 2015/05/11 15:32:11CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.2
--- Added comments ---  uidv8815 [May 11, 2015 3:32:12 PM CEST]
Change Package : 336934:1 http://ims-adas:7002/im/viewissue?selection=336934
Revision 1.3 2015/05/08 18:10:08CEST Hospes, Gerd-Joachim (uidv8815)
autocreate rel VT_STK_02.03.01_INT-1
--- Added comments ---  uidv8815 [May 8, 2015 6:10:08 PM CEST]
Change Package : 331867:1 http://ims-adas:7002/im/viewissue?selection=331867
Revision 1.2 2015/04/30 11:09:26CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:26 AM CEST]
Change Package : 330394:1 http://ims-adas:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/28 17:34:22CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/project.pj
Revision 1.67 2015/04/23 17:55:25CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.3.1
--- Added comments ---  uidv8815 [Apr 23, 2015 5:55:25 PM CEST]
Change Package : 331867:1 http://ims-adas:7002/im/viewissue?selection=331867
Revision 1.66 2015/04/23 15:53:35CEST Hospes, Gerd-Joachim (uidv8815)
rel 2.2.5
--- Added comments ---  uidv8815 [Apr 23, 2015 3:53:35 PM CEST]
Change Package : 327131:1 http://ims-adas:7002/im/viewissue?selection=327131
Revision 1.65 2015/04/16 10:21:55CEST Hospes, Gerd-Joachim (uidv8815)
fix mks id
--- Added comments ---  uidv8815 [Apr 16, 2015 10:21:55 AM CEST]
Change Package : 327131:1 http://ims-adas:7002/im/viewissue?selection=327131
Revision 1.64 2015/04/10 16:40:35CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.2.5
--- Added comments ---  uidv8815 [Apr 10, 2015 4:40:35 PM CEST]
Change Package : 327131:1 http://ims-adas:7002/im/viewissue?selection=327131
Revision 1.62 2015/03/30 14:13:48CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.2.4
--- Added comments ---  uidv8815 [Mar 30, 2015 2:13:49 PM CEST]
Change Package : 323313:1 http://ims-adas:7002/im/viewissue?selection=323313
Revision 1.61 2015/03/27 16:59:31CET Hospes, Gerd-Joachim (uidv8815)
rel 2.2.3
--- Added comments ---  uidv8815 [Mar 27, 2015 4:59:31 PM CET]
Change Package : 317330:1 http://ims-adas:7002/im/viewissue?selection=317330
Revision 1.60 2015/03/19 18:39:29CET Hospes, Gerd-Joachim (uidv8815)
fix mks issue no
--- Added comments ---  uidv8815 [Mar 19, 2015 6:39:29 PM CET]
Change Package : 317330:1 http://ims-adas:7002/im/viewissue?selection=317330
Revision 1.59 2015/03/13 16:01:36CET Hospes, Gerd-Joachim (uidv8815)
prep 2.2.3
--- Added comments ---  uidv8815 [Mar 13, 2015 4:01:37 PM CET]
Change Package : 317330:1 http://ims-adas:7002/im/viewissue?selection=317330
Revision 1.58 2015/03/13 15:51:40CET Hospes, Gerd-Joachim (uidv8815)
rel 2.2.2
--- Added comments ---  uidv8815 [Mar 13, 2015 3:51:41 PM CET]
Change Package : 311672:1 http://ims-adas:7002/im/viewissue?selection=311672
Revision 1.57 2015/03/11 17:27:32CET Hospes, Gerd-Joachim (uidv8815)
add intver to version str
--- Added comments ---  uidv8815 [Mar 11, 2015 5:27:33 PM CET]
Change Package : 311672:1 http://ims-adas:7002/im/viewissue?selection=311672
Revision 1.56 2015/03/05 16:50:03CET Hospes, Gerd-Joachim (uidv8815)
fix use app error, start thread
--- Added comments ---  uidv8815 [Mar 5, 2015 4:50:03 PM CET]
Change Package : 311672:1 http://ims-adas:7002/im/viewissue?selection=311672
Revision 1.55 2015/03/03 11:03:02CET Mertens, Sven (uidv7805)
cast int to str for CP_ID
--- Added comments ---  uidv7805 [Mar 3, 2015 11:03:02 AM CET]
Change Package : 312115:1 http://ims-adas:7002/im/viewissue?selection=312115
Revision 1.54 2015/03/02 16:53:32CET Hospes, Gerd-Joachim (uidv8815)
prep 2.2.2
--- Added comments ---  uidv8815 [Mar 2, 2015 4:53:33 PM CET]
Change Package : 311672:1 http://ims-adas:7002/im/viewissue?selection=311672
Revision 1.53 2015/02/27 13:11:23CET Hospes, Gerd-Joachim (uidv8815)
rel 2.2.1
--- Added comments ---  uidv8815 [Feb 27, 2015 1:11:23 PM CET]
Change Package : 300340:1 http://ims-adas:7002/im/viewissue?selection=300340
Revision 1.52 2015/02/27 09:35:20CET Hospes, Gerd-Joachim (uidv8815)
prep 2.2.1
--- Added comments ---  uidv8815 [Feb 27, 2015 9:35:20 AM CET]
Change Package : 300340:1 http://ims-adas:7002/im/viewissue?selection=300340
Revision 1.51 2015/02/20 09:49:05CET Hospes, Gerd-Joachim (uidv8815)
rel 2.2.0_INT-4
Revision 1.50 2015/02/17 08:24:52CET Hospes, Gerd-Joachim (uidv8815)
prep 2.2.0
--- Added comments ---  uidv8815 [Feb 17, 2015 8:24:52 AM CET]
Change Package : 307327:1 http://ims-adas:7002/im/viewissue?selection=307327
Revision 1.49 2015/02/16 15:33:43CET Hospes, Gerd-Joachim (uidv8815)
and update to INT-2
--- Added comments ---  uidv8815 [Feb 16, 2015 3:33:43 PM CET]
Change Package : 301812:1 http://ims-adas:7002/im/viewissue?selection=301812
Revision 1.48 2015/02/16 15:20:28CET Hospes, Gerd-Joachim (uidv8815)
update cp number
--- Added comments ---  uidv8815 [Feb 16, 2015 3:20:28 PM CET]
Change Package : 301812:1 http://ims-adas:7002/im/viewissue?selection=301812
Revision 1.47 2015/02/16 10:32:05CET Hospes, Gerd-Joachim (uidv8815)
add cp for 2.1.28
--- Added comments ---  uidv8815 [Feb 16, 2015 10:32:05 AM CET]
Change Package : 301812:1 http://ims-adas:7002/im/viewissue?selection=301812
Revision 1.46 2015/02/16 10:21:31CET Hospes, Gerd-Joachim (uidv8815)
create rel 2.1.28
--- Added comments ---  uidv8815 [Feb 16, 2015 10:21:31 AM CET]
Change Package : 301812:1 http://ims-adas:7002/im/viewissue?selection=301812
Revision 1.45 2015/01/30 17:40:39CET Hospes, Gerd-Joachim (uidv8815)
prep 2.1.28
--- Added comments ---  uidv8815 [Jan 30, 2015 5:40:40 PM CET]
Change Package : 301812:1 http://ims-adas:7002/im/viewissue?selection=301812
Revision 1.44 2015/01/30 16:36:38CET Hospes, Gerd-Joachim (uidv8815)
rel 2.1.27
--- Added comments ---  uidv8815 [Jan 30, 2015 4:36:39 PM CET]
Change Package : 296832:1 http://ims-adas:7002/im/viewissue?selection=296832
Revision 1.43 2015/01/29 11:05:06CET Mertens, Sven (uidv7805)
removing some pylint errors on top
--- Added comments ---  uidv7805 [Jan 29, 2015 11:05:07 AM CET]
Change Package : 299025:1 http://ims-adas:7002/im/viewissue?selection=299025
Revision 1.42 2015/01/29 10:40:31CET Mertens, Sven (uidv7805)
as update background thread initialized Logger first,
so taking over minimum things from BaseDB.
Revision 1.41 2015/01/22 10:37:57CET Mertens, Sven (uidv7805)
adding define for minimum sqlite version
--- Added comments ---  uidv7805 [Jan 22, 2015 10:37:58 AM CET]
Change Package : 270558:1 http://ims-adas:7002/im/viewissue?selection=270558
Revision 1.40 2015/01/19 13:17:37CET Mertens, Sven (uidv7805)
update4thread
--- Added comments ---  uidv7805 [Jan 19, 2015 1:17:37 PM CET]
Change Package : 296850:1 http://ims-adas:7002/im/viewissue?selection=296850
Revision 1.39 2015/01/16 14:56:23CET Hospes, Gerd-Joachim (uidv8815)
prep 2.1.27
--- Added comments ---  uidv8815 [Jan 16, 2015 2:56:24 PM CET]
Change Package : 296832:1 http://ims-adas:7002/im/viewissue?selection=296832
Revision 1.38 2015/01/16 14:23:49CET Mertens, Sven (uidv7805)
adding direct writing option for sha1 checksum file
--- Added comments ---  uidv7805 [Jan 16, 2015 2:23:50 PM CET]
Change Package : 296851:1 http://ims-adas:7002/im/viewissue?selection=296851
Revision 1.37 2015/01/16 14:16:16CET Mertens, Sven (uidv7805)
adding checksum option (-c) to print out sha1
Revision 1.36 2015/01/16 11:43:50CET Hospes, Gerd-Joachim (uidv8815)
rel 2.1.26_INT-2 with correct checkpoint id
--- Added comments ---  uidv8815 [Jan 16, 2015 11:43:51 AM CET]
Change Package : 292840:1 http://ims-adas:7002/im/viewissue?selection=292840
Revision 1.35 2015/01/16 10:58:40CET Hospes, Gerd-Joachim (uidv8815)
rel 2.1.26
--- Added comments ---  uidv8815 [Jan 16, 2015 10:58:40 AM CET]
Change Package : 292840:1 http://ims-adas:7002/im/viewissue?selection=292840
Revision 1.34 2015/01/15 13:10:56CET Mertens, Sven (uidv7805)
hostname --> computername
--- Added comments ---  uidv7805 [Jan 15, 2015 1:10:57 PM CET]
Change Package : 296252:1 http://ims-adas:7002/im/viewissue?selection=296252
Revision 1.33 2014/12/18 11:46:48CET Hospes, Gerd-Joachim (uidv8815)
prep 2.1.26
--- Added comments ---  uidv8815 [Dec 18, 2014 11:46:49 AM CET]
Change Package : 292840:1 http://ims-adas:7002/im/viewissue?selection=292840
Revision 1.32 2014/12/18 11:01:20CET Hospes, Gerd-Joachim (uidv8815)
rel 2.1.25
--- Added comments ---  uidv8815 [Dec 18, 2014 11:01:20 AM CET]
Change Package : 292764:1 http://ims-adas:7002/im/viewissue?selection=292764
Revision 1.31 2014/12/16 17:17:25CET Hospes, Gerd-Joachim (uidv8815)
prep 2.1.25
--- Added comments ---  uidv8815 [Dec 16, 2014 5:17:25 PM CET]
Change Package : 283688:1 http://ims-adas:7002/im/viewissue?selection=283688
Revision 1.30 2014/12/08 11:46:38CET Mertens, Sven (uidv7805)
update according CR
--- Added comments ---  uidv7805 [Dec 8, 2014 11:46:39 AM CET]
Change Package : 288772:1 http://ims-adas:7002/im/viewissue?selection=288772
Revision 1.29 2014/12/05 13:25:38CET Hospes, Gerd-Joachim (uidv8815)
rel 2.1.24
--- Added comments ---  uidv8815 [Dec 5, 2014 1:25:39 PM CET]
Change Package : 283688:1 http://ims-adas:7002/im/viewissue?selection=283688
Revision 1.28 2014/11/21 17:53:43CET Hospes, Gerd-Joachim (uidv8815)
prep 2.1.24
--- Added comments ---  uidv8815 [Nov 21, 2014 5:53:44 PM CET]
Change Package : 283688:1 http://ims-adas:7002/im/viewissue?selection=283688
Revision 1.26 2014/11/07 17:33:20CET Hospes, Gerd-Joachim (uidv8815)
prep 2.1.23
--- Added comments ---  uidv8815 [Nov 7, 2014 5:33:21 PM CET]
Change Package : 279149:1 http://ims-adas:7002/im/viewissue?selection=279149
Revision 1.25 2014/11/07 16:24:05CET Hospes, Gerd-Joachim (uidv8815)
create rel 2.1.23
--- Added comments ---  uidv8815 [Nov 7, 2014 4:24:06 PM CET]
Change Package : 275075:1 http://ims-adas:7002/im/viewissue?selection=275075
Revision 1.24 2014/10/24 16:52:58CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.1.22
--- Added comments ---  uidv8815 [Oct 24, 2014 4:52:59 PM CEST]
Change Package : 275075:1 http://ims-adas:7002/im/viewissue?selection=275075
Revision 1.23 2014/10/24 14:43:22CEST Hospes, Gerd-Joachim (uidv8815)
rel 2.1.21
--- Added comments ---  uidv8815 [Oct 24, 2014 2:43:23 PM CEST]
Change Package : 270444:1 http://ims-adas:7002/im/viewissue?selection=270444
Revision 1.22 2014/10/13 10:21:32CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.1.21
--- Added comments ---  uidv8815 [Oct 13, 2014 10:21:33 AM CEST]
Change Package : 270444:1 http://ims-adas:7002/im/viewissue?selection=270444
Revision 1.20 2014/09/29 11:25:22CEST Hospes, Gerd-Joachim (uidv8815)
set prep for 2.1.20
--- Added comments ---  uidv8815 [Sep 29, 2014 11:25:22 AM CEST]
Change Package : 267675:1 http://ims-adas:7002/im/viewissue?selection=267675
Revision 1.19 2014/09/26 13:01:22CEST Hospes, Gerd-Joachim (uidv8815)
fix naming
--- Added comments ---  uidv8815 [Sep 26, 2014 1:01:23 PM CEST]
Change Package : 264019:1 http://ims-adas:7002/im/viewissue?selection=264019
Revision 1.18 2014/09/26 12:54:41CEST Hospes, Gerd-Joachim (uidv8815)
rel 2.1.20
--- Added comments ---  uidv8815 [Sep 26, 2014 12:54:42 PM CEST]
Change Package : 264019:1 http://ims-adas:7002/im/viewissue?selection=264019
Revision 1.17 2014/09/15 09:02:55CEST Hecker, Robert (heckerr)
Updated Release Information for upcoming CP.
--- Added comments ---  heckerr [Sep 15, 2014 9:02:55 AM CEST]
Change Package : 260941:1 http://ims-adas:7002/im/viewissue?selection=260941
Revision 1.16 2014/09/14 17:27:26CEST Hecker, Robert (heckerr)
Updated Version Info for upcoming release.
--- Added comments ---  heckerr [Sep 14, 2014 5:27:27 PM CEST]
Change Package : 260941:1 http://ims-adas:7002/im/viewissue?selection=260941
Revision 1.15 2014/08/29 15:06:38CEST Hospes, Gerd-Joachim (uidv8815)
rel 2.1.17
--- Added comments ---  uidv8815 [Aug 29, 2014 3:06:38 PM CEST]
Change Package : 253121:1 http://ims-adas:7002/im/viewissue?selection=253121
Revision 1.14 2014/08/21 18:01:15CEST Hospes, Gerd-Joachim (uidv8815)
add integration and mks id string and option -i to return integration version
--- Added comments ---  uidv8815 [Aug 21, 2014 6:01:15 PM CEST]
Change Package : 253467:1 http://ims-adas:7002/im/viewissue?selection=253467
Revision 1.13 2014/08/18 09:41:49CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.1.17
--- Added comments ---  uidv8815 [Aug 18, 2014 9:41:50 AM CEST]
Change Package : 253121:1 http://ims-adas:7002/im/viewissue?selection=253121
Revision 1.12 2014/08/15 18:48:12CEST Hospes, Gerd-Joachim (uidv8815)
prep rel 2.1.16
--- Added comments ---  uidv8815 [Aug 15, 2014 6:48:12 PM CEST]
Change Package : 253118:1 http://ims-adas:7002/im/viewissue?selection=253118
Revision 1.11 2014/08/11 19:02:55CEST Hospes, Gerd-Joachim (uidv8815)
prep 2.1.16
--- Added comments ---  uidv8815 [Aug 11, 2014 7:02:56 PM CEST]
Change Package : 250913:2 http://ims-adas:7002/im/viewissue?selection=250913
Revision 1.10 2014/08/01 15:12:27CEST Hospes, Gerd-Joachim (uidv8815)
create rel 2.1.15
--- Added comments ---  uidv8815 [Aug 1, 2014 3:12:27 PM CEST]
Change Package : 250913:1 http://ims-adas:7002/im/viewissue?selection=250913
Revision 1.9 2014/07/24 10:43:54CEST Hospes, Gerd-Joachim (uidv8815)
2.1.15 prep
--- Added comments ---  uidv8815 [Jul 24, 2014 10:43:54 AM CEST]
Change Package : 250913:1 http://ims-adas:7002/im/viewissue?selection=250913
Revision 1.8 2014/07/18 13:40:02CEST Hospes, Gerd-Joachim (uidv8815)
build 2.1.14_INT-1
--- Added comments ---  uidv8815 [Jul 18, 2014 1:40:03 PM CEST]
Change Package : 245481:1 http://ims-adas:7002/im/viewissue?selection=245481
Revision 1.7 2014/07/07 16:34:25CEST Hospes, Gerd-Joachim (uidv8815)
set rel to 2.1.14 pre
--- Added comments ---  uidv8815 [Jul 7, 2014 4:34:26 PM CEST]
Change Package : 245481:1 http://ims-adas:7002/im/viewissue?selection=245481
Revision 1.6 2014/07/03 11:03:56CEST Hospes, Gerd-Joachim (uidv8815)
update for rel 02.01.13
--- Added comments ---  uidv8815 [Jul 3, 2014 11:03:57 AM CEST]
Change Package : 243906:1 http://ims-adas:7002/im/viewissue?selection=243906
Revision 1.5 2014/06/23 09:50:12CEST Hospes, Gerd-Joachim (uidv8815)
update for rel 2.1.12_INT-1
--- Added comments ---  uidv8815 [Jun 23, 2014 9:50:12 AM CEST]
Change Package : 243589:1 http://ims-adas:7002/im/viewissue?selection=243589
Revision 1.4 2014/05/21 16:53:47CEST Hospes, Gerd-Joachim (uidv8815)
add __version__ and remove mks strings
--- Added comments ---  uidv8815 [May 21, 2014 4:53:47 PM CEST]
Change Package : 236981:1 http://ims-adas:7002/im/viewissue?selection=236981
Revision 1.3 2014/05/15 18:21:30CEST Hospes, Gerd-Joachim (uidv8815)
again, ProjectLabel was not modified druing checkin
--- Added comments ---  uidv8815 [May 15, 2014 6:21:31 PM CEST]
Change Package : 236981:1 http://ims-adas:7002/im/viewissue?selection=236981
Revision 1.2 2014/05/15 18:14:48CEST Hospes, Gerd-Joachim (uidv8815)
use revision label as version string
--- Added comments ---  uidv8815 [May 15, 2014 6:14:48 PM CEST]
Change Package : 236981:1 http://ims-adas:7002/im/viewissue?selection=236981
Revision 1.1 2014/05/15 17:20:25CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/project.pj
"""
