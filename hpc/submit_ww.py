"""
submit_ww.py
-------------

function(s) to submit jobs to HPC clusters to different sites

the submit_ww is used to submit a master job that is delivered to different sites depending on the storage location
of the recordings to run. Parameters for this script are:

    - git repo url of submit folder, use git@github-am.geo.conti.de:...
    - collection name (no bpl) of rec files
    - Python version to execute (Python36 or Python27_64)
    - email address to sent job info to (optional, default: user account of submitter)

The folder to submit must be stored in an own git repository open for Jenkins account to read.
Jenkins user has stored ssh keys on the servers, so best use git@github-am:... when passing the url.
The structure is similar to the normally created HPC input folder 1_Input and must contain:

  - hpc folder (best: git repo ADAS/HPC_two linked as sub package)
  - mts folder  (normally a simulation is executed, can be left out)
  - mts_measurement folder
  - applications to execute in the job's task(s), can be stored in an own folder

(find an example at git@github-am.geo.conti.de:uidv8815/hpc_submit_example)


"""
# first tests with params:
# git@github-am.geo.conti.de:uidv8815/HPC_submit_example.git -c HPC_ww_submit_test -p submit\submit_example.py
# -v Python36

# - Python imports ----------------------------------------------------------------------------------------------------
from sys import exit as sysexit, platform, path as syspath, argv
from os.path import abspath, join, dirname
from os import getenv
from re import match, IGNORECASE
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from six import iteritems
import requests

if platform == "win32":
    from win32com.client import GetObject, Dispatch

# - HPC imports --------------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), ".."))
if HPC_FOLDER not in syspath:
    syspath.append(HPC_FOLDER)

from hpc.core import UID_NAME
from hpc.core.tds import LOC_HEAD_MAP, HPC_STORAGE_MAP, WW_SUBMIT_SRV_MAP, PRODUCTION_HEADS
from hpc.rdb.base import BaseDB, BaseDbException
from hpc.core.tds import LOCATION
from hpc.bpl.base import Bpl

JENKINS_URL = "https://lu00209vma.cw01.contiwan.com:8443"
SUBMIT_TOKEN = 'HPC_SUBMIT_TEST'
PROJECT_NAME = 'HPC_submit'
COLL_DB = "VGA_PWR"
USER_ID = "{}\\{}".format(getenv("USERDOMAIN"), getenv("USERNAME"))
HTTP_RETURN_CODES = {500: 'server does not respond - network problem or server down'
                          ' - or found an error in the parameters.\n'
                          '    Please check on the Jenkins server what parameters are allowed for HPC_submit job.',
                     403: 'SERVER PROBLEM with authentication, please contact HPC development team',
                     404: 'SERVER PROBLEM - Jenkins job not available, please contact HPC development team',
                     405: "SERVER PROBLEM - Jenkins job can't be executed, please contact HPC development team"}
# map share name to location name for production sites
HPC_STORAGE_HEADS = dict((HPC_STORAGE_MAP[LOC_HEAD_MAP[l][0]][2], l) for l in LOC_HEAD_MAP
                         if LOC_HEAD_MAP[l][0] in PRODUCTION_HEADS)

PRODUCTION_SITES = ",".join([loc for loc in LOC_HEAD_MAP if LOC_HEAD_MAP[loc][0] in PRODUCTION_HEADS])


# - classes / functions -----------------------------------------------------------------------------------------------
def get_locations(bpl_name):
    """
    List all locations where rec files are stored.

    Use bpl entries to get locations, only files on local file shares listed in.

    :param str bpl_name: name for the collection as generated with TDSM or bpl path/filename
    :return: short site names ('LND', 'ABH' etc.)
    :rtype: list
    """
    locs = set()
    with Bpl(bpl_name, db=COLL_DB, loc=PRODUCTION_SITES) as bpl:
        for ent in bpl:
            for loc, heads in iteritems(LOC_HEAD_MAP):
                if heads[0] in PRODUCTION_HEADS and any([match(r"(?i)\\\\%s\\.*" % i, str(ent), IGNORECASE)
                                                         for i in HPC_STORAGE_MAP[heads[0]][0]]):
                    locs.add(loc)
                    break
    return locs


