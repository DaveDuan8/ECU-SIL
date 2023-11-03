"""
stk/db/db_sql.py
----------------

Python library to support the generation of SQL statements

 ADAS_DB


:org:           Continental AG
:author:        Dominik Froehlich

:version:       $Revision: 1.11 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/07/13 16:02:46CEST $
"""

# pylint: disable=W0231,R0201

# Import Python Modules ----------------------------------------------------------------------------------------------
from copy import copy
from datetime import datetime
from time import timezone
from cx_Oracle import NUMBER, STRING, BLOB, CLOB
from sqlite3 import Binary
from warnings import warn

# Defines -------------------------------------------------------------------------------------------------------------
# SQL Statements ------------------------------------------------------------------------------------------------------

STMT_SELECT = "SELECT"  # SELECT
STMT_UPDATE = "UPDATE"  # UPDATE
STMT_INSERT = "INSERT INTO"  # INSERT
STMT_DELETE = "DELETE FROM"  # DELETE
STMT_DROP_TABLE = "DROP TABLE"  # DROP
EXPR_WHERE = "WHERE"  # WHERE
EXPR_SET = "SET"  # SET
EXPR_VALUES = "VALUES"  # VALUES
EXPR_DISTINCT = "DISTINCT"  # DISTINCT
EXPR_FROM = "FROM"  # FROM
EXPR_GROUP_BY = "GROUP BY"  # GROUP BY
EXPR_ORDER_BY = "ORDER BY"  # ORDER BY
EXPR_HAVING = "HAVING"  # HAVING

EXPR_ASC = "ASC"  # ASC
EXPR_DESC = "DESC"  # DESC

EXPR_TRUE = "TRUE"  # TRUE
EXPR_FALSE = "FALSE"  # FALSE

EXPR_WITH = "WITH"
EXPR_COUNT = "COUNT"

# following placeholders will be replace according DB connection ...
EXPR_DATE = "$CD"  # ... to current date
EXPR_TIME = "$CT"  # ... to current time
EXPR_DATETIME = "$DT"  # ... to current datetime
# SQL Operators -------------------------------------------------------------------------------------------------------

OP_NOP = ""  # no operation

OP_POS = "+"  # unary plus
OP_NEG = "-"  # unary minus

OP_ADD = "+"  # binary add
OP_MUL = "*"  # mult.
OP_SUB = "-"  # binary sub
OP_DIV = "/"  # div
OP_MOD = "%"  # modulo

OP_ASGN = "="  # assignment
OP_EQ = "="  # equal
OP_NEQ = "!="  # not equal
OP_LT = "<"  # less than
OP_LEQ = "<="  # less than or equal to
OP_GT = ">"  # greater than
OP_GEQ = ">="  # greater than or equal to

OP_AND = "AND"  # log. and
OP_NOT = "NOT"  # log. not
OP_OR = "OR"  # log. or

OP_LIKE = "LIKE"  # LIKE operator (pattern matching)
OP_IN = "IN"  # IN operator (sub-queries)

OP_BIT_AND = "&"  # bitwise and
OP_BIT_NOT = "~"  # bitwise not
OP_BIT_OR = "|"  # bitwise or
OP_BIT_XOR = "^"  # bitwise xor

OP_AS = "AS"  # Alias
OP_BETWEEN = "BETWEEN"  # Between operator
OP_EXISTS = "EXISTS"  # exists operator

OP_INNER_JOIN = "INNER JOIN"  # Inner join
OP_LEFT_OUTER_JOIN = "LEFT OUTER JOIN"  # Left outer join
OP_RIGHT_OUTER_JOIN = "RIGHT OUTER JOIN"  # Right outer join
OP_NATURAL_JOIN = "NATURAL JOIN"  # Natural join
OP_UNION_ALL = "UNION ALL"  # Union all
OP_RETURNING = "RETURNING"

OP_ON = "ON"  # On

OP_IS = "IS"  # On

OP_USING = "USING"  # using operator

# Miscellaneous settings ----------------------------------------------------------------------------------------------
GEN_RECUR_NAME = "RECUR"
GEN_SHRECUR_NAME = "SHRECUR"

# Separator for table prefix and table base name
TABLE_PREFIX_SEPARATOR = "_"
SCHEMA_PREFIX_SEPARATOR = "."

# ---specifics for supported DB's -------------------------------------------------------------------------------------
CONN_STRING = {"MFC4XX": ("uid=DEV_MFC4XX_PWUSER_GT;pwd=MFC4XX_PWUSER_GT", "DEV_MFC4XX_ADMIN"),
               "ARS4XX": ("uid=DEV_ARS4XX_PWUSER_GT;pwd=ARS4XX_PWUSER_GT", "DEV_ARS4XX_ADMIN"),
               "VGA": ("uid=VAL_GLOBAL_USER;pwd=PWD4VAL_GLBL", "VAL_GLOBAL_ADMIN",),
               "VGA_PWR": ("uid=VAL_GLOBAL_PWUSER_GT;pwd=VAL_GLBL_PWUSER_GT1", "VAL_GLOBAL_ADMIN",),
               "HPC": ("uid=HPC_USER;pwd=Baba1234", "HPC_ADMIN",),
               "stk": ("uid=MT_STK_DEV_ADMIN;pwd=MT_STK_DEV_ADMIN_PW1", ""),
               "algo": ("uid=ALGO_DB_USER;pwd=read", "ADMSADMIN")}

