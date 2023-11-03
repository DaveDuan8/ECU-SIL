"""
stk/db/lbl/genlabel.py
----------------------

Classes for Database access of Generic Labels.

Sub-Scheme lbl

**User-API**
    - `BaseGenLabelDB`
        Methods to add and read additional event information similar to label data
        like events, their type or states

The other classes in this module are handling the different DB types and are derived from BaseGenLabelDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseGenLabelDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseGenLabelDB`.


:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.8 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/08/25 15:47:09CEST $
"""
# =====================================================================================================================
# Imports
# =====================================================================================================================
from stk.db.db_common import BaseDB, DB_FUNC_NAME_MIN, DB_FUNC_NAME_LOWER, \
    ERROR_TOLERANCE_LOW, AdasDBError, PluginBaseDB
from stk.db.db_sql import GenericSQLSelect, GenericSQLStatementFactory, SQLBinaryExpr, SQLFuncExpr, OP_EQ, \
    SQLLiteral, SQLColumnExpr, SQLTableExpr, OP_AS, OP_AND, SQLJoinExpr, OP_INNER_JOIN, EXPR_ORDER_BY

from stk.util.helper import deprecated

# =====================================================================================================================
# Constants
# =====================================================================================================================

# Table base names:
TABLE_NAME_LABELS = "LB_Labels"
TABLE_NAME_ATTRIBUTE_NAMES = "LB_AttributeNames"
TABLE_NAME_ATTRIBUTES = "LB_Attributes"
TABLE_NAME_STATES = "LB_States"
TABLE_NAME_TYPES = "LB_Types"
TABLE_NAME_RECTOBJIDMAP = "LB_RectObjIDMap"
TABLE_NAME_ADDINFO = "LB_AdditionalInfo"
TABLE_NAME_CAMCALIBERATIONS = "LB_CAMCALIBERATIONS"

COL_NAME_LABELS_LBID = "LBID"
COL_NAME_LABELS_ABSTS = "ABSTS"
COL_NAME_LABELS_TYPEID = "TYPEID"
COL_NAME_LABELS_WFID = "WFID"
COL_NAME_LABELS_STATEID = "STATEID"
COL_NAME_LABELS_MEASID = "MEASID"
COL_NAME_LABELS_USERID = "USERID"
COL_NAME_LABELS_MODDATE = "MODDATE"

COL_NAME_ATTRIBUTES_LBATTRID = "LBATTRID"
COL_NAME_ATTRIBUTES_LBID = "LBID"
COL_NAME_ATTRIBUTES_LBATTNAMEID = "LBATTNAMEID"
COL_NAME_ATTRIBUTES_UNITID = "UNITID"
COL_NAME_ATTRIBUTES_VTID = "VTID"
COL_NAME_ATTRIBUTES_VALUE = "VALUE"

COL_NAME_ATTR_NAMES_LBATTNAMEID = "LBATTNAMEID"
COL_NAME_ATTR_NAMES_NAME = "NAME"

COL_NAME_STATES_STATEID = "STATEID"
COL_NAME_STATES_NAME = "NAME"
COL_NAME_STATES_DESC = "DESCRIPTION"
COL_NAME_STATES_VALUE = "VALUE"
COL_NAME_STATES_TYPEID = "TYPEID"

COL_NAME_TYPES_TYPEID = "TYPEID"
COL_NAME_TYPES_NAME = "NAME"
COL_NAME_TYPES_DESC = "DESCRIPTION"
COL_NAME_TYPES_PARENT = "PARENT"

COL_NAME_RECTOBJIDMAP_RECTOBJIDMAPID = "RECTOBJIDMAPID"
COL_NAME_RECTOBJIDMAP_RECTOBJID = "RECTOBJID"
COL_NAME_RECTOBJIDMAP_LBID = "LBID"

COL_NAME_INFO_ID = "LBID"
COL_NAME_INFO_DESC = "DESCRIPTION"

# Tablle LB_CAMCALIBERATIONS
COL_NAME_CAMCALIBERATIONS_ABSTS = "ABSTS"
COL_NAME_CAMCALIBERATIONS_MEASID = "MEASID"
COL_NAME_CAMCALIBERATIONS_TYPEID = "TYPEID"
COL_NAME_CAMCALIBERATIONS_YAW = "YAW"
COL_NAME_CAMCALIBERATIONS_PITCH = "PITCH"
COL_NAME_CAMCALIBERATIONS_ROLL = "ROLL"

IDENT_STRING = "dblb"

# =====================================================================================================================
# functions
# =====================================================================================================================


def get_attibute_condition(labelid, att_name_id=None):
    """
    Get the SQL condition expression to access the label attribute record

    :param labelid: the label id
    :type labelid: int
    :param att_name_id: the attibute name id
    :return: Returns the condition expression
    """
    cond = SQLBinaryExpr(COL_NAME_ATTRIBUTES_LBID, OP_EQ, labelid)

    if att_name_id is not None:
        cond_name = SQLBinaryExpr(COL_NAME_ATTRIBUTES_LBATTNAMEID, OP_EQ, att_name_id)
        cond = SQLBinaryExpr(cond, OP_AND, cond_name)

    return cond


def get_add_label_info_condition(lbid):
    """
    Get the condition expression to access the additional label

    :param lbid: Label ID
    :return: Returns the condition expression
    :rtype: SQLBinaryExpression
    """
    return SQLBinaryExpr(COL_NAME_INFO_ID, OP_EQ, SQLLiteral(lbid))


# =====================================================================================================================
# Constraint DB Libary Base Implementation
# =====================================================================================================================


