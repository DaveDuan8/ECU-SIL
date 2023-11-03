r"""
job_clone.py
------------

**Extract information about a task / job from DB.**

**Features:**
    - export starttime, task and exitcode to CSV
    - print amount of succeeded and failed tasks from last hour, day and week
    - print the amount of errors and warnings of a node
    - print amount of errors, error description and measurement used questing DB

**UseCase:**
 Used to ahve some information for the IT available, when we have some Job /Task Problems.

**Usage:**

`C:\\>python job_clone.py -h ...`
`C:\\>python job_clone.py overview -h ...`
...

"""
__all__ = ["job_clone", "pack_job", "requeue_job"]

# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from os.path import abspath, join, basename, dirname, exists
from argparse import ArgumentParser, RawDescriptionHelpFormatter, SUPPRESS
from fnmatch import fnmatch
from shutil import rmtree, copyfile
from xml.etree.ElementTree import tostring, parse
from xml.dom.minidom import parseString
from tarfile import open as topen
from tempfile import mkdtemp
from datetime import datetime
from subprocess import Popen, PIPE
from json import loads, dumps, load
from scandir import listdir
from win32com.client.dynamic import Dispatch
from win32api import GetUserNameEx

# - import HPC modules -------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), r"..\.."))
if HPC_FOLDER not in sys.path:
    sys.path.append(HPC_FOLDER)

from hpc.rdb.env_data import EnvData
from hpc.core.dicts import DefDict, tointlist
from hpc.core.tds import resolve_alias, server_path, DEFAULT_DB_CONN, DEFAULT_HEAD_NODE, DEV_HEAD
from hpc.core.robocopy import Robocopy

# - defines ------------------------------------------------------------------------------------------------------------
PACK_EXT = ".tar.bz2"


# - functions ----------------------------------------------------------------------------------------------------------
def pack_job(**kwargs):
    r"""
    pack whole input folder (1_Input) of a job into a tar.gz file for later requeue

    :keyword \**kwargs:
        * *headnode* (``str``): HPC head node name
        * *jobid* (``int``): id of HPC job
        * *filename* (``str``): destination name of file without extention

    :return: always 0
    :rtype: int
    """
    headnode = resolve_alias(kwargs.pop('headnode', DEFAULT_HEAD_NODE))
    base = server_path(headnode)
    match = "%d_*" % kwargs['jobid']
    folder = next((i for i in listdir(base) if fnmatch(i, match)), None)
    if folder is None:
        print("couldn't find folder for given job!")
        return 0

    fname = kwargs['filename']
    if not fname.endswith(PACK_EXT):
        fname += PACK_EXT

    tar = topen(fname, "w:bz2")
    try:
        tar.add(join(base, folder, "1_Input"), folder)
    except Exception as ex:
        print("we encountered an error: {!s}".format(ex))
        return 1
    finally:
        tar.close()
    return 0


def requeue_job(**kwargs):
    r"""
    unpack job's zip and then call clone tool

    :keyword \**kwargs:
        * *filename* (``str``): name of zip to unpack

    :raises Exception: when job cannot be extracted
    :return: new job id (returned by requeue_job command)
    :rtype: int
    """
    fname = kwargs['filename']
    if not exists(fname):
        fname += PACK_EXT

    tar = topen(fname, 'r:bz2')
    tmpdir = mkdtemp(prefix='hpc_')
    req_cmd = join(tmpdir, tar.members[0].name, "hpc", "cmd", basename(__file__).replace(".pyc", ".py"))
    try:
        tar.extractall(tmpdir)
    except Exception as ex:
        raise Exception("unable to extract job: {!s}".format(ex))
    finally:
        tar.close()

    proc = Popen([sys.executable, basename(req_cmd), "-n", resolve_alias(kwargs['headnode']), "_requeue"],
                 cwd=dirname(req_cmd), stdout=PIPE)
    proc.wait()

    rmtree(tmpdir, ignore_errors=True)

    return proc.returncode


