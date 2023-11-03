"""
bpl_splt.py
-----------

Bpl splitter
"""
# - Python imports ----------------------------------------------------------------------------------------------------
from os.path import exists, join, basename
from shutil import copyfile
from six import iteritems

# - HPC imports -------------------------------------------------------------------------------------------------------
from ..rdb.base import BaseDB
from ..core.error import HpcError
from ..core.logger import deprecated
from ..core.tds import LOC_HEAD_MAP
from .base import Bpl


# - classes / functions -----------------------------------------------------------------------------------------------
class BplSplitter(object):
    r"""
    The BplSplitter will create the needed bpl folder inside 1_Input,
    reads the whole \*.bpl and provide either the path to rec file, or if bpl entry contains a section
    a newly created \*.bpl file with corrected path inside the new created bpl is created.
    """

    @deprecated("please, stop using internals, we'll drop that class soon!")
    def __init__(self, job, _net_job_in_path, bpl_file_path, **kwargs):
        r"""
        :param hpc.Job job: HPC job instance
        :param str _net_job_in_path: path to input folder of job
        :param str bpl_file_path: path to batch play list
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *ignore_missing* (``bool``): ignore missing recordings on destination location
        """
        self._job = job
        self._bpl_folder = job.sched.net_in_path + r'\bpl'
        self._bpl_count = 1
        self._bpl_list = 0

        # Copy the input *.bpl to network.
        if exists(str(bpl_file_path)):
            copyfile(bpl_file_path, join(job.sched.net_in_path, basename(bpl_file_path)))

        # Parse bpl file and provide rec file list
        db = "VGA_PWR" if job.base_db is None or job.job_sim or job.base_db.db_type[0] == BaseDB.ORACLE \
            else job.base_db
        self._bpl_list = Bpl(bpl_file_path,  # pylint: disable=E1111
                             db=db, loc=next((k for k, v in iteritems(LOC_HEAD_MAP) if self._job.head_node in v), None),
                             ignore_missing=kwargs.get("ignore_missing", False)).read()

    def __getitem__(self, index):
        """
        return a specific item

        :param int index: index within me
        :return: item
        :rtype: BplEntry
        :raises IndexError: once index is out of range
        :raises HpcError: once recording entry is unreadable
        """
        if index >= len(self._bpl_list):
            raise IndexError("that's enough!")

        bpl_entry = self._bpl_list[index]

        if bpl_entry.is_simple:
            try:
                value = (False, str(bpl_entry))
            except UnicodeEncodeError as ex:
                raise HpcError("your bpl contains some illegal chars, please check it: {!s} ({})".format(ex, bpl_entry))
        else:
            # Create a single bpl
            bpl_path = join(self._bpl_folder, "rec{:05d}.bpl".format(self._bpl_count))
            self._bpl_count += 1
            bpl_entry.save(bpl_path)
            # use the created bpl.
            value = (True, bpl_path)

        return value

    def __len__(self):
        """
        :return: length of bpl list
        :rtype: int
        """
        return len(self._bpl_list)
