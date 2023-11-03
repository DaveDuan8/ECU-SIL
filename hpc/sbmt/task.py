"""
task.py
-------

TODO: documentation
"""
# pylint: disable=all
# - Python imports ----------------------------------------------------------------------------------------------------
from os.path import join
from six import iteritems
from numpy import array as nparray

# - HPC imports -------------------------------------------------------------------------------------------------------
from hpc.core.error import HpcError
from hpc.core.tds import PRODUCTION_HEADS
from hpc.rdb.base import basepath, serverpath, crc

# - defines ------------------------------------------------------------------------------------------------------------
MAX_TIME_WATCH = 120.


# - classes / functions -----------------------------------------------------------------------------------------------
class Task(object):
    """task implementation"""

    def __init__(self, job, **kwargs):
        """

        :param job:
        :type job:
        :param kwargs:
        :type kwargs:
        """
        self._job = job
        self._task = len(self._job.sched) + 1
        self._kwargs = dict(kwargs)
        self._subcnt = 0
        if self._task not in self._job.taskmeas:
            self._job.taskmeas[self._task] = nparray([0, 0])

        if self._task > 50000 and self._job.head_node in PRODUCTION_HEADS:
            raise HpcError("maximum number of tasks reached: 50000!")

        # create HPC task
        sep = "/" if self._job.linux else "\\"
        starter = "{}hpc{}starter.py --id {}.{}".format("./" if self._job.linux else "python.exe ", sep,
                                                        self._job.jobid, self._task)
        if self._kwargs.pop('verbose', False):
            starter += " -l"
        if len(starter) > 479:  # should never happen as we're controlling it
            raise HpcError("CMDLine length greater than 480 characters!")

        name = self._kwargs.pop('name', None)
        if not name:
            name = "T{:0>5d}".format(self._task)
        self._job.sched.append_task(name=name, resources=1, runtime=self._kwargs.pop("runtime", None),
                                    command_line=starter, depends_on=self._kwargs.pop("depends_on", None),
                                    work_directory=sep.join([self._job.sched.work_path,
                                                             self._job.sched.job_folder_name, '1_Input']))
        # stderr=join(self._job.sched.net_out_path, "T{:05d}".format(self._task),
        #             "status.url"))

        # Fill Task with needed Input
        if self._task == 1:
            cmds = ['@echo off', 'if "%1" == "" (set task=1) else (set task=%1)',
                    "set CCP_JOBID={}".format(self._job.jobid), "{} -t %task%".format(starter), 'pause']
            with open(join(self._job.sched.net_in_path, 'test.bat'), 'w') as bat_file:
                bat_file.write("\n".join(cmds))

    def add_subtask(self, app, **kwargs):
        """
        add a subtask

        :param (``hpc.task.App``) app: application class
        """
        kargs = dict(self._kwargs)
        kargs.update(kwargs)

        tmwatch = float(kargs.get("time_watch", 0.))
        tmfact = float(kargs.get("time_factor", 16.))
        recording = kargs.get("recording", app.recording)
        recmap = kargs.get("rec_map", True) if recording is not None else False
        rectms, recdiff = [], kargs.get("rec_diff", 10)

        cnt, tms, measid, rec = -1, [], [], None
        if recording is not None and self._job.base_db is not None:
            for cnt, rec in enumerate(split_rec_name(recording)):
                try:
                    totms = True
                    res = self._job.base_db("SELECT MEASID, NVL(BEGINABSTS, 0) BA, NVL(ENDABSTS, 0), FILESIZE, PARENT "
                                            "FROM DMT_FILES WHERE CRC_NAME = :crc AND SERVERSHARE = :srvs "
                                            "AND BASEPATH = :bph AND NVL(BEGINABSTS, 0) <= NVL(ENDABSTS, 0) "
                                            "ORDER BY BA DESC", crc=crc(rec[1]),
                                            srvs=serverpath(rec[1]), bph=basepath(rec[1]))
                    if len(res) > 0 and len(res[0]) > 0:
                        res = res[0]
                        measid.append(res[0])
                        tms = list(res[1:3])
                        # do we have a parent?
                        if res[-1] is not None:
                            par = self._job.base_db("SELECT NVL(BEGINABSTS, 0), NVL(ENDABSTS, 0), FILESIZE "
                                                    "FROM DMT_FILES WHERE MEASID = :meas", meas=res[-1])
                            if len(par) > 0 and len(par[0]) > 0:
                                tms = list(par[0][0:2])

                        if not app.playsecs:  # it's weird, MTS config set's it to 0 if sections should be played
                            for sec in rec[2]:
                                rectms.append([sec[0] + (tms[0] if sec[2][0] else 0),
                                               sec[1] + (tms[0] if sec[2][1] else 0)])
                                if not (tms[0] <= rectms[-1][0] <= tms[1] and tms[0] <= rectms[-1][1] <= tms[1]
                                        and rectms[-1][0] < rectms[-1][1]):
                                    self._job.logger.error("section times out of bounds: begin=%d, end=%d"
                                                           % (rectms[-1][0], rectms[-1][1]))
                                totms = False

                        # intended to be saved to local sqlite db
                        self._job.records.append({"measid": res[0], "beginabsts": res[1], "endabsts": res[2],
                                                  "filepath": rec[1], "project": rec[0][2].upper(), "filesize": res[3],
                                                  "basepath": basepath(rec[1])})
                        self._job.taskmeas[self._task] += [res[3], res[2] - res[1]]

                    if totms and len(tms) > 0:
                        rectms.append(tms)

                except Exception as _:  # in case of escape sequences (seen at unittest)
                    pass

            if cnt < 0:
                recmap = False
            elif cnt > 0:
                recording = None
            else:
                recording = rec[1]

        if tmwatch == 0.:  # 16 x actual / ([us] * 1[h]) + about 12' for loading
            for tms in rectms:
                tmwatch += tmfact * (tms[1] - tms[0]) / 3600000000 + 0.2
        if tmwatch > MAX_TIME_WATCH:
            self._job.logger.warning("time watch too high, limit of 192 hours exceeded: %.1f!" % tmwatch)
            tmwatch = MAX_TIME_WATCH

        sargs = ", ".join(("{}={}".format(i, v)) for i, v in iteritems(kargs))
        if len(sargs) > 0:
            sargs = " (arguments: %s)" % sargs
        if self._job.loglevel > 1:
            self._job.logger.info("adding {}.{}: {} {}".format(self._task, self._subcnt, app.app, sargs))

        wrap = kargs.get("wrapexe", [])
        if not isinstance(wrap, list):
            wrap = [wrap]

        self._job.jenv_update(task=self._task, subtask=self._subcnt,
                              command=app.cmd_list(kargs.get("cmd_asis", False)), workdir=app.cwd, wrapexe=wrap,
                              envdata=kargs.get("env", {}),
                              iowatch=kargs.get("io_watch", True) and not self._job.linux,
                              cpuwatch=kargs.get("cpu_watch", True), timewatch=tmwatch,
                              prnwatch=kargs.get("prn_watch", False), mtscheck=kargs.get("mtscheck", False),
                              recmap=recmap, recording=recording, measid=None if len(measid) != 1 else measid[0],
                              local_rec=kargs.get("local_rec", False), rectms=rectms, recdiff=recdiff, app=app.app,
                              errorlevel=kargs.get("errorlevel", self._job.errorlevel), simcfg=app.simcfg,
                              skipon=kargs.get("skipon", []))

        self._subcnt += 1
