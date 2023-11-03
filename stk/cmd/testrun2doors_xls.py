r"""
stk/cmd/testrun2doors_xls
-------------------------

generate the Excel table in csv format to be imported in Doors

Testrun must be stored in ValResult DB,
either use DB connection parameters for Oracle Server or the SqLite DB file name.

**proposed Doors update process:**

- in Doors: create new test run copy
    - get testrun index from that copy
- find correct testrun ID in validation result DB
    - e.g. using this tool with option ``-r ?`` like ``testrun2doors_xls -c ARS4XX -r ?``
- create Doors import csv file with this tool
- in Doors: import created file for the testrun

created Doors import table will look like:

================== ============= ============== ============== ================== ============= =======================
_TestID            _TestResult 1 _test_status 1 _FR_Number 1   _TestDate 1        _TesterName 1 _TestStatus_<ProjectId>
================== ============= ============== ============== ================== ============= =======================
ACC_TC_001_002                   Passed                        29.07.2015 11:43   ulli1704      Passed
ACC_TC_001_002-01   0.003        Passed         not Assigned   18.07.2015 14:03   uidv8815      Passed
ACC_TC_001_002-02   16           Passed         not Assigned   29.07.2015 11:43   ulli1704      Passed
================== ============= ============== ============== ================== ============= =======================

Because test cases can contain test steps from different users executed on different dates
the test case row shows the latest test date and its tester.

**usage**::

    Usage: testrun2doors_xls.py [options]

    Options:
      -h, --help            show this help message and exit
      -c CONN_PAR, --connection=CONN_PAR
                            connection parameter: either SQLite file or technology
                            (D:\path\myDB.sql, ARS4XX, MFC4XX)
      -r TEST_RUN, --test_run=TEST_RUN
                            testrun <db id>, **use ? for a list of testrun IDs**
      -f FILE_NAME, --filename=FILE_NAME
                            csv file name the testrun results should be exported to
      -i TEST_INDEX, --index=TEST_INDEX
                            index to add to column headers as created by doors
                            testrun copy (number in "_TestResult 3")
      -p PROJECT_ID, --projectid=PROJECT_ID
                            additional column with same entries as _test_status
                            named _TestStatus_<ProjectId>
      -d DELIMITER, --delimiter DELIMITER
                            opt. setting delimiter used between entries (pure
                            char, no ''), default is ',' (needed for Doors import)

**example**:

.. python::

    # with sqlite db and doors release counter (test counter) '1'
    testrun2doors_xls.py -c D:\\moduletest\\test_api\\TestResultsAPIDemo.sqlite -r 1 -f d:\\tmp\\testout.csv -i 1

    # for MFC in Oracle:
    testrun2doors_xls.py -c MFC4XX -f d:\\tmp\\testout.csv -i 12 -r 8322

    # searching all testrun IDs for ARS4XX in Oracle:
    testrun2doors_xls.py -c ARS4XX -r ? d:\\tmp\\testout.csv


:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.10 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/02/20 23:52:16CET $
"""

# test on oracle with

# Import Python Modules --------------------------------------------------------
from os import path as opath
from sys import path as spath
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import defaultdict

# Import STK Modules -----------------------------------------------------------
STKDIR = opath.abspath(opath.join("..", ".."))
if STKDIR not in spath:
    spath.append(STKDIR)

from stk.db.db_common import BaseDB
from stk.db import cat, cl, fct, gbl, lbl, obj, par, sim, val
import stk.val as val_res

# excel column headers
# column:  1          2              3               4
HEADER = ['_TestID', '_TestResult', '_test_status', '_FR_Number',
          #     5             6           7 (opt)
          '_TestDate', '_TesterName']  # '_TestStatus_<ProjectId>']
DELIMITER = ','


