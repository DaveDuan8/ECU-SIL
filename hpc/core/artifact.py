"""
artifact.py
-----------

download a certain piece from artifactory
"""
# - Python imports -----------------------------------------------------------------------------------------------------
from os import environ, makedirs
from os.path import exists, dirname
from fnmatch import fnmatch
from time import time
from re import search
from zipfile import ZipFile
from tarfile import open as topen
try:
    from artifactory import ArtifactoryPath
    from io import BytesIO
except ImportError:
    ArtifactoryPath = None

# - HPC imports --------------------------------------------------------------------------------------------------------
from ..core.logger import DummyLogger
from ..core.error import HpcError
from ..core.convert import human_size


# - classes / functions ------------------------------------------------------------------------------------------------
def articopy(src, dst, logger=None):  # pylint: disable=R0912,R0915,R1260
    """
    download src from artifactory and save it to dst folder, using logger for further info outputs

    :param str src: source link to load the MTS from
    :param str dst: destination to place it
    :param logging.Logger logger: logger instance to use
    :raises hpc.HpcError: once it doesn't exist
    """
    if logger is None:
        logger = DummyLogger()

    if not ArtifactoryPath:
        raise HpcError("'articopy' is not available, please use official Python3 installation!")

    with ArtiWrap(src, timeout=1440) as art:
        try:
            if not art.exists():
                raise HpcError("Artifactory link doesn't exist: {}!".format(src))
        except RuntimeError as rex:
            mtc = search(r"<title>(.*)</title>", str(rex))
            msg = "(unknown)" if mtc is None else mtc.groups()[0]
            raise HpcError("general Artifactory problem: {}".format(msg))

        startm, lastm, tsz, cnt, omi, idx, item = time(), int(time() / 60), 0, 0, 0, len(art.path_in_repo), None
        if src[-4:].lower() not in (".zip", ".tgz"):  # hardly used recently as Artifactory has a problem packing it
            for item in art.glob("**/*"):
                loc_path = dst + item.path_in_repo[idx:]
                if item.is_dir():
                    for i in ['/__pycache__', '/mts_system/doc', '/mts_system/lib', '/mts_system/include',
                              '/mts_system/mi4_system_driver', '/mts_system/MTSV2AppWizard',
                              '/mts_measurement/data/sil_test', '/mts_measurement/data/DF_SILTest_bpl',
                              '/mts_measurement/log/siltest']:
                        if item.path_in_repo[idx:].endswith(i):
                            omi += 1
                            break
                    else:
                        if exists(dirname(loc_path)):
                            makedirs(loc_path)
                elif exists(dirname(loc_path)):
                    for i in ['*.pdb', '.gitignore', '*.bpl']:
                        if fnmatch(item.name, i):
                            omi += 1
                            break
                    else:
                        item.writeto(loc_path, 1024 * 1024)
                        tsz += item.stat().size
                        cnt += 1
                        chtm = int(time() / 60)
                        if chtm != lastm:
                            lastm = chtm
                            logger.info("downloaded %d files (%s) by now (%s)", cnt, human_size(tsz),
                                        human_size(tsz / (time() - startm), "B/s"))

            logger.info("finished downloading %d files (%s) after %.0fmin (%s), ommitted %d files",
                        cnt, human_size(tsz), (time() - startm) / 60,
                        human_size(tsz / (time() - startm), "B/s"), omi)
        else:
            with art.open() as afp:
                unpacker, opt, names = (ZipFile, "file", "namelist") if src[-4:].lower() == ".zip" \
                    else (topen, "fileobj", "getnames")
                with unpacker(**{opt: BytesIO(afp.read())}) as zfp:
                    zfp.extractall(dst)
                    cnt = len(getattr(zfp, names)())
            logger.info("finished downloading and extracting %d files after %.1fmin", cnt, (time() - startm) / 60)


class ArtiWrap(object):
    """preserve some environment variables"""

    def __init__(self, *args, **kwargs):
        """
        wrap around the ArtifactoryPath class

        :param args: std arguments to pass
        :param kwargs: xtra args to pass
        """
        self._envals = {v: environ.pop(v) for v in ["HTTP_PROXY", "HTTPS_PROXY"] if v in environ}
        self._arti = ArtifactoryPath(*args, **kwargs)
        self.error = None

    def __enter__(self):
        """enter"""
        return self

    def __exit__(self, *args):
        """exit"""
        self._arti.session.close()

        for k, v in self._envals.items():
            environ[k] = v

    def exists(self):
        """overload as of extra exception handling"""
        try:
            return self._arti.exists()
        except RuntimeError as ex:
            self.error = ex.args[0]
        except Exception as ex:
            self.error = str(ex)
        return False

    def __getattr__(self, item):
        """do as if we'd be ArtifactoyPath itself, as we cannot inherit as of missing __init__"""
        return self._arti.__getattribute__(item)