# dbType --> 0: sqlite, 1: sqlCE, 2 / -1: oracle
DBTYPE = ["sqlite3", "adodbapi", "pyodbc", "cx_Oracle"]
SQL_TABLENAMES = ["SELECT name FROM sqlite_master WHERE type='table' AND NAME LIKE '$TS_%%' ORDER BY name",
                  "SELECT CAST(TABLE_NAME AS NCHAR(127)) FROM information_schema.tables "
                  "WHERE (TABLE_TYPE LIKE 'TABLE' AND TABLE_NAME LIKE '$TS_%%') ORDER BY TABLE_NAME",
                  "SELECT DISTINCT OBJECT_NAME FROM ALL_OBJECTS WHERE OBJECT_TYPE IN ('TABLE', 'VIEW') "
                  "AND OWNER = $NM AND LOWER(OBJECT_NAME) LIKE '$TS%'"]
#                  "SELECT TABLE_NAME AS NAME FROM ALL_TABLES WHERE TABLE_NAME LIKE '$TS_%%' ORDER BY TABLE_NAME"]
SQL_DT_EXPR = ["CURRENT_TIMESTAMP", "GETDATE()", "CURRENT_DATE"]
SQL_DATETIME = ["SELECT strftime('%Y-%m-%d %H:%M:%S','now')",
                "SELECT CONVERT(NVARCHAR(19), DATEADD(hour, %d, GETDATE()), 120)" % (timezone / 3600),
                "SELECT TO_CHAR(systimestamp at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS') FROM SYS.dual"]
SQL_COLUMNS = [([1, 2], "PRAGMA table_info($TBL)"),
               ([0, 1], "SELECT CAST(column_name AS NTEXT), CAST(UPPER(data_type) AS NTEXT) "
                "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '$TBL'"),
               ([0, 1], "SELECT column_name, data_type || CASE WHEN data_type LIKE '%CHAR%' THEN "
                        "'(' || char_length || ')' ELSE '' END FROM all_tab_cols WHERE table_name = '$TBL' "
                        "AND COLUMN_ID IS NOT NULL AND owner = $NM")]

IDENT_SPACE = {"dbcat": "CAT", "dbcl": "CL", "dbgbl": "GBL", "dbobj": "OBJ",
               "dbpar": "PAR", "dbval": "VAL", "dbfct": "FCT"}

SQL_PARM = ['?', '?', ':1']

CX_VARS = {'number': NUMBER, 'string': STRING, 'blob': BLOB, 'clob': CLOB}
SQ_VARS = {'blob': Binary}

# Functions -----------------------------------------------------------------------------------------------------------

# SQL Statement Exceptions --------------------------------------------------------------------------------------------

# try:
#     from exceptions import StandardError as _BaseException
# except ImportError:
#     # py3k
#     _BaseException = Exception


class SQLStatementError(StandardError):
    """Base of all SQL statement errors"""
    pass


class SQLStatementGenerationError(SQLStatementError):
    """Error during the generation of a SQL statement"""
    pass

# Classes -------------------------------------------------------------------------------------------------------------


