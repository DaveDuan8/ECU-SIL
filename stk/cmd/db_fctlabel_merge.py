"""
db_fctlabel_merge.py
--------------------

Merge function label database tables

:org:           Continental AG
:author:        Sohaib Zafar

:version:       $$
:contact:       $$ (last change)
:date:          $$
"""
# ====================================================================
# System Imports
# ====================================================================

import os
import time
import sys
import logging
import copy
from optparse import OptionParser
from datetime import datetime

# ====================================================================
# Set system path
# ====================================================================
MODULE_TEST_FOLDER = os.path.abspath(os.path.split(__file__)[0])
if MODULE_TEST_FOLDER not in sys.path:
    sys.path.append(MODULE_TEST_FOLDER)
STK_FOLDER = os.path.abspath(os.path.join(os.path.split(__file__)[0], r"..\.."))
if STK_FOLDER not in sys.path:
    sys.path.append(STK_FOLDER)

# ====================================================================
# Import STK Modules
# ====================================================================
from stk.db.gbl import gbl
from stk.db.val import val
from stk.db.cat import cat
from stk.db.fct import fct
from stk.db.obj import objdata
from stk.db.lbl import genlabel
from stk.db.db_connect import DBConnect
from stk.db import ERROR_TOLERANCE_NONE
from stk.obj.error import AdasObjectLoadError
from stk.obj.label_objects import LabelRectObject, DbObjectList
from stk.obj.adas_object_filters import ObjectInRectangle
from stk.db import db_common


