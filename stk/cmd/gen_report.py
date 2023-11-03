"""
stk/cmd/gen_report
------------------

generate the Algo Test Report as pdf or excel file for a given TestRun Id

Testrun must be stored in ValResult DB, either use DB connection parameters or SqLite db file name

type of report based on the filename extension
  - pdf: create pdf report
  - xlsx: create Excel table

default details level for pdf report is 'detailed': contains test details and runtime error lists

Generation of Regression test reports to compare a test run to some reference test is only supported for pdf format.

call ``gen_report.py -h`` to get a list of all parameters

**usage**:

  - generate excel report:
    `gen_report.py -f my_sqlite.sqlite 4711 report.xlsx`
  - generate pdf report (performance or functional, depending on testrun db entry):
    `gen_report.py -u <db_user> -p <db_passwd> 4235 report.pdf -a`
  - generate regression test report comparing test run (1st id) against a regression run (2nd id):
    `gen_report.py -u <db_user> -p <db_passwd> 4235 4200 report.pdf -a`

See STK class descriptions (as epydoc.chm in mks or `html doc online`_ for more details on report generation.

.. _`html doc online`: http://uud296ag:8080/job/STK_NightlyBuild/ws/
              04_Engineering/10_Workspace/epydoc/stk_docu/stk.rep.pdf.algo_test.report.AlgoTestReport-class.html

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:03:46CEST $
"""

# test on oracle with
#  -u DEV_MFC4XX_ADMIN -p MFC4XX_ADMIN -c DEV_MFC4XX_ADMIN 3692 test.xlsx
# test on my sqlite with
#  -f TestRun2.sqlite 1 test.xlsx
#  -f TestResultsAPIDemo.sqlite 1 test.pdf

# Import Python Modules --------------------------------------------------------
from os import path as opath, unlink
from sys import path as spath, exit as sexit
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from platform import release

# Import STK Modules -----------------------------------------------------------
STKDIR = opath.abspath(r"..\..")
if STKDIR not in spath:
    spath.append(STKDIR)
from stk.val.testrun import TestRun
from stk.rep.pdf.algo_test.report import AlgoTestReport
from stk.rep.excel import Excel
from stk.db import db_common, ERROR_TOLERANCE_NONE
from stk.db.gbl import gbl
from stk.db.val import val
from stk.db.cat import cat
from stk.db.db_connect import DBConnect
from stk.util.logger import Logger
from stk.val import ValSaveLoadLevel

# defines ----------------------------------------------------------------------
ERROR = -1  # exit code in case of errors

PDF_REPORT = 'pdf'
EXCEL_REPORT = 'excel'

# The database parameters
DB_MASTER_SCHEMA_PREFIX = db_common.DEFAULT_MASTER_SCHEMA_PREFIX
DB_MASTER_DSN = db_common.DEFAULT_MASTER_DSN
DB_MASTER_DBQ = db_common.DEFAULT_MASTER_DBQ
DB_DEFAULT_USER = "DEV_ARS4XX_USER"
DB_DEFAULT_PW = "ARS4XX_USER"

MODE_INFO = 15
MODE_DEBUG = 10
MODE = MODE_INFO