class BaseSQLStatement(object):
    """Base SQL statement"""

    TABLE_PREFIX_SET_METHOD_NAME = "SetTablePrefix"

    def __init__(self):
        pass

    @staticmethod
    def IsPrimitiveType(item):
        """Check if an item is of a primitive type

        :param item: name of the DB type to be checked
        :type item: db type
        :return: Returns True if the item type is primitive
        :rtype: bool
        """
        return item == str or item == unicode or item == datetime

    def ConvertConstantsToSQLLiterals(self, assign_items):
        """
        Copy given dictionary and convert all constant values to SQL literals

        :param assign_items: The assignment items whose values are to be converted.
        :type assign_items: dictionary
        :return: Returns a copy of the assignment items with all info converted.
        """
        assign_items_copy = copy(assign_items)
        for key in assign_items_copy:
            value = assign_items_copy[key]
            assign_items_copy[key] = self.GetExprForValue(value)
        # done
        return assign_items_copy

    @staticmethod
    def GetExprForValue(value):
        """
        Returns the appropriate SQL expression for a value.

        :param value: The value for which to return the expression.
        :return: Returns the expression representing the vaue.
        """
        if type(value) == SQLExpr or type(value) == BaseSQLStatement:
            return value
        elif type(value) == long or type(value) == int:
            return SQLIntegral(value)
        elif type(value) == float:
            return SQLFloat(value)
        elif type(value) == str or type(value) == unicode:
            return SQLString(value)
        elif type(value) == datetime:
            return SQLDate(value)
        elif value is None:
            return SQLNull()
        else:
            return value

    def SetTablePrefix(self, table_prefix, recurse=True):
        """Set the table prefix recursively in expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        pass

    def _set_table_prefix(self, obj, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param obj: The object to set the prefix for, if supported.
        :type obj: Object
        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if obj is not None:
            try:
                set_prefix_func = getattr(obj, self.TABLE_PREFIX_SET_METHOD_NAME)
            except AttributeError:
                pass
            else:
                set_prefix_func(table_prefix, recurse)

# ====================================================================
# SQL SELECT Statement Support
# ====================================================================


class GenericSQLSelect(BaseSQLStatement):
    """SQL SELECT statement"""
    def __init__(self, select_list=["*"], distinct_rows=False, table_list=None, where_condition=None, with_clause=None):
        """
        Initialize new statement

        :param select_list: List of selected items
        :type select_list:
        :param table_list: List of source tables
        :type table_list:
        """
        self.with_clause = with_clause
        self.select_list = select_list
        self.table_list = table_list
        self.distinct_rows = distinct_rows
        self.where_condition = where_condition
        self.group_by_list = None
        self.having_condition = None
        self.order_by_list = None

    def __str__(self):
        """Generate SQL SELECT statement"""
        if not self.select_list or len(self.select_list) == 0:
            raise SQLStatementGenerationError("Invalid select list", str(self.select_list))

        stmt = ''
        if self.with_clause:
            stmt = EXPR_WITH + " " + str(self.with_clause) + " "
        stmt += STMT_SELECT
        # DISTINCT
        if self.distinct_rows:
            stmt = stmt + " " + EXPR_DISTINCT
        # Selected items
        stmt = stmt + " " + str(SQLListExpr(self.select_list))
        # Source tables
        if self.table_list and len(self.table_list) > 0:
            stmt = stmt + " " + EXPR_FROM + " " + str(SQLListExpr(self.table_list))
        # WHERE clause
        if self.where_condition:
            stmt = stmt + " " + EXPR_WHERE + " " + str(self.where_condition)
        # GROUP BY clause
        if self.group_by_list and len(self.group_by_list) > 0:
            stmt = stmt + " " + EXPR_GROUP_BY + " " + str(SQLListExpr(self.group_by_list))
        # HAVING clause
        if self.having_condition:
            stmt = stmt + " " + EXPR_HAVING + " " + str(self.having_condition)
        # ORDER BY clause
        if self.order_by_list and len(self.order_by_list) > 0:
            stmt = stmt + " " + EXPR_ORDER_BY + " " + str(SQLListExpr(self.order_by_list))
            # done
        return stmt

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            self._set_table_prefix(self.select_list, table_prefix, recurse)
            self._set_table_prefix(self.table_list, table_prefix, recurse)
            self._set_table_prefix(self.group_by_list, table_prefix, recurse)
            self._set_table_prefix(self.having_condition, table_prefix, recurse)
            self._set_table_prefix(self.order_by_list, table_prefix, recurse)


class GenericSQLUpdate(BaseSQLStatement):
    """SQL UPDATE statement"""
    def __init__(self, table_name=None, assign_items=None, where_condition=None):
        """
        Initialize new statement

        :param table_name: The name of the updated table
        :type table_name: str
        :param assign_items: The dictionary of names and values to be set.
        :type assign_items: Dictionary
        :param where_condition: The condition hat must be fulfilled by the updated rows,
        :type where_condition: str
        """
        self.table_name = table_name
        self.assign_items = assign_items
        self.where_condition = where_condition

    def __str__(self):
        """Generate SQL UPDATE statement"""
        if not self.table_name or len(self.table_name) == 0:
            raise SQLStatementGenerationError("Invalid table name", str(self.table_name))
        if not self.assign_items or len(self.assign_items) == 0:
            raise SQLStatementGenerationError("Invalid set values", str(self.assign_items))
        stmt = STMT_UPDATE
        # Updated table
        stmt = stmt + " " + str(self.table_name)
        # Set values
        stmt = stmt + " " + EXPR_SET + " "
        stmt += str(SQLAssignListExpr(self.ConvertConstantsToSQLLiterals(self.assign_items)))
        # WHERE clause
        if self.where_condition:
            stmt = stmt + " " + EXPR_WHERE + " " + str(self.where_condition)
        # done
        return stmt


class GenericSQLInsert(BaseSQLStatement):
    """SQL INSERT statement"""
    def __init__(self, table_name=None, assign_items=None, returning=None):
        """
        Initialize new statement

        :param table_name: The name of the table ito which values are inserted
        :type table_name: str
        :param assign_items: Dictionary of columns and values to insert
        :type assign_items: dict
        :param returning: column name to get new auto incremented index
        """
        self.table_name = table_name
        self.assign_items = assign_items
        self.returning = returning

    def __str__(self):
        """Generate SQL INSERT statement"""
        if not self.assign_items or len(self.assign_items) == 0:
            raise SQLStatementGenerationError("Invalid set values", str(self.assign_items))
        stmt = STMT_INSERT
        # table
        stmt = stmt + " " + str(self.table_name)
        # columns
        assign_items_copy = self.ConvertConstantsToSQLLiterals(self.assign_items)
        stmt = stmt + " " + "(" + str(SQLListExpr(assign_items_copy.keys())) + ")"
        # values
        stmt = stmt + " " + EXPR_VALUES + "(" + str(SQLListExpr(assign_items_copy.values())) + ")"
        # returning
        if self.returning:
            stmt += " " + str(self.returning)
        # done
        return stmt


class GenericSQLPreparedInsert(BaseSQLStatement):
    """SQL INSERT statement"""
    def __init__(self, table_name=None, assign_items=None):
        """
        Initialize new statement

        :param table_name: The name of the table ito which values are inserted
        :type table_name: str
        :param assign_items: Dictionary of columns and values to insert
        :type assign_items: Dictionary
        """
        self.table_name = table_name
        self.assign_items = assign_items

    def __str__(self):
        """Generate SQL INSERT statement"""
        if not self.assign_items or len(self.assign_items) == 0:
            raise SQLStatementGenerationError("Invalid set values", str(self.assign_items))
        stmt = STMT_INSERT
        # table
        stmt = stmt + " " + str(self.table_name) + "("
        # column + values
        vals = " " + EXPR_VALUES + "("
        for i in range(len(self.assign_items)):
            stmt += " %s," % self.assign_items[i]
            vals += " :%s," % str(i + 1)
        stmt = stmt[:-1] + " )"
        vals = vals[:-1] + " )"
        stmt += vals

        return stmt


class GenericSQLDelete(BaseSQLStatement):
    """SQL DELETE statement"""
    def __init__(self, table_name=None, where_condition=None):
        """
        Initialize new statement

        :param table_name: The name of the table into which values are inserted
        :type table_name: str
        :param where_condition: The optional where condition
        :type where_condition: str
        """
        self.table_name = table_name
        self.where_condition = where_condition

    def __str__(self):
        """Generate SQL DELETE statement"""
        stmt = STMT_DELETE
        # table
        stmt = stmt + " " + str(self.table_name)
        # where clause
        if self.where_condition:
            stmt = stmt + " " + EXPR_WHERE + " " + str(self.where_condition)
        # done
        return stmt


class GenericSQLDropTable(BaseSQLStatement):
    """SQL DROP statement for tables"""
    def __init__(self, table_name=None, *args, **kwargs):
        """
        Initialize new statement

        :param table_name: The name of the table to drop
        :type table_name: str
        """
        self.table_name = table_name
        if len(args) or len(kwargs):
            warn("additional arguments to 'GenericSQLDropTable' are not supported!")

    def __str__(self):
        """Generate SQL DROP statement"""
        if not self.table_name or len(self.table_name) == 0:
            raise SQLStatementGenerationError("Invalid table name", str(self.table_name))
        stmt = STMT_DROP_TABLE
        # table
        stmt = stmt + " " + str(self.table_name)
        # done
        return stmt

# ====================================================================
# SQL Statement Factories
# ====================================================================


class BaseSQLStatementFactory(object):
    """Base factory to get database specific imlementations of SQL statements"""
    def __init__(self):
        pass


class GenericSQLStatementFactory(BaseSQLStatementFactory):
    """Generic SQL statements applicable to most DBMS"""
    def __init__(self):
        pass

    @staticmethod
    def GetSelectBuilder():
        """Returns a new builder for generic SQL Select statements"""
        return GenericSQLSelect()

    @staticmethod
    def GetUpdateBuilder():
        """Returns a new builder for generic SQL Update statements"""
        return GenericSQLUpdate()

    @staticmethod
    def GetInsertBuilder():
        """Returns a new builder for generic SQL Insert statements"""
        return GenericSQLInsert()

    @staticmethod
    def GetPreparedInsertBuilder():
        """Returns a new builder for generic SQL Insert statements"""
        return GenericSQLPreparedInsert()

    @staticmethod
    def GetDeleteBuilder():
        """Returns a new builder for generic SQL Delete statements"""
        return GenericSQLDelete()

    @staticmethod
    def GetDropTableBuilder():
        """Returns a new builder for generic SQL drop table statements"""
        return GenericSQLDropTable()

# ====================================================================
# SQL Expressions
# ====================================================================


class SQLExpr(object):
    """SQL Base expression"""

    TABLE_PREFIX_SET_METHOD_NAME = "SetTablePrefix"

    @staticmethod
    def IsPrimitiveType(tname):
        """
        Check if an item is of a primitive type

        :param tname: Name of the type to be checked
        :type tname: str
        :return: Returns True if the item type is primitive
        :rtype: bool
        """
        return tname in (float, long, int, str, unicode, datetime)

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        pass

    def _set_table_prefix(self, obj, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.



        :param obj: The object to set the prefix for, if supported.
        :type obj: Object
        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if obj is not None:
            try:
                set_prefix_func = getattr(obj, self.TABLE_PREFIX_SET_METHOD_NAME)
            except AttributeError:
                pass
            else:
                set_prefix_func(table_prefix, recurse)


class SQLLiteral(SQLExpr):
    """SQL Literal"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "'" + str(self.value) + "'"


