"""
bpl.ini
-------

class for BPL ini (BatchPlayList) handling
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from codecs import open as copen
from re import match
from configparser import ConfigParser
# import warnings
# from six import PY2

# - import HPC modules -------------------------------------------------------------------------------------------------
from .bpl_ex import BplException
from .bpl_cls import BplReaderIfc
from ..core.logger import deprecated


# - defines ------------------------------------------------------------------------------------------------------------
INI_FILE_SECTION_NAME = "SimBatch"
STRING_TARGET_ENCODING = 'utf-8'


# - classes ------------------------------------------------------------------------------------------------------------
class BPLIni(BplReaderIfc):
    r"""
    Specialized BPL Class which handles only writing and reading of \*.ini Files.
    This class is not a customer Interface, it should only be used internal of hpc.
    """

    @deprecated("ini support will be dropped in future...")
    def __init__(self, *args, **kwargs):
        """
        init collection, as it can and will be recursive, we call ourself again and again and again

        :param tuple args: args for the interface
        :param dict kwargs: kwargs, loc is taken out immediately, others are passed through
        """
        BplReaderIfc.__init__(self, *args, **kwargs)

    def read(self):
        """
        read the batch play list file content

        :return: The list of file entries or None if there is no entry.
        :rtype: self
        """
        config = ConfigParser()
        with copen(self.filepath, "r", STRING_TARGET_ENCODING) as filep:
            config.read_file(filep)

        del self[:]
        for i in config.items(INI_FILE_SECTION_NAME):
            if match(r"file\d+", i[0]):
                self.append(i[1].strip('"').replace('\\\\', '\\'))

        self._read = True
        return self

    def write(self):
        """do not write"""
        raise BplException("unable to write by now.")

    # def write(self):
    #     """write the complete recfilelist to the file"""
    #     config = ConfigParser()
    #     config.optionxform = lambda x: x
    #     config.add_section(INI_FILE_SECTION_NAME)
    #
    #     if PY2:
    #         def warn(*_args, **_kwargs):  # suppress the PY2 warning
    #             pass
    #         owarn = warnings.warn
    #         warnings.warn = warn
    #
    #     config.set(INI_FILE_SECTION_NAME, "FileCount", str(len(self)))
    #     for i, v in enumerate(self):
    #         v = v.filepath[0]
    #         if PY2:
    #             try:
    #                 v = v.encode(STRING_TARGET_ENCODING)
    #             except Exception:
    #                 pass
    #         config.set(INI_FILE_SECTION_NAME, "File{}".format(i), '"{}"'.format(v.replace('\\', '\\\\')))
    #     if PY2:
    #         warnings.warn = owarn
    #
    #     if self._fp:
    #         config.write(self._fp)
    #     else:
    #         with copen(self.filepath, "wb" if PY2 else "w", encoding=STRING_TARGET_ENCODING) as fpo:
    #             config.write(fpo)