class BaseGenLabelDB(BaseDB):  # pylint: disable=R0904
    """**base implementation of Generic label Database**

    For the first connection to the DB for lbl tables just create a new instance of this class like

    .. python::

        from stk.db.lbl.genlabel import BaseGenLabelDB

        dblbl = BaseGenLabelDB("ARS4XX")   # mainly used in radar, or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dblbl = BaseGenLabelDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    **error_tolerance**

    The setting of an error tolerance level allows to define if an error during later processing is

    - just listed to the log file (error_tolerance = 3, HIGH) if possible,
      e.g. if it can return the existing id without changes in case of adding an already existing entry
    - raising an AdasDBError immediately (error_tolerance < 1, LOW)

    More optional keywords are described at `BaseDB` class initialization.

    """
    # ====================================================================
    # Constraint DB Libary Interface for public use
    # ====================================================================

    # ====================================================================
    # Handling of database
    # ====================================================================

    def __init__(self, *args, **kwargs):
        """
        Constructor to initialize BaseGenLabelDB to represent LB subschema

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        :keyword error_tolerance: Error tolerance level based on which some error are acceptable
        :type error_tolerance: int
        """
        kwargs['strIdent'] = IDENT_STRING
        BaseDB.__init__(self, *args, **kwargs)

    # ====================================================================
    # Handling of label state
    # ====================================================================
    def add_state(self, state):
        """
        Add Label state record to table LB_STATES

        :param state: record to insert
        :type state: dict
        :return: return stateId as primary key of the newly inserted row
        :rtype: int
        """

        stateid = None
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_STATES_NAME),
                             OP_EQ, SQLLiteral(state[COL_NAME_STATES_NAME].lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_STATES], where=cond)
        if len(entries) <= 0:
            stateid = self._GetNextID(TABLE_NAME_STATES, COL_NAME_STATES_STATEID)
            state[COL_NAME_STATES_STATEID] = stateid
            self.add_generic_data(state, TABLE_NAME_STATES)
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("state '%s' exists already in the generic label database" %
                                  state[COL_NAME_STATES_NAME])
            else:
                self._log.warning("state '%s' already exists in the generic label database."
                                  % state[COL_NAME_STATES_NAME])
                if len(entries) == 1:
                    stateid = entries[0][COL_NAME_STATES_STATEID]
                elif len(entries) > 1:
                    raise AdasDBError("state name '%s' cannot be resolved because it is ambiguous. (%s)" %
                                      (state[COL_NAME_STATES_NAME], entries))
        # done
        return stateid

    def update_state(self, state, where=None):
        """
        Update existing state records.

        :param state: state record with new values
        :type state: dict
        :param where: SQL Condition as criteria of record to update
        :type where: SQLBinaryExpr
        """

        rowcount = 0

        if where is None:
            where = SQLBinaryExpr(COL_NAME_STATES_STATEID, OP_EQ, SQLLiteral(state[COL_NAME_STATES_STATEID]))

        if (state is not None) and (len(state) != 0):
            rowcount = self.update_generic_data(state, TABLE_NAME_STATES, where)
        # done
        return rowcount

    def delete_state(self, state):
        """
        Delete Label state by name

        :param state: dictionary Record contain Label state name
        :type state: dict
        """

        rowcount = 0
        if (state is not None) and (len(state) != 0):
            cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_STATES_NAME),
                                 OP_EQ, SQLLiteral(state[COL_NAME_STATES_NAME].lower()))
            rowcount = self.delete_generic_data(TABLE_NAME_STATES, where=cond)
        # done
        return rowcount

    def get_state(self, name):
        """
        Get Label state record by name

        :param name: Label state name
        :type name: str
        """

        record = {}
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_STATES_NAME),
                             OP_EQ, SQLLiteral(name.lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_STATES], where=cond)
        if len(entries) <= 0:
            self._log.warning("State with name '%s' does not exists in the generic label database." % name)
        elif len(entries) > 1:
            self._log.warning("State with name '%s' cannot be resolved because it is ambiguous. (%s)"
                              % (name, entries))
        else:
            record = entries[0]
        # done
        return record

    def get_state_id(self, name):
        """
        Get Label State Id by name

        :param name: Label state name
        :type name: str
        :return: Return label state Id
        :rtype: int
        """

        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_STATES_NAME), OP_EQ,
                             SQLLiteral(name.lower()))
        entries = self.select_generic_data(table_list=[TABLE_NAME_STATES], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_STATES_STATEID]
        elif len(entries) <= 0:
            raise AdasDBError("State '%s' doesn't exists in the generic label database." % name)
        else:
            raise AdasDBError("State name '%s' cannot be resolved because it is ambiguous. (%s)" % (name, entries))
        # done

    def get_state_value(self, stateid):
        """
        Get Label State Value

        :param stateid: Label state ID
        :type stateid: int
        :return: The value of label state
        :rtype: Float
        """

        cond = SQLBinaryExpr(COL_NAME_STATES_STATEID, OP_EQ, stateid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_STATES], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_STATES_VALUE]
        elif len(entries) <= 0:
            raise AdasDBError("State with id '%s' doesn't exists in the generic label database." % stateid)
        else:
            raise AdasDBError("State with id '%s' cannot be resolved because it is ambiguous. (%s)" %
                              (stateid, entries))
        # done

    def get_state_name(self, stateid):
        """
        Get Label state name by stateId

        :param stateid: Label state Id
        :type stateid: str
        :return: Label state name
        :rtype: str
        """

        cond = SQLBinaryExpr(COL_NAME_STATES_STATEID, OP_EQ, stateid)

        entries = self.select_generic_data(table_list=[TABLE_NAME_STATES], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_STATES_NAME]
        elif len(entries) <= 0:
            raise AdasDBError("State with id '%s' doesn't exists in the generic label database." % stateid)
        else:
            raise AdasDBError("State with id '%s' cannot be resolved because it is ambiguous. (%s)" %
                              (stateid, entries))
        # done

    def _get_parrent_state_names_uvalues(self, childtypeid):  # pylint: disable=C0103
        """
        Get all existing states Names records of the parent of with child type id.

        :param childtypeid: Child Type Id
        :type childtypeid: int
        :return: Returns the state Names and values record of the parent.
        :rtype: list
        """

        record = {}
        cond = SQLBinaryExpr(COL_NAME_TYPES_TYPEID, OP_EQ, childtypeid)

        parenttypeid = self.select_generic_data(table_list=[TABLE_NAME_TYPES], where=cond)

        if len(parenttypeid) > 0:
            parenttypeid = parenttypeid[0][COL_NAME_TYPES_PARENT]
            cond = SQLBinaryExpr(COL_NAME_STATES_TYPEID, OP_EQ, parenttypeid)

            select_list = [COL_NAME_STATES_NAME, COL_NAME_STATES_VALUE]
            parententries = self.select_generic_data(select_list=select_list,
                                                     table_list=[TABLE_NAME_STATES],
                                                     where=cond)
            record = parententries
        else:
            self._log.warning("Label type with ID '%s' has no parent." % childtypeid)

        return record

    def get_state_names_uvalues(self, typeid):
        """
        Get all label state with given type Id

        :param typeid: Label type ID
        :type typeid: int
        :return: Returns the types Names record.
        :rtype: list
        """
        cond = SQLBinaryExpr(COL_NAME_STATES_TYPEID, OP_EQ, typeid)

        select_list = [COL_NAME_STATES_NAME, COL_NAME_STATES_VALUE]
        entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_STATES], where=cond)
        if len(entries) <= 0:
            record = self._get_parrent_state_names_uvalues(typeid)
            if len(record) <= 0:
                self._log.warning("Label type with ID '%s' is not assigned too any state "
                                  "in the generic label database." % typeid)
        else:
            record = self._get_parrent_state_names_uvalues(typeid)
            if len(record) != 0:
                # this code will never work:
                #   if record contains data it will be a list -> does not support update()
                record.update(entries)
            else:
                record = entries
        # done
        return record

    # ====================================================================
    # Handling of label types
    # ====================================================================
    def add_type(self, rectype):
        """
        Add Label record

        :param rectype: The type record.
        :type rectype: dict
        :return: Returns the type ID of the newly inserted row
        :rtype: int
        """
        typeid = None
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_TYPES_NAME),
                             OP_EQ,
                             SQLLiteral(rectype[COL_NAME_TYPES_NAME].lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_TYPES], where=cond)
        if len(entries) <= 0:
            typeid = self._GetNextID(TABLE_NAME_TYPES, COL_NAME_TYPES_TYPEID)
            rectype[COL_NAME_TYPES_TYPEID] = typeid
            self.add_generic_data(rectype, TABLE_NAME_TYPES)
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("type '%s' exists already in the generic label database"
                                  % rectype[COL_NAME_TYPES_NAME])
            else:
                self._log.warning("type '%s' already exists in the generic label database."
                                  % rectype[COL_NAME_TYPES_NAME])
                if len(entries) == 1:
                    typeid = entries[0][COL_NAME_TYPES_TYPEID]
                elif len(entries) > 1:
                    raise AdasDBError("type name '%s' cannot be resolved because it is ambiguous. (%s)" %
                                      (rectype[COL_NAME_TYPES_NAME], entries))
        # done
        return typeid

    def update_type(self, rectype, where=None):
        """
        Update existing type records.

        :param rectype: The type record update.
        :type rectype: dict
        :param where: The condition to be fulfilled by the type to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected type.
        :rtype: int
        """
        rowcount = 0

        if where is None:
            where = SQLBinaryExpr(COL_NAME_TYPES_TYPEID, OP_EQ, rectype[COL_NAME_TYPES_TYPEID])

        if rectype is not None and len(rectype) != 0:
            rowcount = self.update_generic_data(rectype, TABLE_NAME_TYPES, where)
        # done
        return rowcount

    def delete_type(self, rectype):
        """
        Delete existing type records.

        :param rectype: The type record update.
        :type rectype: dict
        :return: Returns the number of affected type.
        :rtype: int
        """
        rowcount = 0
        if (rectype is not None) and (len(rectype) != 0):
            cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_TYPES_NAME),
                                 OP_EQ, SQLLiteral(rectype[COL_NAME_TYPES_NAME].lower()))
            rowcount = self.delete_generic_data(TABLE_NAME_TYPES, where=cond)
        # done
        return rowcount

    def get_type(self, name):
        """
        Get Label Type record by name.

        :param name: label type name.
        :type name: str
        :return: Returns the type record.
        :rtype: dict
        """
        record = {}
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_TYPES_NAME),
                             OP_EQ, SQLLiteral(name.lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_TYPES], where=cond)
        if len(entries) <= 0:
            self._log.warning("Type with name '%s' does not exists in the generic label database." % name)
        elif len(entries) > 1:
            self._log.warning("Type with name '%s' cannot be resolved because it is ambiguous. (%s)" % (name, entries))
        else:
            record = entries[0]
        # done
        return record

    def get_type_name_with_id(self, typeid):
        """
        Get existing type Name for given type id

        :param typeid: The type ID.
        :type typeid: int
        :return: record containing type name.
        :rtype: dict
        """
        record = {}
        cond = SQLBinaryExpr(COL_NAME_TYPES_TYPEID, OP_EQ, typeid)

        entries = self.select_generic_data(table_list=[TABLE_NAME_TYPES], where=cond)
        if len(entries) <= 0:
            self._log.warning("Type with TypeID '%s' does not exists in the generic label database." % typeid)
        elif len(entries) > 1:
            self._log.warning("Type with TypeID '%s' cannot be resolved because it is ambiguous. (%s)"
                              % (typeid, entries))
        else:
            record = entries[0]
        # done
        return record

    def get_types_names(self, parent_name=None):
        """
        Get all child label types Names records for the given parent name

        :param parent_name: if parent name is set get all Typenames with this parent name
        :type parent_name: str
        :return: Returns the types Names record.
        :rtype: list
        """
        record = {}

        select_list = [COL_NAME_TYPES_NAME]

        if parent_name is None:
            entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_TYPES])
        else:
            # get the parent id
            parent_id = self.get_type(parent_name)[COL_NAME_TYPES_TYPEID]

            cond = SQLBinaryExpr(COL_NAME_TYPES_PARENT, OP_EQ, parent_id)

            entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_TYPES], where=cond)

        if len(entries) <= 0:
            self._log.warning("Types does not exists in the generic label database.")
        else:
            record = entries
        # done
        return record

    # ====================================================================
    # Handling of label attributes
    # ====================================================================

    def add_attribute(self, attribute):
        """
        Add attribute to database.

        :param attribute: The attribute record.
        :type attribute: dict
        :return: Returns the attribute ID of newly inserted row
        :rtype: int
        """
        attributeid = None
        cond = get_attibute_condition(attribute[COL_NAME_ATTRIBUTES_LBID],
                                      attribute[COL_NAME_ATTRIBUTES_LBATTNAMEID])

        entries = self.select_generic_data(table_list=[TABLE_NAME_ATTRIBUTES], where=cond)
        if len(entries) <= 0:
            attributeid = self._GetNextID(TABLE_NAME_ATTRIBUTES, COL_NAME_ATTRIBUTES_LBATTRID)
            attribute[COL_NAME_ATTRIBUTES_LBATTRID] = attributeid
            self.add_generic_data(attribute, TABLE_NAME_ATTRIBUTES)
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("attribute '%s' exists already in the generic label database"
                                  % attribute[COL_NAME_ATTRIBUTES_LBATTNAMEID])
            else:
                self._log.warning("attribute '%s' already exists in the generic label database."
                                  % attribute[COL_NAME_ATTRIBUTES_LBATTNAMEID])
                if len(entries) == 1:
                    attributeid = entries[0][COL_NAME_ATTRIBUTES_LBATTRID]
                elif len(entries) > 1:
                    raise AdasDBError("attribute name '%s' cannot be resolved because it is ambiguous. (%s)"
                                      % (attribute[COL_NAME_ATTRIBUTES_LBATTNAMEID], entries))
        # done
        return attributeid

    def add_attribute_to_label_id(self, labelid, name, value, value_type_id=None, value_unit_id=None):
        """
        Add attribute to database and link it to label with id.

        :param labelid: the label id.
        :type labelid: int
        :param name: the name of the attibute
        :param value: The value of the attribute
        :type value: float
        :param value_type_id: Value type id corresponding to Value type registered in GBL_VALTYPES
        :type value_type_id: int
        :param value_unit_id: Unit Id for corresponding quantity registered in GBL_UNITS. Default No Unit
        :type value_unit_id: int
        :return: Returns the id of newly inserted attibute
        :rtype: int
        """

        attributeid = -1
        label = self.get_detailed_generic_label(labelid)
        if len(label) > 0:
            attr_name = self.get_attribute_name(name)
            # if name does not exits add attibute name
            if len(attr_name) == 0:
                attr_name_id = self.add_attribute_name(name)
            else:
                attr_name_id = attr_name[COL_NAME_ATTR_NAMES_LBATTNAMEID]

            attribute = {COL_NAME_ATTRIBUTES_LBID: labelid, COL_NAME_ATTRIBUTES_LBATTNAMEID: attr_name_id,
                         COL_NAME_ATTRIBUTES_VALUE: value}
            if value_type_id is not None:
                attribute[COL_NAME_ATTRIBUTES_VTID] = value_type_id
            if value_unit_id is not None:
                attribute[COL_NAME_ATTRIBUTES_UNITID] = value_unit_id

            attributeid = self.add_attribute(attribute)
        else:
            self._log.warning("label id '%s' does not exists in the generic label database." % labelid)
        return attributeid

    def update_attribute(self, attribute, where=None):
        """
        Update existing attribute records.

        :param attribute: The attribute record update wit new values
        :type attribute: dict
        :param where: The condition to be fulfilled by the attribute to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected attribute.
        :rtype: int
        """
        rowcount = 0

        if (attribute is not None) and (len(attribute) != 0):
            rowcount = self.update_generic_data(attribute, TABLE_NAME_ATTRIBUTES, where)
        # done
        return rowcount

    def delete_attribute(self, attribute):
        """
        Delete existing attribute records.

        :param attribute: The attribute record update wit new values
        :type attribute: dict
        :return: Returns the number of affected attribute.
        :rtype: int
        """
        rowcount = 0
        if (attribute is not None) and (len(attribute) != 0):
            cond = get_attibute_condition(attribute[COL_NAME_ATTRIBUTES_LBID],
                                          attribute[COL_NAME_ATTRIBUTES_LBATTNAMEID])
            rowcount = self.delete_generic_data(TABLE_NAME_ATTRIBUTES, where=cond)
        # done
        return rowcount

    def get_attribute_with_name(self, labelid, name):
        """
        Get existing attribute records for given labelid and name

        :param labelid: The labelid.
        :type labelid: int
        :param name: The attribute name.
        :type name: str
        :return: Returns the attribute record.
        :rtype: list
        """
        record = {}
        tables = []
        tblattr = TABLE_NAME_ATTRIBUTES
        tblattrnames = TABLE_NAME_ATTRIBUTE_NAMES
        tables.append(SQLJoinExpr(SQLTableExpr(TABLE_NAME_ATTRIBUTES),
                                  OP_INNER_JOIN,
                                  SQLTableExpr(TABLE_NAME_ATTRIBUTE_NAMES),
                                  SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblattr),
                                                              COL_NAME_ATTRIBUTES_LBATTNAMEID),
                                                OP_EQ,
                                                SQLColumnExpr(SQLTableExpr(tblattrnames),
                                                              COL_NAME_ATTR_NAMES_LBATTNAMEID))))

        cond = SQLBinaryExpr(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblattr),
                                                         COL_NAME_ATTRIBUTES_LBID), OP_EQ, SQLLiteral(labelid)),
                             OP_AND,
                             SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblattrnames), COL_NAME_ATTRIBUTES_LBID),
                                           OP_EQ, SQLLiteral(name.lower())))

        select_list = [SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblattrnames), COL_NAME_ATTR_NAMES_NAME),
                                     OP_AS, COL_NAME_ATTR_NAMES_NAME),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblattr), COL_NAME_ATTRIBUTES_UNITID),
                                     OP_AS, COL_NAME_ATTRIBUTES_UNITID),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblattr), COL_NAME_ATTRIBUTES_VTID),
                                     OP_AS, COL_NAME_ATTRIBUTES_VTID),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblattr), COL_NAME_ATTRIBUTES_VALUE),
                                     OP_AS, COL_NAME_ATTRIBUTES_VALUE)]

        entries = self.select_generic_data(select_list=select_list, table_list=tables, where=cond)
        if len(entries) <= 0:
            self._log.warning("Attribute with name '%s' does not exists in the generic label database." % name)
        elif len(entries) > 1:
            self._log.warning("Attribute with name '%s' cannot be resolved because it is ambiguous. (%s)"
                              % (name, entries))
        else:
            record = entries[0]
        # done
        return record

    def get_attributes(self, labelid):
        """
        Get existing attribute records for given Label Id

        :param labelid: The labelid.
        :type labelid: int
        :return: Returns the attribute record.
        :rtype: list
        """
        record = {}
        # check if label exists
        label = self.get_generic_label(labelid)
        if len(label) >= 0:

            cond = get_attibute_condition(labelid)

            entries = self.select_generic_data(table_list=[TABLE_NAME_ATTRIBUTES], where=cond)
            if len(entries) <= 0:
                self._log.warning("Attribute with label id '%s' does not exists in the generic label database."
                                  % labelid)
            else:
                record = entries
        else:
            self._log.warning("Label with id '%s' does not exists in the generic label database" % labelid)
        # done
        return record

    # ====================================================================
    # Handling of label attribute Names
    # ====================================================================
    def add_attribute_name(self, name):
        """
        Add attribute to database.

        :param name: The attribute Name
        :type name: str
        :return: Returns the attribute ID.
        :rtype: int
        """
        attr_name_id = None
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                             COL_NAME_ATTR_NAMES_NAME), OP_EQ, SQLLiteral(name.lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_ATTRIBUTE_NAMES], where=cond)
        attr_name = {}
        if len(entries) <= 0:
            attr_name_id = self._GetNextID(TABLE_NAME_ATTRIBUTE_NAMES, COL_NAME_ATTR_NAMES_LBATTNAMEID)
            attr_name[COL_NAME_ATTR_NAMES_NAME] = name
            attr_name[COL_NAME_ATTR_NAMES_LBATTNAMEID] = attr_name_id
            self.add_generic_data(attr_name, TABLE_NAME_ATTRIBUTE_NAMES)
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("attribute name '%s' exists already in the generic label database" % name)
            else:
                self._log.warning("attribute name '%s' already exists in the generic label database." % name)
                if len(entries) == 1:
                    attr_name_id = entries[0][COL_NAME_ATTR_NAMES_LBATTNAMEID]
                elif len(entries) > 1:
                    raise AdasDBError("attribute name '%s' cannot be resolved because it is ambiguous. (%s)" %
                                      (name, entries))
        # done
        return attr_name_id

    def update_attribute_name(self, attribute, where=None):
        """
        Update existing attribute Name records.

        :param attribute: The attribute record update with new values.
        :type attribute: dict
        :param where: The condition to be fulfilled by the attribute for update
        :return: SQLBinaryExpression
        """
        rowcount = 0

        if attribute is not None and len(attribute) != 0:
            rowcount = self.update_generic_data(attribute, TABLE_NAME_ATTRIBUTE_NAMES, where)
        # done
        return rowcount

    def delete_attribute_name(self, attribute):
        """
        Delete existing attribute Name records.

        :param attribute: The attribute record to be deleted.
        :type attribute: dict
        :return: Returns the number of affected attribute.
        :rtype: int
        """
        rowcount = 0
        if (attribute is not None) and (len(attribute) != 0):
            cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             TABLE_NAME_ATTRIBUTE_NAMES),
                                 OP_EQ, SQLLiteral(attribute[COL_NAME_ATTR_NAMES_NAME].lower()))
            rowcount = self.delete_generic_data(TABLE_NAME_ATTRIBUTES, where=cond)
        # done
        return rowcount

    def get_attribute_name(self, name):
        """
        Get existing attribute name Record

        :param name: The attribute name.
        :type name: str
        :return: Returns the attribute record.
        :rtype: dict
        """
        record = {}
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         COL_NAME_ATTR_NAMES_NAME),
                             OP_EQ, SQLLiteral(name.lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_ATTRIBUTE_NAMES], where=cond)
        if len(entries) <= 0:
            self._log.warning("Attribute name '%s' does not exists in the generic label database." % name)
        elif len(entries) > 1:
            self._log.warning("Attribute name '%s' cannot be resolved because it is ambiguous. (%s)" % (name, entries))
        else:
            record = entries[0]
        # done
        return record

    # ====================================================================
    # Handling of generic labels
    # ====================================================================
    def add_generic_label(self, label):
        """
        Add label to database.

        :param label: The label record.
        :type label: dict
        :return: Returns the label ID.
        :rtype: int
        """
        cond = SQLBinaryExpr(COL_NAME_LABELS_ABSTS, OP_EQ, label[COL_NAME_LABELS_ABSTS])

        # and meas id
        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_LABELS_MEASID, OP_EQ, label[COL_NAME_LABELS_MEASID]))
        # and typeid
        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_LABELS_TYPEID, OP_EQ, label[COL_NAME_LABELS_TYPEID]))

        labelid = None
        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)
        if len(entries) <= 0:
            labelid = self._GetNextID(TABLE_NAME_LABELS, COL_NAME_LABELS_LBID)
            label[COL_NAME_LABELS_LBID] = labelid
            self.add_generic_data(label, TABLE_NAME_LABELS)
        else:
            tmp = "Label with TS '%s' exists already in the generic label database" % label[COL_NAME_LABELS_ABSTS]
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    labelid = entries[0][COL_NAME_ATTRIBUTES_LBID]
                elif len(entries) > 1:
                    tmp = "Label with TS '%s' " % (label[COL_NAME_LABELS_ABSTS])
                    tmp += "cannot be resolved because it is ambiguous. "
                    tmp += "(%s)" % entries
                    raise AdasDBError(tmp)
        # done
        return labelid

    def add_generic_recording_label(self, label):
        """
        Add a label for the recording to database, the timestamp for recording labels is always -1.

        :param label: The label record.
        :type label: dict
        :return: Returns the label ID of newly inserted record
        :rtype: int
        """
        # state id
        cond = SQLBinaryExpr(COL_NAME_LABELS_STATEID, OP_EQ, label[COL_NAME_LABELS_STATEID])

        # and meas id
        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_LABELS_MEASID, OP_EQ, label[COL_NAME_LABELS_MEASID]))
        # and typeid
        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_LABELS_TYPEID, OP_EQ, label[COL_NAME_LABELS_TYPEID]))

        labelid = None
        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)
        if len(entries) <= 0:
            labelid = self._GetNextID(TABLE_NAME_LABELS, COL_NAME_LABELS_LBID)
            label[COL_NAME_LABELS_LBID] = labelid
            label[COL_NAME_LABELS_ABSTS] = -1
            self.add_generic_data(label, TABLE_NAME_LABELS)
        else:
            tmp = "Label with state '%s', " % (label[COL_NAME_LABELS_STATEID])
            tmp += "type '%s' and " % (label[COL_NAME_LABELS_TYPEID])
            tmp += "measid '%s' exists " % (label[COL_NAME_LABELS_MEASID])
            tmp += "already in the generic label database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    labelid = entries[0][COL_NAME_ATTRIBUTES_LBID]
                elif len(entries) > 1:
                    tmp = "Label with state '%s', " % (label[COL_NAME_LABELS_STATEID])
                    tmp += "type '%s' " % (label[COL_NAME_LABELS_TYPEID])
                    tmp += "and measid '%s' " % (label[COL_NAME_LABELS_MEASID])
                    tmp += "cannot be resolved because it is ambiguous. "
                    tmp += "(%s)" % entries
                    raise AdasDBError(tmp)
        # done
        return labelid

    def update_generic_label(self, label, where=None):
        """
        Update existing label records.

        :param label: The label record update.
        :type label: dict
        :param where: The condition to be fulfilled by the label to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected label.
        :rtype: int
        """
        rowcount = 0

        if (label is not None) and (len(label) != 0):
            rowcount = self.update_generic_data(label, TABLE_NAME_LABELS, where)
        # done
        return rowcount

    def delete_generic_label(self, label):
        """
        Delete existing label records.

        :param label: The label record update.
        :type label: dict
        :return: Returns the number of affected label.
        :rtype: int
        """
        rowcount = 0
        if (label is not None) and (len(label) != 0):
            if label[COL_NAME_LABELS_LBID] is not None:
                cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, label[COL_NAME_LABELS_LBID])
            else:
                cond = SQLBinaryExpr(COL_NAME_LABELS_ABSTS, OP_EQ, label[COL_NAME_LABELS_ABSTS])

            # and meas id
            cond = SQLBinaryExpr(cond, OP_AND,
                                 SQLBinaryExpr(COL_NAME_LABELS_MEASID, OP_EQ, label[COL_NAME_LABELS_MEASID]))
            # and typeid
            cond = SQLBinaryExpr(cond, OP_AND,
                                 SQLBinaryExpr(COL_NAME_LABELS_TYPEID, OP_EQ, label[COL_NAME_LABELS_TYPEID]))

            rowcount = self.delete_generic_data(TABLE_NAME_LABELS, where=cond)
        # done
        return rowcount

    def delete_generic_label_with_label_id(self, labelid):  # pylint: disable=C0103
        """
        Delete existing and attributes label records with label id

        :param labelid: Label Id
        :type labelid: int
        :return: Returns the number of affected label.
        :rtype: int
        """

        # Delete Attributes
        attributes = self.get_attributes(labelid)
        for attribute in attributes:
            self.delete_attribute(attribute)
        # Delete Label
        rowcount = self.delete_generic_label(self.get_generic_label(labelid))

        # done
        return rowcount

    def get_generic_label(self, labelid):
        """
        Get existing generic label record.

        :param labelid: The id of the label.
        :type labelid: int
        :return: Returns the label record.
        :rtype: dict
        """
        record = {}
        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)

        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)
        if len(entries) <= 0:
            self._log.warning("Label with ID '%s' does not exists in the generic label database." % labelid)
        elif len(entries) > 1:
            self._log.warning("Label with ID '%s' cannot be resolved because it is ambiguous. (%s)"
                              % (labelid, entries))
        else:
            record = entries[0]
        # done
        return record

    def get_detailed_generic_label(self, labelid):
        """
        Get existing detailed generic label record which include timestamp, label type, label state, value

        :param labelid: The id of the label.
        :type labelid: int
        :return: Returns the label record.
        :rtype: dict
        """
        record = {}

        tables = []

        tbl_lab = TABLE_NAME_LABELS

        type_join = SQLJoinExpr(SQLTableExpr(tbl_lab),
                                OP_INNER_JOIN,
                                SQLTableExpr(TABLE_NAME_TYPES),
                                SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tbl_lab),
                                                            COL_NAME_LABELS_TYPEID),
                                              OP_EQ,
                                              SQLColumnExpr(SQLTableExpr(TABLE_NAME_TYPES),
                                                            COL_NAME_TYPES_TYPEID)))

        tables.append(SQLJoinExpr(SQLTableExpr(type_join),
                                  OP_INNER_JOIN,
                                  SQLTableExpr(TABLE_NAME_STATES),
                                  SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tbl_lab), COL_NAME_LABELS_STATEID),
                                                OP_EQ,
                                                SQLColumnExpr(SQLTableExpr(TABLE_NAME_STATES),
                                                              COL_NAME_STATES_STATEID))))

        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         SQLColumnExpr(SQLTableExpr(TABLE_NAME_LABELS),
                                                       COL_NAME_LABELS_LBID)),
                             OP_EQ,
                             SQLLiteral(labelid))

        select_list = [SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_LABELS), COL_NAME_LABELS_ABSTS),
                                     OP_AS, COL_NAME_LABELS_ABSTS),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_TYPES), COL_NAME_TYPES_NAME),
                                     OP_AS, "TYPE"),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_STATES), COL_NAME_STATES_NAME),
                                     OP_AS, "STATE"),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_STATES), COL_NAME_STATES_VALUE),
                                     OP_AS, COL_NAME_STATES_VALUE)]

        entries = self.select_generic_data(select_list=select_list, table_list=tables, where=cond)
        if len(entries) <= 0:
            self._log.warning("Label with ID '%s' does not exists in the generic label database." % labelid)
        elif len(entries) > 1:
            self._log.warning("Label with ID '%s' cannot be resolved because it is ambiguous. (%s)"
                              % (labelid, entries))
        else:
            record = entries[0]
        # done
        return record

    def get_generic_labels_ids_with_meas_id_and_type(self, measid, typename=None):  # pylint: disable=C0103
        """
        Get the Label Id for given measurement Id and optionally with Label Type name

        :param measid: The rec file measurement ID.
        :type measid: int
        :param typename: opt. name of the label type. Default All type name
        :type typename: str
        :return: Returns the label ID's.
        :rtype: list
        """
        labelids = None

        tables = []
        tbl_labels = TABLE_NAME_LABELS
        tbl_types = TABLE_NAME_TYPES
        tables.append(SQLJoinExpr(SQLTableExpr(tbl_labels),
                                  OP_INNER_JOIN,
                                  SQLTableExpr(TABLE_NAME_TYPES),
                                  SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tbl_labels), COL_NAME_LABELS_TYPEID),
                                                OP_EQ,
                                                SQLColumnExpr(SQLTableExpr(tbl_types),
                                                              COL_NAME_TYPES_TYPEID))))

        if typename is None:
            cond = SQLBinaryExpr(COL_NAME_LABELS_MEASID, OP_EQ, measid)
        else:
            cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_LABELS_MEASID, OP_EQ, measid),
                                 OP_AND,
                                 SQLBinaryExpr(COL_NAME_TYPES_NAME, OP_EQ, SQLLiteral(typename)))

        entries = self.select_generic_data(table_list=tables, where=cond)

        if len(entries) > 0:
            labelids = []
            for item in range(len(entries)):
                labelids.append(entries[item][COL_NAME_LABELS_LBID])
        # done
        return labelids

    def has_generic_labels_state_value(self, measid, typename):
        """
        Check if the generic label data is available for given measurement and label type
        returns boolean true if such label data exists otherwise return false

        :param measid: Measurement Id
        :type measid: int
        :param typename: label type name
        :type typename: str
        :return: Boolean flag true if such value exist otherwise false
        :rtype: bool
        """

        lbl_type_rec = self.get_type(typename)
        if type(lbl_type_rec) is dict:
            lbl_type_id = int(lbl_type_rec[COL_NAME_TYPES_TYPEID])
            cond1 = SQLBinaryExpr(COL_NAME_LABELS_MEASID, OP_EQ, measid)
            cond2 = SQLBinaryExpr(COL_NAME_LABELS_TYPEID, OP_EQ, lbl_type_id)
            cond = SQLBinaryExpr(cond1, OP_AND, cond2)
            tables = [TABLE_NAME_LABELS]
            select_list = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MIN],
                                                    COL_NAME_LABELS_LBID), OP_AS, COL_NAME_LABELS_LBID)
            entries = self.select_generic_data(select_list=[select_list], table_list=tables, where=cond)
            return entries[0][COL_NAME_LABELS_LBID] is not None

        else:
            return False

    def get_generic_labels_state_values(self, measid, typename):
        """
        Get the State values of labels with with MEAS ID and type name.

        :param measid: The rec file meas ID.
        :type measid: int
        :param typename: The name of the label type.
        :type typename: str
        :return: Returns the state values/names and timestamps.
        :rtype: dict
        """
        states = None

        tables = []

        label_type_join = "LabelTypeJoin"
        tbl_lab = TABLE_NAME_LABELS
        tbl_types = TABLE_NAME_TYPES
        tables.append(SQLJoinExpr(SQLTableExpr(tbl_lab),
                                  OP_INNER_JOIN,
                                  SQLTableExpr(TABLE_NAME_TYPES),
                                  SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tbl_lab), COL_NAME_LABELS_TYPEID),
                                                OP_EQ,
                                                SQLColumnExpr(SQLTableExpr(tbl_types), COL_NAME_TYPES_TYPEID))))

        cond = SQLBinaryExpr(SQLBinaryExpr(SQLBinaryExpr(COL_NAME_LABELS_MEASID, OP_EQ, measid), OP_AND,
                                           SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tbl_types), COL_NAME_TYPES_NAME),
                                                         OP_EQ, SQLLiteral(typename))),
                             EXPR_ORDER_BY,
                             SQLColumnExpr(SQLTableExpr(tbl_lab), COL_NAME_LABELS_ABSTS))

        subselect = GenericSQLSelect(table_list=tables, where_condition=cond)

        tables = [SQLTableExpr(TABLE_NAME_STATES),
                  SQLTableExpr(SQLBinaryExpr("(", subselect, ")"), table_alias=label_type_join)]

        cond = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_STATES),
                                           COL_NAME_STATES_STATEID),
                             OP_EQ,
                             SQLColumnExpr(SQLTableExpr(label_type_join), COL_NAME_LABELS_STATEID))

        select_list = [SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(label_type_join), COL_NAME_LABELS_ABSTS),
                                     OP_AS, COL_NAME_LABELS_ABSTS),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_STATES), COL_NAME_STATES_NAME),
                                     OP_AS, COL_NAME_STATES_NAME),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_STATES), COL_NAME_STATES_VALUE),
                                     OP_AS, COL_NAME_STATES_VALUE),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(label_type_join), COL_NAME_LABELS_STATEID),
                                     OP_AS, COL_NAME_LABELS_STATEID)]

        entries = self.select_generic_data(select_list=select_list, table_list=tables, where=cond)

        if len(entries) <= 0:
            tmp = "Label with meas id '%s' " % measid
            tmp += "and type '%s' " % typename
            tmp += "doesn't exists in the generic label database."
            self._log.warning(tmp)
        else:
            states = entries
        # done
        return states

    def get_generic_labels_state_value_at_ts(self, measid, typename, absts,  # pylint: disable=C0103
                                             interpolate=False):
        """
        Get the State values of labels with with MEAS ID and type name at abs timestamp.

        :param measid: The rec file Measurement ID.
        :type measid: int
        :param typename: The name of the label type.
        :type typename: str
        :param absts: The absolute timestamp.
        :type absts: int
        :param interpolate: Flag to interpolate in case of exact absolute timestamp is missing
        :type interpolate: bool
        :return: Returns the state values/names label AbsTS.
        :rtype: float or None
        """
        state = None
        states = self.get_generic_labels_state_values(measid, typename)
        if states is not None:
            if absts >= states[len(states) - 1][COL_NAME_LABELS_ABSTS]:
                return states[len(states) - 1]
            for stateidx in range(len(states) - 1):
                if states[stateidx][COL_NAME_LABELS_ABSTS] <= absts <= states[stateidx + 1][COL_NAME_LABELS_ABSTS]:
                    if (interpolate is False or
                            states[stateidx][COL_NAME_STATES_VALUE] is None or
                            states[stateidx + 1][COL_NAME_STATES_VALUE] is None):
                        return states[stateidx]
                    else:
                        valueint = (states[stateidx][COL_NAME_STATES_VALUE] +
                                    (absts - states[stateidx][COL_NAME_LABELS_ABSTS]) *
                                    (states[stateidx + 1][COL_NAME_STATES_VALUE] -
                                     states[stateidx][COL_NAME_STATES_VALUE]) /
                                    (states[stateidx + 1][COL_NAME_LABELS_ABSTS] -
                                     states[stateidx][COL_NAME_LABELS_ABSTS]))
                        ret_value = states[stateidx]
                        ret_value[COL_NAME_STATES_VALUE] = valueint
                        return ret_value

        return state

    def get_generic_label_type(self, labelid):
        """
        Get the Label Type ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :return: Returns the label type ID.
        :rtype: int
        """
        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_LABELS_TYPEID]
        elif len(entries) <= 0:
            raise AdasDBError("Label with id '%s' doesn't exists in the generic label database." % labelid)
        else:
            tmp = "Label with id '%s' cannot be resolved because it is ambiguous. (%s)" % (labelid, entries)
            raise AdasDBError(tmp)

    def set_generic_label_type(self, labelid, typeid):
        """
        Set the Label Type ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :param typeid: The label Type ID.
        :type typeid: int
        :return: Returns the number of affected label.
        :rtype: int
        """
        # rowcount = 0

        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        settings = {COL_NAME_LABELS_TYPEID: typeid}
        rowcount = self.update_generic_data(settings, TABLE_NAME_LABELS, where=cond)
        # done
        return rowcount

    def get_generic_label_workflow(self, labelid):
        """
        Get the Label workflow ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :return: Returns the label workflow ID.
        :rtype: int
        """
        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_LABELS_WFID]
        elif len(entries) <= 0:
            raise AdasDBError("Label with id '%s' doesn't exists in the generic label database." % labelid)
        else:
            tmp = "Label with id '%s' cannot be resolved because it is ambiguous. (%s)" % (labelid, entries)
            raise AdasDBError(tmp)

    def set_generic_label_workflow(self, labelid, workflowid):
        """
        Set the Label workflow ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :param workflowid: The label id
        :type workflowid: int.
        :return: Returns the number of affected label.
        :rtype: int
        """
        # rowcount = 0

        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        settings = {COL_NAME_LABELS_WFID: workflowid}
        rowcount = self.update_generic_data(settings, TABLE_NAME_LABELS, where=cond)
        # done
        return rowcount

    def get_generic_label_state(self, labelid):
        """
        Get the Label state ID for given Label Id.

        :param labelid: The label id.
        :type labelid: int
        :return: Returns the label state ID.
        :rtype: int
        """
        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_LABELS_STATEID]
        elif len(entries) <= 0:
            raise AdasDBError("Label with id '%s' doesn't exists in the generic label database." % labelid)
        else:
            tmp = "Label with id '%s' cannot be resolved because it is ambiguous. (%s)" % (labelid, entries)
            raise AdasDBError(tmp)

    def set_generic_label_state(self, labelid, stateid):
        """
        Get the Label state ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :param stateid: The state id.
        :type stateid: int
        :return: Returns the number of affected label.
        :rtype: int
        """
        # rowcount = 0

        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        settings = {COL_NAME_LABELS_STATEID: stateid}
        rowcount = self.update_generic_data(settings, TABLE_NAME_LABELS, where=cond)
        # done
        return rowcount

    def get_generic_label_user(self, labelid):
        """
        Get the Label user ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :return: Returns the label user ID.
        :rtype: int
        """
        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_LABELS_USERID]
        elif len(entries) <= 0:
            raise AdasDBError("Label with id '%s' doesn't exists in the generic label database." % labelid)
        else:
            tmp = "Label with id '%s' cannot be resolved because it is ambiguous. (%s)" % (labelid, entries)
            raise AdasDBError(tmp)

    def set_generic_label_user(self, labelid, userid):
        """
        Set the Label user ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :param userid: The user id.
        :type userid: int
        :return: Returns the number of affected label.
        :rtype: int
        """
        # rowcount = 0

        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        settings = {COL_NAME_LABELS_USERID: userid}
        rowcount = self.update_generic_data(settings, TABLE_NAME_LABELS, where=cond)
        # done
        return rowcount

    def set_generic_label_timestamp(self, labelid, timestamp):
        """
        Set the Label user ID with Label Id.

        :param labelid: The label id.
        :type labelid: int
        :param timestamp: The Timestamp.
        :type timestamp: int
        :return: Returns the number of affected label.
        :rtype: int
        """
        # rowcount = 0

        cond = SQLBinaryExpr(COL_NAME_LABELS_LBID, OP_EQ, labelid)
        settings = {COL_NAME_LABELS_ABSTS: timestamp}
        rowcount = self.update_generic_data(settings, TABLE_NAME_LABELS, where=cond)
        # done
        return rowcount

    # ====================================================================
    # Handling of rect object map
    # ====================================================================
    @deprecated()
    def add_label_rect_obj_map(self, labelrectobjmap):
        """
        method had coding error and could never have been used

        left to prevent code checking errors if it was somewhere implemented in dead code
        """
        pass

    def update_label_rect_obj_map(self, labelrectobjmap, where=None):
        """
        Update existing LabelRectObjMap records.

        :param labelrectobjmap: The LabelRectObjMap record update.
        :type labelrectobjmap: dict
        :param where: The condition to be fulfilled by the LabelRectObjMap to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected LabelRectObjMap.
        :rtype: int
        """
        rowcount = 0

        if labelrectobjmap is not None and len(labelrectobjmap) != 0:
            rowcount = self.update_generic_data(labelrectobjmap, TABLE_NAME_RECTOBJIDMAP, where)
        # done
        return rowcount

    def delete_label_rect_obj_map(self, labelrectobjmap):
        """
        Delete existing LabelRectObjMap records.

        :param labelrectobjmap: The LabelRectObjMap record update.
        :type labelrectobjmap: dict
        :return: Returns the number of affected LabelRectObjMap.
        :rtype: int
        """
        rowcount = 0
        if labelrectobjmap is not None and len(labelrectobjmap) != 0:
            cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_RECTOBJIDMAP_RECTOBJID, OP_EQ,
                                               labelrectobjmap[COL_NAME_RECTOBJIDMAP_RECTOBJID]),
                                 OP_AND,
                                 SQLBinaryExpr(COL_NAME_RECTOBJIDMAP_LBID, OP_EQ,
                                               labelrectobjmap[COL_NAME_RECTOBJIDMAP_LBID]))
            rowcount = self.delete_generic_data(TABLE_NAME_RECTOBJIDMAP, where=cond)
        # done
        return rowcount

    def get_label_rect_obj_map(self, labelid, rectobjid):
        """
        Get LabelRectObjMap existing attribute records.

        :param labelid: The Label Id.
        :type labelid: int
        :param rectobjid: The Rect Obj Id.
        :type rectobjid: int
        :return: Returns the LabelRectObjMap record.
        :rtype: int
        """
        record = {}
        cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_RECTOBJIDMAP_LBID, OP_EQ, labelid),
                             OP_AND,
                             SQLBinaryExpr(COL_NAME_RECTOBJIDMAP_RECTOBJID, OP_EQ, rectobjid))

        entries = self.select_generic_data(table_list=[TABLE_NAME_RECTOBJIDMAP], where=cond)
        if len(entries) <= 0:
            tmp = "LabelRectObjMap with labelid '%s' " % labelid
            tmp += "and RectObjID '%s' " % rectobjid
            tmp += "does not exists in the generic label database."
            self._log.warning(tmp)
        elif len(entries) > 1:
            tmp = "LabelRectObjMap with labelid '%s' " % labelid
            tmp += "and RectObjID '%s' " % rectobjid
            tmp += "cannot be resolved because it is ambiguous. "
            tmp += "(%s)" % entries
            self._log.warning(tmp)
        else:
            record = entries[0]
        # done
        return record

    def get_rect_obj_ids_linked_to_label(self, labelid):  # pylint: disable=C0103
        """
        Get Rect Objects Linked to Label with ID.

        :param labelid: The Label ID.
        :type labelid: int
        :return: Returns the Rect Obj Id(s) linked to the Label.
        :rtype: list of int
        """
        record = {}
        cond = SQLBinaryExpr(COL_NAME_RECTOBJIDMAP_LBID, OP_EQ, labelid)

        select_list = [COL_NAME_RECTOBJIDMAP_RECTOBJID]
        entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_RECTOBJIDMAP], where=cond)
        if len(entries) <= 0:
            self._log.warning("labelid with name '%s' does not exists in the generic label database." % labelid)
        elif len(entries) >= 1:
            record = entries
        # done
        return record

    def get_label_ids_linked_to_rect_obj(self, rectobjid):  # pylint: disable=C0103
        """
        Get Labels Linked to Rect Obj with ID.

        :param rectobjid: The Rect Object Id
        :type rectobjid: int
        :return: Returns the Label Id(s) linked to the rectobjid.
        :rtype: list
        """
        record = {}
        cond = SQLBinaryExpr(COL_NAME_RECTOBJIDMAP_RECTOBJID, OP_EQ, rectobjid)

        select_list = [COL_NAME_RECTOBJIDMAP_LBID]
        entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_RECTOBJIDMAP], where=cond)
        if len(entries) <= 0:
            self._log.warning("RectObjID with name '%s' does not exists in the generic label database." % rectobjid)
        elif len(entries) >= 1:
            record = entries
        # done
        return record

    # ====================================================================
    # Handling of workflow
    # ====================================================================
    def add_additional_info(self, lbid, desc):
        """
        Add Additional Info for an existing label.

        :param lbid: Label ID
        :type lbid: int
        :param desc: Info Text
        :type desc: str
        """
        cond = get_add_label_info_condition(lbid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_LABELS], where=cond)

        if len(entries) <= 0:
            raise AdasDBError("Label with ID '%i' doesn't exist in the generic label database" % lbid)
        else:
            if desc is None or desc == "":
                raise AdasDBError("Additional Text Info is not defined")

            rec = {COL_NAME_INFO_ID: lbid, COL_NAME_INFO_DESC: desc}
            self.add_generic_data(rec, TABLE_NAME_ADDINFO)

    def update_additional_info(self, lbid, desc):
        """
        Update existing label info  records.

        :param lbid: The Label ID record update.
        :type lbid: int
        :param desc: Info Text
        :type desc: str
        :return: Returns the number of affected workflow.
        :rtype: int
        """
        cond = get_add_label_info_condition(lbid)

        entries = self.select_generic_data(table_list=[TABLE_NAME_ADDINFO], where=cond)
        if len(entries) == 0:
            raise AdasDBError("Additional Info for Label with ID '%i' doesn't exist in the generic label database.",
                              lbid)
        elif len(entries) > 1:
            raise AdasDBError("Additional Info for Label with ID '%i' cannot be resolved because it is ambiguous.",
                              lbid)

        rec = {COL_NAME_INFO_ID: lbid, COL_NAME_INFO_DESC: desc}
        rowcount = self.update_generic_data(rec, TABLE_NAME_ADDINFO, where=cond)
        return rowcount

    def delete_additional_info(self, lbid):
        """
        Delete existing label info.

        :param lbid: Label ID
        :type lbid: int
        :return: Returns the number of affected label info entries
        :rtype: int
        """
        cond = get_add_label_info_condition(lbid)
        return self.delete_generic_data(TABLE_NAME_ADDINFO, where=cond)

    def get_additional_info(self, lbid):
        """
        Get existing addional info of label.

        :param lbid: Label ID
        :type lbid: int
        :return: Returns the workflow record.
        :rtype: int
        """
        cond = get_add_label_info_condition(lbid)
        return self.select_generic_data(table_list=[TABLE_NAME_ADDINFO], where=cond)

    def get_cam_caliberation(self, measid, typeid=None, absts=None):
        """
        Get Camera Caliberation Data

        :param measid: Measurement Id
        :type measid: integer
        :param typeid: cam caliberation type id corresponding to e.g. mac, sac
        :type typeid: integer
        :param absts: Absolute time stamp
        :type absts: integer
        :return: list of records
        :rtype: list
        """
        cond = SQLBinaryExpr(COL_NAME_CAMCALIBERATIONS_MEASID, OP_EQ, measid)
        if typeid is not None:
            cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_CAMCALIBERATIONS_TYPEID, OP_EQ, typeid))

        if absts is not None:
            cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_CAMCALIBERATIONS_ABSTS, OP_EQ, absts))

        return self.select_generic_data(table_list=[TABLE_NAME_CAMCALIBERATIONS], where=cond)

    def add_cam_caliberation(self, camcalib_record):
        """
        Add Camera Caliberation record(s). If the list of record provided then reocrd will be insert using prepared
        statement

        :param camcalib_record: dictionary representing record to be insert
        :type camcalib_record: dict or list of dict
        """
        if type(camcalib_record) is list:
            self.add_generic_data_prepared(camcalib_record, TABLE_NAME_CAMCALIBERATIONS)
        else:
            self.add_generic_data(camcalib_record, TABLE_NAME_CAMCALIBERATIONS)

    def delete_cam_caliberation(self, measid, typeid=None):
        """
        Delete Cameria Caliberation data for given measurement Id and Typeid

        :param measid: Measurement Id
        :type measid: int
        :param typeid: tyepid for camera caliberation e.g. mac sac
        :type typeid: int
        :return: number of deleted entries if supported by DB (SQLite always returns 0)
        :rtype: int
        """

        cond = SQLBinaryExpr(COL_NAME_CAMCALIBERATIONS_MEASID, OP_EQ, measid)
        if typeid is not None:
            cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_CAMCALIBERATIONS_TYPEID, OP_EQ, typeid))

        return self.delete_generic_data(TABLE_NAME_CAMCALIBERATIONS, where=cond)

    # =================================================================================================================
    # deprecated methods
    # =================================================================================================================

    @deprecated('add_state')
    def AddState(self, state):  # pylint: disable=C0103
        """deprecated"""
        return self.add_state(state)

    @deprecated('update_state')
    def UpdateState(self, state, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_state(state, where)

    @deprecated('delete_state')
    def DeleteState(self, state):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_state(state)

    @deprecated('get_state')
    def GetState(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state(name)

    @deprecated('get_state_id')
    def GetStateID(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_id(name)

    @deprecated('stateid')
    def GetStateValue(self, stateid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_value(stateid)

    @deprecated('get_state_name')
    def GetStateName(self, stateid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_name(stateid)

    @deprecated('get_state_names_uvalues')
    def GetStateNamesUValues(self, TypeID):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_names_uvalues(TypeID)

    @deprecated('add_type')
    def AddType(self, recType):  # pylint: disable=C0103
        """deprecated"""
        return self.add_type(recType)

    @deprecated('update_type')
    def UpdateType(self, recType, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_type(recType, where)

    @deprecated('get_type')
    def GetType(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_type(name)

    @deprecated('delete_type')
    def DeleteType(self, recType):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_type(recType)

    def GetTypeNameWithID(self, TypeID):  # pylint: disable=C0103
        """deprecated"""
        return self.get_type_name_with_id(TypeID)

    def GetTypesNames(self, parent_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_types_names(parent_name)

    def AddAttribute(self, attribute):  # pylint: disable=C0103
        """deprecated"""
        return self.add_attribute(attribute)

    def AddAttributeToLabelId(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.add_attribute_to_label_id(*args, **kw)

    def GetAttributes(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_attributes(labelid)

    def UpdateAttribute(self, attribute, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_attribute(attribute, where)

    def DeleteAttribute(self, attribute):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_attribute(attribute)

    def GetAttributeWithName(self, labelid, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_attribute_with_name(labelid, name)

    def AddAttributeName(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.add_attribute_name(name)

    def UpdateAttributeName(self, attribute, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_attribute_name(attribute, where)

    def DeleteAttributeName(self, attribute):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_attribute_name(attribute)

    def GetAttributeName(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_attribute_name(name)

    def AddGenericLabel(self, label):  # pylint: disable=C0103
        """deprecated"""
        return self.add_generic_label(label)

    def AddGenericRecordingLabel(self, label):  # pylint: disable=C0103
        """deprecated"""
        return self.add_generic_recording_label(label)

    def UpdateGenericLabel(self, label, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_generic_label(label, where)

    def DeleteGenericLabel(self, label):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_generic_label(label)

    def DeleteGenericLabelWithLabelID(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_generic_label_with_label_id(labelid)

    def GetGenericLabel(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_generic_label(labelid)

    def GetDetailedGenericLabel(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_detailed_generic_label(labelid)

    def GetGenericLabelsIDsWithMeasIDAndType(self, MeasID, TypeName=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_generic_labels_ids_with_meas_id_and_type(MeasID, TypeName)

    def HasGenericLabelsStateValue(self, MeasID, TypeName):  # pylint: disable=C0103
        """deprecated"""
        return self.has_generic_labels_state_value(MeasID, TypeName)

    def GetGenericLabelsStateValues(self, MeasID, TypeName):  # pylint: disable=C0103
        """deprecated"""
        return self.get_generic_labels_state_values(MeasID, TypeName)

    def GetGenericLabelsStateValueAtTS(self, MeasID, TypeName, AbsTS, interpolate=False):  # pylint: disable=C0103
        """deprecated"""
        return self.get_generic_labels_state_value_at_ts(MeasID, TypeName, AbsTS, interpolate)

    def GetGenericLabelType(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_generic_label_type(labelid)

    def SetGenericLabelType(self, labelid, TypeID):  # pylint: disable=C0103
        """deprecated"""
        return self.set_generic_label_type(labelid, TypeID)

    def GetGenericLabelWorkflow(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_generic_label_workflow(labelid)

    def SetGenericLabelWorkflow(self, labelid, WorkflowID):  # pylint: disable=C0103
        """deprecated"""
        return self.set_generic_label_workflow(labelid, WorkflowID)

    def GetGenericLabelState(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_generic_label_state(labelid)

    def SetGenericLabelState(self, labelid, StateID):  # pylint: disable=C0103
        """deprecated"""
        return self.set_generic_label_state(labelid, StateID)

    def GetGenericLabelUser(self, labelid):  # pylint: disable=C0103
        """deprecatd"""
        return self.get_generic_label_user(labelid)

    def SetGenericLabelUser(self, labelid, userid):  # pylint: disable=C0103
        """deprecated"""
        return self.set_generic_label_user(labelid, userid)

    def SetGenericLabelTimestamp(self, labelid, Timestamp):  # pylint: disable=C0103
        """deprecated"""
        return self.set_generic_label_timestamp(labelid, Timestamp)

    def AddLabelRectObjMap(self, LabelRectObjMap):  # pylint: disable=C0103
        """deprecated"""
        return self.add_label_rect_obj_map(LabelRectObjMap)

    def UpdateLabelRectObjMap(self, LabelRectObjMap, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_label_rect_obj_map(LabelRectObjMap, where)

    def DeleteLabelRectObjMap(self, LabelRectObjMap):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_label_rect_obj_map(LabelRectObjMap)

    def GetLabelRectObjMap(self, labelid, RectObjID):  # pylint: disable=C0103
        """deprecated"""
        return self.get_label_rect_obj_map(labelid, RectObjID)

    def GetRectObjIdsLinkedToLabel(self, labelid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_rect_obj_ids_linked_to_label(labelid)

    def GetLabelIdsLinkedToRectObj(self, RectObjID):  # pylint: disable=C0103
        """deprecated"""
        return self.get_label_ids_linked_to_rect_obj(RectObjID)

    def AddAdditionalInfo(self, lbid, desc):  # pylint: disable=C0103
        """deprecated"""
        return self.add_additional_info(lbid, desc)

    def UpdateAdditionalInfo(self, lbid, desc):  # pylint: disable=C0103
        """deprecated"""
        return self.update_additional_info(lbid, desc)

    def DeleteAdditionalInfo(self, lbid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_additional_info(lbid)

    def GetAdditionalInfo(self, lbid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_additional_info(lbid)

    def GetCamCaliberation(self, measid, typeid=None, absts=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_cam_caliberation(measid, typeid, absts)

    def AddCamCaliberation(self, camcalib_record):  # pylint: disable=C0103
        """deprecated"""
        return self.add_cam_caliberation(camcalib_record)

    def DeleteCamCaliberation(self, measid, typeid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_cam_caliberation(measid, typeid)

    def _GetNextID(self, table_name, col_name):  # pylint: disable=C0103
        """deprecated"""
        return self._get_next_id(table_name, col_name)


# ====================================================================
# Constraint DB Libary SQL Server Compact Implementation
# ====================================================================
class PluginGenLabelDB(BaseGenLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseGenLabelDB.__init__(self, *args, **kwargs)


class SQLCEGenLabelDB(BaseGenLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseGenLabelDB.__init__(self, *args, **kwargs)


class OracleGenLabelDB(BaseGenLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseGenLabelDB.__init__(self, *args, **kwargs)


class SQLite3GenLabelDB(BaseGenLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseGenLabelDB.__init__(self, *args, **kwargs)


"""
$Log: genlabel.py  $
Revision 1.8 2017/08/25 15:47:09CEST Hospes, Gerd-Joachim (uidv8815) 
static check fixes
Revision 1.7 2016/08/16 16:24:12CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.6 2016/08/16 16:01:43CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.5 2016/08/16 12:26:26CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.4 2016/02/05 16:24:26CET Hospes, Gerd-Joachim (uidv8815)
removed warning,
also removed errogenous code in add_label_rect_obj_map()
Revision 1.3 2015/07/14 13:16:07CEST Mertens, Sven (uidv7805)
reverting some changes
--- Added comments ---  uidv7805 [Jul 14, 2015 1:16:08 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/07/14 09:30:52CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:30:53 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:04:10CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/lbl/project.pj
Revision 1.31 2015/03/09 11:52:15CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:15 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.30 2015/03/05 14:17:40CET Mertens, Sven (uidv7805)
fix for parameter
--- Added comments ---  uidv7805 [Mar 5, 2015 2:17:41 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.29 2015/01/19 11:29:27CET Ahmed, Zaheer (uidu7634)
Bug fix in get_generic_label_type() to return label type id
--- Added comments ---  uidu7634 [Jan 19, 2015 11:29:27 AM CET]
Change Package : 283678:1 http://mks-psad:7002/im/viewissue?selection=283678
Revision 1.28 2014/12/08 10:03:13CET Mertens, Sven (uidv7805)
removing duplicate get_next_id
--- Added comments ---  uidv7805 [Dec 8, 2014 10:03:14 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.27 2014/11/17 08:10:39CET Mertens, Sven (uidv7805)
name updates
Revision 1.26 2014/10/10 08:51:49CEST Hecker, Robert (heckerr)
Updates in naming convensions.
--- Added comments ---  heckerr [Oct 10, 2014 8:51:50 AM CEST]
Change Package : 270868:1 http://mks-psad:7002/im/viewissue?selection=270868
Revision 1.25 2014/10/06 15:43:07CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Oct 6, 2014 3:43:07 PM CEST]
Change Package : 245347:1 http://mks-psad:7002/im/viewissue?selection=245347
Revision 1.24 2014/09/25 13:31:32CEST Ahmed, Zaheer (uidu7634)
bug fix add missing op_eq in sql binary expression
--- Added comments ---  uidu7634 [Sep 25, 2014 1:31:33 PM CEST]
Change Package : 260444:2 http://mks-psad:7002/im/viewissue?selection=260444
Revision 1.23 2014/09/22 12:58:11CEST Ahmed, Zaheer (uidu7634)
bug fix remove sql literal over measurement Id column
--- Added comments ---  uidu7634 [Sep 22, 2014 12:58:12 PM CEST]
Change Package : 241665:3 http://mks-psad:7002/im/viewissue?selection=241665
Revision 1.22 2014/07/30 13:59:37CEST Ahmed, Zaheer (uidu7634)
Add new function GetCamCaliberation()  AddCamCaliberation() DeleteCamCaliberation()
--- Added comments ---  uidu7634 [Jul 30, 2014 1:59:38 PM CEST]
Change Package : 241665:1 http://mks-psad:7002/im/viewissue?selection=241665
Revision 1.21 2014/06/30 17:53:50CEST Ahmed, Zaheer (uidu7634)
Suppressing Warning/error which are flooding log file too many messages
raodtype label and default assessment warning message
--- Added comments ---  uidu7634 [Jun 30, 2014 5:53:51 PM CEST]
Change Package : 243816:1 http://mks-psad:7002/im/viewissue?selection=243816
Revision 1.20 2014/06/24 10:34:18CEST Mertens, Sven (uidv7805)
alignment db_common / rec cat manager
--- Added comments ---  uidv7805 [Jun 24, 2014 10:34:18 AM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.19 2013/05/29 13:26:51CEST Mertens, Sven (uidv7805)
removing pylint errors locally
--- Added comments ---  uidv7805 [May 29, 2013 1:26:51 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.18 2013/04/26 15:39:13CEST Mertens, Sven (uidv7805)
resolving some pep8 / pylint errors
--- Added comments ---  uidv7805 [Apr 26, 2013 3:39:13 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.17 2013/04/26 10:46:05CEST Mertens, Sven (uidv7805)
moving strIdent
Revision 1.16 2013/04/25 14:35:15CEST Mertens, Sven (uidv7805)
epydoc adaptation to colon instead of at
Revision 1.14 2013/04/12 14:37:10CEST Mertens, Sven (uidv7805)
adding a short representation used by db_connector.PostInitialize
Revision 1.13 2013/04/02 10:25:02CEST Mertens, Sven (uidv7805)
pylint: E0213, E1123, E9900, E9904, E1003, E9905, E1103
--- Added comments ---  uidv7805 [Apr 2, 2013 10:25:03 AM CEST]
Change Package : 176171:9 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.12 2013/03/27 11:37:23CET Mertens, Sven (uidv7805)
pep8 & pylint: rowalignment and error correction
Revision 1.11 2013/03/26 16:19:29CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:29 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/03/22 08:24:29CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
Revision 1.9 2013/03/21 17:22:37CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:37 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/04 07:47:35CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:47:36 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.7 2013/02/28 08:12:23CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:24 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/27 17:55:12CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:13 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/27 16:19:59CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:59 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/26 20:10:28CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:10:28 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/19 14:07:29CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:29 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/11 10:10:00CET Raedler, Guenther (uidt9430)
- fixed wrong intension in comment section
--- Added comments ---  uidt9430 [Feb 11, 2013 10:10:03 AM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:58:41CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/lbl/project.pj
------------------------------------------------------------------------------
-- From ETK/ADAS_DB Archive
------------------------------------------------------------------------------

Revision 1.14 2012/10/19 10:47:25CEST Hammernik-EXT, Dmitri (uidu5219)
bugfix
--- Added comments ---  uidu5219 [Oct 19, 2012 10:47:26 AM CEST]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.13 2012/10/19 10:27:23CEST Hammernik-EXT, Dmitri (uidu5219)
- added aditional return value in GetGenericLabelsStateValues function
--- Added comments ---  uidu5219 [Oct 19, 2012 10:27:25 AM CEST]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.12 2012/10/12 08:29:35CEST Spruck, Jochen (spruckj)
- Update Get Type names function, get all types names with parent xyz
- Delete generic label if label id is given
- Add delete generic labal with all attributs for a given label id
--- Added comments ---  spruckj [Oct 12, 2012 8:29:35 AM CEST]
Change Package : 93947:1 http://mks-psad:7002/im/viewissue?selection=93947
Revision 1.11 2012/03/20 11:12:40CET Spruck, Jochen (spruckj)
Add label attribute support
--- Added comments ---  spruckj [Mar 20, 2012 11:12:40 AM CET]
Change Package : 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.10 2012/02/06 08:23:39CET Raedler-EXT, Guenther (uidt9430)
- cast new ID as integer value
--- Added comments ---  uidt9430 [Feb 6, 2012 8:23:40 AM CET]
Change Package : 95134:1 http://mks-psad:7002/im/viewissue?selection=95134
Revision 1.9 2011/09/09 08:16:35CEST Spruck, Jochen (spruckj)
lower of MeasID is not needed
--- Added comments ---  spruckj [Sep 9, 2011 8:16:35 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.8 2011/09/06 09:58:27CEST Spruck Jochen (spruckj) (spruckj)
- show error only in case of on record found
- lower the meas id
--- Added comments ---  spruckj [Sep 6, 2011 9:58:27 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.7 2011/08/30 09:38:07CEST Spruck Jochen (spruckj) (spruckj)
Remove some typing errors
--- Added comments ---  spruckj [Aug 30, 2011 9:38:07 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.6 2011/08/08 10:19:17CEST Raedler Guenther (uidt9430) (uidt9430)
-- removed unused GetDateTime method
-- added Additional Label Info Handling
-- Changed Testcode
--- Added comments ---  uidt9430 [Aug 8, 2011 10:19:18 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.5 2011/07/15 10:01:36CEST Spruck Jochen (spruckj) (spruckj)
Add generic label type parent support
--- Added comments ---  spruckj [Jul 15, 2011 10:01:36 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.4 2011/07/11 13:32:27CEST Spruck Jochen (spruckj) (spruckj)
Set generic label abs timestamp bug fix, wrong column
--- Added comments ---  spruckj [Jul 11, 2011 1:32:27 PM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.3 2011/07/04 15:17:53CEST Raedler Guenther (uidt9430) (uidt9430)
-- moved workflow into global (GBL) schema
-- added parent column for label types
--- Added comments ---  uidt9430 [Jul 4, 2011 3:17:53 PM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.2 2011/07/01 12:52:29CEST Spruck Jochen (spruckj) (spruckj)
Update label interface module
--- Added comments ---  spruckj [Jul 1, 2011 12:52:29 PM CEST]
Change Package : 46866:8 http://mks-psad:7002/im/viewissue?selection=46866
Revision 1.1 2011/06/16 17:49:26CEST Spruck Jochen (spruckj) (spruckj)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/VDY_VehicleDynamics/05_Testing/05_Test_Environment/algo/vdy_req_test/valf_tests/
    adas_database/lb/project.pj
"""