# ====================================================================
# FCT Label Merging Class
# ====================================================================
class FCTLabelDBMerge(object):
    """Merge function label database"""
    def __init__(self):
        """Constructor"""
        self.input = None
        self.update = None

    def synchronize_database(self, master_databaseconnections, slave_databaseconnections, update="Master"):
        """
        Update Master and Slave Database by merging FCT Labels
        :param master_databaseconnections: master database connections
        :type master_databaseconnections: array
        :param slave_databaseconnections: slave database connections
        :type slave_databaseconnections: array
        :param update: variable defining which database is to be updated
        :type update: string
        returns: the overlapping scenarios of input database
        """
        if update.lower() == "master":
            self.update = "Master"
            out_gbldb = master_databaseconnections["gbl"]
            out_catdb = master_databaseconnections["cat"]
            out_fctdb = master_databaseconnections["fct"]
            out_objdb = master_databaseconnections["obj"]
            out_lbldb = master_databaseconnections["lbl"]

            self.input = "Slave"
            in_gbldb = slave_databaseconnections["gbl"]
            in_catdb = slave_databaseconnections["cat"]
            in_fctdb = slave_databaseconnections["fct"]
            in_objdb = slave_databaseconnections["obj"]
            in_lbldb = slave_databaseconnections["lbl"]

        elif update.lower() == "slave":
            self.update = "Slave"
            out_gbldb = slave_databaseconnections["gbl"]
            out_catdb = slave_databaseconnections["cat"]
            out_fctdb = slave_databaseconnections["fct"]
            out_objdb = slave_databaseconnections["obj"]
            out_lbldb = slave_databaseconnections["lbl"]

            self.input = "Master"
            in_gbldb = master_databaseconnections["gbl"]
            in_catdb = master_databaseconnections["cat"]
            in_fctdb = master_databaseconnections["fct"]
            in_objdb = master_databaseconnections["obj"]
            in_lbldb = master_databaseconnections["lbl"]
        else:
            logging.error("update option could either be 'master' or 'slave'")

        in_scns = []
        input_overlap_scenarioids = []
        input_scn = in_fctdb.get_all_scenarios()
        if type(input_scn) == dict:
            in_scns.append(input_scn)
        elif type(input_scn) == list:
            in_scns = input_scn
        else:
            in_scns = []

        updated_in_scns = copy.deepcopy(in_scns)
        if fct.COL_NAME_SCENARIO_SCENARIOID in in_scns[0]:

            for i in xrange(len(in_scns)):
                # Get Label Names from Slave DB Label IDs
                if in_scns[i][fct.COL_NAME_SCENARIO_SCENARIOID] >= CMD_OPTIONS[0].firstscenarioid:
                    print "Reading " + self.input + " DB FCT Labels " + str(i) + " of " + str(len(in_scns))
                    recfilename = in_catdb.get_rec_file_name_for_measid(in_scns[i][fct.COL_NAME_SCENARIO_MEASID])
                    infrastructure = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_ENV_INFRASTRUCTURE])
                    light_cond = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_ENV_LIGHT_CONDITION])
                    weather = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_ENV_WEATHER_CONDITION])
                    data_integrity = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_ENV_DATAINTEGRITY])
                    labeler_crit = in_fctdb.get_criticality_name(in_scns[i][fct.COL_NAME_SCENARIO_LABELER_CRITICALITY])
                    vehicle_crit = in_fctdb.get_criticality_name(in_scns[i][fct.COL_NAME_SCENARIO_VEHICLE_CRITICALITY])
                    driver_crit = in_fctdb.get_criticality_name(in_scns[i][fct.COL_NAME_SCENARIO_DRIVER_CRITICALITY])
                    label_state = in_lbldb.get_state_name(in_scns[i][fct.COL_NAME_SCENARIO_LBLSTATEID])
                    lb_by = in_gbldb.get_user(user_id=in_scns[i][fct.COL_NAME_SCENARIO_LBLBY])[gbl.COL_NAME_USER_LOGIN]
                    project = in_gbldb.get_project_name(in_scns[i][fct.COL_NAME_SCENARIO_PID])
                    ego_bhvr = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_EGO_BEHAVIOR])
                    rel_ego_bhvr = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_REL_EGO_BEHAVIOR])
                    obj_dynamic = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_OBJ_DYNAMIC])
                    obj_type = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_OBJ_TYPE])
                    obj_bhvr = in_fctdb.get_environment(in_scns[i][fct.COL_NAME_SCENARIO_OBJ_BEHAVIOR])

                    # Get Master DB Label IDs from Label Names
                    print "Reading " + self.update + " DB FCT Labels."
                    tmp_measid = out_catdb.get_measurement_id(recfilename)
                    tmp_inf_id = out_fctdb.get_environment_id(infrastructure[fct.COL_NAME_ENVIRONMENT_NAME],
                                                              infrastructure[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_light_cond_id = out_fctdb.get_environment_id(light_cond[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                     light_cond[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_weather_id = out_fctdb.get_environment_id(weather[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                  weather[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_data_int_id = out_fctdb.get_environment_id(data_integrity[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                   data_integrity[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_labeler_crit_id = out_fctdb.get_criticality_id(labeler_crit)
                    tmp_vehicle_crit_id = out_fctdb.get_criticality_id(vehicle_crit)
                    tmp_driver_crit_id = out_fctdb.get_criticality_id(driver_crit)
                    tmp_label_state_id = out_lbldb.get_state_id(label_state)
                    try:
                        tmp_lbl_id = out_gbldb.get_user(login=lb_by)[gbl.COL_NAME_USER_ID]
                    except KeyError:
                        userid = in_scns[i][fct.COL_NAME_SCENARIO_LBLBY]
                        tmp_lbl_id = out_gbldb.AddUser(in_gbldb.get_user(user_id=userid))
                    tmp_project_id = out_gbldb.get_project_id(project)
                    tmp_ego_bhvr_id = out_fctdb.get_environment_id(ego_bhvr[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                   ego_bhvr[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_relego_bhvr_id = out_fctdb.get_environment_id(rel_ego_bhvr[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                      rel_ego_bhvr[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_obj_dynamic_id = out_fctdb.get_environment_id(obj_dynamic[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                      obj_dynamic[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_obj_type_id = out_fctdb.get_environment_id(obj_type[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                   obj_type[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])
                    tmp_obj_bhvr_id = out_fctdb.get_environment_id(obj_bhvr[fct.COL_NAME_ENVIRONMENT_NAME],
                                                                   obj_bhvr[fct.COL_NAME_ENVIRONMENT_ENVTYPEID])

                    # Update Slave DB Scenario with Master DB IDs
                    print "Updating " + self.update + " DB FCT Labels."
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_MEASID] = tmp_measid
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_ENV_INFRASTRUCTURE] = tmp_inf_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_ENV_LIGHT_CONDITION] = tmp_light_cond_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_ENV_WEATHER_CONDITION] = tmp_weather_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_ENV_DATAINTEGRITY] = tmp_data_int_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_LABELER_CRITICALITY] = tmp_labeler_crit_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_VEHICLE_CRITICALITY] = tmp_vehicle_crit_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_DRIVER_CRITICALITY] = tmp_driver_crit_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_LBLSTATEID] = tmp_label_state_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_LBLBY] = tmp_lbl_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_PID] = tmp_project_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_EGO_BEHAVIOR] = tmp_ego_bhvr_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_REL_EGO_BEHAVIOR] = tmp_relego_bhvr_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_OBJ_DYNAMIC] = tmp_obj_dynamic_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_OBJ_TYPE] = tmp_obj_type_id
                    updated_in_scns[i][fct.COL_NAME_SCENARIO_OBJ_BEHAVIOR] = tmp_obj_bhvr_id
                    updated_in_scns[i].pop(fct.COL_NAME_SCENARIO_SCENARIOID)
                    scenario_id = out_fctdb.add_scenario(updated_in_scns[i])
                    # Rectangular Object
                    if scenario_id is not None and scenario_id >= 0:
                        tmp_rect_obj_id = self.compare_rectangular_objects(in_scns[i][fct.COL_NAME_SCENARIO_RECTOBJID],
                                                                           in_objdb, tmp_measid, out_objdb, out_gbldb)
                        updated_in_scns[i][fct.COL_NAME_SCENARIO_RECTOBJID] = tmp_rect_obj_id
                        out_fctdb.update_scenario(updated_in_scns[i])
                        out_fctdb.commit()
                        logging.info(self.update + " DB FCT committed.")
                    else:
                        input_overlap_scenarioids.append(in_scns[i][fct.COL_NAME_SCENARIO_SCENARIOID])
                        out_fctdb.rollback()
                        logging.info(update + " DB FCT rollback.")
        logging.info("Overlapping " + self.input + " DB Scenario IDs : %s." % input_overlap_scenarioids)
        return input_overlap_scenarioids

    def compare_rectangular_objects(self, input_rect_obj_id, in_objdb, tmp_measid, out_objdb, out_gbldb):
        """
        Compare the Rectangular Objects between two databases
        :param input_rect_obj_id: Rectangular Object ID
        :param in_objdb: OBJ Database 1 connection
        :param tmp_measid: Measurement ID
        :param out_objdb: OBJ Database 2 connection
        :param out_gbldb: GBL Database 2 connection
        return: Updated Database Rectangular Object ID
        """
        tmp_rect_obj_id = None
        if input_rect_obj_id is not None:
            print "Reading " + self.input + " Rectangular Object Labels."
            label_object = LabelRectObject(input_rect_obj_id, None, None, data_source=in_objdb)
            tmp_objects = DbObjectList(out_objdb, tmp_measid, "sensor", "DbObjectList", ObjectInRectangle())
            try:
                print "Comparing " + self.input + " DB Rectangular Object to " + self.update + " DB."
                tmp_objects.load_objects()
                best_object = tmp_objects.get_best_tracked_object(label_object, label_object.get_start_time(),
                                                                  label_object.get_end_time())
            except AdasObjectLoadError:
                best_object = []
            if best_object != []:
                tmp_rect_obj_id = best_object[0].get_id()
            else:
                print "Inserting " + self.input + " Rectangular Object and Kinematics in " + self.update + " DB."
                user = out_gbldb.get_user(login=os.environ["USERNAME"])
                current_time = datetime.now()
                rect_obj_record_template = {objdata.COL_NAME_RECT_OBJ_MEASID: tmp_measid,
                                            objdata.COL_NAME_RECT_OBJ_ASSOCTYPEID: 0,
                                            objdata.COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED: 0,
                                            objdata.COL_NAME_RECT_OBJ_OBJCLASSID: 1,
                                            objdata.COL_NAME_RECT_OBJ_CLSLBLSTATEID: 1,
                                            objdata.COL_NAME_RECT_OBJ_CLSLBLTIME: current_time,
                                            objdata.COL_NAME_RECT_OBJ_CLSLBLBY: user[gbl.COL_NAME_USER_ID],
                                            objdata.COL_NAME_RECT_OBJ_OBJWIDTH: 1,
                                            objdata.COL_NAME_RECT_OBJ_OBJLENGTH: 1,
                                            objdata.COL_NAME_RECT_OBJ_OBJHEIGHT: 1,
                                            objdata.COL_NAME_RECT_OBJ_DIMLBLSTATEID: 1,
                                            objdata.COL_NAME_RECT_OBJ_DIMLBLTIME: current_time,
                                            objdata.COL_NAME_RECT_OBJ_DIMLBLBY: user[gbl.COL_NAME_USER_ID],
                                            objdata.COL_NAME_RECT_OBJ_ZLAYER: 5,
                                            objdata.COL_NAME_RECT_OBJ_ZOVERGROUND: 1,
                                            objdata.COL_NAME_RECT_OBJ_ZOLBLSTATEID: 1,
                                            objdata.COL_NAME_RECT_OBJ_ZOLBLBY: user[gbl.COL_NAME_USER_ID],
                                            objdata.COL_NAME_RECT_OBJ_ZOLBLTIME: current_time,
                                            objdata.COL_NAME_RECT_OBJ_KINLBLSTATEID: 1,
                                            objdata.COL_NAME_RECT_OBJ_KINLBLMODTIME: current_time,
                                            objdata.COL_NAME_RECT_OBJ_LBLBY: user[gbl.COL_NAME_USER_ID]}

                tmp_rect_obj_id = label_object.write_object_into_db(meas_id=tmp_measid, assoc_type=0,
                                                                    rect_obj_record_template=rect_obj_record_template,
                                                                    db_source=out_objdb)
                out_objdb.commit()
                logging.info(self.update + " DB OBJ committed.")
        return tmp_rect_obj_id

# ====================================================================
# Main
# ====================================================================

if __name__ == '__main__':
    START_TIME = time.time()
    """
    Examples:
    * Update Master SQLite database file by synchronizing from Slave SQLite database file.
    --slave-db-file <path><filename>.sqlite --master-db-file <path><filename>.sqlite --master-db-update

    * Update Slave SQLite database file by synchronizing from Master SQLite database file.
    --slave-db-file <path><filename>.sqlite --master-db-file <path><filename>.sqlite --slave-db-update

    * Update Master ORACLE database by synchronizing from Slave SQLite database file.
    ---slave-db-file <path><filename>.sqlite  -u <user> -p <login> --master-db-update

    * Update Slave SQLite database file by synchronizing from Master ORACLE database.
    --slave-db-file <path><filename>.sqlite  -u <user> -p <login> --slave-db-update
    """

    # Parse command line parameters
    OPTPARSER = OptionParser(usage="usage: %prog [options] label-path(s)")
    OPTPARSER.add_option("-s", "--slave-db-file", dest="slavedbfile", default=False,
                         help="The path to the slave database file. [default=%s]" % False)
    OPTPARSER.add_option("-m", "--master-db-file", dest="masterdbfile", default=None,
                         help="The path to the slave database file. [default=%s]" % False)
    OPTPARSER.add_option("-a", "--slave-db-update", dest="slavedbupdate", action="store_true", default=False,
                         help="Set if the slave database shall be updated from master. default=%s" % False)
    OPTPARSER.add_option("-b", "--master-db-update", dest="masterdbupdate", action="store_true", default=False,
                         help="Set  if the master database shall be updated from slave. default=%s" % False)
    OPTPARSER.add_option("-n", "--master-db-dsn", dest="masterdbdsn", default=db_common.DEFAULT_MASTER_DSN,
                         help="The name of the DSN. [default=%s]" % db_common.DEFAULT_MASTER_DSN)
    OPTPARSER.add_option("-q", "--master-db-dbq", dest="masterdbdbq", default=db_common.DEFAULT_MASTER_DBQ,
                         help="The name of the DBQ. [default=%s]" % db_common.DEFAULT_MASTER_DBQ)
    OPTPARSER.add_option("-u", "--master-db-user", dest="masterdbuser",
                         help="The name of the database user.")
    OPTPARSER.add_option("-p", "--master-db-password", dest="masterdbpassword",
                         help="The name of the database password.")
    OPTPARSER.add_option("-f", "--first-scenario-id", dest="firstscenarioid", default=1,
                         help="First Scenario ID where the scenario from master and slave DBS are not duplicate. \
                         default=%s" % 1)

    CMD_OPTIONS = OPTPARSER.parse_args()
    # Initialize connection for master db
    if CMD_OPTIONS[0].masterdbfile is None:
        MASTER_DB_CONNECTOR = DBConnect(dsn=CMD_OPTIONS[0].masterdbdsn, dbq=CMD_OPTIONS[0].masterdbdbq,
                                        user=CMD_OPTIONS[0].masterdbuser, pw=CMD_OPTIONS[0].masterdbpassword,
                                        error_tolerance=ERROR_TOLERANCE_NONE)
    else:
        if not os.path.isfile(CMD_OPTIONS[0].masterdbfile):
            logging.error('Master Database %s not found.', str(CMD_OPTIONS[0].masterdbfile))
            raise BaseException
        else:
            MASTER_DB_CONNECTOR = DBConnect(db_file=CMD_OPTIONS[0].masterdbfile, error_tolerance=ERROR_TOLERANCE_NONE)

    MASTER_VALDB = MASTER_DB_CONNECTOR.Connect(val)
    MASTER_GBLDB = MASTER_DB_CONNECTOR.Connect(gbl)
    MASTER_CATDB = MASTER_DB_CONNECTOR.Connect(cat)
    MASTER_OBJDB = MASTER_DB_CONNECTOR.Connect(objdata)
    MASTER_FCTDB = MASTER_DB_CONNECTOR.Connect(fct)
    MASTER_LBLDB = MASTER_DB_CONNECTOR.Connect(genlabel)
    MASTER_DB_CONNECTIONS = {"val": MASTER_VALDB,
                             "gbl": MASTER_GBLDB,
                             "cat": MASTER_CATDB,
                             "obj": MASTER_OBJDB,
                             "fct": MASTER_FCTDB,
                             "lbl": MASTER_LBLDB}

    # Initialize connection for slave db
    if not os.path.isfile(CMD_OPTIONS[0].slavedbfile):
        logging.error('Slave Database %s not found.', str(CMD_OPTIONS[0].slavedbfile))
        raise BaseException
    else:
        SLAVE_DB_CONNECTOR = DBConnect(db_file=CMD_OPTIONS[0].slavedbfile, error_tolerance=ERROR_TOLERANCE_NONE)

    SLAVE_VALDB = SLAVE_DB_CONNECTOR.Connect(val)
    SLAVE_GBLDB = SLAVE_DB_CONNECTOR.Connect(gbl)
    SLAVE_CATDB = SLAVE_DB_CONNECTOR.Connect(cat)
    SLAVE_OBJDB = SLAVE_DB_CONNECTOR.Connect(objdata)
    SLAVE_FCTDB = SLAVE_DB_CONNECTOR.Connect(fct)
    SLAVE_LBLDB = SLAVE_DB_CONNECTOR.Connect(genlabel)
    SLAVE_DB_CONNECTIONS = {"val": SLAVE_VALDB,
                            "gbl": SLAVE_GBLDB,
                            "cat": SLAVE_CATDB,
                            "obj": SLAVE_OBJDB,
                            "fct": SLAVE_FCTDB,
                            "lbl": SLAVE_LBLDB}

    # Merge the Database
    FCT_LABEL_DB_MERGE = FCTLabelDBMerge()
    if CMD_OPTIONS[0].masterdbupdate:
        # Master DB Update
        OVERLAP_SCENARIOIDS = FCT_LABEL_DB_MERGE.synchronize_database(MASTER_DB_CONNECTIONS,
                                                                      SLAVE_DB_CONNECTIONS)
        TEXT = "Overlapping Slave DB Scenario IDs."

    if CMD_OPTIONS[0].slavedbupdate:
        # Slave DB Update
        OVERLAP_SCENARIOIDS = FCT_LABEL_DB_MERGE.synchronize_database(MASTER_DB_CONNECTIONS,
                                                                      SLAVE_DB_CONNECTIONS, update="Slave")
        TEXT = "Overlapping Master DB Scenario IDs."

    TEXT_OUTPUT_FOLDER = os.path.split(CMD_OPTIONS[0].slavedbfile)[0]
    # Open a file
    FILE_OPEN = open(TEXT_OUTPUT_FOLDER + "\\overlapping_scenarios.txt", "w")
    FILE_OPEN.writelines(TEXT + "\n%s" % OVERLAP_SCENARIOIDS)
    # Close open file
    FILE_OPEN.close()

    # Done
    STOP_TIME = time.time()
    logging.info("Done in %s.", str(time.strftime('%Hh:%Mm:%Ss', time.gmtime(STOP_TIME - START_TIME))))


"""
$Log: db_fctlabel_merge.py  $
Revision 1.3 2017/07/14 11:59:51CEST Mertens, Sven (uidv7805) 
default is None
Revision 1.2 2015/12/07 16:25:59CET Mertens, Sven (uidv7805) 
removing pep8 error
Revision 1.1 2015/04/23 19:03:44CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.8 2015/02/03 18:55:37CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 3, 2015 6:55:38 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.7 2015/01/23 14:18:28CET Mertens, Sven (uidv7805)
deprecating another method
--- Added comments ---  uidv7805 [Jan 23, 2015 2:18:28 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.6 2015/01/20 08:05:10CET Mertens, Sven (uidv7805)
changing deprecated calls
--- Added comments ---  uidv7805 [Jan 20, 2015 8:05:11 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.5 2014/12/11 15:40:28CET Ellero, Stefano (uidw8660)
Removed all db.fct based deprecated function usage inside stk and module tests
--- Added comments ---  uidw8660 [Dec 11, 2014 3:40:29 PM CET]
Change Package : 281275:1 http://mks-psad:7002/im/viewissue?selection=281275
Revision 1.4 2014/11/21 11:23:56CET Zafar, Sohaib (uidu6396)
Removing pep8, pylint and deprecation Warnings.
--- Added comments ---  uidu6396 [Nov 21, 2014 11:23:57 AM CET]
Change Package : 283224:1 http://mks-psad:7002/im/viewissue?selection=283224
Revision 1.3 2014/11/20 17:06:04CET Zafar, Sohaib (uidu6396)
First Duplicate Scenario ID command line parameter introduced
--- Added comments ---  uidu6396 [Nov 20, 2014 5:06:05 PM CET]
Change Package : 283224:1 http://mks-psad:7002/im/viewissue?selection=283224
Revision 1.2 2014/08/27 10:22:23CEST Zafar, Sohaib (uidu6396)
pep8 errors removed
--- Added comments ---  uidu6396 [Aug 27, 2014 10:22:23 AM CEST]
Change Package : 253404:1 http://mks-psad:7002/im/viewissue?selection=253404
Revision 1.1 2014/08/26 20:10:14CEST Zafar, Sohaib (uidu6396)
Initial revision
Member added to project
/nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/cmd/project.pj
"""