# class ------------------------------------------------------------------------
class GenReport(object):
    """
    generate pdf report and excel table
    """
    def __init__(self):
        self.__report_level = None
        self.__report_type = None
        self.__testrun_id = None
        self.__reftest_id = None
        self.__outfile = None
        self.__db_gbl = None
        self.__db_val = None
        self.__db_cat = None
        self.__dbfile = None
        self.__masterdbdrv = None
        self.__masterdbdsn = None
        self.__masterdbdbq = None
        self.__masterdbuser = None
        self.__masterdbpassword = None
        self.__masterdbschemaprefix = None
        self.__db_connector = None
        self.__logger = Logger(self.__class__.__name__, level=MODE)
        self.excel_header = []

        # addon for testing this script:
        self.__val_obs_name = "UNIT_TEST_DEMO_TYPE"
        self.__coll_id = 0
        self.__coll_name = 'TestResultsAPIDemo'
        self.__meas_ids = []

    def __parse_arguments(self):
        """
        get user options

        usage: gen_report.py [-h] [-m | -d | -a] [-f DBFILE | -u MASTERDB_USER]
                             [-p MASTERDB_PASSWORD] [-c MASTERDB_SCHEMAPREFIX]
                             [-b MASTERDB_DSN | -q MASTERDB_DBQ]
                             testrun_id out_file
        """
        opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
        # mandatory settings:
        opts.add_argument('testrun_id', type=str, help='testrun id as stored in val-db')
        opts.add_argument('out_file', type=str, help='path/name of report file to generate (*.xls or *.pdf)')
        opts.add_argument('-r', '--reftest_id', dest='reftest_id', type=str,
                          help='reference test id as in val-db for regression report')
        # optional: set report type: level of details [-m|-d|-f]
        sel_type = opts.add_mutually_exclusive_group()
        sel_type.add_argument('-m', '--management', dest='rep_type',
                              action='store_const', const=AlgoTestReport.REP_MANAGEMENT,
                              help='generate management report (no details, no errorlists)')
        sel_type.add_argument('-d', '--detailed', dest='rep_type',
                              action='store_const', const=AlgoTestReport.REP_DETAILED,
                              help='generate detailed report (default: details, errorlists)')
        sel_type.add_argument('-a', '--all', dest='rep_type',
                              action='store_const', const=AlgoTestReport.REP_DEVELOPER,
                              help='generate all chapters for developer report')
        # database settings - [-f|[-u,-p,-c,[-b|-q]]
        db_set = opts.add_argument_group('db settings', 'select either SqLite or Oracle')
        db_opts = db_set.add_mutually_exclusive_group()
        db_opts.add_argument("-f", "--dbfile", dest="dbfile", help="The name of the SQlite database file. ")
        db_opts.add_argument("-u", "--master-db-user", dest="masterdb_user", type=str,
                             help="The name of the oracle database user.")
        db_conn = opts.add_argument_group('oracle db', '')
        db_conn.add_argument("-p", "--master-db-password", dest="masterdb_password", type=str,
                             help="The name of the oracle database password.")
        db_conn.add_argument("-c", "--master-db-schema-prefix", dest="masterdb_schemaprefix",
                             type=str, default=DB_MASTER_SCHEMA_PREFIX,
                             help="The name of the oracle database schema prefix.")
        dbtype = db_conn.add_mutually_exclusive_group()
        dbtype.add_argument("-b", "--master-db-dsn", dest="masterdb_dsn",
                            help="The name of the DSN, opt.")
        dbtype.add_argument("-q", "--master-db-dbq", dest="masterdb_dbq",
                            help="The name of the DBQ, default: %s" % DB_MASTER_DBQ)
        args = opts.parse_args()
        # default report type: detailed
        if args.rep_type is None:
            args.rep_type = AlgoTestReport.REP_DETAILED
        self.__report_level = args.rep_type
        self.__testrun_id = args.testrun_id
        self.__reftest_id = args.reftest_id
        self.__outfile = args.out_file
        ext = opath.splitext(args.out_file)
        if '.xlsx' == ext[1]:
            self.__report_type = EXCEL_REPORT
        elif ext[1] == '.pdf':
            self.__report_type = PDF_REPORT
        else:
            self.__logger.error('wrong output file extension! Use "*.xlsx" or ".pdf" only!')
            sexit(ERROR)
        # db settings
        if not args.masterdb_dsn and not args.masterdb_dbq:
            args.masterdb_dbq = DB_MASTER_DBQ
        if args.dbfile is not None:
            self.__dbfile = args.dbfile
        elif args.masterdb_user is not None:
            self.__masterdbdsn = args.masterdb_dsn
            self.__masterdbdbq = args.masterdb_dbq
            self.__masterdbuser = args.masterdb_user
            self.__masterdbpassword = args.masterdb_password
            self.__masterdbschemaprefix = args.masterdb_schemaprefix
        else:
            self.__logger.error('no connection to Result DB specified,'
                                ' enter either sqlite file or DB connection settings (-u -p -c)!')
            sexit(ERROR)

        if args.reftest_id:
            self.__logger.info('generate Regression Test report with reference test id %s' % args.reftest_id)

        return

    def _initialize(self):
        """
        parse arguments,  establish connection
        """
        self.__parse_arguments()

        if release() == "XP":
            self.__masterdbdrv = db_common.DEFAULT_MASTER_DRV_XP
        else:
            self.__masterdbdrv = db_common.DEFAULT_MASTER_DRV

        if self.__dbfile is None:
            self.__db_connector = DBConnect(dbq=self.__masterdbdbq,
                                            dsn=self.__masterdbdsn,
                                            user=self.__masterdbuser,
                                            pw=self.__masterdbpassword,
                                            master=self.__masterdbschemaprefix,
                                            drv=self.__masterdbdrv,
                                            tbl_prefix=None,
                                            error_tolerance=ERROR_TOLERANCE_NONE,
                                            use_cx_oracle=True)
        else:
            self.__db_connector = DBConnect(db_file=self.__dbfile,
                                            error_tolerance=ERROR_TOLERANCE_NONE)

        self.__db_gbl = self.__db_connector.Connect(gbl)
        self.__db_val = self.__db_connector.Connect(val)
        self.__db_cat = self.__db_connector.Connect(cat)

    def _terminate(self):
        """
        close database connections
        """
        self.__db_connector.DisConnect(self.__db_gbl)
        self.__db_connector.DisConnect(self.__db_val)
        self.__db_connector.DisConnect(self.__db_cat)

    def gererate_report(self):
        """
        generate the pdf and excel report, main method
        """
        self._initialize()

        if self.__report_level == AlgoTestReport.REP_MANAGEMENT:
            self.__logger.info('generate management report for TestRun %s' % self.__testrun_id)
        if self.__report_level == AlgoTestReport.REP_DETAILED:
            self.__logger.info('generate detailed report for TestRun %s' % self.__testrun_id)
        if self.__report_level == AlgoTestReport.REP_DEVELOPER:
            self.__logger.info('generate full developer report for TestRun %s, all chapters' % self.__testrun_id)

        testrun = TestRun()
        testrun.Load(self.__db_val, self.__db_gbl, self.__db_cat, self.__testrun_id)

        # for testing CR 220008 before saving of RuntimeJob is implemented
        # testrun.AddRuntimeJob(3988)  # 3988: 5/0/0  3445:66/66/67
        # testrun.AddRuntimeJob(3445)

        reftest = None
        if self.__reftest_id:
            reftest = TestRun()
            if reftest.Load(self.__db_val, self.__db_gbl, self.__db_cat, self.__reftest_id) is False:
                self.__logger.error('!! Reference Testrun not found with id: %s !!' % self.__reftest_id)
                self.__logger.error('Generating normal report instead Regression Test Report!')
                reftest = None

        if testrun is not None:
            for testcase in testrun.GetTestcases():
                testcase.Load(self.__db_val, self.__db_gbl, self.__db_cat, testrun.GetId(),
                              level=ValSaveLoadLevel.VAL_DB_LEVEL_ALL)
            for job in testrun.runtime_details:
                job.LoadHpcIncidents()
            if reftest:
                for testcase in reftest.GetTestcases():
                    testcase.Load(self.__db_val, self.__db_gbl, self.__db_cat, reftest.GetId(),
                                  level=ValSaveLoadLevel.VAL_DB_LEVEL_ALL)

            if self.__report_type == PDF_REPORT:
                self.generate_pdf(testrun, self.__outfile, reftest)
            elif self.__report_type == EXCEL_REPORT:
                self.generate_excel(testrun, self.__outfile)
        return

    def generate_pdf(self, testrun, outfile, reftest=None):
        """
        generate pdf report as specified in call options

        :param testrun: testrun as loaded from ResultDB
        :type testrun:  `TestRun`
        """
        report = AlgoTestReport(testrun, reftest)

        report.build(outfile, level=self.__report_level)

    def generate_excel(self, testrun, outfile):
        """
        generate excel report table as specified in call options

        :param testrun: TestRun Id as in resultDb
        :type testrun:  int
        :param outfile: path and filename of the report file
        :type outfile:  str
        """
        # init the excel stuff
        try:
            unlink(outfile)
        except Exception:  # pylint: disable=W0703
            pass
        xls = Excel()
        xls.create_workbook()
        xls.create_worksheet('testruns')  # str(testrun.name))

        # insert table header
        self.excel_header = ['_TestID', '_Test Date', '_TesterName',
                             '_Test Result', '_test_status', '_FR_Number']
        column_widths = [30, 15, 15, 30, 15, 30]
        for iheader in xrange(len(self.excel_header)):
            xls.set_cell_value(1, iheader + 1, self.excel_header[iheader])
            xls.set_cell_font_style(1, iheader + 1, bold=True)
            xls.set_column_width(1, iheader + 1, column_widths[iheader])

        row = 2
        row = self.__add_excel_testrun_rows(xls, row, testrun)
        xls.set_format(1, 1, row_to=row,
                       col_to=len(self.excel_header), wrap_text=True)

        try:
            xls.save_workbook(outfile)
            print("Test run successfully exported to '%s'" % outfile)
        except Exception:  # pylint: disable=W0703
            print(":-( couldn't save the workbook to '%s'" % outfile)
        xls.close_workbook()

    def __add_excel_testrun_rows(self, xls, row, testrun):
        """
        fill rows for a test run, can be called recursively for child testruns

        template: ['_TestID', '_Test Date', '_TesterName',
                   '_Test Result', '_test_status', '_FR_Number']

        :param xls: Excel workbook
        :type xls:  `Excel` as in stk.rep.excel
        :param row: start row for this test run
        :type row:  int
        :param testrun: (child-) test run
        :type testrun:  `TestRun`
        :returns: current (next empty) row
        :rtype:   int
        """
        # test run line:
        xls.set_data([testrun.name], row, 1)
        xls.set_cell_color(row, 1, row, len(self.excel_header), 'Light Orange')
        row += 1
        # go through test run childs
        for trun in testrun.GetChildTestRuns():
            row = self.__add_excel_testrun_rows(xls, row, trun)
        # go through test cases
        for tcase in testrun.GetTestcases(inc_child_tr=False):
            tc_result = tcase.test_result
            xls.set_data([tcase.id, '', '', '', tc_result], row, 1)
            xls.set_cell_color(row, 1, row, len(self.excel_header), 'Light Yellow')
            row += 1
            # go trough test steps
            for tstep in tcase.GetTestSteps():
                # todo: JHo add tstep.asmt.userid, tstep.asmt.date and
                # change last col to asmt.info
                xls.set_data([str(tstep.id), tstep.date,
                              tstep.user_account, tstep.meas_result,
                              tstep.test_result, tstep.issue], row, 1)
                row += 1
        return row


