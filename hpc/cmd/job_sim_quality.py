"""
provide job simulation quality of projects

1. Connect to production head node
2. Get finished jobs for each project from production
3. Clone jobs and execute on test cluster
4. map production and test cluster job ids

"""
# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from os.path import abspath, join, dirname
from argparse import ArgumentParser
from fnmatch import fnmatch
from xml.etree.ElementTree import tostring, parse
from xml.dom.minidom import parseString
from datetime import datetime
from json import loads, dumps, load
from scandir import listdir
from win32api import GetUserNameEx

# - import HPC modules -------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), r"..\.."))
if HPC_FOLDER not in sys.path:
    sys.path.append(HPC_FOLDER)

from hpc import HpcSched
from hpc.rdb.env_data import EnvData
from hpc.core.dicts import DefDict, tointlist
from hpc.core.tds import resolve_alias, server_path, DEFAULT_HEAD_NODE, DEV_HEAD, DEV_DB_CONN
from hpc.core.robocopy import Robocopy

# - Defines ------------------------------------------------------------------------------------------------------------
SIM_JOBS = abspath(join(dirname(__file__), r"..\..\simjobs.json"))


def job_clone_sim_quality(**kwargs):  # pylint: disable=R0912,R0914,R0915,R1260
    """
    clone job from production to test cluster and simulate in test cluster to check quality of job

    :param dict kwargs: production headnode, test headnode, top finished jobs and project
    :return: success state
    :rtype: int
    """
    headnode = resolve_alias(kwargs.pop('pheadnode', DEFAULT_HEAD_NODE))
    base = server_path(headnode)
    match = "%d_*" % kwargs['jobid']
    o_folder = next((i for i in listdir(base) if fnmatch(i, match)), None)
    if o_folder is None:
        return 0

    # connect
    with HpcSched(headnode) as sched:
        # find failed task names
        ecodes = kwargs.get('exitcodes', [0])
        codes2check = tointlist(ecodes) if isinstance(ecodes, str) else ecodes
        hpcjob = sched.OpenJob(kwargs['jobid'])
        if len(codes2check) == 0:
            codes2check = [int(i.strip()) for i in hpcjob.ValidExitCodes.split(',') if len(i)]
            failed = (lambda i: i != 0) if len(codes2check) == 0 else (lambda i: i not in codes2check)
        else:
            failed = lambda i: i in codes2check

        failed_tasks = [i.Name for i in hpcjob.GetTaskList(None, None, False)
                        if not i.IsParametric and failed(i.ExitCode)]
        if len(failed_tasks) == 0:  # no failed task at all
            return 0

    # create new job and copy all sources
    test_headnode = resolve_alias(kwargs.pop('theadnode', DEV_HEAD))
    test_base = server_path(test_headnode)
    sched = HpcSched(test_headnode)
    print("Connect to test cluster: %s" % test_headnode)
    env_data = {"headnode": test_headnode, "submitstart": datetime.utcnow()}
    n_job = sched.CreateJob()
    sched.AddJob(n_job)
    n_folder = "%d_%s" % (n_job.Id, o_folder.split('_', 1)[1])
    print("Clone job %d on test cluster" % n_job.Id)
    env_data.update({"jobid": n_job.Id})
    print("Cloning...")
    Robocopy(verbose=0).copy(join(base, o_folder), join(test_base, n_folder))
    print("Job %s cloned successfully on test cluster" % n_folder)
    with open(join(base, o_folder, "1_Input", "job.json")) as ojenv:
        o_jenv = load(ojenv)
    env_data.update({'tasks': {'1': ['0', '0']}})
    with open(join(test_base, n_folder, "1_Input", "job.json")) as njenv:
        n_jenv = loads(njenv.read())
    # n_jenv = loads(join(base, n_folder, "1_Input", o_folder + ".env"))
    n_jenv['job']['jobid'] = n_job.Id
    n_jenv['job']['name'] = o_jenv['job']['name']
    n_jenv['job']['head'] = test_headnode
    n_jenv['job']['errorlevel'] = o_jenv['job']['errorlevel']
    n_jenv['job']['skipon'] = o_jenv['job']['skipon']
    with open(join(test_base, n_folder, "1_Input", "job.json"), 'w') as fp:
        fp.write(dumps(n_jenv))

    # open hpc file and reduce it
    tree = parse(join(test_base, n_folder, "1_Input", "hpc", "job.xml"))
    o_root = tree.getroot()
    env_data.update({'project': o_root.attrib['Project'], 'template': o_root.attrib['JobTemplate'],
                     'jname': o_jenv['job']['name']})

    # from copy import deepcopy
    n_root = tree.getroot()
    tlist = sched.GetJobTemplateList()
    templates = [tlist.Item(i) for i in range(tlist.Count)]
    temp2set = "Short_Test" if headnode.upper() in [DEV_HEAD] else "Analysis_Test"
    if temp2set in templates:
        n_root.set("JobTemplate", temp2set)
    else:
        n_root.attrib.pop("JobTemplate", None)

    for variable in n_root.findall('EnvironmentVariables/Variable'):
        if variable.find('Name').text == 'JOB_NET_PATH':
            variable.find('Value').text = join(test_base, n_folder)

    for k, v in enumerate(o_root):
        if v.tag != "Tasks":
            continue
        removals = []
        for i, task in enumerate(v):
            if task.get("Name") in failed_tasks[:1] or task.get("Type") in ["NodePrep", "NodeRelease"]:
                task.set("CommandLine", task.get("CommandLine").replace(o_folder, n_folder))
                task.set("WorkDirectory", task.get("WorkDirectory").replace(o_folder, n_folder))
            else:
                removals.append(task)
        for i in removals:
            n_root[k].remove(i)
        break

    n_name = join(test_base, n_folder, "1_Input", "hpc", "job.xml")
    with open(n_name, "wb") as fpo:
        fpo.write(parseString(tostring(n_root, 'utf-8')).toprettyxml(indent='   ', encoding='utf-8'))

    # finalize job
    env_data["submitstop"] = datetime.utcnow()
    with EnvData(DEV_DB_CONN) as env:
        env.insert_job(**env_data)
    n_job.RestoreFromXml(n_name)
    n_job.Commit()
    sched.SubmitJobById(n_job.Id, GetUserNameEx(2), '')
    sched.Close()

    return n_job.Id