def main():
    """main feature"""
    argparser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    argparser.add_argument("-c", "--connection", dest="conn_par", required=True,
                           help="connection parameter: either sqlite file or technology "
                                "(D:\\path\\myDB.sql, ARS4XX, MFC4XX)")
    argparser.add_argument("-r", "--test_run", dest="test_run", required=True,
                           help="test <checkpoint name>[ / <observer name>]\nuse ? for a list")
    argparser.add_argument("-f", "--filename", dest="file_name", required=True,
                           help="file name the test run results should be exported to")
    argparser.add_argument("-i", "--index", dest="test_index", default=None,
                           help="opt. index to add to column headers as created by doors test run copy "
                                "(number in '_TestResult 3')")
    argparser.add_argument("-p", "--project_id", dest="project_id", default=None,
                           help="opt. additional column with same entries as _test_status "
                                "named _TestStatus_<PROJECT_ID>")
    argparser.add_argument("-d", "--delimiter", dest="delimiter", default=None,
                           help="opt. setting delimiter used between entries (pure char, no ''), default is ,"
                                " (needed for Doors import!)")
    cmd_options = argparser.parse_args()

    trid = cmd_options.test_run.split(' / ')
    # let's build up the DB connection and check we have a run with that name
    try:
        dbase = BaseDB(cmd_options.conn_par)
    except Exception, ex:  # pylint: disable=W0703
        print("unable to get connection to DB with given parameter -c %s\n%s" % (cmd_options.conn_par, str(ex)))
        exit(-1)

    # well, if we don't know, just list what we have
    if trid[0] == '?':
        frmt = "%-6s|%-50s|%-35s|%-16s"
        print(frmt % ("ID", "Checkpoint", "Observer", "Start Time"))
        print("-" * (6 + 50 + 35 + 16 + 3))
        for trn in dbase.execute("""SELECT t.TRID, t.CHECKPOINT, o.NAME, t.STARTTS
                                    FROM VAL_TESTRUN t INNER JOIN GBL_VALOBSERVER o ON t.TYPEID = o.TYPEID
                                    WHERE t.IS_DELETED = 0 AND t.IS_LOCKED = 0
                                    ORDER BY t.STARTTS DESC
                                 """):
            print(frmt % trn)
    else:
        test_run = get_testrun(cmd_options.conn_par, trid[0])
        create_doors_csv(test_run, cmd_options.file_name,
                         doors_index=cmd_options.test_index, delimiter=cmd_options.delimiter,
                         project_id=cmd_options.project_id)


def get_testrun(conn_par, trid):
    """
    read test run with all test cases and their test steps

    returns test run instance

    :param conn_par: db connection to Oracle, SqLite etc.
    :type  conn_par: `db_connection`
    :param trid: db internal test run id
    :type  trid: int
    :return: `TestRun` instance
    """
    mods = defaultdict(lambda: lambda _: None,
                       {'cat': cat.BaseRecCatalogDB, 'cl': cl.BaseCLDB, 'fct': fct.BaseFctDB,
                        'gbl': gbl.BaseGblDB, 'lbl': lbl.BaseCameraLabelDB, 'gen': lbl.BaseGenLabelDB,
                        'obj': obj.BaseObjDataDB, 'par': par.BaseParDB, 'sim': sim.BaseSimulationDB,
                        'val': val.BaseValResDB})
    dbmods = ['cat', 'gbl', 'val']
    conns = {mod.lower(): mods[mod.lower()](conn_par) for mod in dbmods}

    tr_db = val_res.TestRun()

    tr_db.Load(conns['val'], conns['gbl'], conns['cat'], testrun_id=trid,
               level=val_res.ValSaveLoadLevel.VAL_DB_LEVEL_ALL)

    for test_case in tr_db.test_cases:
        test_case.Load(conns['val'], conns['gbl'], conns['cat'], tr_db.GetId(),
                       level=val_res.ValSaveLoadLevel.VAL_DB_LEVEL_ALL)
    return tr_db


