# -*- coding: iso-8859-1 -*-
"""
base.py
-------

Classes for BPL (BatchPlayList) Handling, supports BPL (of course), collection, ini and text files
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from os.path import splitext
from warnings import warn

# - import HPC modules -------------------------------------------------------------------------------------------------
from .bpl_xml import BPLXml
from .bpl_ini import BPLIni
from .bpl_txt import BPLTxt
from .bpl_db import BPLDb
from .bpl_coll import BPLColl
from .bpl_cls import BplListEntry
from ..core.dicts import DefDict

# - defines ------------------------------------------------------------------------------------------------------------
BPL_SUPPORTS = {".bpl": BPLXml, ".ini": BPLIni, ".txt": BPLTxt}
EXT_SUPPORTS = DefDict(BPLDb, **{"falcon": BPLColl, "legacy": BPLDb})


# - classes ------------------------------------------------------------------------------------------------------------
class Bpl(object):
    r"""
    Possibility to read and write Batch Play Lists or Collections supported by mts.

    Currently \*.ini, \*.txt and \*.bpl based BatchPlayLists are supported.
    The file structure is automatically selected by the ending.

    - \*.bpl files based on xml and support section definitions for the rec files
    - \*ini, \*.txt files simply list the complete path and file name
    - if filepath is not a readable file: a collection from DB is used (as created with TDSM tool)

    *structure*::

        `BplList`  -  list (`BplListEntry`)
            |
            +- filepath (str)
            |
            +- location (str)
            |
            -- sectionlist (list(`Section`))
                |
                +- start_ts (long)
                +- end_ts (long)
                +- rel (bool)

    In case of BplList read from \*.ini or \*.txt file the sectionlist is empty.

    The location is internal only (not directly visible in Bpl files) and provides the site abbreviation
    where the file is stored. Usage like if mybpllistentry.location in ['LND', 'FFM']: print("file stored in Europe")

    **example usage one**

        code::

            # Create an instance of your BPL-Reader
            bpl = hpc.Bpl(r"D:\testdir\MyBatchPlayList.bpl")

            # Get whole RecFile List out from bpl file
            bpllist = bpl.read()                        # type: BplList

            # Iterate over whole list in a for loop
            for bplentry in bpllist:                    # type: BplListEntry
                recfilename = bplentry.filepath
                storage_site = bplentry.location
                for section in bplentry.sectionlist:     # type: Section
                    start = section.start_ts
                    end = section.end_ts
                    is_relative_timestamp = section.rel

    **example usage two**

        code::

            with Bpl(r"D:\another\file.bpl") as bpl:  # open a bpl
                for i, ent in enumerate(bpl):
                    print("saving {!s}".format(ent))
                    ent.save(join(job.job_folder, "1_Input", "bpl", "part_{:0>5d}.bpl".format(i))

    **example usage three**

        code::

                # supported modes are "w" and "r" similar to files
                # for "r" it's automatically read, for "w" it's automatically written when using with statement
                with Bpl("sample.bpl", "w") as bpl, BaseDB("VGA") as db:
                    for i in db.executex("SELECT FILEPATH FROM CAT_DMT_FILES WHERE ....."):
                        bpl.append(i[0])

    **example usage four**

        code::

                # go throught a Falcon based collection:
                with Bpl("my_falcon_collection", collbase="falcon") as bpl:
                    for ent in bpl:
                        task_fact.create_task(ent)

    The internal Bpl structure is ported from mts, but you can convert it to a dict if needed.
    Similar there is a method to convert the Section to a list::

        list_dict = bpllist.bpl2dict()
        secttupel = bpllist[0].sectionlist[0].sect2list()  # tuple(<start_ts>, <end_ts>, <rel>)

    Functions to create a BPL files for different usecases are available in module `bpl` .
    """

    def __new__(cls, filepath, *args, **kwargs):
        """init and return child class"""
        if isinstance(filepath, BplListEntry):
            return BPLXml(filepath, *args, **kwargs).read()

        fname = filepath.name if hasattr(filepath, "read") else filepath
        ext = splitext(str(fname))[-1].lower()
        if ext in BPL_SUPPORTS:
            return BPL_SUPPORTS[ext](filepath, *args, **kwargs)

        cbase = kwargs.get("collbase", None)
        if not cbase:
            warn("'collbase' option to Bpl missing, assuming 'legacy', will be changed soon to 'falcon' as default!",
                 stacklevel=2)
        return EXT_SUPPORTS[cbase](filepath, *args, **kwargs)

    def __enter__(self):
        """enter"""

    def __exit__(self, *_):
        """exit"""

    def read(self):
        """read file"""

    def write(self):
        """write file"""

    def append(self, _):
        """append item"""
