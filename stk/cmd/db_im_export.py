# -*- coding:utf-8 -*-
"""
db_im_export
----------------

**Database Import Export command Utility.**

**Features:**
    - The tool allows to import data from oracle database to sqlite database
    - The data include collections, obj and ego kinematics, rect objects, result data.
    - Currently there is only one way database export is allowed i.e. from oracle to sqlite

**UseCase:**
 There are many possibilities to use this script as shown in example

Parameters:

 -r
    The name of the DBQ e.g. RACADMPE
 -u
    User name of Oracle database
 -p
    Password of Oracle database
 -c
    Master Schema of oracle database
 -b
    Master DSN name of Oracle database
 -q
    Master DBQ of Oracle database
 -f
    File path to destination SQLite file (Optional: blank sqlite file from
    stk.db.sqlite.adas_db.sqlite will be use if no argument is passed)
 -s
    Source database type (e.g oracle)
 -d
    Destination database type (e.g sqlite)
 -w
    remove initial data of module test and Overwrite the existing records in
    destination SQLite file or(yes)
 -r
    Collection name (Optional: If not provide whole data will be export
    otherwise data only related collection will be export)
 -m
    path and filename of BPL (Batch Play List) file to export only entries of rec files in bpl
 -t
    TestRun name to export db entries related to a test run
 -v
    additional Checkpoint label (Version) of a TestRun
 -o
    Output Path to store the db to

**Output:**

 The output is sqlite file will be produced at location
 stk.cmd.output.%MasterSchema%_adas_db.sqlite_out%DateTime%.sqlite

**1. Example:**

 Command line usage when everything is to be export i.e. replica of oracle database

 db_im_export -q RACADMPE -u MyOracleDbUser  -p MyOracleDbPassword -c  MyMasterSchema
 -s oracle -d sqlite -w yes

**2. Example:**

 Command line usage when data specific to collection exported which includes label data
 for measurement in collection. measurement parameter and collection record

 db_im_export -q RACADMPE -u MyOracleDbUser -p MyOracleDbPassword -c  MyMasterSchema
 -s oracle -d sqlite -w yes -r MyCollectoinName

**3. Example:**

 Command line usage when data related to measurement in for given BPL File to be export
 which includes label data for measurement in collection. measurement parameter and collection record

 db_im_export -q RACADMPE -u MyOracleDbUser  -p MyOracleDbPassword -c  MyMasterSchema
 -s oracle -d sqlite -w yes -m MyPathToBPLfile

:org:           Continental AG
:author:        Zaheer Ahmed
:version:       $Revision: 1.16 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/07/14 11:59:33CEST $
"""
# import Python modules -----------------------------------------------------------------------------------------------
import os
from sys import path as spath, exit as sexit
from shutil import copyfile
from platform import release
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime

# import STK modules --------------------------------------------------------------------------------------------------
MODULE_TEST_FOLDER = os.path.dirname(__file__)
STK_FOLDER = os.path.abspath(os.path.join(os.path.split(__file__)[0], r"..\.."))
if STK_FOLDER not in spath:
    spath.append(STK_FOLDER)

import stk.db.db_common as dbc
from stk.db.db_connect import DBConnect
from stk.db.gbl import gbl
from stk.db.val import val
from stk.db.cat import cat
from stk.db.lbl import genlabel
from stk.db.par import par
from stk.db.obj import objdata
from stk.db import ERROR_TOLERANCE_NONE
from stk.db.db_sql import SQLBinaryExpr, OP_EQ, SQLLiteral, OP_AND, OP_IN
from stk.db.mdl.adas_db_def import PK, NAME, GBL, CAT, PAR, OBJ, LBL, VAL, COL_LIST, ADAS_DATABASE_MODULE_NAMES, \
    MODULE_TABLEINFOMAP, TABLE_NAME_FILES_INFO, TABLE_NAME_COLL_INFO, TABLE_NAME_KWMAP_INFO, TABLE_NAME_COLLMAP_INFO, \
    TABLE_NAME_VALUE_INFO, TABLE_NAME_EGO_KINEMATICS_INFO, TABLE_NAME_LABELS_INFO, TABLE_NAME_RECTANGULAR_OBJECT_INFO, \
    TABLE_NAME_ACC_LANE_REL_INFO, TABLE_NAME_KINEMATICS_INFO, TABLE_NAME_EGO_KINEMATICS_ADMA_INFO, \
    TABLE_NAME_OBJ_EGOKINE_CHECKPOINTMAP_INFO, TABLE_NAME_OBJ_RECTOBJ_CHECKPOINTMAP_INFO, \
    TABLE_NAME_ADMA_KINEMATICS_INFO, TABLE_NAME_TEST_CASES_INFO, TABLE_NAME_PROBS_CAM_INFO, EXCLUDE

from stk.db.val.val import TABLE_NAME_RESULT_IMAGE, TABLE_NAME_EVENT_IMAGE, COL_NAME_EVENT_IMG_IMAGE, \
    COL_NAME_RESIMG_IMAGE, COL_NAME_TR_ID
from stk.db.cat.cat import COL_NAME_COLL_COLLID, COL_NAME_FILES_MEASID, COL_NAME_COLL_PARENTID
from stk.db.obj.objdata import COL_NAME_RECT_OBJ_RECTOBJID
from stk.util.logger import Logger
from stk.val.testrun import TestRun
from stk.val.results import ValSaveLoadLevel
from stk.mts.bpl import Bpl
from stk.db.db_connect import MAX_INT64

# Global definition of the variable
ORACLE = "oracle"
SQLITE = "sqlite"
SRC = "SRC"
DEST = "DEST"
IDS = "IDS"
COUNT = "COUNT"
MAX_PREPARED_RECORDS = 300000
MAX_BATCH_MODE_LIMIT = 999

MODE_INFO = 15
MODE_DEBUG = 10
MODE = MODE_INFO

ADAS_DATABASE_MODULES = {GBL: gbl, CAT: cat, PAR: par, OBJ: objdata, LBL: genlabel, VAL: val}


