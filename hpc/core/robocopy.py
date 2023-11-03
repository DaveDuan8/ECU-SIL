"""
robocopy.py
-----------

Python's robocopy implementation
"""
# pylint: disable=R1260
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import stdout, stderr, exc_info, platform
from os import listdir, makedirs, stat, error, unlink, chmod, lstat
from os.path import join, exists, dirname, basename, isfile, splitext
from platform import architecture
from stat import S_ISDIR, S_ISREG, S_IWRITE
from time import sleep, time
from shutil import copystat, rmtree
from fnmatch import fnmatch
from filecmp import dircmp
from zipfile import ZipFile, ZIP_DEFLATED
from lxml.etree import parse, XSLT
from psutil import process_iter
from six import iteritems

# - HPC imports --------------------------------------------------------------------------------------------------------
from .path import linux2win
from .convert import human_size

# - defines ------------------------------------------------------------------------------------------------------------
MSWIN = platform == "win32"


# - functions / classes ------------------------------------------------------------------------------------------------
class Robocopy(object):  # pylint: disable=R0902
    """robo copy"""

    def __init__(self, **kwargs):
        r"""
        copy src to dst with some arguments

        :param dict kwargs: ...
        :keyword `arguments`:
            retry int: retry x times, default: 3
            wait int: wait time [s] between retries, default: 10
            verbose bool: print messages, default: True
            progress str: print out progress message with added percentage (each minute)
            stdout stream: default: stdout.write
            stderr stream: default: stderr.write
            ignore str: ignore pattern, same as for copytree
            replace dict: replacement dict, containing file pattern plus replacement list
            common bool: only copy common files to both: source and dest
            stat bool: whether to copy file stats as well on windows or not
            comp_pat str: compress pattern, means files which match are compressed, e.g. \*.dmp
            unc_conv bool: custom path to unc converter
        """
        self._retry = kwargs.pop('retry', 3)
        assert self._retry > 0, "'retry' must be greater than 0!"
        self._wait = max(kwargs.pop('wait', 12), 0)
        self._verb = kwargs.pop('verbose', 2)
        self._progress = kwargs.pop('progress', None)
        if self._progress is True:
            self._progress = "   progress:"
        assert self._verb in (0, 1, 2), "'verbose' must be in (1, 2, 3)!"
        self._out = kwargs.pop('stdout', lambda l: stdout.write(l + '\r\n'))
        self._err = kwargs.pop('stderr', lambda l: stderr.write(l + '\r\n'))
        self._ignore = kwargs.pop('ignore', None)
        self._changes = []
        self._replace = kwargs.pop('replace', {})
        self._stat = kwargs.pop('stat', True)
        self._common = kwargs.pop('common', False)
        self._comp_pat = kwargs.pop('comp_pat', None)
        self._unc_conv = kwargs.pop('unc_conv', self._to_unc if MSWIN else lambda x: x)
        self._errmon = kwargs.pop('errmon', None)

        self._nfiles = 0
        self._ndirs = 0
        self._noverwrite = 0
        self._errcnt = 0
        self._startm, self._lastm, self._tot_bytes = None, [], 0
        self._errmons = []

    @property
    def changes(self):
        """
        :return: ignored / not copied or moved files
        :rtype: list
        """
        return self._changes

    @property
    def bytes_written(self):
        """
        :return: total number of bytes written to dst
        :rtype: int
        """
        return self._tot_bytes

    @property
    def errmons(self):
        """return errmon translated files"""
        return self._errmons

    def _update_prog(self, final=False):
        """update progress"""
        if final:
            self._out("final: {}B ({}) / {}."
                      .format(self._tot_bytes, human_size(self._tot_bytes),
                              human_size(8. * self._tot_bytes / max(time() - self._startm, 1.0), "bps")))
        else:
            now = time() // 60
            if now not in self._lastm and self._startm // 60 != now:
                self._lastm.append(now)
                self._out("{} {}B ({}) / {}".format(self._progress, self._tot_bytes, human_size(self._tot_bytes),
                                                    human_size(8. * self._tot_bytes / (len(self._lastm) * 60), "bps")))

    @staticmethod
    def _to_unc(path):
        """convert path to unc long path"""
        # https://docs.microsoft.com/en-us/windows/desktop/FileIO/naming-a-file#maximum_path_length
        if path[0:2] == "\\\\":
            path = "UNC" + path[1:]

        if path[1] == ":" and architecture()[0] == "32bit":
            return path

        return "\\\\?\\" + path

    def copy(self, src, dst):
        """
        start copy procedure

        :param str src: source path
        :param str dst: destination path

        :returns: tuple of files copied, dirs copied, errors occured and time used
        :rtype: tuple
        """
        return self._copy_wrp(str(src), str(dst))

    def move(self, src, dst):
        """
        copy & delete = move

        :param str src: source path
        :param str dst: destination path

        :returns: tuple of files copied, dirs copied, errors occurred and time used
        :rtype: tuple
        """
        if src == dst:  # nothing to be moved
            return 0, 0, 0, 0, 0

        return self._copy_wrp(str(src), str(dst), True)

    def _remove(self, path):
        """remove an item from file system"""
        if path.endswith('\\'):
            try:
                names = listdir(path)
            except error:
                self._rmtree_err(listdir, path, exc_info())
            for name in names:
                fullname = join(path, name)
                try:
                    mode = lstat(fullname).st_mode
                except error:
                    mode = 0
                if S_ISDIR(mode):
                    rmtree(fullname, onerror=self._rmtree_err)
                else:
                    try:
                        unlink(fullname)
                    except error:
                        self._rmtree_err(unlink, fullname, exc_info())
        else:
            rmtree(path, onerror=self._rmtree_err)

    def _rmtree_err(self, *args):
        """rmtree error handler"""
        try:
            if isfile(args[1]):
                chmod(args[1], S_IWRITE)
                unlink(args[1])
        except Exception as ex:
            self._errcnt += 1
            self._err("cannot remove '{}', EX: {}".format(args[1], ex))
            for proc in process_iter():
                try:
                    for ptr in proc.get_open_files():
                        if ptr.path == args[1]:
                            self._err("%d still keeps it open!" % proc.pid)
                            return
                except Exception:
                    pass

    def _copy_wrp(self, src, dst, move=False):
        """wrap around _copy"""
        self._nfiles = 0
        self._ndirs = 0
        self._noverwrite = 0
        self._errcnt = 0
        self._startm = timing = time()

        if self._verb > 0:
            self._out("   src: " + src)
            self._out("   dst: " + dst)

        if not exists(src):
            if self._verb > 0:
                self._out("ERROR: source doesn't exists!")
            return 0, 0, 1, time() - timing

        for _ in range(self._retry):
            try:
                if not exists(dst):
                    makedirs(dst)
                    self._ndirs += 1
                break
            except Exception as ex:
                self._err("ERROR makedirs: {!s}, trying again...".format(ex))
                sleep(self._wait)
        else:
            return 0, 0, 1, time() - timing

        self._copy(self._unc_conv(src), self._unc_conv(dst), move)
        if move:
            self._remove(src)

        timing = time() - timing

        if self._verb > 0:
            self._out("%sed %d files and %d directories with %d error(s)"
                      % ("mov" if move else "copi", self._nfiles, self._ndirs, self._errcnt))
        if self._progress:
            self._update_prog(True)

        return self._nfiles, self._ndirs, self._errcnt, self._noverwrite, timing

    def _copy(self, src, dst, move=False):  # pylint: disable=R0912,R0915
        """
        start moving procedure

        :param str src: source file / dir
        :param str dst: destination file /dir
        :param bool move: move it or copy it
        """
        if self._progress:
            self._update_prog()

        dcmp = dircmp(src, dst)
        prn = "mov" if move else "copy"

        # files & directories only in source directory
        if not self._common and hasattr(dcmp, "left_only"):  # pylint: disable=R1702
            for fname in self._filter_names(src, dcmp.left_only):
                try:
                    fstat = stat(join(src, fname))
                except error:
                    continue

                dstfp = join(dst, fname)

                if S_ISREG(fstat.st_mode):
                    self._copy_file(join(src, fname), dstfp, prn)
                    self._tot_bytes += fstat.st_size

                elif S_ISDIR(fstat.st_mode):
                    # copy tree
                    if self._verb > 1:
                        self._out("   %sing tree: %s" % (prn, dstfp))

                    for _ in range(self._retry):
                        try:
                            if not exists(dstfp):
                                makedirs(dstfp)
                            break
                        except OSError as ex:
                            self._err("ERROR makedirs: {!s}, trying again...".format(ex))
                            sleep(self._wait)
                    else:
                        self._errcnt += 1

                    self._copy(join(src, fname), dstfp, move)
                    self._ndirs += 1

                if self._progress:
                    self._update_prog()

        # common files/directories
        if hasattr(dcmp, "common"):
            for fname in self._filter_names(src, dcmp.common):
                try:
                    s_file = join(src, fname)
                    s_st = stat(join(src, fname))
                except error:
                    continue

                if S_ISREG(s_st.st_mode):
                    d_file = join(dst, fname)
                    try:
                        d_st = stat(d_file)

                        # Update file if file's modification time is older than
                        # source file's modification time.
                        if round(s_st.st_mtime) > round(d_st.st_mtime) or s_st.st_size != d_st.st_size:
                            self._copy_file(s_file, d_file, "updat")
                            self._nfiles += 1
                            self._tot_bytes += s_st.st_size

                        self._noverwrite += 1
                    except error:
                        self._errcnt += 1

                elif S_ISDIR(s_st.st_mode):
                    # Call tail recursive
                    self._copy(join(src, fname), join(dst, fname))

                if self._progress:
                    self._update_prog()

    def _copy_file(self, src, dst, prn):  # pylint: disable=R0912,R0915
        """use retry"""
        binmode, compmode = not any([fnmatch(basename(src), i) for i in self._replace]), False
        if binmode and self._comp_pat is not None and fnmatch(basename(src), self._comp_pat):
            dst += ".zip"
            compmode = True

        if self._verb > 1:
            if compmode:
                self._out("   %sing and zipping file: %s" % (prn, basename(src)))
            else:
                self._out("   %sing file: %s" % (prn, basename(src)))

        for retr in range(self._retry):
            try:
                if compmode:
                    with ZipFile(dst, 'w', ZIP_DEFLATED, allowZip64=True) as zfp:
                        zfp.write(src, basename(src))
                else:
                    with open(src, 'rb' if binmode else 'r') as fsrc, open(dst, 'wb' if binmode else 'w') as fdst:
                        if binmode:
                            while 1:
                                buf = fsrc.read(65536)  # 64ki
                                if not buf:
                                    break
                                fdst.write(buf)
                        else:
                            repl = next(k for i, k in iteritems(self._replace) if fnmatch(basename(src), i))
                            replaced = False

                            while 1:
                                buf = fsrc.readline()
                                if not buf:
                                    break
                                obuf = buf
                                for o, n in repl:
                                    if buf.startswith(o):
                                        buf = n + '\n'
                                if buf != obuf:
                                    replaced = True
                                fdst.write(buf)

                            if replaced:
                                self._changes.append("adapted: %s" % src)

                    if self._errmon and fnmatch(basename(src), self._errmon):  # transform the errmon
                        try:
                            trans = XSLT(parse(join(dirname(src), "errorlog.xslt")))
                            dst_doc = trans(parse(src))
                            dst_fn = splitext(dst)[0] + ".html"
                            dst_doc.write(dst_fn)
                            self._out("   generated file: %s" % basename(dst_fn))
                            self._errmons.append(linux2win(dst_fn))
                        except Exception as ex:
                            self._out("   html generation failure: {!s}".format(ex))

                if self._stat and MSWIN:  # pragma: nocover
                    copystat(src, dst)
                self._nfiles += 1
                break
            except (IOError, OSError) as ex:
                if retr < self._retry - 1:
                    self._err("ERROR copy2: {!s}, trying again...".format(ex))
                    sleep(self._wait)
                else:
                    self._err("giving up.")
        else:
            self._errcnt += 1

    def _filter_names(self, folder, files):
        """filter files by _ignore"""
        if self._ignore is None:
            return files

        lefts = set(files) - self._ignore(folder, files)
        self._changes.extend([("ignored: " + join(folder, i)) for i in set(files) - lefts])
        return lefts