def submit_ww(repo, coll, prog, pyver, **kwargs):  # pylint: disable=R1260
    r"""
    submit a master job

    checking the passed collection for sites where the recordings are stored,
    then sending the submit request to the Jenkins servers at these sites

    mandatory parameters:
    - repo: git repository to check out with sources for the HPC job
    - coll: collection of rec files to process
    - prog: HPC job submit script to define the tasks and programs to execute
    - pyver: Python version to use

    optional arguments:
    - email to send submit status status to (default: user's address), complete mail addr., sep. with ';'

    code::

        repo = "git@github-am.geo.conti.de:ADAS/my_submit_folders.git"
        coll = "EBA_Swiss_tunnel_crashes"
        prog = "path\\submit.py vers='2.3.31'"
        pyver = "Python36"

        res = submit_ww(repo, coll, path, prog, pyver)


    :param str repo:  url of the git repo to check out
    :param str coll:  collection name of rec files as stored in DB or path/name of bpl file
    :param str prog:  path\program to call to submit the job on the sites
    :param str pyver: Python version: Python36 or Python27_64
    :param kwargs: additional keyword arguments

    :keyword \*kwargs:
        * *email*  (``str``): opt. emails to send submit info to (default: user), complete mail addr., sep. with ';'
        * *location* (``str``): opt. hidden option for testing

    :return: number of failed submits
    :rtype: int

    :raises AssertException: if no collection is passed
    :raises BaseDbException: if wrong masterid is returned from BaseDb
    """
    err = 0
    email = kwargs.get('email', None)
    if not email:
        try:
            nres = Dispatch(dispatch="NameTranslate")
            nres.Set(3, UID_NAME)
            email = GetObject("LDAP://" + nres.Get(1)).Get("mail")
        except Exception:
            email = "@"

    assert coll, "a collection or bpl must be given"

    orig_loc = kwargs.get('orig_loc')
    # careful with changing list of sites for orig_loc:
    #   if it doesn't match setting in Jenkins projects HPC_submit you might receive error 500 without further details
    if orig_loc is None:
        orig_loc = LOCATION
    assert orig_loc in WW_SUBMIT_SRV_MAP, \
        'target location %s not available for WW Submits, ' \
        'either set valid location or start from a valid HPC site: %s' % (orig_loc, ', '.join(WW_SUBMIT_SRV_MAP.keys()))

    # get locations where files of collections are stored
    # option: set locations for testing only! (deactivate this option when ww submit is stable?)
    kwloc = kwargs.get('location')
    if kwloc:
        locs = set(kwloc)
    else:  # this should be the only usage in production!!!
        locs = get_locations(coll)

    # test for correct locations, breaks if rec file from not supported site in collection
    # we use list of all HPC locations even if one (like SHA currently) does not provide a submit server
    #   so we can at least submit to the other sites. A not known site (e.g. from opt. -l) should cause an exception.
    assert locs.issubset(set(list(LOC_HEAD_MAP.keys()) + ["DEV"])), \
        "illegal locations are used: " + ", ".join(locs) + \
        ", allowed location names are: " + ", ".join(LOC_HEAD_MAP.keys())

    # ok, we have valid locations extracted from the collection,
    # now we can start to deliver submit builds to the different servers
    # 1.) get a new, valid masterid using query "select hpc_masterid_seq.nextval from dual"
    with BaseDB('HPC') as hpc:
        masterid = hpc.execute("SELECT HPC_ADMIN.HPC_MASTERID_SEQ.nextval from dual")
        try:
            masterid = masterid[0][0]
        except TypeError:
            raise BaseDbException("a unique master job id could not be requested from Oracle HPC DB")
    print("deploy submits for masterjob with MASTERID %s:" % masterid)
    # 2.) trigger submit builds at the submit servers
    #loop through agents
    for agent_name in locs:
        print("start HPC submit in %s" % agent_name)
        job_url = "{0}/job/{1}/buildWithParameters".format(JENKINS_URL, PROJECT_NAME)

        params = {'token': SUBMIT_TOKEN,
                  'GIT_REPO': repo,
                  'COLLECTION': coll.strip(),
                  'PROGRAM_NAME': prog.strip(),
                  'PY_VERSION': pyver.strip(),
                  'EMAIL_TO': email.strip(),
                  'USERID': USER_ID,
                  'ORIG_LOC': orig_loc,
                  'MASTERID': masterid,
                  'NODE' : agent_name
                  }

        # POST request to build on Jenkins (in example not all params used, defaults in Jenkins project):
        # curl -vs http://uud9x2nw:8080/job/HPC_submit/buildWithParameters?token=HPC_SUBMIT_TEST
        # \&GIT_REPO="https://github-am.geo.conti.de/uidv8815/HPC_submit_example.git"\&START_PATH="submit"
        # \&EMAIL_ADDRESS="uidv8815"
        #
        # returns (also as json return):
        #     < HTTP/1.1 201 Created
        #     < Date: Tue, 09 Jun 2020 18:09:39 GMT
        #     < X-Content-Type-Options: nosniff
        #     < Location: http://uud9x2nw:8080/queue/item/25229/
        #     < Content-Length: 0
        #     < Server: Jetty(9.4.27.v20200227)
        #
        # to get the build number send GET request:
        #     curl -v GET http://uud9x2nw:8080/queue/item/25229/api/json
        # return includes an 'executable' section if build is not queued anymore

        try:
            req = requests.get(job_url, params=params, headers={'content-type': 'application/json'})
        except OSError as ex:
            print('Network/Windoze problem: {}'.format(ex))
            continue
        if str(req.status_code) == "201":
            print("  Jenkins build is triggered and queued on {0}/job/{1}/ for cluster/agent {2}"
                  .format(JENKINS_URL, PROJECT_NAME, params.get('NODE')))
        else:
            print("  Failed to trigger the Jenkins build at {}:\n  {}"
                  .format(job_url,
                          HTTP_RETURN_CODES.get(req.status_code, "server returned code {}".format(req.status_code))))
            with BaseDB("HPC") as hpc:
                hpc.execute("INSERT INTO HPC_ADMIN.HPC_MASTERJOB (MASTERID, NODEID, STATUS) "
                            "VALUES(:mid, (SELECT NODEID FROM HPC_NODE WHERE NODENAME = :loc), :stat)",
                            mid=masterid, loc=agent_name, stat="failed to submit")
            err += 1
    print("all sites triggered, follow the execution on 'http://hpcportal.conti.de/masterjobs with id: %s'" % masterid)
    print("  in case of high load on one Jenkins server the master job table will be updated with some delay \n"
          "  until the submit could be executed there (just reload the page until all queued jobs appear).")
    return err