# Classes -------------------------------------------------------------------------------------------------------------
class DbImportExport(object):
    """Db Export Utility Class

    for usage examples see module documentation of `db_im_export`
    """
    def __init__(self):
        self.__dbfile = None
        self._destdbfile = None
        self.__masterdbdsn = None
        self.__masterdbdbq = None
        self.__masterdbuser = None
        self.__masterdbpassword = None
        self.__masterdbschemaprefix = None
        self.__srcdbschemaprefix = None
        self.__destdbschemaprefix = None
        self.__masterdbdrv = None
        self.__srcdb = None
        self.__destdb = None
        self.__overwrite = False
        self.__collection = None
        self.__trname = None
        self.__checkpoint = None
        self.__db_connector_ora = None
        self.__db_connector_sql = None
        self.__exclude = []
        self.__adas_connection = {}
        self.__logger = None
        self.__outfolder = None
        self.__bplfile = None
        self.__inc_obj = False
        self.__inc_val = False

    def __initialize(self, line=None):
        """
        Initialize Export process with Establishing connection and parsing argument
        """
        if not os.path.exists(os.path.join(MODULE_TEST_FOLDER, r"output")):
            os.makedirs(os.path.join(MODULE_TEST_FOLDER, r"output"))
        self.__logger = Logger(self.__class__.__name__,
                               filename=os.path.join(MODULE_TEST_FOLDER, r"output", "export.log"),
                               level=MODE)
        self.__parse_arguments(line)
        if release() == "XP":
            self.__masterdbdrv = dbc.DEFAULT_MASTER_DRV_XP
        else:
            self.__masterdbdrv = dbc.DEFAULT_MASTER_DRV

        file_name = r"%s_adas_db.sqlite_out_%s.sqlite" % (self.__masterdbschemaprefix,
                                                          datetime.now().strftime("%d_%m_%Y_at_%H_%M_%S"))

        if self.__outfolder is None:
            self._destdbfile = os.path.abspath(os.path.join(MODULE_TEST_FOLDER + r"\output", file_name))
        else:
            if not os.path.exists(self.__outfolder):
                os.makedirs(self.__outfolder)
            self._destdbfile = os.path.abspath(os.path.join(self.__outfolder, file_name))
        try:
            copyfile(self.__dbfile, self._destdbfile)
        except IOError, copy_error:
            self.__logger.error("copy error")
            self.__logger.error(copy_error)
            sexit(1)

        self.__db_connector_ora = DBConnect(dbq=self.__masterdbdbq,
                                            dsn=self.__masterdbdsn,
                                            user=self.__masterdbuser,
                                            pw=self.__masterdbpassword,
                                            master=self.__masterdbschemaprefix,
                                            drv=self.__masterdbdrv,
                                            tbl_prefix=None,
                                            error_tolerance=ERROR_TOLERANCE_NONE,
                                            use_cx_oracle=True)

        self.__db_connector_sql = DBConnect(db_file=self._destdbfile, error_tolerance=ERROR_TOLERANCE_NONE)

        for key, value in ADAS_DATABASE_MODULES.items():
            src_dbc_obj = self.__get_db_connection_object(self.__srcdb, value)
            dest_dbc_obj = self.__get_db_connection_object(self.__destdb, value)

            self.__adas_connection[key] = {SRC: src_dbc_obj,
                                           DEST: dest_dbc_obj}

    def __terminate(self):
        """
        Terminating method with closing database connections
        """
        for key in ADAS_DATABASE_MODULES.keys():
            if self.__srcdb == ORACLE and self.__destdb == SQLITE:
                self.__db_connector_ora.DisConnect(self.__adas_connection[key][SRC])
                self.__db_connector_sql.DisConnect(self.__adas_connection[key][DEST])
            elif self.__srcdb == SQLITE and self.__destdb == ORACLE:
                self.__db_connector_sql.DisConnect(self.__adas_connection[key][SRC])
                self.__db_connector_ora.DisConnect(self.__adas_connection[key][DEST])

    @staticmethod
    def __check_db_connections(src, dest):
        """
        Check the connection types for safety check to prevent accidental export in oracle

        :param src: Source database connection
        :type src: child of OracleBaseDB
        :param dest: Destination database connection
        :type dest: child of  SQLite3BaseDB
        """
        if not (src.db_type[0] == -1 and dest.db_type[0] == 0):
            raise StandardError("Wrong Database Connection")

    def __get_db_connection_object(self, conn_type, db_interface_module):
        """
        Create adas database module db connection
        :param conn_type: type of connection e.g. oracle or Sqlite
        :type conn_type: str
        :param db_interface_module: python module for Subschema of ADAS database
        :type db_interface_module: python module
        """

        if conn_type == ORACLE:
            return self.__db_connector_ora.Connect(db_interface_module)
        elif conn_type == SQLITE:
            return self.__db_connector_sql.Connect(db_interface_module)

        return None

    def __parse_arguments(self, line=None):
        """
        Parsing commandline arguments
        """
        optparser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
        optparser.add_argument("-s", "--src-db", default="oracle", dest="srcdb", required=True,
                               choices=['oracle', 'sqlite'], help="The name of the source database e.g. oracle,sqlite")
        optparser.add_argument("-d", "--dest-db", default="sqlite", dest="destdb", required=True,
                               choices=['oracle', 'sqlite'],
                               help="The name of the Destination database e.g. oracle,sqlite")
        optfile = optparser.add_argument_group('sqlite_file', 'use sqlite file path & name')
        optfile.add_argument("-f", "--dbfile", dest="dbfile", default=None,
                             help="The name of the Sqlite database file. ")
        optoracle = optparser.add_argument_group('oracle', 'connect to oracle db using ' +
                                                           'a correct set of dsn, user, password and schema')
        optoracle.add_argument("-b", "--master-db-dsn", dest="masterdbdsn", default=None,
                               help="The name of the DB DSN.")
        optoracle.add_argument("-q", "--master-db-dbq", default="RACADMPE",
                               dest="masterdbdbq", help="The name of the DBQ.")
        optoracle.add_argument("-u", "--master-db-user", dest="masterdbuser", default=None,
                               help="The name of the oracle database user.")
        optoracle.add_argument("-p", "--master-db-password", dest="masterdbpassword", default=None,
                               help="The name of the oracle database password.")
        optoracle.add_argument("-c", "--master-db-schema-prefix", dest="masterdbschemaprefix", default=None,
                               help="The name of the oracle database schema prefix.")
        optparser.add_argument("-w", "--over-write", default="yes", dest="overwrite",
                               help="clean the tables in Destination database before insert e.g. " +
                               "y/n,yes/no,True/False")
        optparser.add_argument("-r", "--collection", dest="collection", default=None,
                               help="Collection name to be import")
        optparser.add_argument("-m", "--bpl", dest="bplfile", default=None, help="File path of BPL")
        optparser.add_argument("-t", "--trname", dest="trname", default=None, help="Testrun to import export")
        optparser.add_argument("-v", "--checkpoint", dest="checkpoint", default=None, help="Checkpoint of a TestRun")
        optparser.add_argument("-o", "--outputpath", dest="output", default=None, help="outpath Directory")
        optparser.add_argument("-e", "--exclschema", dest="exclschema", default="",
                               help="exclude subschema(s) without any space e.g. -e val,obj")

        if line is not None:
            cmd_options = optparser.parse_args(line.split())
        else:
            cmd_options = optparser.parse_args()

        self.__dbfile = cmd_options.dbfile

        self.__masterdbdsn = cmd_options.masterdbdsn
        self.__masterdbdbq = cmd_options.masterdbdbq
        self.__masterdbuser = cmd_options.masterdbuser

        self.__masterdbpassword = cmd_options.masterdbpassword
        self.__masterdbschemaprefix = cmd_options.masterdbschemaprefix

        self.__srcdb = cmd_options.srcdb
        self.__destdb = cmd_options.destdb
        self.__overwrite = cmd_options.overwrite.lower()
        self.__overwrite = (self.__overwrite == "true" or
                            self.__overwrite == "yes" or
                            self.__overwrite == "y")
        self.__collection = cmd_options.collection
        self.__bplfile = cmd_options.bplfile
        self.__trname = cmd_options.trname
        self.__checkpoint = cmd_options.checkpoint
        self.__outfolder = cmd_options.output
        self.__inc_obj = "obj" not in cmd_options.exclschema.lower()
        self.__inc_val = "val" not in cmd_options.exclschema.lower()

        db_fileprefix = ""

        if self.__srcdb == 'oracle' and \
                (self.__masterdbschemaprefix is None or self.__masterdbuser is None or self.__masterdbpassword is None):
            self.__logger.error("for Oracle connections the options -u, -p and -c must be defined")
            sexit(2)
        elif self.__srcdb == 'sqlite' and self.__dbfile is None:
            self.__logger.error("for sqlite usage a db file must be passed")
            sexit(2)
        if self.__dbfile is None:
            self.__dbfile = os.path.abspath(os.path.join(os.path.join(STK_FOLDER, r"stk\db\sqlite_db"),
                                                         db_fileprefix.lower() + "adas_db.sqlite"))
        if self.__destdb == ORACLE:
            self.__logger.error("If you are sure to export data into Oracle DB then comment this check and run again")
            sexit(2)

    def export_data(self, line=None):
        """
        Main function of DB Export

        gets arguments using either sys.argv or passed line,
        check list of arguments in module documentation of `db_im_export`
        or using option '-h' to get the help output of the script

        :param line: opt. command line arguments if not passed using sys.argv
        :type  line: str or list(str)
        :return: execution result, '0' for success, '-1' in case of errors
        """
        start_date = datetime.now()
        self.__initialize(line)
        self.__logger.info("Starting Export at %s" % start_date.strftime("%d-%m-%Y %H:%M:%S"))
        result = None

        if self.__collection is None and self.__bplfile is None and self.__trname is None:
            #  Export Everything !
            self.__logger.info("Creating Oracle Copy...")
            result = self.__export_everything(replace=self.__overwrite)
            if type(result) is not bool and not result:
                self.__logger.info("Failed to create Oracle Copy...")
                return -1

        else:
            if self.__collection is not None or self.__bplfile is not None:
                self.__copy_module(self.__adas_connection[GBL][SRC], self.__adas_connection[GBL][DEST],
                                   MODULE_TABLEINFOMAP[GBL], self.__overwrite)
                self.__logger.info("Exporting data for Measurement....")
                result, _, measids = self.__export_data_for_measurements(coll_name=self.__collection,
                                                                         bpl_filepath=self.__bplfile,
                                                                         replace=self.__overwrite)
                if type(result) is not bool and not result:
                    self.__logger.error("Export to data for Measurement Failed!")
                    return -1

                self.__logger.info("Exporting parameters....")
                result = self.__export_data_for_parameter(measids, replace=self.__overwrite)
                if type(result) is not bool and not result:
                    self.__logger.error("Export parameters for Measurements Failed!")
                    return -1

                if self.__inc_obj:
                    self.__logger.info("Exporting Rectangular Objects/Ego/Kinematics....")
                    result = self.__export_data_for_object(measids, replace=self.__overwrite)
                    if type(result) is not bool and not result:
                        self.__logger.error("Exporting Rectangular Objects/Ego/Kinematics Failed!")
                        return -1

                self.__logger.info("Exporting Generic Labels....")
                result = self.__export_data_for_label(measids, replace=self.__overwrite)
                if type(result) is not bool and not result:
                    self.__logger.error("Exporting Generic Label Failed!")
                    return -1

            if self.__trname is not None:
                src_catdb = self.__adas_connection[CAT][SRC]
                src_valdb = self.__adas_connection[VAL][SRC]
                src_gbldb = self.__adas_connection[GBL][SRC]
                dest_valdb = self.__adas_connection[VAL][DEST]
                dest_gbldb = self.__adas_connection[GBL][DEST]
                tr_records = src_valdb.get_testrun(name=self.__trname, checkpoint=self.__checkpoint)
                if type(tr_records) is dict:
                    tr_records = [tr_records]
                for tr_rec in tr_records:
                    testrun = TestRun(replace=True)
                    testrun.Load(src_valdb, src_gbldb, src_catdb, testrun_id=tr_rec[COL_NAME_TR_ID],
                                 level=ValSaveLoadLevel.VAL_DB_LEVEL_ALL)
                    testrun.Save(dest_valdb, dest_gbldb, level=ValSaveLoadLevel.VAL_DB_LEVEL_ALL)

            self.__adas_connection[GBL][DEST].commit()
        self.__terminate()
        end_date = datetime.now()
        duration = end_date - start_date
        if type(result) is bool and result:
            self.__logger.info("Export Finished with Total Duration = %s " % str(duration))
            print "exit"
            return 0
        else:
            self.__logger.error("Export Failed!")
            return -1

    def __export_data_for_measurements(self, coll_name=None, bpl_filepath=None, replace=False):
        """
        Db Export specific to Collection  or bpl file for CAT module

        :param coll_name: collection name
        :type coll_name: str
        :param replace: flag to replace the existing data or not
        :type replace: boolean
        """
        #        Copy Global
        src_catdb = self.__adas_connection[CAT][SRC]
        dest_catdb = self.__adas_connection[CAT][DEST]
        self.__check_db_connections(src_catdb, dest_catdb)
        measids = []
        collids = par_collid = None

        if coll_name is not None:
            par_collid = src_catdb.get_collection_id(coll_name)
            measids = list(set(src_catdb.get_collection_measurements(par_collid)))
            collids = list(set([par_collid] + src_catdb.get_collections(par_collid)))
        elif bpl_filepath is not None:
            bpl = Bpl(bpl_filepath)
            recordings = bpl.read()
            for rec in recordings:
                measids.append(src_catdb.get_measurement_id(str(rec)))

        if replace:
            init_cat_tab_infos = self.__get_table_no_column(CAT, [COL_NAME_FILES_MEASID,
                                                                  COL_NAME_COLL_COLLID])
            self.__copy_table(src_catdb, dest_catdb, init_cat_tab_infos, replace=replace)

        self.__copy_records(src_catdb, dest_catdb, TABLE_NAME_FILES_INFO,
                            COL_NAME_FILES_MEASID, measids, replace=replace)

        self.__copy_records(src_catdb, dest_catdb, TABLE_NAME_KWMAP_INFO,
                            COL_NAME_FILES_MEASID, measids, replace=replace)

        if collids is not None:
            self.__copy_records(src_catdb, dest_catdb, TABLE_NAME_COLL_INFO,
                                COL_NAME_COLL_COLLID, collids, replace=replace)

            self.__copy_records(src_catdb, dest_catdb, TABLE_NAME_COLLMAP_INFO,
                                COL_NAME_COLL_COLLID, collids, replace=replace)
            parcoll_rec = dest_catdb.get_collection(par_collid)
            parcoll_rec[COL_NAME_COLL_PARENTID] = None
            dest_catdb.update_collection(parcoll_rec, par_collid)

        return True, collids, measids

    def __export_data_for_parameter(self, measids, replace=False):
        """
        Db Export specfic to measurements for PAR module
        :param measids: list of measurement ids
        :type measids: list
        :param replace: flag to replace the existing data or nor
        :type replace: boolean
        """
        src_pardb = self.__adas_connection[PAR][SRC]
        dest_pardb = self.__adas_connection[PAR][DEST]
        self.__check_db_connections(src_pardb, dest_pardb)

        if replace:
            init_par_tab_infos = self.__get_table_no_column(PAR, [COL_NAME_FILES_MEASID])
            self.__copy_table(src_pardb, dest_pardb, init_par_tab_infos, replace=replace)

        self.__copy_records(src_pardb, dest_pardb, TABLE_NAME_VALUE_INFO, COL_NAME_FILES_MEASID,
                            measids, replace=replace)

        return True

    def __export_data_for_object(self, measids, replace=False):
        """
        Db Export specific to measurements for OBJ module

        :param measids: list of measurement ids
        :type measids: list
        :param replace: flag to replace the existing data or nor
        :type replace: boolean
        """
        src_objdb = self.__adas_connection[OBJ][SRC]
        dest_objdb = self.__adas_connection[OBJ][DEST]
        self.__check_db_connections(src_objdb, dest_objdb)
        if replace:
            init_obj_tab_infos = self.__get_table_no_column(OBJ, [COL_NAME_FILES_MEASID,
                                                                  COL_NAME_RECT_OBJ_RECTOBJID])
            # obj_init = [TABLE_NAME_CONFIGS, TABLE_NAME_DESCRIPTION, TABLE_NAME_CFGMAP]
            self.__copy_table(src_objdb, dest_objdb, init_obj_tab_infos, replace=replace)

        self.__logger.info("Copying Ego Kinematics Checkpoint ....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_OBJ_EGOKINE_CHECKPOINTMAP_INFO,
                            COL_NAME_FILES_MEASID, measids, replace=replace)

        self.__logger.info("Copying Ego Kinematics ....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_EGO_KINEMATICS_INFO,
                            COL_NAME_FILES_MEASID, measids, replace=replace)
        self.__logger.info("Copying Ego Kinematics ADMA....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_EGO_KINEMATICS_ADMA_INFO,
                            COL_NAME_FILES_MEASID, measids, replace=replace)

        self.__logger.info("Copying Rectangular Objects....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_RECTANGULAR_OBJECT_INFO,
                            COL_NAME_FILES_MEASID, measids, replace=replace)
        rect_objids = []

        for measid in measids:
            for rectobj in src_objdb.get_rect_object_ids(measid, incl_deleted=True):
                rect_objids += [rectobj[COL_NAME_RECT_OBJ_RECTOBJID]]

        self.__logger.info("Copying Rectangular Object Checkpoints ....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_OBJ_RECTOBJ_CHECKPOINTMAP_INFO,
                            COL_NAME_RECT_OBJ_RECTOBJID, rect_objids, replace=replace)
        self.__logger.info("Copying ACC Lane Relations for Objects....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_ACC_LANE_REL_INFO,
                            COL_NAME_RECT_OBJ_RECTOBJID, rect_objids, replace=replace)
        self.__logger.info("Copying Object Kinematics....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_KINEMATICS_INFO,
                            COL_NAME_RECT_OBJ_RECTOBJID, rect_objids, replace=replace)
        self.__logger.info("Copying Object Kinematics ADMA....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_ADMA_KINEMATICS_INFO,
                            COL_NAME_RECT_OBJ_RECTOBJID, rect_objids, replace=replace)
        self.__logger.info("Copying Object Test Cases....")
        self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_TEST_CASES_INFO,
                            COL_NAME_RECT_OBJ_RECTOBJID, rect_objids, replace=replace)

        if TABLE_NAME_PROBS_CAM_INFO not in EXCLUDE[self.__masterdbschemaprefix]:
            self.__logger.info("Copying Object CAM Prob....")
            self.__copy_records(src_objdb, dest_objdb, TABLE_NAME_PROBS_CAM_INFO,
                                COL_NAME_RECT_OBJ_RECTOBJID, rect_objids, replace=replace)
        return True

    def __export_data_for_label(self, measids, replace=False):
        """
        Db Export specific to measurements for LBL module

        :param measids: list for measurement ids
        :type measids: list
        :param replace: flag to replace the existing label data or nor
        :type replace: boolean
        """
        src_lbldb = self.__adas_connection[LBL][SRC]
        dest_lbltdb = self.__adas_connection[LBL][DEST]
        if replace:
            init_lbl_tab_infos = self.__get_table_no_column(LBL, [COL_NAME_FILES_MEASID])
            self.__copy_table(src_lbldb, dest_lbltdb, init_lbl_tab_infos, replace=replace)
