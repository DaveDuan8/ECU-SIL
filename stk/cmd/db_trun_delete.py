# -*- coding:utf-8 -*-
"""
db_trun_delete
--------------

**Features:**
    - Delete Testrun from database
    - Target Database is Oracle
    - Only Database with ADMIN rights can run this script

**UseCase:**e
 Occasionally use to perform to delete testrun data permanently to keep the
 database clean

**Usage:**

db_trun_delete.py -q RACADMPE -u MyDatabaseuser -p MyDatabasePassword -c MyDatabaseMasterSCHEMA
                  -l max_no_trun_to_delete -t testrun_name -v checkpoint -n project_name

Parameters:

-f path_to_dbs_qliteFile
-q RACADMPE
-u MyDatabaseuser
-p MyDatabasePassword
-c MyDatabaseMasterSCHEMA
-l max_no_trun_to_delete
-t testrun_name
-v checkpoint
-n project_name


**1. Example:**
Command line usage to physically delete all testrun marked as deleted
python db_trun_delete -q RACADMPE -u MyOracleDbUser  -p MyOracleDbPassword -c  MyMasterSchema
                    -l -1
**2. Example:**
Command line usage to physically delete 20 testrun which are marked as deleted
python db_trun_delete -q RACADMPE -u MyOracleDbUser  -p MyOracleDbPassword -c  MyMasterSchema
                    -l 20

**3. Example:**
Command line usage to physically delete all testrun which are marked as deleted
with testrun name Mytestrun

python db_trun_delete -q RACADMPE -u MyOracleDbUser  -p MyOracleDbPassword -c  MyMasterSchema
                    -l -1 -t MytestrunName

:org:           Continental AG
:author:        Zaheer Ahmed

:version:       $Revision: 1.4 $
:contact:       $Author: Ahmed, Zaheer (uidu7634) $ (last change)
:date:          $Date: 2016/07/08 10:38:33CEST $
"""

from os import path as ospath
from sys import path as syspath
from optparse import OptionParser
from datetime import datetime
STK_FOLDER = ospath.abspath(ospath.join(ospath.split(__file__)[0], r"..\.."))
if STK_FOLDER not in syspath:
    syspath.append(STK_FOLDER)

from stk.db import ERROR_TOLERANCE_NONE
from stk.db.val.val import BaseValResDB
from stk.db.gbl.gbl import BaseGblDB
from stk.util.logger import Logger
# Global defination of the variable

MODE_INFO = 15
MODE_DEBUG = 10
MODE = MODE_DEBUG