def _requeue_job(**kwargs):  # pragma: no cover
    r"""
    inside and should not be used directly, as it should be called by requeue_job via command as
    this is compatibility layer of current release...

    :keyword \**kwargs:
        * *headnode* (``str``): HPC head node name

    :return: new job id
    :rtype: int
    """
    headnode = resolve_alias(kwargs['headnode'])
    base = server_path(headnode)
    # connect and create new job
    sched = Dispatch("Microsoft.Hpc.Scheduler.Scheduler")
    sched.Connect(headnode)
    env_data = {"headnode": headnode, "submitstart": datetime.utcnow()}
    job = sched.CreateJob()
    sched.AddJob(job)

    old_path = abspath(join(dirname(__file__), "..", ".."))
    old_name = basename(old_path)
    new_name = "%d_%s" % (job.Id, old_name.split('_', 1)[1])
    new_path = join(server_path(headnode), new_name, "1_Input")
    cfgfile = join(new_path, "%s.hpc" % new_name)
    if exists(new_path):
        rmtree(new_path)
    env_data.update({"jobid": job.Id})

    # move all files to new destination
    Robocopy(verbose=0).move(old_path, new_path)
    copyfile(join(new_path, "%s.hpc" % old_name), cfgfile)

    # open hpc cfg file and exchange working dirs
    root = parse(cfgfile).getroot()
    for i, v in enumerate(root):
        if v.tag == "Tasks":
            for k in range(len(root[i])):
                task = v[k]
                task.set("CommandLine", task.get("CommandLine").replace(old_name, new_name))
                task.set("WorkDirectory", task.get("WorkDirectory").replace(old_name, new_name))
            break

    with open(cfgfile, "wb") as fpo:
        fpo.write(parseString(tostring(root, 'utf-8')).toprettyxml(indent='   ', encoding='utf-8'))

    with open(join(base, new_name, "1_Input", "job.json")) as ojenv:
        o_jenv = load(ojenv)
    env_data.update({'tasks': {'1': ['0', '0']}})
    with open(join(base, new_name, "1_Input", "job.json")) as njenv:
        n_jenv = loads(njenv.read())
    # n_jenv = loads(join(base, n_folder, "1_Input", o_folder + ".env"))
    n_jenv['job']['jobid'] = job.Id
    n_jenv['job']['name'] = o_jenv['job']['name']
    n_jenv['job']['headnode'] = headnode
    n_jenv['job']['errorlevel'] = o_jenv['job']['errorlevel']
    n_jenv['job']['skipon'] = o_jenv['job']['skipon']
    with open(join(base, new_name, "1_Input", "job.json"), 'w') as fp:
        fp.write(dumps(n_jenv))

    # finalize job
    env_data["submitstop"] = datetime.utcnow()
    with EnvData(DEFAULT_DB_CONN) as env:
        env.insert_job(**env_data)
    job.RestoreFromXml(cfgfile)
    job.Commit()
    sched.SubmitJobById(job.Id, GetUserNameEx(2), '')
    sched.Close()

    return job.Id


