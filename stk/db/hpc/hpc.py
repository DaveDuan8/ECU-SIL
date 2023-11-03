"""
hpc.py
------

Interface into the Error Database of HPC.

**User-API**
    - `HpcErrorDB`
        reading HPC errors for a known HPC job Id

**internally used class**
    - `ToHex`
        sqlite aggregation support for converting numbers to a hex string

:org:           Continental AG
:author:        Robert Hecker

:since: 10.12.2013

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:26CEST $
"""
# pylint: disable=W0142
__all__ = ["HpcErrorDB"]
# - Python imports ----------------------------------------------------------------------------------------------------
from functools import partial

# - STK imports -------------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, AdasDBError


# - classes -----------------------------------------------------------------------------------------------------------
class ToHex(object):
    """sqlite aggregation support for converting numbers to a hex string
    """
    def __init__(self):
        self._number = 0

    def step(self, value):
        """take over each line's value"""
        self._number = value

    def finalize(self):
        """return value in hex"""
        return "%X" % self._number


class HpcErrorDB(BaseDB):
    """
    **Hpc Error DB Interface**

    This class provides a interface towards the Error-DB from HPC.
    All Errors which are found in the Subtask xxx_check will be stored here.

    For the connection to the DB for hpc error tables just create a new instance of this class
    with server name and job id like

    .. python::

        from stk.db.hpc.hpc import HpcErrorDB

        dbhpc = HpcErrorDB("luss021", 0815)

    The connection is closed when the instance using it is deleted.

    """

    def __init__(self, node, jobid, **kwargs):
        """error DB interface

        :param node: name of node to use
        :param jobid: id of job to use
        """
        BaseDB.__init__(self, kwargs.pop('db', 'HPC'), autocommit=kwargs.pop('autocommit', False), aggregates=[ToHex])

        try:
            self._jobid = self.execute("SELECT JOBID FROM HPC_JOB INNER JOIN HPC_NODE USING(NODEID) "
                                       "WHERE NODENAME = :node AND HPCJOBID = :job", node=node.upper(), job=jobid)[0][0]
        except:
            raise AdasDBError("no such job %d for node %s existing in DB" % (jobid, node))

        self.err_types = {i[0]: i[1] for i in self.execute("SELECT TYPENAME, TYPEID FROM HPC_ERRTYPE")}

    def __exit__(self, *args):  # value / traceback
        """just exit"""
        BaseDB.__exit__(self, *args)

    @property
    def jobid(self):
        """returns db's jobid"""
        return self._jobid

    def __getattr__(self, item):
        """old signatures looked like that:
             def get_count(self, task_id=None, err_type=None)
               '''return the amount of errors for given task and type (either or both can be None).'''

           also provides those:
             def get_num_crashes(self, task_id=None)
             def get_num_exceptions(self, task_id=None)
             def get_num_errors(self, task_id=None)
             def get_num_alerts(self, task_id=None)
             def get_num_information(self, task_id=None)
             def get_num_debugs(self, task_id=None)

        """
        def get_count(*args, **kwargs):
            """get count

            :keyword err_type: type of error you want to have count from
            :keyword task_id: narrow down task
            :returns a number of how much items we have in DB"""
            if self._jobid is None:
                return 0

            vals = {'job': self._jobid}
            errtype = kwargs.pop('err_type', None if len(args) <= 1 else args[1])
            if errtype in (None, "count"):
                errtype = ""
            else:
                vals['terr'] = self.err_types[errtype.capitalize()]
                errtype = " AND TYPEID = :terr "

            taskid = kwargs.pop('task_id', None if len(args) == 0 else args[0])
            if taskid is None:
                taskid = ""
            else:
                vals['task'] = taskid
                taskid = " AND HPCTASKID = :task "

            sql = ("SELECT SUM(CNT) FROM HPC_ERRTYPE INNER JOIN HPC_TASKERRORS USING(TYPEID) "
                   "INNER JOIN HPC_TASK USING(TASKID) INNER JOIN HPC_JOB USING(JOBID) "
                   "WHERE JOBID = :job %s%s"
                   "GROUP BY TYPENAME" % (errtype, taskid))

            return sum([k[0] for k in self.execute(sql, **vals)])

        item = item.rstrip('es').lower()
        if item in ([("get_num_" + i.lower()) for i in self.err_types] + ["get_count"]):
            item = item[8 if item[4:].startswith('num_') else 4:]

            return partial(get_count, err_type=item)
        else:
            raise AttributeError(item)

    if False:  # just for the docu...
        @staticmethod
        def get_num_crashes():
            """:return: number of crashes for certain task, if None, all tasks of job"""
            pass

        @staticmethod
        def get_num_exceptions():
            """:return: number of exceptions for certain task, if None, all tasks of job"""
            pass

        @staticmethod
        def get_num_errors(task_id=None):
            """:return: number of errors for certain task, if None, all tasks of job"""
            pass

        @staticmethod
        def get_num_alerts(task_id=None):
            """:return: number of alerts for certain task, if None, all tasks of job"""
            pass

        @staticmethod
        def get_num_information(task_id=None):
            """:return: number of info messages for certain task, if None, all tasks of job"""
            pass

        @staticmethod
        def get_num_debugs(task_id=None):
            """:return: number of debug messages for certain task, if None, all tasks of job"""
            pass

    def get_list_of_incidents(self, task_id=None, err_type=None, **kwargs):
        """Get a list of all incidents (errors, exceptions and crashes)
        for the given job_id and, optionally, task_id

        :param task_id: hpc task id to get the list from
        :type task_id: int
        :param err_type: type of incidents to return: 'Error', 'Exception', 'Crash'
        :type err_type: str | int
        :param kwargs: additional parameters to execute statement
        :return: list of incidents
        """
        if self._jobid is None:
            return []

        if err_type is None:
            err_type = self.err_types.values()
        elif type(err_type) == str:
            err_type = [self.err_types[err_type.capitalize()]]

        args = {'job': self._jobid}
        args.update({("id%d" % (k + 1)): v for k, v in enumerate(err_type)})

        sql = ("SELECT TYPEID, TYPENAME, SUM(CNT), '0x' || %s, DESCR, NVL(SRC, '-'), NVL(%s, '-') "
               "FROM HPC_ERRORS INNER JOIN HPC_ERRTYPE USING(TYPEID) "
               "INNER JOIN HPC_TASK USING(TASKID) "
               "INNER JOIN HPC_JOB USING(JOBID) "
               "WHERE JOBID = :job AND TYPEID IN (%s) "
               % (["TOHEX(CODE)", "TRIM(TO_CHAR(CODE,'XXXXXXXX'))"][self._db_type],
                  ["strftime('%%Y-%%m-%%d %%H:%%M:%%S', ERRDATE)",
                   "TO_CHAR(ERRDATE, 'YYYY-MM-DD HH24:MI:SS')"][self._db_type],
                  ", ".join([":id%d" % i for i in xrange(1, len(err_type) + 1)])))

        if task_id is not None and task_id != []:
            if type(task_id) == int:
                task_id = [task_id]
            args.update({("tsk%d" % (k + 1)): v for k, v in enumerate(task_id)})
            sql += "AND HPCTASKID in (%s) " % ", ".join([":tsk%d" % i for i in xrange(1, len(task_id) + 1)])
        sql += ("GROUP BY TYPEID, TYPENAME, CODE, DESCR, SRC, ERRDATE "
                "ORDER BY 1, 4, 3 DESC")
        args.update(kwargs)

        return self.execute(sql, **args)


