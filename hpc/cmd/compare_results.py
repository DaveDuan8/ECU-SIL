"""
compare_results
---------------
This file provides compare production vs test cluster jobs for projects
"""
# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from json import load, dumps
from argparse import ArgumentParser
from os.path import abspath, join, dirname

# - import HPC modules ------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), r"..\.."))
if HPC_FOLDER not in sys.path:
    sys.path.append(HPC_FOLDER)

from hpc.rdb.base import BaseDB
from hpc.core.tds import DEFAULT_DB_CONN, DEV_DB_CONN, DEFAULT_HEAD_NODE, DEV_HEAD
from hpc.core.dicts import DefDict

# - Defines -----------------------------------------------------------------------------------------------------------
SIM_JOBS_DETAILS = abspath(join(dirname(__file__), r"..\..\simjobdetails.json"))


def compare_results(**kwargs):
    """
    compare results production vs test cluster jobs
    :param kwargs: production head node, test head node and project
    :return: int
    :rtype: int
    """
    try:
        with open(kwargs['simjobs']) as file:
            data = load(file)
            print("Job ids %s" % data["jobids"])
            print("Fetching job details...")
            with BaseDB(DEFAULT_DB_CONN) as prod:
                prod_job_details = prod.execute("SELECT HPC_JOB.HPCJOBID, HPC_VER.VERSTR, HPC_SUBTASK.COMMAND, "
                                                "HPC_SUBTASK.EXITCODE FROM HPC_SUBTASK "
                                                "INNER JOIN HPC_TASK ON HPC_SUBTASK.TASKID = HPC_TASK.TASKID "
                                                "INNER JOIN HPC_JOB ON HPC_TASK.JOBID = HPC_JOB.JOBID "
                                                "INNER JOIN HPC_PRJTMPL ON HPC_JOB.PRJID = HPC_PRJTMPL.PTID "
                                                "INNER JOIN HPC_NODE ON HPC_NODE.NODEID = HPC_JOB.NODEID "
                                                "INNER JOIN HPC_VER ON HPC_VER.VERID = HPC_JOB.VERID "
                                                "WHERE HPC_PRJTMPL.NAME = :prj AND HPC_TASK.HPCTASKID = '1' "
                                                "AND HPC_JOB.HPCJOBID = :pjobid "
                                                "AND HPC_NODE.NODENAME = :phn AND HPC_SUBTASK.SUBTASKID = '0'",
                                                pjobid=data['jobids'][0][0], prj=kwargs['project'],
                                                phn=kwargs['pheadnode'])

            with BaseDB(DEV_DB_CONN) as test:
                test_job_details = test.execute("SELECT HPC_JOB.HPCJOBID, HPC_VER.VERSTR, HPC_SUBTASK.COMMAND, "
                                                "HPC_SUBTASK.EXITCODE FROM HPC_SUBTASK "
                                                "INNER JOIN HPC_TASK ON HPC_SUBTASK.TASKID = HPC_TASK.TASKID "
                                                "INNER JOIN HPC_JOB ON HPC_TASK.JOBID = HPC_JOB.JOBID "
                                                "INNER JOIN HPC_PRJTMPL ON HPC_JOB.PRJID = HPC_PRJTMPL.PTID "
                                                "INNER JOIN HPC_NODE ON HPC_NODE.NODEID = HPC_JOB.NODEID "
                                                "INNER JOIN HPC_VER ON HPC_VER.VERID = HPC_JOB.VERID "
                                                "WHERE HPC_PRJTMPL.NAME = :prj AND HPC_TASK.HPCTASKID = '1' "
                                                "AND HPC_JOB.HPCJOBID = :tjobid "
                                                "AND HPC_NODE.NODENAME = :thn AND HPC_SUBTASK.SUBTASKID = '0'",
                                                tjobid=data['jobids'][0][1], prj=kwargs['project'],
                                                thn=kwargs['theadnode'])
        quality = "differ"
        if prod_job_details[2:] == test_job_details[2:]:
            quality = 'same'

        job_details = [(prod_job_details, test_job_details, quality)]
        dict_jobids = {'jobquality': job_details}
        json_obj = dumps(dict_jobids)
        with open(SIM_JOBS_DETAILS, 'w+') as file:
            file.write(json_obj)
            print("simulation job details: %s" % SIM_JOBS_DETAILS.split('\\')[-1])
    except Exception as err:
        print("Error: %s" % str(err))

    return 0


def parse_job_args(args):  # pragma: nocover
    """
    This parse job argument to compare results production vs test cluster
    :param list args: production head node, test head node and project
    :return: int
    :rtype: int
    """
    opts = ArgumentParser(description=__doc__)
    opts.add_argument("-p", "--pheadnode", type=str, default=DEFAULT_HEAD_NODE, help="production cluster")
    opts.add_argument("-t", "--theadnode", type=str, default=DEV_HEAD, help="test cluster")
    opts.add_argument('-pr', "--project", type=str, default="ALL", help='project')
    opts.add_argument('-sj', "--simjobs", type=str, help='simulation job ids')

    args = opts.parse_args(args, namespace=DefDict())
    try:
        compare_results(**args)
    except KeyboardInterrupt:
        print("user interrupt!")
        return -1
    return 0


if __name__ == '__main__':
    sys.exit(parse_job_args(None if sys.argv[1:] else ['-h']))
