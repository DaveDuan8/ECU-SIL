"""
bpl_txt.py
----------

class for BPL text (BatchPlayList) handling
"""
# - import HPC modules -------------------------------------------------------------------------------------------------
from .bpl_ex import BplException
from .bpl_cls import BplReaderIfc, BplListEntry
from ..core.logger import deprecated


# - classes ------------------------------------------------------------------------------------------------------------
class BPLTxt(BplReaderIfc):
    r"""
    Specialized BPL Class which handles only writing and reading of \*.txt Files.
    This class is not a customer Interface, it should only be used internal of hpc.
    """

    @deprecated("txt support will be dropped in future...")
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

        :return: list of file entries or None if there is no entry
        :rtype: self
        """
        del self[:]
        if self._fp:
            self.extend([BplListEntry(i.strip()) for i in self._fp])
        else:
            with open(self.filepath, "rb") as fpo:
                self.extend([BplListEntry(i.strip()) for i in fpo])

        self._read = True
        return self

    def write(self):
        """do not write"""
        raise BplException("unable to write by now.")

    # def write(self):
    #     """write the complete recfilelist to the file"""
    #     data = "\n".join([str(i) for i in self])
    #
    #     if self._fp:
    #         self._fp.write(data)
    #     else:
    #         with open(self.filepath, "wb") as fpo:
    #             fpo.write(data)
