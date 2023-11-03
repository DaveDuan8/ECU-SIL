"""
bsig_check.py
-------------

check for bsig files and whether they are corrupt or having 0 length or no signal at all,
used by command line tool bsig_check and starter.
"""
# - Python imports ----------------------------------------------------------------------------------------------------
from os import walk
from os.path import join, abspath, dirname, exists, isdir, splitext
from fnmatch import fnmatch
import numpy as np

# - HPC imports -------------------------------------------------------------------------------------------------------
from ..core.exitcodes import ExitCodes
from ..core.error import ERR_OK, ERR_APP_BSIG_CORRUPT, ERR_APP_BSIG_DURATION_DIFFERS, ERR_APP_BSIG_TIME_JUMPS, \
    ERR_APP_BSIG_MISSING
from ..core.logger import DummyLogger
from .signal import Signal

# - defines -----------------------------------------------------------------------------------------------------------
LOGGER_NAME = "bsig check:"
TIME_SIGS = ["MTS.Package.TimeStamp", "AbsoluteTimestamp"]


# - classes / functions -----------------------------------------------------------------------------------------------
def bsig_check(**kwargs):  # pylint: disable=R0912,R0914,R0915,R1260
    r"""
    check all bsigs for given folder or just one

    :keyword \**kwargs:
        * *bsigs* (``list | str``): input folder or file to check bsig file from or a bsig file directly
        * *logger* (``Logger``): use logger given, if done so
        * *rectms* (``list``): expected recording begin and end timestamp
        * *recdiff* (``int``): allowed recording difference, default: 10%
        * *exit_prio* (``ExitCode``): exit code priorizer, instance of ExitCode, default: None

    :return: error found
    :rtype: int
    """
    logger = kwargs.get("logger", DummyLogger(True))
    infiles = abspath(kwargs["bsigs"])

    if not exists(infiles):
        return ERR_OK

    if isdir(infiles):
        baselen = len(infiles) + 1
        bsigs = []
        exts = kwargs.get("bsig_ext", [".bsig"])
        for (path_, _, files) in walk(infiles):
            bsigs.extend([abspath(join(path_, f)) for f in files
                          if splitext(f)[-1].lower() in exts
                          and not fnmatch(f, "Export*.bsig") and not fnmatch(f, "*_tstp.bsig")])
    else:
        baselen = len(dirname(infiles)) + 1
        bsigs = [infiles]

    exitcode = ExitCodes(kwargs.get("exit_prio"))

    if bsigs:
        logger.info("quantity OK: %d files available.", len(bsigs))
    else:
        logger.error("quantity NOK: no bsig at all!")
        exitcode(ERR_APP_BSIG_MISSING)

    errcnt = 0
    for bsig in bsigs:
        logger.info("processing %s ...", bsig[baselen:])
        try:
            with Signal(bsig, delim=',') as sig:
                timesig = next((i for i in TIME_SIGS if i in sig.signal_names), None)
                if timesig is None:  # pylint: disable=R1702
                    logger.error("not any time signal found: '%s'!", "', '".join(TIME_SIGS))
                    exitcode(ERR_APP_BSIG_CORRUPT)
                    errcnt += 1
                    continue
                if len(sig) == 0 or sig[0].size == 0:
                    logger.error("bsig contains %d signals or of zero length!", len(sig))
                    exitcode(ERR_APP_BSIG_CORRUPT)
                    errcnt += 1
                    continue

                # check recording length
                mts = sig[timesig]
                rectms = kwargs.get("rectms")
                if kwargs.get("cmdline", False) and rectms:
                    rectms = [[rectms[i], rectms[1 + 1]] for i in range(0, len(rectms), 2)]
                if not rectms:
                    rectms = [None]

                sigdiff = abs(np.diff(mts))
                sigavg = np.average(sigdiff) * 3.
                diffidxs = np.append(np.insert(np.where(sigdiff > sigavg)[0] + 1, 0, 0), 0)

                logger.info("bsig contains %d signals of length %d: OK", len(sig), sig[0].size)

                if len(rectms) != len(diffidxs) - 1 and np.any(diffidxs > 23):
                    if len(diffidxs) > 14:
                        dfs = ", ".join([str(i) for i in diffidxs[1:7]]) + ", ..., " \
                              + ", ".join([str(i) for i in diffidxs[-7:-1]])
                    else:
                        dfs = ", ".join([str(i) for i in diffidxs[1:-1]])
                    logger.error("we have %d section(s) and detected %d time jump(s) > %.0f @ pos %s!",
                                 len(rectms), len(diffidxs) - 2, sigavg, dfs)
                    exitcode(ERR_APP_BSIG_TIME_JUMPS)
                    errcnt += 1

                if len(rectms) != 1:
                    logger.info("currently not possible to check bsigs with sections...")
                    continue
                if rectms[0] is None:
                    continue

                # for idx, sec in enumerate(rectms):
                #     beg, end = mts[diffidxs[idx]], mts[diffidxs[idx + 1] - 1]
                #     dur, seclen = end - beg, sec[1] - sec[0]
                beg, end, sec = mts[0], mts[-1], rectms[0]
                dur, seclen = end - beg, sec[1] - sec[0]
                logger.info("%s: %d (end) - %d (begin) = %d (duration)", timesig, end, beg, dur)
                if seclen != 0.:
                    logger.info("database timestamp: %d (end) - %d (begin) = %d (duration)",
                                sec[1], sec[0], seclen)
                    diff = abs(dur * 100. / seclen - 100.)
                    maxdiff = kwargs.get("recdiff", 10.)
                    if diff > maxdiff:  # 10% difference (default)
                        exitcode(ERR_APP_BSIG_DURATION_DIFFERS)
                        logger.error("mts timestamp differs more than %.1f%%: %.1f%% => bad!", maxdiff, diff)
                        errcnt += 1
                    else:
                        logger.info("section duration diff is within %.1f%% range: %.1f%% => good.", maxdiff, diff)
                else:
                    logger.warning("DB has invalid timestamps: %d (end) - %d (begin)!", sec[1], sec[0])
                    errcnt += 1
        except Exception as ex:
            logger.error("%s is broken (%s)!", bsig[baselen:], str(ex))
            exitcode(ERR_APP_BSIG_CORRUPT)
            errcnt += 1

    if kwargs.get("cmdline", False):
        if errcnt == 0:
            logger.info("quality OK: all files have proper size / are readable")
        else:
            logger.error("quality NOK: %d file(s) processed, %d errors found!", len(bsigs), errcnt)
    elif bsigs:
        logger.info("done, processing %d file(s) where %d errors encountered", len(bsigs), errcnt)

    logger.info("returning %s", str(exitcode))
    return exitcode.error