class DbTestRunDelete(object):
    """
        Db TestRun Data Delete Utility Class
    """
    def __init__(self):

        self.__dbfile = None
        self.__masterdbdsn = None
        self.__masterdbdbq = None
        self.__masterdbuser = None
        self.__masterdbpassword = None
        self.__masterdbschemaprefix = None
        self.__db_connector = None
        self.__masterdbdrv = None
        self.__trname = None
        self.__checkpoint = None
        self.__projname = None
        self.__limit = 10
        self.__trids = []
        self.__logger = Logger(self.__class__.__name__, level=MODE)
        self._dbgbl = None
        self._dbval = None

    def __initialize(self, line=None):
        """
        Initialize Export process with Establishing connection and parsing argument
        """
        self.__parse_arguements(line)

        if self.__dbfile is None:
            self._dbval = BaseValResDB("uid=%s;pwd=%s" % (self.__masterdbuser, self.__masterdbpassword),
                                       table_prefix="%s." % (self.__masterdbuser),
                                       error_tolerance=ERROR_TOLERANCE_NONE)
            self._dbgbl = BaseGblDB("uid=%s;pwd=%s" % (self.__masterdbuser, self.__masterdbpassword),
                                    table_prefix="%s." % (self.__masterdbuser), error_tolerance=ERROR_TOLERANCE_NONE)
        else:
            self._dbval = BaseValResDB(self.__dbfile, error_tolerance=ERROR_TOLERANCE_NONE)
            self._dbgbl = BaseGblDB(self.__dbfile,
                                    table_prefix="%s." % (self.__masterdbuser), error_tolerance=ERROR_TOLERANCE_NONE)

    def __terminate(self):
        """
        Terminating method with closing database connections
        """
        self._dbval.close()
        self._dbgbl.close()

    def __parse_arguements(self, line=None):
        """
        Parsing commandline arguements
        """
        optparser = OptionParser(usage="usage: %prog [options] command")
        optparser.add_option("-f", "--dbfile", dest="dbfile", help="The name of the Sqlite database file. ")
        optparser.add_option("-b", "--master-db-dsn", dest="masterdbdsn", help="The name of the DSN.")
        optparser.add_option("-q", "--master-db-dbq", dest="masterdbdbq", help="The name of the DBQ.")
        optparser.add_option("-u", "--master-db-user", dest="masterdbuser",
                             help="The name of the oracle database user.")
        optparser.add_option("-p", "--master-db-password", dest="masterdbpassword",
                             help="The name of the oracle database password.")
        optparser.add_option("-c", "--master-db-schema-prefix", dest="masterdbschemaprefix",
                             help="The name of the oracle database schema prefix.")
        optparser.add_option("-l", "--limit", dest="limit",
                             help="MAX no. of parent testrun deleted e.g. default:10, -1 all deleted testrun")
        optparser.add_option("-t", "--trname", dest="trname", help="Testrun to import export")
        optparser.add_option("-v", "--checkpoint", dest="checkpoint", help="Checkpoint")
        optparser.add_option("-n", "--prname", dest="prname", help="Project Name e.g. ARS400_PR")

        if line is not None:
            cmd_options = optparser.parse_args(line.split())
        else:
            cmd_options = optparser.parse_args()

        self.__dbfile = cmd_options[0].dbfile
        self.__masterdbdsn = cmd_options[0].masterdbdsn
        self.__masterdbdbq = cmd_options[0].masterdbdbq
        self.__masterdbuser = cmd_options[0].masterdbuser
        self.__masterdbpassword = cmd_options[0].masterdbpassword
        self.__masterdbschemaprefix = cmd_options[0].masterdbschemaprefix
        if cmd_options[0].limit is not None:
            self.__limit = int(cmd_options[0].limit)
        self.__trname = cmd_options[0].trname
        self.__checkpoint = cmd_options[0].checkpoint
        self.__projname = cmd_options[0].prname

    def delete_test_run_data(self, line=None):
        """
        Main function of DB Delete Testrun
        """
        start_date = datetime.now()
        self.__logger.info("Starting TestRun Delete at %s" % start_date.strftime("%d-%m-%Y %H:%M:%S"))
        self.__initialize(line)
        if self.__projname is not None:
            pid = self._dbgbl.GetProjectId(self.__projname.upper())
        else:
            pid = None
        self.__trids = self._dbval.get_deleted_testrun_ids(name=self.__trname,
                                                           checkpoint=self.__checkpoint,
                                                           pid=pid, limit=self.__limit, distinct=False)
        for trid in self.__trids:
            self._dbval.delete_testrun(tr_id=trid)

        for trid in reversed(self.__trids):
            tr_rec = self._dbval.get_testrun(tr_id=trid)
            if len(tr_rec) > 0:
                self.__logger.error("Testrun with Id = %d delete attempt failed" % trid)
                self.__logger.error("Delete operation Aborted with no Commit Changes in Database")
                raise StandardError("Operation Aborted")

        end_date = datetime.now()
        duration = end_date - start_date
        self._dbval.commit()
        print str(tuple(self.__trids))
        self.__logger.info("Delete Finshed with Total Duration = %s " % str(duration))
        self.__logger.info("Total Testrun deleted = %s " % str(len(self.__trids)))
        print "exit"


def main():
    """
    Main Function
    """
    db_trun_del = DbTestRunDelete()
    db_trun_del.delete_test_run_data()


if __name__ == '__main__':
    main()