"""
CHANGE LOG:
-----------
$Log: hpc.py  $
Revision 1.4 2016/08/16 12:26:26CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.3 2016/07/07 08:16:39CEST Mertens, Sven (uidv7805)
just for the documentation purpose
Revision 1.2 2016/07/06 13:49:07CEST Mertens, Sven (uidv7805)
update to non-sqlalchemy
Revision 1.1 2015/04/23 19:04:06CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/hpc/project.pj
Revision 1.3 2015/03/06 15:00:47CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Mar 6, 2015 3:00:48 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.2 2015/01/20 16:54:36CET Mertens, Sven (uidv7805)
removing the only pep8 error
Revision 1.1 2015/01/20 08:13:46CET Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/db/hpc/project.pj
Revision 1.12 2014/10/22 10:49:51CEST Hecker, Robert (heckerr)
updated deprecateion handling,
and take care that deprecation is inside epydoc.
--- Added comments ---  heckerr [Oct 22, 2014 10:49:51 AM CEST]
Change Package : 273927:1 http://mks-psad:7002/im/viewissue?selection=273927
Revision 1.11 2014/08/08 12:09:49CEST Mertens, Sven (uidv7805)
adding exception when no task exists on listing incidents
--- Added comments ---  uidv7805 [Aug 8, 2014 12:09:49 PM CEST]
Change Package : 253435:1 http://mks-psad:7002/im/viewissue?selection=253435
Revision 1.10 2014/08/04 15:14:05CEST Mertens, Sven (uidv7805)
adaptation for HPC head node
--- Added comments ---  uidv7805 [Aug 4, 2014 3:14:05 PM CEST]
Change Package : 253438:1 http://mks-psad:7002/im/viewissue?selection=253438
Revision 1.9 2014/07/25 11:09:33CEST Hecker, Robert (heckerr)
Added Task filter.
--- Added comments ---  heckerr [Jul 25, 2014 11:09:34 AM CEST]
Change Package : 251622:1 http://mks-psad:7002/im/viewissue?selection=251622
Revision 1.8 2014/06/27 13:34:00CEST Mertens, Sven (uidv7805)
adding support for count column to reduce err storage a bit
--- Added comments ---  uidv7805 [Jun 27, 2014 1:34:01 PM CEST]
Change Package : 244394:1 http://mks-psad:7002/im/viewissue?selection=244394
Revision 1.7 2014/06/13 10:34:24CEST Hecker, Robert (heckerr)
Marked old methods as deprecated, replaced old with new ones.
--- Added comments ---  heckerr [Jun 13, 2014 10:34:24 AM CEST]
Change Package : 242565:1 http://mks-psad:7002/im/viewissue?selection=242565
Revision 1.6 2014/05/20 17:41:06CEST Hecker, Robert (heckerr)
improved pep8.
--- Added comments ---  heckerr [May 20, 2014 5:41:06 PM CEST]
Change Package : 227494:1 http://mks-psad:7002/im/viewissue?selection=227494
Revision 1.5 2014/03/14 12:18:49CET Hecker, Robert (heckerr)
Updates for get support on long commandline part2:
- Removed unnecessary code.
--- Added comments ---  heckerr [Mar 14, 2014 12:18:49 PM CET]
Change Package : 225192:1 http://mks-psad:7002/im/viewissue?selection=225192
Revision 1.4 2014/02/27 18:17:11CET Hospes, Gerd-Joachim (uidv8815)
new method GetListOfIncidents
--- Added comments ---  uidv8815 [Feb 27, 2014 6:17:12 PM CET]
Change Package : 220009:1 http://mks-psad:7002/im/viewissue?selection=220009
Revision 1.3 2014/01/24 20:40:16CET Hecker, Robert (heckerr)
Get Interface working for sqlite.
--- Added comments ---  heckerr [Jan 24, 2014 8:40:16 PM CET]
Change Package : 215447:1 http://mks-psad:7002/im/viewissue?selection=215447
Revision 1.2 2013/12/15 14:38:25CET Hecker, Robert (heckerr)
Added Oracle schema information.
--- Added comments ---  heckerr [Dec 15, 2013 2:38:25 PM CET]
Change Package : 210873:1 http://mks-psad:7002/im/viewissue?selection=210873
Revision 1.1 2013/12/12 09:32:24CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
    STK_ScriptingToolKit/04_Engineering/stk/hpc/ifc/masterdb/project.pj
"""