# - main --------------------------------------------------------------------------------------------------------------
def main(args):
    """
    just calling the operation and saving the result

    :param dict args: arguments to parse and pass to submit_ww
    :return: number of errors as returned by submit_ww
    :rtype: int
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument(dest="repo", type=str, help="url of git repository of submit folder, best use git@github-am...")
    opts.add_argument("-c", dest="coll", required=True, type=str,
                      help="collection as created with TDSM or path/name of bpl file")
    opts.add_argument("-p", dest="prog", required=True, type=str, help="path\\name of submit script rel. to 1_Input")
    opts.add_argument("-v", dest="pyver", required=True, type=str, help="version of used Python")
    opts.add_argument("-e", dest="email", type=str,
                      help="email addresses for submit and execution info (one str, sep. by ';')")
    opts.add_argument("-o", dest="orig_loc", type=str,
                      help="origin HPC share site where to store the results (ABH, BLR, LND)")
    opts.add_argument("-l", dest="location", type=str, nargs="+", help="locations for first tests (sep. by ' ') "
                                                                       "do not use in production (remove opt)")
    # opts.add_argument("-")
    args = opts.parse_args(args)
    args = vars(args)

    return submit_ww(args.pop('repo'), args.pop('coll'), args.pop('prog'), args.pop('pyver'), **args)


if __name__ == '__main__':
    sysexit(main(None if argv[1:] else ['-h']))
