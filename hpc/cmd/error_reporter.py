r"""
error_reporter.py
-----------------

**Extract information about a task / job from DB.**

**Features:**
    - export starttime, task and exitcode to CSV
    - print amount of succeeded and failed tasks from last hour, day and week
    - print the amount of errors and warnings of a node
    - print amount of errors, error description and measurement used questing DB

**UseCase:**
 Used to ahve some information for the IT available, when we have some Job /Task Problems.

**Usage:**

`C:\\>python error_reporter.py -h ...`
`C:\\>python error_reporter.py overview -h ...`
...

"""
from __future__ import print_function

__all__ = ["overview", "fail_succeeds", "win_events", "rec_errors"]

# - import Python modules ----------------------------------------------------------------------------------------------
from sys import exit as sexit, path as spath, argv
from os.path import abspath, join, dirname
from csv import DictWriter
from argparse import ArgumentParser, RawDescriptionHelpFormatter, FileType
from six import PY2

# - import HPC modules -------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), r"..\.."))
if HPC_FOLDER not in spath:
    spath.append(HPC_FOLDER)

from hpc.rdb.base import BaseDB
from hpc.core.dicts import DefDict
from hpc.core.tds import DEFAULT_HEAD_NODE


# - functions ----------------------------------------------------------------------------------------------------------
def overview(args):
    """
    we export time, name and exitcode to a csv

    :param list args: head node name, job ident, output file and exitcodes
    :return: 0
    :rtype: int
    """
    fields = ['TIME', 'DURATION', 'NODE', 'EXITCODE']
    conv = [str, lambda x: x * 60., str, str]

    sqadd, sqargs = "", {"head": args.head}
    if args.job is not None:
        sqargs["job"] = args.job
        sqadd += " AND HPCJOBID = :job"
    if args.exitcodes is not None:
        sqadd += " AND EXITCODE IN ({})".format(", ".join([str(i) for i in args.exitcodes]))

    with BaseDB('HPC' if not hasattr(args, 'dbconn') else args.dbconn) as hpc:
        csvlog = DictWriter(args.outfile, delimiter=';', fieldnames=fields)
        csvlog.writeheader()
        for i in hpc.execute("SELECT to_char(t.STARTTIME, 'DD.MM.YYYY HH24:MI:SS'), "
                             "(CAST(t.STOPTIME AS DATE) - CAST(t.STARTTIME AS DATE)) * 1440, s.NAME, t.EXITCODE "
                             "FROM HPC_ADMIN.HPC_JOB INNER JOIN HPC_ADMIN.HPC_TASK t USING(JOBID) "
                             "INNER JOIN HPC_ADMIN.HPC_SLAVE s USING(SLAVEID) "
                             "INNER JOIN HPC_ADMIN.HPC_NODE n ON n.NODEID = s.NODEID "
                             "WHERE n.NODENAME = :head %s "
                             "ORDER BY 1" % sqadd, **sqargs):
            csvlog.writerow({fields[k]: conv[k](i[k]) for k in range(len(fields))})

    return 0


def fail_succeeds(args):
    """
    print amount of succeeded and failed tasks from last hour, day and week

    :param list args: head node name, job ident
    :return: 0
    :rtype: int
    """
    sql = ("SELECT COUNT(*) FROM HPC_ADMIN.HPC_TASK "
           "INNER JOIN HPC_ADMIN.HPC_JOB USING(JOBID) "
           "INNER JOIN HPC_ADMIN.HPC_NODE USING(NODEID) "
           "WHERE NODENAME = :head %s AND EXITCODE %s 0 AND STARTTIME > CURRENT_TIMESTAMP - %s")

    sqadd, sqargs = "", {"head": args.head}
    if args.job is not None:
        sqargs["job"] = args.job
        sqadd += "AND HPCJOBID = :job"

    with BaseDB('HPC' if not hasattr(args, 'dbconn') else args.dbconn) as hpc:
        for dname, dtime in (('hour', "1/24",), ('day', "1",), ('week', "7",),):
            rec = hpc.execute((sql % (sqadd, "=", dtime)) + " union " + (sql % ("!=", dtime)), **sqargs)
            print("%d tasks succeeded and %d failed last %s" % (rec[0][0], rec[1][0], dname))

    return 0


