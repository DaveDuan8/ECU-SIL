r"""
bpl_func.py
-----------

functions, helping the user to manipulate bpl files
"""
# pylint: disable=C0103
# - import Python modules ----------------------------------------------------------------------------------------------
from os.path import normpath
from re import match, IGNORECASE
from xml.sax.saxutils import escape
from lxml.etree import Element, _Element, SubElement, parse, tostring, XMLSyntaxError
from six import PY2, iteritems

# - import HPC modules -------------------------------------------------------------------------------------------------
from .bpl_ex import BplException
from ..core.tds import replace_server_path, LOC_HEAD_MAP, HPC_STORAGE_MAP, DEV_LOC, LND_LOC

if not PY2:
    unicode = str


# - classes ------------------------------------------------------------------------------------------------------------
class BplList(list):
    """
    data-container for the Bpl()-Class.
    It is build out of a list of BplListEntries
    """

    def __init__(self):
        """init myself"""
        list.__init__(self)

    def bpl2dict(self):
        """
        convert a BplList to a dictionary, it leaves out the relative Timestamp flag!!

        You need to know / check by yourself if the Timestamps are relative or absolute

        :return: dict with all sections per recfile {'rec1':[(23, 34), (47, 52)], 'rec2:[(31, 78)], ...}
        :rtype:  dictionary
        """
        return {b.filepath[0]: [(s.start_ts, s.end_ts, s.rel,) for s in b.sectionlist] for b in self}

    def clear(self):
        """delete the whole internal RecFileList."""
        self.__delitem__(slice(0, None))


class BplReaderIfc(BplList):  # pylint: disable=R0902
    """interface for BplReader Subclasses, like BPLIni, BPLtxt, BPLxml"""

    def __init__(self, filepath, *args, **kwargs):
        """hold the path to file and rec list"""
        BplList.__init__(self)

        self._version = None
        self._written = 0
        self._read = False
        self._kwargs = kwargs
        self._mode = args[0] if len(args) > 0 else kwargs.pop("mode", "r")

        if not hasattr(filepath, 'read'):
            self.filepath = filepath
            self._fp = None
        else:
            self.filepath = filepath.name
            self._fp = filepath
            self._fp.seek(0)

        self._iter_idx = 0

    def __enter__(self):
        """support with statement"""
        if self._mode in ["r", "a"] and not self._read:
            self.read()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """support with statement"""
        if self._mode in ["w", "a"] and not self._written:
            self.write()

    def __str__(self):
        """my repr"""
        return "<BPL: '{}'>".format(self.filepath)

    def __contains__(self, filepath):
        """do we have a recording by that name inside?"""
        for i in self:
            if i.filepath.lower() == str(filepath).lower():
                return True
        return False

    def __getitem__(self, item):
        """
        :return: item at position or filepath
        :rtype: ``BplListEntry``
        :raises IndexError: once item is not found
        """
        if isinstance(item, int):
            return BplList.__getitem__(self, item)

        for i in self:
            if i.filepath == item:
                return i

        raise IndexError

    def append(self, entry):
        """append an entry"""
        BplList.append(self, entry if isinstance(entry, BplListEntry) else BplListEntry(entry))

    def validate(self):
        """validate the file"""
        try:
            if len(self.read()) > 0:
                return True
        except Exception as _:
            pass

        return False

    def read(self):
        """read stub"""
        raise NotImplementedError

    def write(self):
        """write stub"""
        raise NotImplementedError

    def __or__(self, other):
        """let's do | (or) operator"""
        return list(set(self).union(set(other)))

    def __xor__(self, other):
        """let's do ^ (xor) operator"""
        return list(set(self).symmetric_difference(set(other)))

    def __and__(self, other):
        """let's do & (and) operator"""
        return list(set(self).intersection(set(other)))

    def __sub__(self, other):
        """let's do - (sub) operator"""
        return list(set(self).difference(set(other)))

    def _extract_items(self, xml):
        """extract list from root"""
        try:
            root = parse(xml).getroot()
        except XMLSyntaxError as ex:
            raise BplException("'{}' has invalid syntax: '{!s}'!".format(self.filepath, ex.msg))
        self._version = root.get("version")

        del self[:]
        for entry in root.iter("BatchEntry"):  # pylint: disable=R1702
            if entry.get("fileName") or entry.get("mergeListName") or entry.get("groupName"):
                rec = BplListEntry(entry, root)
            else:
                raise BplException("not a supported BPL entry: {}!".format("/".join(entry.keys())))

            BplList.append(self, rec)