def parse_job_args(args):  # pragma: nocover
    """
    parse job argument to simulate on test cluster

    :param list args: production head node, test head node, no of finished jobs and project
    :return: success code
    :rtype: int
    """
    opts = ArgumentParser(description=__doc__)
    opts.add_argument("-p", "--pheadnode", type=str, default=DEFAULT_HEAD_NODE, help="production cluster")
    opts.add_argument("-t", "--theadnode", type=str, default=DEV_HEAD, help="test cluster")
    opts.add_argument('-pt', "--ptop", type=int, default=1, help="top finished jobs")
    opts.add_argument('-pr', "--project", type=str, default="ALL", help='project')

    args = opts.parse_args(args, namespace=DefDict())
    map_jobids = []
    try:
        with HpcSched(args["pheadnode"]) as sched:
            print("Connect to scheduler: %s" % args['pheadnode'])
            fltr = sched.CreateFilterCollection()
            fltr.Add(sched.const.FilterOperator_Equal, sched.const.PropId_Job_State, sched.const.JobState_Finished)
            fltr.Add(sched.const.FilterOperator_Equal, sched.const.PropId_Job_Project, args['project'])
            jobids = [id for id in sched.GetJobIdList(fltr, None)]  # pylint: disable=R1721

        for jobid in jobids[:args['ptop']]:
            print("Finished job %d from scheduler" % jobid)
            args['jobid'] = jobid
            tc_jobid = job_clone_sim_quality(**args)
            map_jobids.append((jobid, tc_jobid))
            dict_jobids = {'jobids': map_jobids}
            json_obj = dumps(dict_jobids)
            with open(SIM_JOBS, 'w+') as file:
                file.write(json_obj)

        print("Map production and test cluster job ids", map_jobids)
        return 0
    except KeyboardInterrupt:
        print("user interrupt!")
        return -1


# - main main ----------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(parse_job_args(None if sys.argv[1:] else ['-h']))