#             self.__copy_table(src_lbldb, dest_lbltdb, init_lbl_tab_infos, replace=replace)

        return self.__copy_records(src_lbldb, dest_lbltdb, TABLE_NAME_LABELS_INFO, COL_NAME_FILES_MEASID,
                                   measids, replace=replace)

    def __copy_records(self, src_db, dest_db, table_info, column_name=None,
                       ids=None, replace=False):
        """
        Copy records for list of ids from src database to destination database

        :param src_db: source database
        :type src_db: oracle db connection
        :param dest_db: destination database
        :type dest_db: sqlite database
        :param table_info: Table structure information from db model module
        :type table_info: dict
        :param column_name: name of the column correspond to IDs
        :type column_name: str
        :param ids: list of id if none is passed then copy whole table
        :type ids: list
        :param replace: flag to replace the existing record or not
        :type replace: boolean
        """
        self.__check_db_connections(src_db, dest_db)
        table_name = table_info[NAME]
        # Get total records from source database to be copied
        src_count_stats = self.__get_record_count(src_db, table_info, column_name, ids, "src db")

        for src_count_stat in src_count_stats:

            if src_count_stat[IDS] is not None:
                if len(src_count_stat[IDS]) == 1:
                    cond = SQLBinaryExpr(column_name, OP_EQ, src_count_stat[IDS][0])
                else:
                    cond = SQLBinaryExpr(column_name, OP_IN, str(tuple(src_count_stat[IDS])))
                if src_count_stat[COUNT] > 0:
                    records = src_db.select_generic_data(select_list=table_info[COL_LIST], table_list=[table_name],
                                                         where=cond)
                    if replace:
                        dest_db.delete_generic_data(table_info[NAME], where=cond)
                    self.__add_generic_prepared_data(dest_db, records, table_info,
                                                     del_existing_record=False)
            else:
                src_cursor = src_db.db_connection.cursor()
                stmt = "Select * from %s" % table_info[NAME]
                if replace:
                    dest_db.delete_generic_data(table_info[NAME])
                try:
                    src_cursor.execute(stmt)
                    while True:
                        if table_info[NAME] in [TABLE_NAME_RESULT_IMAGE, TABLE_NAME_EVENT_IMAGE]:
                            rows = [src_cursor.fetchone()]
                        else:
                            rows = src_cursor.fetchmany(MAX_PREPARED_RECORDS)
                        records = []
                        if len(rows) > 0 and rows[0] is not None:

                            for row in rows:

                                colindex = 0
                                columns = {}
                                for column in src_cursor.description:
                                    columns[column[0].upper()] = row[colindex]
                                    colindex += 1
                                records.append(columns)

                            self.__add_generic_prepared_data(dest_db, records, table_info,
                                                             del_existing_record=False)
                        else:
                            break
                except Exception, src_stmt_exec:
                    self.__logger.error(stmt)
                    self.__logger.error(src_stmt_exec)
                    raise StandardError("Failed to Copy table %s" % table_name)
                finally:
                    src_cursor.close()
        # Get total records from dest database after copy
        dest_count_stats = self.__get_record_count(dest_db, table_info, column_name, ids, "dest db")

        # Check if all is copied!
        if len(src_count_stats) != len(dest_count_stats):
            raise StandardError("Failed to Copy Records for table %s" % table_name)

        else:
            for i in range(len(src_count_stats)):
                if src_count_stats[i][COUNT] != dest_count_stats[i][COUNT]:
                    raise StandardError("Failed to Copy Records for table %s" % table_name)
        return True

    def __get_record_count(self, db_conn, table_info, column_name=None, ids=None, db_type=""):
        """
        Get record statistic for given table

        :param db_conn: Database connection
        :type db_conn: BaseDB
        :param table_info: table information model dictionary
        :type table_info: dict
        :param column_name: column  name
        :type column_name: string
        :param ids: list of Ids
        :type ids: integer
        """
        count_stats = []
        total_count = 0

        if ids is None:

            current_count = db_conn.select_generic_data(select_list=["Count(*) AS COUNT"],
                                                        table_list=[table_info[NAME]],)[0]["COUNT"]
            count_stats = [{IDS: None, COUNT: current_count}]
            total_count = current_count

        else:
            # ids_slices = [ids[i: i + MAX_BATCH_MODE_LIMIT] for i in range(0, len(ids), MAX_BATCH_MODE_LIMIT)]
            current_count = 0
            ids_slices = [[]]
            for id_ in ids:
                cond = SQLBinaryExpr(column_name, OP_EQ, id_)
                count = db_conn.select_generic_data(select_list=["Count(*) AS COUNT"],
                                                    table_list=[table_info[NAME]],
                                                    where=cond)[0]["COUNT"]
                total_count += count
                current_count += count
                ids_slices[-1].append(id_)
                if not (current_count < MAX_PREPARED_RECORDS and len(ids_slices[-1]) < MAX_BATCH_MODE_LIMIT):
                    count_stats.append({IDS: ids_slices[-1], COUNT: current_count})
                    current_count = 0
                    ids_slices.append([])

            if current_count > 0:
                count_stats.append({IDS: ids_slices[-1], COUNT: current_count})

        self.__logger.info("Found %d records in %s" % (total_count, db_type))
        sum_ = 0
        if ids is not None:

            for c_stat in count_stats:
                sum_ += c_stat[COUNT]

            if sum_ != total_count:
                self.__logger.error("Generating chunks of record failed!")
                raise StandardError("Generating chunks of record failed!")

        return count_stats

    def __add_generic_prepared_data(self, dest_conn, records, table_info, del_existing_record=False):
        """
        Add Generic function using prepared statement to insert record in bulk

        :param dest_conn: destination database
        :type dest_conn: sqlite database
        :param records: list of record
        :type records: list
        :param table_info: table info from adase_db_def model
        :type table_info: dict
        :param del_existing_record: flag to delete existing record
        :type del_existing_record: boolean
        """
        not_prepared_idx = []
        prepared = True
        images_ = False
        for i in range(len(records)):
            record = records[i]
            if del_existing_record:
                self.__delete_existing_record(dest_conn, record, table_info)

            if table_info[NAME].lower() == TABLE_NAME_RESULT_IMAGE.lower():
                record[COL_NAME_RESIMG_IMAGE] = buffer(record[COL_NAME_RESIMG_IMAGE].read())
                dest_conn.add_generic_data_prepared([record], table_info[NAME])
                images_ = True

            elif table_info[NAME].lower() == TABLE_NAME_EVENT_IMAGE.lower():
                record[COL_NAME_EVENT_IMG_IMAGE] = buffer(record[COL_NAME_EVENT_IMG_IMAGE].read())
                dest_conn.add_generic_data_prepared([record], table_info[NAME])
                images_ = True
            else:
                if len([j for j in record.values() if type(j) is long and j > MAX_INT64]) > 0:
                    # Add them invidually as string with special datatype adapter
                    # because SQLite3 doesn't support uint64 !
                    not_prepared_idx.append(i)
                    prepared = False

        if not images_:
            if prepared:
                dest_conn.add_generic_data_prepared(records, table_info[NAME])
            else:
                start_idx = 0
                for i in not_prepared_idx:
                    dest_conn.add_generic_data_prepared(records[start_idx: i], table_info[NAME])
                    dest_conn.add_generic_data(records[i], table_info[NAME])
                    start_idx = i + 1
                dest_conn.add_generic_data_prepared(records[start_idx:], table_info[NAME])

    def __export_everything(self, replace=False):
        """
        Export whole db schema instead of specific collection or testrun

        :param replace: flag to replace existing record in the the destination database
        :type replace: boolean
        """
        for mod_name in ADAS_DATABASE_MODULE_NAMES:
            if MODULE_TABLEINFOMAP[mod_name] is not None:
                #  self.__delete_module_tables_record(self.__adas_connection[mod_name][DEST],
                #                                     MODULE_TABLEINFOMAP[mod_name])
                self.__logger.info("Exporting SUBschema %s...." % mod_name)
                self.__copy_module(self.__adas_connection[mod_name][SRC],
                                   self.__adas_connection[mod_name][DEST],
                                   MODULE_TABLEINFOMAP[mod_name], replace=replace)
        return True

    def __copy_module(self, src_connection, dest_connection, table_infolist, replace=False):
        """
        Copy Database modules (e.g. cat val gbl subschemas)

        :param src_connection: db connection object of the source database
        :type src_connection: dbc.OracleBaseDB
        :param dest_connection: db connection of the destination database
        :type dest_connection: dbc.SQLite3BaseDB
        :param table_infolist: list of schema info from adase_db_def model definition
        :type table_infolist: list
        :param replace: flag to replace existing record in database
        :type replace: boolean
        """
        self.__check_db_connections(src_connection, dest_connection)
        for table_info in table_infolist:
            if table_info not in EXCLUDE[self.__masterdbschemaprefix]:
                if not self.__copy_table(src_connection, dest_connection, [table_info], replace=replace):
                    return False
        self.__adas_connection[GBL][DEST].commit()
        return True

    def __copy_table(self, src_connection, dest_connection, table_infolist, replace=False):
        """
        Copy whole table records from source to destination database

        :param src_connection: db connection object of the source database
        :type src_connection: dbc.OracleBaseDB
        :param dest_connection: db connection of the destination database
        :type dest_connection: dbc.SQLite3BaseDB
        :param table_infolist: list of schema info from adase_db_def model definition
        :type table_infolist: list
        :param replace: flag to replace existing record in database
        :type replace: boolean
        """
        self.__check_db_connections(src_connection, dest_connection)
        for table_info in table_infolist:
            self.__logger.info("Copying... %s" % table_info[NAME])
            if replace:
                self.__logger.debug("All record for ... %s will be replace" % table_info[NAME])
                dest_connection.delete_generic_data(table_info[NAME])
            if "ARCHIVE".lower() in table_info[NAME].lower():
                continue
            if table_info in EXCLUDE[self.__masterdbschemaprefix]:
                continue
            self.__copy_records(src_connection, dest_connection, table_info, replace=replace)

            self.__logger.info("Copy table %s Done!" % table_info[NAME])
        return True

    @staticmethod
    def __get_table_no_column(module_name, col_list):
        """
        Get the list of tables which doesnt contain the columns specified in col_list

        :param module_name: subschema name e.g. CAT VAL GBL
        :type module_name: str
        :param col_list: list of column name
        :type col_list: list
        """
        init_tables_infolist = []
        if MODULE_TABLEINFOMAP[module_name] is not None:
            for table_info in MODULE_TABLEINFOMAP[module_name]:
                found = False
                for column_name in col_list:
                    if column_name in table_info[COL_LIST]:
                        found = True
                        break
                if not found:
                    init_tables_infolist.append(table_info)

        return init_tables_infolist

    @staticmethod
    def __delete_module_tables_record(dest_connection, table_infolist):
        """
        Clean all the record from tables from destination database

        :param dest_connection: db connection of the destination database
        :type dest_connection: dbc.SQLite3BaseDB
        :param table_infolist: list of schema info from adase_db_def model definition
        :type table_infolist: list
        """
        for table_info in table_infolist:
            dest_cursor = dest_connection.db_connection.cursor()
            stmt = "Delete from %s" % table_info[NAME]
            try:
                dest_cursor.execute(stmt)
            except Exception, del_exec:
                print stmt
                print del_exec
                raise
            finally:
                dest_cursor.close()

    @staticmethod
    def __delete_existing_record(dest_connection, record, table_info):
        """
        Delete the record in the destination database if exist

        :param dest_connection: db connection of the destination database
        :type dest_connection: dbc.SQLite3BaseDB
        :param record: record in dictionary to be delete
        :type record: dict
        :param table_info: table information from db model definition
        :type table_info: dict
        """
        condition = None
        if len(table_info[PK]) > 0:
            for pk_col in table_info[PK]:
                if condition is not None:
                    condition = SQLBinaryExpr(condition, OP_AND,
                                              SQLBinaryExpr(pk_col, OP_EQ, SQLLiteral(record[pk_col])))
                else:
                    condition = SQLBinaryExpr(pk_col, OP_EQ, SQLLiteral(record[pk_col]))
        else:
            for col_name, value in record.iteritems():
                if col_name not in [COL_NAME_RESIMG_IMAGE, COL_NAME_EVENT_IMG_IMAGE]:
                    if condition is not None:
                        condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(col_name, OP_EQ, SQLLiteral(value)))
                    else:
                        condition = SQLBinaryExpr(col_name, OP_EQ, SQLLiteral(value))
        if len(dest_connection.select_generic_data(table_list=[table_info[NAME]], where=condition)) > 0:
            return dest_connection.delete_generic_data(table_info[NAME], condition)
        else:
            return 0