def create_doors_csv(test_run, file_name, doors_index=None, delimiter=None, project_id=None):
    """
    create csv file that can be imported by doors as described in the module header

    :param test_run: TestRun instance loaded down to test steps
    :type  test_run: `TestRun`
    :param file_name: name of csv file to create, can contain path, otherwise current directory is used
    :type  file_name: str
    :param doors_index: opt. number behind the column name as created by Doors (number in '_TestResult 3')
    :type  doors_index: str
    :param delimiter: opt. delimiter, default is ',' (for Doors import)
    :type  delimiter: str
    :param project_id: project id if Doors expects additional column "_TestStatus_<PROJECT_ID>"
    :type  project_id: str
    """
    # sort helper to get test steps without date (ts.date=='None') at end of the list
    def datesorter(a):
        if a.date == 'None':
            return "1900-01-01"
        return a.date

    delim = delimiter if delimiter is not None else DELIMITER
    header = list(HEADER)
    # add header for project_id column if requested
    if project_id is not None:
        header.append('_TestStatus_{}'.format(project_id))
    # doors_index to add to column headers as created by doors testrun copy: "_TestResult 3"
    index = ' ' + doors_index if doors_index else ''

    csv = open(file_name, 'w')
    # write column headers
    csv.write(header[0] + delim)
    for ihh in xrange(1, len(header)):
        csv.write(('{}{}'.format(header[ihh], index)) + delim)
    csv.write('\n')

    # now walk through the test cases and steps and export needed entries
    # excel column headers
    # column:  1         2              3               4
    #       ['_TestID', '_TestResult', '_test_status', '_FR_Number',
    #     5             6             7 (opt)
    #  '_TestDate', '_TesterName', '_TestStatus_<PROJECT_ID>]

    for test_case in sorted(test_run.test_cases, key=lambda k: k.GetSpecTag()):
        # temp list to add date and user of last test result to test case line if available
        ts = sorted(test_case.test_steps, key=lambda k: k.date, reverse=True)
        # don't list result entries without date, they are sorted on top
        ts = [t for t in ts if t.date != 'None']
        if ts:
            csv.write(delim.join([test_case.id, '', test_case.test_result, '', ts[0].date, ts[0].user_account]))
        else:
            csv.write(delim.join([test_case.id, '', test_case.test_result, '', '', '']))
        if project_id is not None:
            csv.write(delim + ' {}'.format(test_case.test_result))
        csv.write('\n')

        for test_step in sorted(test_case.test_steps, key=lambda k: k.GetSpecTag()):
            issue = test_step.issue if (test_step.issue is not None and str(test_step.issue).lower() != 'none') else ''
            # to export python lists the ',' in results is replaced with '|'
            # other solution could have been using " " around the field entry, here a replacement was requested
            csv.write(delim.join([test_step.id, str(test_step.meas_result).replace(',', '|'), test_step.test_result,
                                  issue, test_step.date, test_step.user_account]))
            if project_id is not None:
                csv.write(delim + ' {}'.format(test_step.test_result))
            csv.write('\n')

    csv.close()
    print("Test run %s successfully exported to '%s'" % (test_run.id, file_name))


if __name__ == '__main__':
    # tested locally with
    # -c D:\mks_sandboxes\STK\05_Software\05_Testing\05_Test_Environment\moduletest\test_api\TestResultsAPIDemo.sqlite
    #    -r 1 -f d:\tmp\tr2d_test.csv
    # -c MFC4XX -r 8805 -f d:\tmp\tr2d_test.csv
    exit(main())


"""
CHANGE LOG:
-----------
$Log: testrun2doors_xls.py  $
Revision 1.10 2017/02/20 23:52:16CET Hospes, Gerd-Joachim (uidv8815) 
fix header copy to run test twice
Revision 1.9 2017/02/20 20:01:08CET Hospes, Gerd-Joachim (uidv8815)
fix delimiter usage, extend test and docu to use ',' for doors import
Revision 1.8 2017/02/19 20:36:25CET Hospes, Gerd-Joachim (uidv8815)
fix adding latest test date and user to test case line
Revision 1.7 2016/12/20 18:11:14CET Hospes, Gerd-Joachim (uidv8815)
add user and date to test case row
Revision 1.6 2016/06/20 16:26:37CEST Hospes, Gerd-Joachim (uidv8815)
split main into several methods to call csv write itself
Revision 1.5 2016/03/30 16:44:09CEST Mertens, Sven (uidv7805)
reducing some pylints
Revision 1.4 2015/12/07 15:50:02CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.3 2015/12/04 16:36:26CET Hospes, Gerd-Joachim (uidv8815)
add opt column for project Id, use ',' as default delimiter with opt change, adapt columns
Revision 1.2 2015/11/19 10:54:39CET Hospes, Gerd-Joachim (uidv8815)
output in csv format, delete some columns
--- Added comments ---  uidv8815 [Nov 19, 2015 10:54:39 AM CET]
Change Package : 391552:1 http://mks-psad:7002/im/viewissue?selection=391552
Revision 1.1 2015/07/31 15:33:15CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
"""