class BplListEntry(object):
    """
    Data-Container which holds following Information:
     - RecFilePath
     - list of all Sections applied to the file.
    """

    def __init__(self, entry, parent=None):  # pylint: disable=R0912,R1260
        """
        BPL version 2 explained:
        https://confluence.auto.continental.cloud/display/MTS26/Sequential+Merging

        :param lxml.etree.Element entry: full path to rec file
        :param lxml.etree.Element parent: parent of element
        :raises BplException: on problem with a section
        """
        self.entry = []
        self.filepath = []
        self._xelems = []
        self._sectionlist = []
        self.location = None
        self.is_simple = False
        self._version = parent.get("version") if parent is not None else None

        if isinstance(entry, (str, unicode,)):
            self.entry = [Element("BatchEntry", {"fileName": entry})]
            self.filepath = [normpath(entry.strip())]
            self.is_simple = True

        elif isinstance(entry, _Element) and entry.tag == "BatchEntry":  # pylint: disable=R1702
            if entry.get("fileName"):
                self.entry = [entry]
                self.filepath = [escape(entry.get("fileName").strip())]
                self._xelems = list(entry)
                for sec in entry.iter("SectionList"):
                    for k in sec.iter("Section"):
                        begt, endt = k.get("startTime"), k.get("endTime")
                        if begt and endt:
                            rels, rele = begt.endswith('R'), endt.endswith('R')
                            try:
                                self.append(int(begt[:len(begt) - int(rels)]), int(endt[:len(endt) - int(rele)]),
                                            (rels, rele,))
                            except Exception:
                                raise BplException("Section has errors: {!s}".format(tostring(sec)))

                def _recur(elem):
                    """recur through whatever we find"""
                    for ent in elem:
                        if ent.get("fileName"):
                            self.filepath.append(escape(ent.get("fileName")))
                        _recur(ent)
                for sec in entry:
                    _recur(sec)
                self.is_simple = len(self.filepath) == 1 and len(self._sectionlist) == 0

            elif entry.get("groupName"):
                self.entry = [i for i in parent.findall("Group") if i.get("name") == entry.get("groupName")]
                self.filepath = [escape(i.get("fileName").strip()) for i in list(self.entry[0]) if i.get("fileName")]
                if self.entry[0].get("directory"):
                    self.filepath.append(escape(self.entry[0].get("directory")))
                self.entry.append(entry)

            elif entry.get("mergeListName"):
                self.entry = [i for i in parent.findall("MergeList") if i.get("name") == entry.get("mergeListName")]
                self.filepath = [escape(i.get("fileName").strip()) for i in list(self.entry[0]) if i.get("fileName")]
                grps = [i.get("groupName") for i in list(self.entry[0]) if i.get("groupName")]
                self.entry.extend([i for i in parent.findall("Group") if i.get("name") in grps])
                for i in self.entry[1:]:
                    if i.get("directory"):
                        self.filepath.append(escape(i.get("directory")))
                    else:
                        self.filepath.extend([escape(k.get("fileName").strip()) for k in list(i)])
                self.entry.append(entry)

        for i, v in enumerate(self.filepath):
            self.filepath[i] = replace_server_path(v, True)

        self._location()

    def _location(self):
        """
        set location based on server used in filename

        used for xml and ini/txt files, some classes might need own method
        """
        locs = []
        for fpth in self.filepath:
            for loc, heads in iteritems(LOC_HEAD_MAP):
                if any([match(r"(?i)\\\\%s\\.*" % i, unicode(fpth), IGNORECASE) for i in HPC_STORAGE_MAP[heads[0]][0]]):
                    locs.append(loc if not loc == DEV_LOC else LND_LOC)
                    break
        self.location = set(locs)
        if len(self.location) > 1:
            raise BplException("BatchEntry contains files from multiple locations!")

        if locs:
            self.location = locs[0]

    def append(self, start_ts, end_ts, rel):
        """
        append one section entry into this BplListEntry.

        :param int start_ts: StartTimestamp of Section
        :param int end_ts: EndTimestamp of Section
        :param tuple rel:      relative Timestamp Format (True/False)
        """
        self._sectionlist.append(Section(start_ts, end_ts, rel))

    def save(self, fname):
        """save original content to file"""
        top = Element('BatchList', {"version": self._version} if self._version else {})

        def _recur_add(base, entry):
            """add childs"""
            elem = SubElement(base, entry.tag, entry.attrib)
            for sub in entry:
                _recur_add(elem, sub)

        for rec in self.entry:
            _recur_add(top, rec)

        with open(fname, 'wb') as fp:
            data = tostring(top, pretty_print=True, encoding='utf-8', standalone=True)
            fp.write(data)
        return len(data)

    @property
    def extra_elements(self):
        """
        :return: all other elements
        :rtype: list
        """
        return self._xelems

    def add_element(self, elem):
        """add another element"""
        self._xelems.append(elem)

    @property
    def sectionlist(self):
        """
        kept for backward compatibility

        please use iterator instead if possible:::

            for section in listentry:
                print(section)
        """
        return self._sectionlist

    def __repr__(self):
        """
        :return: path to my own
        :rtype: str
        """
        return "{} [{}]".format(";".join(self.filepath),
                                "" if len(self) == 0 else ", ".join(str(i) for i in self.sectionlist))

    def __str__(self):
        """
        take care that some file names have some unicode encodings and might fail

        :return: path to my own
        :rtype: str
        """
        return self.filepath[0]

    def __len__(self):
        """return the size of entries"""
        return len(self.filepath)

    def __hash__(self):
        """
        :return: my hash
        :rtype: str
        """
        return hash(tuple(self.filepath + [hash(i) for i in self._sectionlist]))

    def __eq__(self, other):
        """equal to other?"""
        if isinstance(other, BplListEntry):
            return len(self.filepath) == len(other.filepath) and self.sectionlist == other.sectionlist \
                and all([self.filepath[i] == other.filepath[i] for i in range(len(self.filepath))])
        return NotImplemented

    def __ne__(self, other):
        """not equal to other?"""
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


class Section(object):
    """Data-Container which holds section information for bpl-lists."""

    def __init__(self, start_ts, end_ts, rel=(False, False,)):
        """set start and end, well rel as well"""
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.rel = rel

    def __str__(self):
        """let user know about us"""
        return str({"start_ts": self.start_ts, "end_ts": self.end_ts, 'rel': self.rel})

    def __hash__(self):
        """hash to section"""
        return hash((self.start_ts, self.end_ts, self.rel))

    def __eq__(self, other):
        """equal to other?"""
        if isinstance(other, Section):
            return self.start_ts == other.start_ts and self.end_ts == other.end_ts and self.rel == other.rel
        return NotImplemented

    def __ne__(self, other):
        """not equal to other?"""
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def sect2list(self):
        """convert a section to a tuple (start_ts, end_ts, rel)"""
        return self.start_ts, self.end_ts, self.rel