if __name__ == '__main__':
    sexit(DbImportExport().export_data())


"""
CHANGE LOG:
-----------
$Log: db_im_export.py  $
Revision 1.16 2017/07/14 11:59:33CEST Mertens, Sven (uidv7805) 
copy only known columns
Revision 1.15 2016/10/27 14:10:35CEST Hospes, Gerd-Joachim (uidv8815) 
fix to copy also object label
Revision 1.14 2016/03/16 15:25:11CET Ahmed, Zaheer (uidu7634)
pep8 fixes
Revision 1.13 2016/03/16 15:18:46CET Ahmed, Zaheer (uidu7634)
pylint fix too long line
Revision 1.12 2016/03/16 15:16:40CET Ahmed, Zaheer (uidu7634)
rename private method pytlint fix
Revision 1.11 2016/03/16 15:05:19CET Ahmed, Zaheer (uidu7634)
fixed update_collection() usage due to rename
Revision 1.10 2016/03/04 12:37:40CET Ahmed, Zaheer (uidu7634)
adaption for update_collection() usage
Revision 1.9 2016/03/04 12:17:08CET Ahmed, Zaheer (uidu7634)
adapted update_collection usage for db_imp_export()
Revision 1.8 2015/12/11 17:38:49CET Hospes, Gerd-Joachim (uidv8815)
fix otput path def for logger
Revision 1.7 2015/12/09 14:04:19CET Hospes, Gerd-Joachim (uidv8815)
fix docu
Revision 1.6 2015/12/09 11:49:18CET Hospes, Gerd-Joachim (uidv8815)
pep8 fixes
Revision 1.5 2015/12/09 11:25:10CET Hospes, Gerd-Joachim (uidv8815)
update to argparser, add check for connection parameters or file,
extend module test to check missing parameters in call
Revision 1.4 2015/12/04 13:36:32CET Mertens, Sven (uidv7805)
removing location info copy
Revision 1.3 2015/07/14 14:29:14CEST Mertens, Sven (uidv7805)
db check adaptation
--- Added comments ---  uidv7805 [Jul 14, 2015 2:29:14 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/05/06 11:40:41CEST Ahmed, Zaheer (uidu7634)
parent ID set to null for the given command line collection export
--- Added comments ---  uidu7634 [May 6, 2015 11:40:41 AM CEST]
Change Package : 334226:1 http://mks-psad:7002/im/viewissue?selection=334226
Revision 1.1 2015/04/23 19:03:45CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.27 2015/03/11 13:19:27CET Ahmed, Zaheer (uidu7634)
importing object ennd ego kinematic checkpoint info
--- Added comments ---  uidu7634 [Mar 11, 2015 1:19:28 PM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.26 2015/02/16 16:14:55CET Ahmed, Zaheer (uidu7634)
Added proper logging to about number of record copied status
bug fixed to avoid skipping of records
--- Added comments ---  uidu7634 [Feb 16, 2015 4:14:55 PM CET]
Change Package : 307395:1 http://mks-psad:7002/im/viewissue?selection=307395
Revision 1.24 2015/01/28 07:57:06CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 28, 2015 7:57:07 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.23 2014/12/17 17:13:02CET Ellero, Stefano (uidw8660)
Removed all db.obj based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Dec 17, 2014 5:13:03 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.22 2014/12/16 19:23:01CET Ellero, Stefano (uidw8660)
Remove all db.obj based deprecated function usage inside STK and module tests.
--- Added comments ---  uidw8660 [Dec 16, 2014 7:23:01 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.21 2014/10/31 10:52:37CET Hospes, Gerd-Joachim (uidv8815)
cleanup
--- Added comments ---  uidv8815 [Oct 31, 2014 10:52:38 AM CET]
Change Package : 275077:1 http://mks-psad:7002/im/viewissue?selection=275077
Change Package : 275077:1 http://mks-psad:7002/im/viewissue?selection=275077
Revision 1.20 2014/10/17 11:00:05CEST Ahmed, Zaheer (uidu7634)
Remove AddGeneric Prepared usage to bind datatype for each record insert in SQLite
--- Added comments ---  uidu7634 [Oct 17, 2014 11:00:06 AM CEST]
Change Package : 267593:2 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.19 2014/10/15 08:29:55CEST Hecker, Robert (heckerr)
corrected usage.
--- Added comments ---  heckerr [Oct 15, 2014 8:29:55 AM CEST]
Change Package : 270440:1 http://mks-psad:7002/im/viewissue?selection=270440
Revision 1.18 2014/10/09 20:46:57CEST Hecker, Robert (heckerr)
Using of deprecated property and example usage.
--- Added comments ---  heckerr [Oct 9, 2014 8:46:58 PM CEST]
Change Package : 270819:1 http://mks-psad:7002/im/viewissue?selection=270819
Revision 1.17 2014/09/01 14:14:17CEST Ahmed, Zaheer (uidu7634)
improve epy doc remove pep8 and pylint errors
--- Added comments ---  uidu7634 [Sep 1, 2014 2:14:17 PM CEST]
Change Package : 260449:1 http://mks-psad:7002/im/viewissue?selection=260449
Revision 1.16 2014/09/01 14:01:28CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Sep 1, 2014 2:01:29 PM CEST]
Change Package : 260449:1 http://mks-psad:7002/im/viewissue?selection=260449
Revision 1.15 2014/09/01 12:09:23CEST Ahmed, Zaheer (uidu7634)
Fixed bug for ARS31XX database compatibilty for importing in ARS4XX sqlite file by
add OBJ_PROBS_CAM tables into exclude list for ARS31XX database
--- Added comments ---  uidu7634 [Sep 1, 2014 12:09:23 PM CEST]
Change Package : 260449:1 http://mks-psad:7002/im/viewissue?selection=260449
Revision 1.14 2014/07/31 18:04:14CEST Hecker, Robert (heckerr)
Changed to correct Bpl Usage.
--- Added comments ---  heckerr [Jul 31, 2014 6:04:15 PM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.13 2014/07/14 16:16:46CEST Ahmed, Zaheer (uidu7634)
added support to handle BPL file as input
--- Added comments ---  uidu7634 [Jul 14, 2014 4:16:47 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.12 2014/06/30 16:00:01CEST Ahmed, Zaheer (uidu7634)
Adaption made for unit test execution
--- Added comments ---  uidu7634 [Jun 30, 2014 4:00:02 PM CEST]
Change Package : 245283:1 http://mks-psad:7002/im/viewissue?selection=245283
Revision 1.11 2014/06/08 13:44:59CEST Ahmed, Zaheer (uidu7634)
pylint fix
--- Added comments ---  uidu7634 [Jun 8, 2014 1:44:59 PM CEST]
Change Package : 238253:1 http://mks-psad:7002/im/viewissue?selection=238253
Revision 1.10 2014/06/08 13:10:13CEST Ahmed, Zaheer (uidu7634)
Improve doucmentation
--- Added comments ---  uidu7634 [Jun 8, 2014 1:10:13 PM CEST]
Change Package : 238253:1 http://mks-psad:7002/im/viewissue?selection=238253
Revision 1.9 2014/05/28 16:15:58CEST Ahmed, Zaheer (uidu7634)
pylint fixes
--- Added comments ---  uidu7634 [May 28, 2014 4:15:59 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.8 2014/05/28 13:49:53CEST Ahmed, Zaheer (uidu7634)
Improve Documentation and PROB CAM data export
--- Added comments ---  uidu7634 [May 28, 2014 1:49:54 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.7 2014/05/06 13:13:05CEST Ahmed, Zaheer (uidu7634)
changes made to support ARS31X database to be export in Sqlite database based on ARS4XX schema
--- Added comments ---  uidu7634 [May 6, 2014 1:13:05 PM CEST]
Change Package : 233916:1 http://mks-psad:7002/im/viewissue?selection=233916
Revision 1.6 2014/04/30 16:28:05CEST Hecker, Robert (heckerr)
removed pep8 issues.
--- Added comments ---  heckerr [Apr 30, 2014 4:28:05 PM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.5 2014/04/15 14:02:33CEST Hecker, Robert (heckerr)
some adaptions to pylint.
--- Added comments ---  heckerr [Apr 15, 2014 2:02:34 PM CEST]
Change Package : 231472:1 http://mks-psad:7002/im/viewissue?selection=231472
Revision 1.4 2014/04/15 08:57:04CEST Hecker, Robert (heckerr)
Added some pylint exceptions to reduce number of messages.
Revision 1.3 2014/03/24 08:14:43CET Ahmed, Zaheer (uidu7634)
Reimplemented __CopyRecord() with bug fix and with more readable code
remove old unsed functions
use AddGenericPrepared() from BaseDB
--- Added comments ---  uidu7634 [Mar 24, 2014 8:14:43 AM CET]
Change Package : 224321:1 http://mks-psad:7002/im/viewissue?selection=224321
Revision 1.2 2013/12/05 15:59:30CET Ahmed, Zaheer (uidu7634)
Improve outfile name to for better description showing which masteer schema
was imported into sqlite db
--- Added comments ---  uidu7634 [Dec 5, 2013 3:59:31 PM CET]
Change Package : 210017:2 http://mks-psad:7002/im/viewissue?selection=210017
Revision 1.1 2013/11/18 10:27:33CET Ahmed-EXT, Zaheer (uidu7634)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
/STK_ScriptingToolKit/04_Engineering/stk/cmd/project.pj
"""