def main():
    """ main function """
    rep = GenReport()
    rep.gererate_report()
    print('ready')


if __name__ == '__main__':
    main()


"""
CHANGE LOG:
-----------
$Log: gen_report.py  $
Revision 1.1 2015/04/23 19:03:46CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.13 2015/01/27 16:16:43CET Ellero, Stefano (uidw8660) 
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 27, 2015 4:16:43 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.12 2015/01/26 20:20:20CET Ellero, Stefano (uidw8660) 
Removed all rep based deprecated function usage inside stk and module tests.
Revision 1.11 2015/01/20 16:48:59CET Mertens, Sven (uidv7805) 
naming convention alignment
--- Added comments ---  uidv7805 [Jan 20, 2015 4:49:00 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.10 2014/07/29 12:41:30CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes of too long lines for http links, epydoc and pylint adjustments
--- Added comments ---  uidv8815 [Jul 29, 2014 12:41:30 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.9 2014/07/28 19:20:43CEST Hospes, Gerd-Joachim (uidv8815)
add regression test option -r
--- Added comments ---  uidv8815 [Jul 28, 2014 7:20:43 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.8 2014/05/28 17:05:08CEST Hospes, Gerd-Joachim (uidv8815)
epydoc improved
--- Added comments ---  uidv8815 [May 28, 2014 5:05:08 PM CEST]
Change Package : 238258:1 http://mks-psad:7002/im/viewissue?selection=238258
Revision 1.7 2014/04/17 09:52:41CEST Hecker, Robert (heckerr)
Adapted to pylint.
--- Added comments ---  heckerr [Apr 17, 2014 9:52:41 AM CEST]
Change Package : 231472:1 http://mks-psad:7002/im/viewissue?selection=231472
Revision 1.6 2014/02/27 18:23:00CET Hospes, Gerd-Joachim (uidv8815)
load incidents from hpc error db
--- Added comments ---  uidv8815 [Feb 27, 2014 6:23:00 PM CET]
Change Package : 220009:1 http://mks-psad:7002/im/viewissue?selection=220009
Revision 1.5 2014/02/27 14:13:05CET Hospes, Gerd-Joachim (uidv8815)
testcase.id used instead of testcase.name, we don't have a testrun id from Doors, only a testrun name
--- Added comments ---  uidv8815 [Feb 27, 2014 2:13:05 PM CET]
Change Package : 222055:1 http://mks-psad:7002/im/viewissue?selection=222055
Revision 1.4 2014/02/20 15:12:27CET Hospes, Gerd-Joachim (uidv8815)
fix method name to user_account for report
--- Added comments ---  uidv8815 [Feb 20, 2014 3:12:28 PM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.3 2014/02/19 11:31:16CET Hospes, Gerd-Joachim (uidv8815)
add user and date of teststep and fix test results in xlsx and pdf
--- Added comments ---  uidv8815 [Feb 19, 2014 11:31:17 AM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.2 2014/02/13 17:44:49CET Hospes, Gerd-Joachim (uidv8815)
pep8 fixes and remove functions of first tests
--- Added comments ---  uidv8815 [Feb 13, 2014 5:44:50 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.1 2014/02/12 18:37:07CET Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/cmd/project.pj
"""
