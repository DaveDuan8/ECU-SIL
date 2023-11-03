"""
convert.py
----------

conversation functions
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from math import log
from ast import parse, Expression, Add, Sub, Mult, Div, Mod, Pow, BinOp, USub, UAdd, UnaryOp, Str, Num
from operator import add, sub, mul, truediv, mod, pow as opow, neg, pos
from numpy import inf

# - import HPC modules -------------------------------------------------------------------------------------------------
from .dicts import DefDict


# - functions ----------------------------------------------------------------------------------------------------------
def human_size(num, unit='B'):
    """
    format a size in bytes to human readable format, e.g. bytes, KB, MB, GB, TB, PB
    Note that bytes/KB will be reported in whole numbers but MB and
    above will have greater precision e.g. 1 byte, 43 bytes, 443 KB, 4.3 MB, 4.43 GB, etc

    :param int num: raw size in bytes
    :param str unit: whished unit to get size_bytes converted
    :return: human readable size aligned
    :rtype: str
    """
    # --> http://en.wikipedia.org/wiki/Metric_prefix#List_of_SI_prefixes
    unit_list = [('', 0), ('k', 0), ('M', 1), ('G', 2), ('T', 2), ('P', 2), ('E', 3), ('Z', 3), ('Y', 3)]

    ret = ""
    if num < 0:
        num *= -1
        ret = "-"
    if num == 0:
        ret = "0"
    elif num == inf:
        ret = "(inf) {}".format(unit)
    elif num >= 1:
        idx = min(int(log(num, 1000)), len(unit_list) - 1)
        quot = float(num) / 10 ** (idx * 3)
        mult, num_decimals = unit_list[idx]
        ret += ('{:.%sf} {}{}' % num_decimals).format(quot, mult, unit)

    return ret


def toint(text):
    """
    convert a text to an integer

    :param str text: text to convert
    :return: integer
    :rtype: int
    """
    number = None
    if text == "min":
        return -2 ** 31
    if text == "max":
        return 2 ** 31 - 1

    mult = 1
    for i, k in enumerate(text):
        try:
            if i == 0 and k in ['-', '+']:
                mult = -1 if k == '-' else 1
                v = 0
            else:
                v = int(k)
            number = v if i == 0 else (10 * number + v)
        except ValueError:
            break
    return None if number is None else (mult * number)


def arg_trans(mapping, *args, **kwargs):
    """
    argument transformation into dict with defaults

    :param list mapping: list of argument names including their defaults
    :param list args: argument list
    :param dict kwargs: named arguments with defaults
    :return: transferred arguments
    :rtype: dict
    """
    dflt = kwargs.pop('default', None)
    newmap = DefDict(dflt)
    k, l = 0, len(args)
    # update from mapping
    for i in mapping:
        key = i[0] if isinstance(i, (tuple, list,)) else i
        val = args[k] if l > k else (i[1] if isinstance(i, (tuple, list,)) else dflt)
        newmap[key] = val
        k += 1
    # update rest from args
    while k < l:
        newmap["arg%d" % k] = args[k]
        k += 1

    # update left over from kwargs
    newmap.update(kwargs)
    return newmap


def safe_eval(txt):
    """
    take over proposal from https://stackoverflow.com/questions/15197673/using-pythons-eval-vs-ast-literal-eval
    as eval() shouldn't be used

    :param str txt: string to evaluate
    :return: result
    :rtype: int
    """
    bin_ops = {Add: add, Sub: sub, Mult: mul, Div: truediv, Mod: mod, Pow: opow, BinOp: BinOp}
    un_ops = {USub: neg, UAdd: pos, UnaryOp: UnaryOp}
    ops = tuple(bin_ops) + tuple(un_ops)

    tree = parse(txt, mode='eval')

    def _eval(node):
        if isinstance(node, Expression):
            return _eval(node.body)
        if isinstance(node, Str):
            return node.s
        if isinstance(node, Num):
            return node.n
        if isinstance(node, BinOp):
            if isinstance(node.left, ops):
                left = _eval(node.left)
            else:
                left = node.left.n
            if isinstance(node.right, ops):
                right = _eval(node.right)
            else:
                right = node.right.n
            return bin_ops[type(node.op)](left, right)
        if isinstance(node, UnaryOp):
            if isinstance(node.operand, ops):
                operand = _eval(node.operand)
            else:
                operand = node.operand.value
            return un_ops[type(node.op)](operand)

        raise SyntaxError("Bad syntax, {}".format(type(node)))

    return _eval(tree)