class SQLNull(SQLLiteral):
    """SQL NULL literal representation"""
    def __init__(self):
        pass

    def __str__(self):
        return "NULL"


class SQLDefault(SQLLiteral):
    """SQL DEFAULT literal representation"""
    def __init__(self):
        pass

    def __str__(self):
        return "DEFAULT"


class SQLString(SQLLiteral):
    """SQL string literal representation"""
    pass


class SQLIntegral(SQLLiteral):
    """SQL integer literal representation"""
    def __str__(self):
        return str(self.value)


class SQLFloat(SQLLiteral):
    """SQL float literal representation"""
    def __str__(self):
        return str(self.value)


class SQLDate(SQLLiteral):
    """SQL date literal representation"""
    pass


class SQLTime(SQLLiteral):
    """SQL time literal representation"""
    pass


class SQLTimestamp(SQLLiteral):
    """SQL timestamp literal representation"""
    pass


class SQLCurrency(SQLLiteral):
    """SQL currency literal representation"""
    pass


class SQLBoolean(SQLLiteral):
    """SQL Boolean literal representation"""
    def __init__(self, value):
        SQLLiteral.__init__(value)

    def __str__(self):
        if self.value:
            return str(EXPR_TRUE)
        else:
            return str(EXPR_FALSE)


class SQLBinary(SQLLiteral):
    """SQL binary literal representation"""
    def __init__(self, value):
        SQLLiteral.__init__(value)

    def __str__(self):
        return str(self.value)