def job_clone(**kwargs):  # pylint: disable=R0914,R0912,R0915,R1260
    r"""
    clone a job with only failed tasks

    :keyword \**kwargs:
        * *headnode* (``str``): HPC head node name
        * *jobid* (``int``): id of HPC job
        * *exitcodes* (``list[int]``): list of exitcodes to limit tasks, default: []

    :return: new job id
    :rtype: int
    """
    headnode = resolve_alias(kwargs.pop('headnode', DEFAULT_HEAD_NODE))
    base = server_path(headnode)
    match = "%d_*" % kwargs['jobid']
    o_folder = next((i for i in listdir(base) if fnmatch(i, match)), None)
    if o_folder is None:
        return 0

    # connect
    sched = Dispatch("Microsoft.Hpc.Scheduler.Scheduler")
    sched.Connect(headnode)

    # find failed task names
    ecodes = kwargs.get('exitcodes', [])
    codes2check = tointlist(ecodes) if isinstance(ecodes, str) else ecodes
    hpcjob = sched.OpenJob(kwargs['jobid'])
    if len(codes2check) == 0:
        codes2check = [int(i.strip()) for i in hpcjob.ValidExitCodes.split(',') if len(i)]
        failed = (lambda i: i != 0) if len(codes2check) == 0 else (lambda i: i not in codes2check)
    else:
        failed = lambda i: i in codes2check

    failed_tasks = [i.Name for i in hpcjob.GetTaskList(None, None, False) if not i.IsParametric and failed(i.ExitCode)]
    if len(failed_tasks) == 0:  # no failed task at all
        return 0

    # create new job and copy all sources
    env_data = {"headnode": headnode, "submitstart": datetime.utcnow()}
    n_job = sched.CreateJob()
    sched.AddJob(n_job)
    n_folder = "%d_%s" % (n_job.Id, o_folder.split('_', 1)[1])
    env_data.update({"jobid": n_job.Id})
    Robocopy(verbose=0).copy(join(base, o_folder), join(base, n_folder))
    copyfile(join(base, r"..\..\HPC_submit\job", "%s_%d.xml" % (headnode, kwargs['jobid'])),
             join(base, r"..\..\HPC_submit\job", "%s_%d.xml" % (headnode, n_job.Id)))
    with open(join(base, n_folder, "1_Input", "job.json")) as ojenv:
        o_jenv = load(ojenv)
    env_data.update({'tasks': {'1': ['0', '0']}})
    with open(join(base, n_folder, "1_Input", "job.json")) as njenv:
        n_jenv = loads(njenv.read())
    # n_jenv = loads(join(base, n_folder, "1_Input", o_folder + ".env"))
    n_jenv['job']['jobid'] = n_job.Id
    n_jenv['job']['name'] = o_jenv['job']['name']
    n_jenv['job']['headnode'] = headnode
    n_jenv['job']['errorlevel'] = o_jenv['job']['errorlevel']
    n_jenv['job']['skipon'] = o_jenv['job']['skipon']
    with open(join(base, n_folder, "1_Input", "job.json"), 'w') as fp:
        fp.write(dumps(n_jenv))

    # open hpc file and reduce it
    tree = parse(join(base.rsplit('\\', 1)[0], r"HPC_submit\job", "%s_%d.xml" % (headnode, n_job.Id)))
    o_root = tree.getroot()
    env_data.update({'project': o_root.attrib['Project'], 'template': o_root.attrib['JobTemplate'],
                     'jname': o_root.attrib['Name']})

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
            variable.find('Value').text = join(base, n_folder)
        if variable.find('Name').text == 'JobId':
            variable.find('Value').text = str(n_job.Id)
    tree.write(join(base.rsplit('\\', 1)[0], r"HPC_submit\job", "%s_%d.xml" % (headnode, n_job.Id)))

    for k, v in enumerate(o_root):
        if v.tag != "Tasks":
            continue
        removals = []
        for i, task in enumerate(v):
            if task.get("Name") in failed_tasks or task.get("Type") in ["NodePrep", "NodeRelease"]:
                task.set("CommandLine", task.get("CommandLine").replace(o_folder, n_folder))
                task.set("WorkDirectory", task.get("WorkDirectory").replace(o_folder, n_folder))
            else:
                removals.append(task)
        for i in removals:
            n_root[k].remove(i)
        break

    n_name = join(base.rsplit('\\', 1)[0], r'HPC_submit\job', r'%s_%d.xml' % (headnode, n_job.Id))
    with open(n_name, "wb") as fpo:
        fpo.write(parseString(tostring(n_root, 'utf-8')).toprettyxml(indent='   ', encoding='utf-8'))

    # finalize job
    env_data["submitstop"] = datetime.utcnow()
    with EnvData(db=DEFAULT_DB_CONN) as env:
        env.insert_job(**env_data)
    n_job.RestoreFromXml(n_name)
    n_job.Commit()
    sched.SubmitJobById(n_job.Id, GetUserNameEx(2), '')
    sched.Close()

    return n_job.Id


def parse_n_go(args):  # pragma: nocover
    """parse arguments and call apropriate function"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-n", "--headnode", type=str, default=DEFAULT_HEAD_NODE, help="name of HPC head node")
    sub = opts.add_subparsers(help='command')

    pack = sub.add_parser('pack', help="pack the whole job")
    pack.set_defaults(func=pack_job)
    pack.add_argument("-j", "--jobid", type=int, required=True, help="id of hpc job")
    pack.add_argument("-f", "--filename", type=str, required=True, help="file name to pack job into or from")

    requeue = sub.add_parser('requeue', help="unpack and requeue job")
    requeue.set_defaults(func=requeue_job)
    requeue.add_argument("-f", "--filename", type=str, required=True, help="file name to pack job into or from")

    _requeu = sub.add_parser('_requeue', help=SUPPRESS)
    _requeu.set_defaults(func=_requeue_job)

    clone = sub.add_parser('clone', help="clone a job immediatelly")
    clone.set_defaults(func=job_clone)
    clone.add_argument("-j", "--jobid", type=int, required=True, help="id of hpc job")
    clone.add_argument("-e", "--exitcodes", default=[], type=int, nargs='+',
                       help='exitcodes to take care about, e.g. "-404,-302", default: all failed')

    args = opts.parse_args(args, namespace=DefDict())

    try:
        return args.func(**args)
    except KeyboardInterrupt:
        print("user interrupt!")
        return -1


# - main main ----------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(parse_n_go(None if sys.argv[1:] else ['-h']))