"""
CHANGE LOG:
-----------
$Log: db_trun_delete.py  $
Revision 1.4 2016/07/08 10:38:33CEST Ahmed, Zaheer (uidu7634) 
bug fix for db connection
Revision 1.3 2016/07/08 09:48:07CEST Ahmed, Zaheer (uidu7634)
reuse stk test trun feature from interface after optimization. Remove the duplicate implementation
Revision 1.2 2016/03/31 16:31:35CEST Mertens, Sven (uidv7805)
pylint fix
Revision 1.1 2015/04/23 19:03:45CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.16 2015/01/28 08:00:16CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 28, 2015 8:00:16 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.15 2015/01/20 08:07:44CET Mertens, Sven (uidv7805)
minor fix
Revision 1.14 2015/01/19 08:50:13CET Ahmed, Zaheer (uidu7634)
bug fix to get all edid and  attrid seperately
--- Added comments ---  uidu7634 [Jan 19, 2015 8:50:14 AM CET]
Change Package : 279151:2 http://mks-psad:7002/im/viewissue?selection=279151
Revision 1.12 2014/12/18 01:12:58CET Hospes, Gerd-Joachim (uidv8815)
remove deprecated methods based on db.val
--- Added comments ---  uidv8815 [Dec 18, 2014 1:12:59 AM CET]
Change Package : 281282:1 http://mks-psad:7002/im/viewissue?selection=281282
Revision 1.11 2014/10/14 18:36:11CEST Ahmed, Zaheer (uidu7634)
get command line argument through line string
--- Added comments ---  uidu7634 [Oct 14, 2014 6:36:12 PM CEST]
Change Package : 268541:3 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.10 2014/09/02 16:56:36CEST Ahmed, Zaheer (uidu7634)
bug fix on getting attribute Id for deleting testrun
--- Added comments ---  uidu7634 [Sep 2, 2014 4:56:37 PM CEST]
Change Package : 260448:1 http://mks-psad:7002/im/viewissue?selection=260448
Revision 1.9 2014/07/14 15:14:36CEST Ahmed, Zaheer (uidu7634)
Exception Handling properly
--- Added comments ---  uidu7634 [Jul 14, 2014 3:14:36 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.8 2014/06/30 17:44:46CEST Ahmed, Zaheer (uidu7634)
changes made to get hiriarchical deleted testrun with distinct flag = False
--- Added comments ---  uidu7634 [Jun 30, 2014 5:44:47 PM CEST]
Change Package : 236899:1 http://mks-psad:7002/im/viewissue?selection=236899
Revision 1.7 2014/06/30 16:02:36CEST Ahmed, Zaheer (uidu7634)
Adapation made to support MFC4XX_ADMIN
--- Added comments ---  uidu7634 [Jun 30, 2014 4:02:36 PM CEST]
Change Package : 236899:1 http://mks-psad:7002/im/viewissue?selection=236899
Revision 1.6 2014/06/08 13:45:00CEST Ahmed, Zaheer (uidu7634)
pylint fix
--- Added comments ---  uidu7634 [Jun 8, 2014 1:45:00 PM CEST]
Change Package : 238253:1 http://mks-psad:7002/im/viewissue?selection=238253
Revision 1.5 2014/06/08 13:10:14CEST Ahmed, Zaheer (uidu7634)
Improve doucmentation
--- Added comments ---  uidu7634 [Jun 8, 2014 1:10:14 PM CEST]
Change Package : 238253:1 http://mks-psad:7002/im/viewissue?selection=238253
Revision 1.4 2014/04/30 16:28:06CEST Hecker, Robert (heckerr)
removed pep8 issues.
--- Added comments ---  heckerr [Apr 30, 2014 4:28:06 PM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.3 2014/04/15 14:02:34CEST Hecker, Robert (heckerr)
some adaptions to pylint.
--- Added comments ---  heckerr [Apr 15, 2014 2:02:35 PM CEST]
Change Package : 231472:1 http://mks-psad:7002/im/viewissue?selection=231472
Revision 1.2 2013/12/09 13:44:29CET Ahmed, Zaheer (uidu7634)
pep8 fix
--- Added comments ---  uidu7634 [Dec 9, 2013 1:44:30 PM CET]
Change Package : 210017:1 http://mks-psad:7002/im/viewissue?selection=210017
Revision 1.1 2013/12/09 11:53:54CET Ahmed-EXT, Zaheer (uidu7634)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/cmd/project.pj
"""