class SQLBinaryExpr(SQLExpr):
    """SQL binary expression"""
    def __init__(self, left_expr, binary_operator, right_expr):
        self.left_expr = left_expr
        self.binary_operator = binary_operator
        self.right_expr = right_expr

    def __str__(self):
        left_str = str(self.left_expr)
        if not (isinstance(self.left_expr, SQLLiteral) or
                isinstance(self.left_expr, SQLColumnExpr) or
                isinstance(self.left_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.left_expr))):
            left_str = "(" + left_str + ")"
        right_str = str(self.right_expr)
        if not (isinstance(self.right_expr, SQLLiteral) or
                isinstance(self.right_expr, SQLColumnExpr) or
                isinstance(self.right_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.right_expr))):
            right_str = "(" + right_str + ")"
        return left_str + " " + str(self.binary_operator) + " " + right_str

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            self._set_table_prefix(self.left_expr, table_prefix, recurse)
            self._set_table_prefix(self.right_expr, table_prefix, recurse)


class SQLConcatExpr(SQLExpr):
    """SQL concatenation expression which just catenates all expressions with space delimiter"""
    def __init__(self, *args):
        self.list = args

    def __str__(self):
        return " ".join([str(i) for i in self.list])


class SQLTernaryExpr(SQLExpr):
    """SQL ternary expression"""
    def __init__(self, left_expr, first_operator, middle_expr, second_operator, right_expr):
        self.left_expr = left_expr
        self.first_operator = first_operator
        self.second_operator = second_operator
        self.middle_expr = middle_expr
        self.right_expr = right_expr

    def __str__(self):
        left_str = str(self.left_expr)
        if not (isinstance(self.left_expr, SQLLiteral) or
                isinstance(self.left_expr, SQLTableExpr) or
                isinstance(self.left_expr, SQLColumnExpr) or
                isinstance(self.left_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.left_expr))):
            left_str = "(" + left_str + ")"
        middle_str = str(self.middle_expr)
        if not (isinstance(self.middle_expr, SQLLiteral) or
                isinstance(self.middle_expr, SQLTableExpr) or
                isinstance(self.middle_expr, SQLColumnExpr) or
                isinstance(self.middle_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.middle_expr))):
            middle_str = "(" + middle_str + ")"
        right_str = str(self.right_expr)
        if not (isinstance(self.right_expr, SQLLiteral) or
                isinstance(self.right_expr, SQLTableExpr) or
                isinstance(self.right_expr, SQLColumnExpr) or
                isinstance(self.right_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.right_expr))):
            right_str = "(" + right_str + ")"

        tmp = left_str + " " + str(self.first_operator) + " " + middle_str
        tmp += " " + str(self.second_operator) + " " + right_str

        return tmp

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            self._set_table_prefix(self.left_expr, table_prefix, recurse)
            self._set_table_prefix(self.middle_expr, table_prefix, recurse)
            self._set_table_prefix(self.right_expr, table_prefix, recurse)


class SQLJoinExpr(SQLTernaryExpr):
    """
    SQL join expression

    :param left_table_expr: The expression representing the left table source.
    :param join_operator: Operant of left and right expression.
    :param right_table_expr:  The expression representing the right table source.
    """
    def __init__(self, left_table_expr, join_operator, right_table_expr, join_cond_expr=None, on_operator=OP_ON):
        SQLTernaryExpr.__init__(self, left_table_expr, join_operator, right_table_expr, on_operator, join_cond_expr)

    def __str__(self):
        left_str = str(self.left_expr)
        if not (isinstance(self.left_expr, SQLLiteral) or
                isinstance(self.left_expr, SQLTableExpr) or
                isinstance(self.left_expr, SQLColumnExpr) or
                isinstance(self.left_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.left_expr))):
            left_str = "(" + left_str + ")"
        middle_str = str(self.middle_expr)
        if not (isinstance(self.middle_expr, SQLLiteral) or
                isinstance(self.middle_expr, SQLTableExpr) or
                isinstance(self.left_expr, SQLColumnExpr) or
                isinstance(self.left_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.middle_expr))):
            middle_str = "(" + middle_str + ")"
        expr_str = left_str + " " + str(self.first_operator) + " " + middle_str
        if self.right_expr is not None:
            right_str = str(self.right_expr)
            if not (isinstance(self.right_expr, SQLLiteral) or
                    isinstance(self.right_expr, SQLTableExpr) or
                    isinstance(self.right_expr, SQLColumnExpr) or
                    isinstance(self.right_expr, SQLFuncExpr) or
                    self.IsPrimitiveType(type(self.right_expr))):
                right_str = "(" + right_str + ")"
            expr_str = expr_str + " " + str(self.second_operator) + " " + right_str
        return expr_str