def win_events(args):
    """
    we just print the amount of errors and warnings

    :param list args: nothing needed
    :return: 0
    :rtype: int
    """
    sql = ("SELECT COUNT(*) FROM HPC_ADMIN.HPC_LOG l "
           "INNER JOIN HPC_ADMIN.HPC_LOGEVENT e USING(EID) "
           "INNER JOIN HPC_ADMIN.HPC_LOGITEM i ON l.DID = i.IID "
           "INNER JOIN HPC_ADMIN.HPC_SLAVE s ON i.NAME = s.NAME "
           "INNER JOIN HPC_ADMIN.HPC_NODE USING(NODEID) "
           "WHERE NODENAME = :head AND e.NAME = :ename AND l.LOGTIME > CURRENT_TIMESTAMP - %s")

    sqargs = {"head": args.head}
    with BaseDB('HPC' if not hasattr(args, 'dbconn') else args.dbconn) as hpc:
        for level, levname in (('error', 'errors',), ('warn', 'warnings',),):
            sqargs["ename"] = level
            for dname, dtime in (('hour', "1/24",), ('day', "1",), ('week', "7",),):
                rec = hpc.execute(sql % dtime, **sqargs)
                print("we have %d %s within last %s" % (rec[0][0], levname, dname))

    return 0


def rec_errors(args):
    """
    print amount of errors, error description and measurement used questing DB

    :param list args: nothing needed
    :return: 0
    :rtype: int
    """
    sql = ("SELECT COUNT(MEASID), MEASID, DESCR, FILEPATH "
           "FROM DMT_FILES "
           "INNER JOIN HPC_SUBTASK USING(MEASID) "
           "INNER JOIN HPC_TASK t USING(TASKID) "
           "INNER JOIN HPC_EXITCODES e ON t.EXITCODE = e.EXITCODE "
           "WHERE t.EXITCODE != 0 "
           "GROUP BY FILEPATH, MEASID, DESCR "
           "ORDER BY 1 DESC")

    with BaseDB('HPC' if not hasattr(args, 'dbconn') else args.dbconn) as hpc:
        print("count / measid / exitcode descr / recording filepath")
        print("=" * 80)
        for i in hpc.execute(sql):
            print("% 5d / % 7d / %s / %s" % i)

    return 0


def parse_args(args):  # pragma: nocover
    """parse arguments"""
    if len(argv) == 1:
        argv.append("-h")
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-n", "--head", type=str, default=DEFAULT_HEAD_NODE, help="cluster head to use")
    opts.add_argument("-j", "--job", type=int, help="job number to use")
    sub = opts.add_subparsers(help='command')

    ovv = sub.add_parser('overview', help="export time;duration;node;exitcode")
    ovv.set_defaults(func=overview)
    ovv.add_argument("-e", "--exitcodes", type=int, nargs='*',
                     help='exitcodes to take care about, e.g. "-404,-302"')
    ovv.add_argument("-o", "--outfile", required=True, type=FileType('wb' if PY2 else 'w'),
                     help="output file name, e.g. out.csv")

    num = sub.add_parser('numbers', help="show numbers of failed and succeeded tasks")
    num.set_defaults(func=fail_succeeds)

    wev = sub.add_parser('events', help="show windows events counts")
    wev.set_defaults(func=win_events)

    err = sub.add_parser('recerrors', help="shows errors summed up over recordings")
    err.set_defaults(func=rec_errors)

    return opts.parse_args(args, namespace=DefDict())


# - main main ----------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    pargs = parse_args(None if argv[1:] else ['-h'])  # pylint: disable=C0103
    pargs.strm = None
    sexit(pargs.func(pargs))