class SQLTableExpr(SQLExpr):
    """Expression representing a table prefix, base name and alias"""
    def __init__(self, table_base_name, table_alias=None, table_prefix=None):
        """
        Expression representing a table prefix, base name and alias

        :param table_base_name: The base name of the table
        :type table_base_name: str
        :param table_alias: Optional alias (default=None)
        :type table_alias: str | None
        :param table_prefix: Optional table prefix. If not given, the table base name is used.
        :type table_prefix: str | None
        """

        self.table_base_name = table_base_name
        self.table_alias = table_alias
        self.table_prefix = table_prefix

    def __str__(self):
        table_name = str(self.table_base_name)
        if self.table_prefix is not None:
            self.table_prefix = self.table_prefix.strip()
            if len(self.table_prefix) > 0:
                table_name = str(self.table_prefix) + table_name
        if self.table_alias is not None:
            return table_name + " " + str(self.table_alias)
        return table_name

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        self.table_prefix = table_prefix


class SQLColumnExpr(SQLExpr):
    """SQL binary expression"""
    def __init__(self, table_expr, column_expr, use_column_quotes=False):
        self.table_expr = table_expr
        self.column_expr = column_expr
        self.use_column_quotes = use_column_quotes

    def __str__(self):
        column_str = str(self.column_expr)
        if self.use_column_quotes is True:
            column_str = '"' + column_str + '"'
        if self.table_expr is not None:
            column_str = str(self.table_expr) + "." + column_str
        return column_str

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            self._set_table_prefix(self.table_expr, table_prefix, recurse)
            self._set_table_prefix(self.column_expr, table_prefix, recurse)


class SQLUnaryExpr(SQLExpr):
    """SQL unary expression"""
    def __init__(self, unary_operator, right_expr):
        self.unary_operator = unary_operator
        self.right_expr = right_expr

    def __str__(self):
        right_str = str(self.right_expr)
        if not (isinstance(self.right_expr, SQLLiteral) or
                isinstance(self.right_expr, SQLColumnExpr) or
                isinstance(self.right_expr, SQLFuncExpr) or
                self.IsPrimitiveType(type(self.right_expr))):
            right_str = "(" + right_str + ")"
        return str(self.unary_operator) + " " + right_str

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            self._set_table_prefix(self.right_expr, table_prefix, recurse)


class SQLFuncExpr(SQLExpr):
    """SQL function expression"""
    def __init__(self, func_name, arg_expr=None):
        self.func_name = func_name
        self.arg_expr = arg_expr

    def __str__(self):
        arg_stmt = ""
        if self.arg_expr:
            arg_stmt = str(self.arg_expr)
        return str(self.func_name) + "(" + arg_stmt + ")"

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            self._set_table_prefix(self.arg_expr, table_prefix, recurse)


class SQLListExpr(SQLExpr):
    """SQL list expression, i.e. comma separated list of expressions"""
    def __init__(self, expr_list, separator=", "):
        self.expr_list = expr_list
        self.separator = separator

    def __str__(self):
        stmt = ""
        num_exprs = len(self.expr_list)
        num_expr = 0
        for expr in self.expr_list:
            stmt += str(expr)
            if (num_expr + 1) < num_exprs:
                stmt += self.separator
            num_expr += 1
        return stmt

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            for expr in self.expr_list:
                self._set_table_prefix(expr, table_prefix, recurse)


class SQLAssignListExpr(SQLExpr):
    """SQL assignment list expression"""
    def __init__(self, assign_items, separator=", "):
        self.assign_items = assign_items
        self.separator = separator

    def __str__(self):
        stmt = ""
        num_items = len(self.assign_items)
        num_item = 0
        for key in self.assign_items:
            stmt = stmt + str(key) + OP_ASGN + str(self.assign_items[key])
            if (num_item + 1) < num_items:
                stmt += self.separator
            num_item += 1
        return stmt

    def SetTablePrefix(self, table_prefix, recurse=True):
        """
        Set the table prefix recursively in sub-expressions.

        :param table_prefix: The table prefix.
        :type table_prefix: str
        :param recurse: Set False, if recursion to sub-expressions shall be allowed. True by default.
        :type recurse: bool
        """
        if recurse:
            for key in self.assign_items:
                self._set_table_prefix(key, table_prefix, recurse)
                self._set_table_prefix(self.assign_items[key], table_prefix, recurse)


"""
$Log: db_sql.py  $
Revision 1.11 2017/07/13 16:02:46CEST Mertens, Sven (uidv7805) 
add power user helper string
Revision 1.10 2016/08/16 16:24:13CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.9 2016/08/16 16:01:40CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.8 2016/08/15 14:24:25CEST Mertens, Sven (uidv7805)
char, not data length
Revision 1.7 2016/08/10 18:22:54CEST Mertens, Sven (uidv7805)
return a similar resultset like sqlite for text fields
Revision 1.6 2016/07/13 13:24:22CEST Mertens, Sven (uidv7805)
use pwuser gt as defined in meeting this morning
Revision 1.5 2016/05/30 18:50:46CEST Hospes, Gerd-Joachim (uidv8815)
changed shared coll queries, add tests in test_collections
Revision 1.4 2016/04/04 12:17:53CEST Mertens, Sven (uidv7805)
username fix
Revision 1.3 2016/04/01 08:01:23CEST Mertens, Sven (uidv7805)
adding hpc define
Revision 1.2 2015/11/06 13:30:03CET Mertens, Sven (uidv7805)
adding fct to ident dict
--- Added comments ---  uidv7805 [Nov 6, 2015 1:30:04 PM CET]
Change Package : 394407:1 http://mks-psad:7002/im/viewissue?selection=394407
Revision 1.1 2015/04/23 19:03:53CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/db/project.pj
Revision 1.26 2015/03/20 13:52:33CET Mertens, Sven (uidv7805)
VGA login update
--- Added comments ---  uidv7805 [Mar 20, 2015 1:52:33 PM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.25 2015/03/17 15:48:59CET Mertens, Sven (uidv7805)
docu fix
--- Added comments ---  uidv7805 [Mar 17, 2015 3:48:59 PM CET]
Change Package : 318011:1 http://mks-psad:7002/im/viewissue?selection=318011
Revision 1.24 2015/03/13 08:08:12CET Mertens, Sven (uidv7805)
fix for wrong table name query
--- Added comments ---  uidv7805 [Mar 13, 2015 8:08:12 AM CET]
Change Package : 316693:1 http://mks-psad:7002/im/viewissue?selection=316693
Revision 1.23 2015/03/05 10:06:54CET Mertens, Sven (uidv7805)
adding missing expressions for current time, date and datetime
--- Added comments ---  uidv7805 [Mar 5, 2015 10:06:55 AM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.22 2015/02/26 15:47:25CET Mertens, Sven (uidv7805)
removing doc errors
--- Added comments ---  uidv7805 [Feb 26, 2015 3:47:26 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.21 2015/02/26 15:44:36CET Mertens, Sven (uidv7805)
adding concatenator and count as expression
--- Added comments ---  uidv7805 [Feb 26, 2015 3:44:37 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.20 2015/01/22 14:55:13CET Mertens, Sven (uidv7805)
adding missing union and returning operator
--- Added comments ---  uidv7805 [Jan 22, 2015 2:55:14 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.19 2015/01/13 09:38:51CET Mertens, Sven (uidv7805)
fix for column name retrieval
--- Added comments ---  uidv7805 [Jan 13, 2015 9:38:52 AM CET]
Change Package : 294959:1 http://mks-psad:7002/im/viewissue?selection=294959
Revision 1.18 2014/12/09 10:43:34CET Mertens, Sven (uidv7805)
additional type fixes
--- Added comments ---  uidv7805 [Dec 9, 2014 10:43:35 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.17 2014/12/08 08:46:12CET Mertens, Sven (uidv7805)
removing additional pep8 / pylints
--- Added comments ---  uidv7805 [Dec 8, 2014 8:46:13 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.16 2014/11/17 08:10:38CET Mertens, Sven (uidv7805)
name updates
--- Added comments ---  uidv7805 [Nov 17, 2014 8:10:38 AM CET]
Change Package : 281272:1 http://mks-psad:7002/im/viewissue?selection=281272
Revision 1.15 2014/11/10 14:45:14CET Mertens, Sven (uidv7805)
being able to leave out old GetQualifiedTableName
--- Added comments ---  uidv7805 [Nov 10, 2014 2:45:15 PM CET]
Change Package : 279419:1 http://mks-psad:7002/im/viewissue?selection=279419
Revision 1.14 2014/10/09 14:23:24CEST Mertens, Sven (uidv7805)
adding views as adms_admin is in use now
--- Added comments ---  uidv7805 [Oct 9, 2014 2:23:25 PM CEST]
Change Package : 270435:1 http://mks-psad:7002/im/viewissue?selection=270435
Revision 1.13 2014/10/09 11:28:38CEST Mertens, Sven (uidv7805)
lint adaption
--- Added comments ---  uidv7805 [Oct 9, 2014 11:28:38 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.12 2014/10/09 10:31:51CEST Mertens, Sven (uidv7805)
fix table name retrieval for oracle
--- Added comments ---  uidv7805 [Oct 9, 2014 10:31:52 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.11 2014/10/08 12:40:02CEST Ellero, Stefano (uidw8660)
Improved epydoc documentation for the for stk.db.root subpackage.
--- Added comments ---  uidw8660 [Oct 8, 2014 12:40:03 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.10 2014/10/07 14:23:27CEST Ellero, Stefano (uidw8660)
Improved epydoc documentation for the for stk.db.root subpackage.
--- Added comments ---  uidw8660 [Oct 7, 2014 2:23:28 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.9 2014/06/24 10:29:34CEST Mertens, Sven (uidv7805)
query update for table descriptors
--- Added comments ---  uidv7805 [Jun 24, 2014 10:29:34 AM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.8 2014/05/13 16:26:18CEST Mertens, Sven (uidv7805)
adding some constants for db_common: common usage need for VAT
--- Added comments ---  uidv7805 [May 13, 2014 4:26:19 PM CEST]
Change Package : 236403:1 http://mks-psad:7002/im/viewissue?selection=236403
Revision 1.7 2014/03/24 08:15:44CET Ahmed, Zaheer (uidu7634)
Added GenericSQLPreparedInsert class
Introduced GetPreparedInsertBuilder()
--- Added comments ---  uidu7634 [Mar 24, 2014 8:15:45 AM CET]
Change Package : 224327:1 http://mks-psad:7002/im/viewissue?selection=224327
Revision 1.6 2013/03/28 09:33:16CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:16 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.5 2013/03/26 16:19:25CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:26 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/03/04 07:47:25CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:47:25 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 13:59:47CET Hecker, Robert (heckerr)
Some changes regarding Pep8
--- Added comments ---  heckerr [Feb 27, 2013 1:59:47 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/26 20:11:53CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:11:53 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/12 08:19:50CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/project.pj
------------------------------------------------------------------------------
-- From CGEB Archive
------------------------------------------------------------------------------
Revision 1.9 2012/04/13 09:12:05CEST Spruck, Jochen (spruckj)
Add " " for collumn expressions
--- Added comments ---  spruckj [Apr 13, 2012 9:12:08 AM CEST]
Change Package : 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.8 2011/01/28 18:48:44CET Froehlich, Dominik01 (froehlichd1)
* change: corercted SQLBoolean expression
--- Added comments ---  froehlichd1 [Jan 28, 2011 6:48:44 PM CET]
Change Package : 33544:49 http://mks-psad:7002/im/viewissue?selection=33544
Revision 1.7 2010/11/18 14:47:28CET Dominik Froehlich (froehlichd1)
* fix: fixed computation of table/schema prefixes
* use one prefix that includes the separators
--- Added comments ---  froehlichd1 [Nov 18, 2010 2:47:28 PM CET]
Change Package : 45990:32 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.6 2010/11/10 10:56:28CET Dominik Froehlich (froehlichd1)
* change: removed default table prefixes
* change: full support of 'no table prefix'
--- Added comments ---  froehlichd1 [Nov 10, 2010 10:56:29 AM CET]
Change Package : 45990:29 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.5 2010/07/05 17:11:57CEST Dominik Froehlich (dfroehlich)
* added list of vehicle function
--- Added comments ---  dfroehlich [2010/07/05 15:11:58Z]
Change Package : 45990:18 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.4 2010/06/25 14:22:11CEST Dominik Froehlich (dfroehlich)
* update
--- Added comments ---  dfroehlich [2010/06/25 12:22:11Z]
Change Package : 45990:3 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.3 2009/11/19 18:58:51CET Dominik Froehlich (dfroehlich)
* minor script maintenance
--- Added comments ---  dfroehlich [2009/11/19 17:58:51Z]
Change Package : 33544:7 http://LISS014:6001/im/viewissue?selection=33544
Revision 1.2 2009/10/21 12:23:14CEST Dominik Froehlich (dfroehlich)
* change: first complete version of use case constraint genertor
--- Added comments ---  dfroehlich [2009/10/21 10:23:14Z]
Change Package : 27037:12 http://LISS014:6001/im/viewissue?selection=27037
--- Added comments ---  dfroehlich [2009/10/21 10:23:14Z]
Change Package : 27037:12 http://LISS014:6001/im/viewissue?selection=27037
Revision 1.1 2009/10/08 12:27:48CEST rthiel
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
Base_CGEB/06_Algorithm/04_Engineering/02_Development_Tools/scripts/project.pj
Revision 1.8 2009/06/23 12:10:34CEST dfroehlich
* add: aded event reports and preview image
--- Added comments ---  dfroehlich [2009/06/23 10:10:34Z]
Change Package : 27675:5 http://LISS014:6001/im/viewissue?selection=27675
Revision 1.7 2009/06/22 08:43:00CEST dfroehlich
* extended CGEB report
--- Added comments ---  dfroehlich [2009/06/22 06:43:00Z]
Change Package : 27675:2 http://LISS014:6001/im/viewissue?selection=27675
Revision 1.6 2009/06/17 19:02:06CEST dfroehlich
* change: intermediate version of new simulation report
--- Added comments ---  dfroehlich [2009/06/17 17:02:06Z]
Change Package : 27675:1 http://LISS014:6001/im/viewissue?selection=27675
Revision 1.5 2009/06/16 11:13:34CEST dfroehlich
* fix: various SQL changes
--- Added comments ---  dfroehlich [2009/06/16 09:13:34Z]
Change Package : 21107:4 http://LISS014:6001/im/viewissue?selection=21107
Revision 1.4 2009/05/28 15:01:48CEST dfroehlich
fix: fixed event import and table init
--- Added comments ---  dfroehlich [2009/05/28 13:01:48Z]
Change Package : 21107:3 http://LISS014:6001/im/viewissue?selection=21107
Revision 1.3 2009/04/27 16:03:24CEST dfroehlich
* sql bug fixes
--- Added comments ---  dfroehlich [2009/04/27 14:03:24Z]
Change Package : 25379:6 http://LISS014:6001/im/viewissue?selection=25379
Revision 1.2 2009/04/10 20:17:27CEST dfroehlich
* change: changed table scheme
--- Added comments ---  dfroehlich [2009/04/10 18:17:27Z]
Change Package : 25379:1 http://LISS014:6001/im/viewissue?selection=25379
"""
