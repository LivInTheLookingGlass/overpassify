"""This is the main transpiler file. It contains functions which provide
translation of a simple subset of Python into OverpassQL. Many of the more
advanced features are provided by transform.py, not this file.

It contains two relevant functions:

overpassify(query: Union[FunctionType, str, List[str]]) -> str
    This is the main function of the library. It provides the public API for
    all language translation features. It is the *only* function meant to be
    called by an outside user.

parse(source, **kwargs) -> str
    This is the function which translates individual AST elements of Python
    into the relevant OverpassQL code. It is started by feeding in a string,
    which it then parses, following for each AST body element.
"""

import ast
import _ast
from functools import singledispatch
from inspect import getsource
from random import randint
from types import FunctionType

try:
    from dill.source import getsource as dillgetsource
except ImportError:
    from warnings import warn
    warn("Could not import dill. No fallback available for source fetching")

from .transform import transform

TMP_PREFIX = 'tmp'


@singledispatch
def overpassify(query):
    """This is the main overpassify function. It is implemented as a
    singledispatch item with registers for each operation.

    Possible Exceptions:
        - IndexError
        - see parse()

    Known bugs:
        - It does not consistently read the last line. The easiest workaround
          is to add a noop() to the end of your function."""
    raise TypeError('Overpassify does not support {}.'.format(type(query)))


@overpassify.register(list)
def _(funcbody):
    return parse(funcbody)


@overpassify.register(str)
def _(source):
    """This is the register which handles operations on function source code"""
    return parse(source)


@overpassify.register(FunctionType)
def _(func):
    """This is the register that handles decorator behavior. It fetches the
    func's source code, then calls overpassify on it"""
    try:
        source = getsource(func)
    except Exception:
        source = dillgetsource(func)
    return overpassify(source)


@singledispatch
def parse(source, **kwargs):
    """This is the main parser function. It is implemented as a singledispatch
    item with registers for each operation.

    Possible Exceptions:
        - IndexError
        - TypeError
        - NameError"""
    print(source)


@parse.register(str)
def _(source, **kwargs):
    return parse(ast.parse(source).body[0].body)


@parse.register(list)
def _(tree, **kwargs):
    options = ''
    if isinstance(tree[0], _ast.Expr) and isinstance(tree[0].value, _ast.Call):
        # test for Settings()
        func = tree[0].value.func.id
        if func == 'Settings':
            keywords = (parse(kwarg) for kwarg in tree[0].value.keywords)
            for key, value in keywords:
                if value[0] == '"':
                    options += '[{}:{}]\n'.format(key, value[1:-1])
                else:
                    options += '[{}:{}]\n'.format(key, value)
            tree = tree[1:]
    return options + '\n'.join(parse(expr) for expr in transform(tree))


@parse.register(_ast.Assign)
def _(assignment, **kwargs):
    if isinstance(assignment.value, (_ast.IfExp)):
        return parse(assignment.value, name=assignment.targets[0])
    else:
        return '({};) -> {};'.format(
            parse(assignment.value),
            parse(assignment.targets[0])
        )


@parse.register(_ast.Expr)
def _(expr, **kwargs):
    return parse(expr.value)


@parse.register(_ast.Name)
def _(name, **kwargs):
    return '.' + name.id


@parse.register(_ast.BinOp)
@parse.register(_ast.BoolOp)
def _(operation, **kwargs):
    """Translates binary and boolean operation statements by passing it to a
    more specialized parser with a value keyword assigned"""
    return parse(
        operation.op,
        left=operation.left,
        right=operation.right
    )


@parse.register(_ast.UnaryOp)
def _(operation, **kwargs):
    """Translates Unary operation statements by passing it to a more specialized
    parser with a value keyword assigned"""
    return parse(operation.op, value=operation.operand)


@parse.register(_ast.Add)  # TODO: make work with count()
def _(_, **kwargs):
    """Translates addition statements"""
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    try:
        float(left)
        try:
            float(right)
            return '{} + {}'.format(left, right)
        except ValueError:
            raise TypeError('You cannot add a number to a set')
    except ValueError:
        try:
            float(right)
        except ValueError:
            return '({}; {})'.format(left, right)
        else:
            raise TypeError('You cannot add a set to a number')


@parse.register(_ast.Sub)  # TODO: make work with count()
def _(_, **kwargs):
    """Translates subtraction statements"""
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    try:
        float(left)
        try:
            float(right)
            return '{} - {}'.format(left, right)
        except ValueError:
            raise TypeError('You cannot subtract a set from a number')
    except ValueError:
        try:
            float(right)
        except ValueError:
            return '({}; - {})'.format(left, right)
        else:
            raise TypeError('You cannot subtract a number from a set')


@parse.register(_ast.Mult)  # TODO: make work with count()
def _(_, **kwargs):
    """Translates multiplication statements"""
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} * {}'.format(left, right)


@parse.register(_ast.Div)  # TODO: make work with count()
def _(_, **kwargs):
    """Translates float division statements"""
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} / {}'.format(left, right)


@parse.register(_ast.FloorDiv)
def _(_, **kwargs):
    """This is a placeholder for the floor division operator. It shouldn't be
    very hard to emulate, so I'm marking it out specifically"""
    raise TypeError("Floor division is not supported by OverpassQL")


@parse.register(_ast.And)
def _(_, **kwargs):
    """Translates boolean and statements"""
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} && {}'.format(left, right)


@parse.register(_ast.Or)
def _(_, **kwargs):
    """Translates boolean or statements"""
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} || {}'.format(left, right)


@parse.register(_ast.USub)
def _(_, **kwargs):
    """Translates unary negation statements"""
    return "-{}".format(parse(kwargs['value']))


@parse.register(_ast.Not)
def _(_, **kwargs):
    """Translates boolean negation statements"""
    return "!{}".format(parse(kwargs['value']))


@parse.register(_ast.Compare)
def _(comp, **kwargs):
    """Translates comparison statements"""
    return parse(
        comp.ops[0],
        left=comp.left,
        right=comp.comparators[0]
    )


@parse.register(_ast.Eq)
def _(_, **kwargs):
    """Translates equality statements"""
    return "{} == {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.NotEq)
def _(_, **kwargs):
    """Translates non-equality statements"""
    return "{} != {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.GtE)
def _(_, **kwargs):
    """Translates greater-than-or-equal-to statements"""
    return "{} >= {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.Gt)
def _(_, **kwargs):
    """Translates greater-than statements"""
    return "{} > {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.LtE)
def _(_, **kwargs):
    """Translates less-than-or-equal-to statements"""
    return "{} <= {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.Lt)
def _(_, **kwargs):
    """Translates less-than statements"""
    return "{} < {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.keyword)
def _(keyword, **kwargs):
    return keyword.arg, parse(keyword.value)


@parse.register(_ast.Call)
def _(call, **kwargs):
    """This register checks for the various functions that have been implemented
    by OverpassQL. It is currently split into two subcalls for object call
    syntax and global call syntax. This is not a distinction drawn in
    OverpassQL, but one drawn here in order to make the code more readable."""
    name = parse(call.func)[1:]
    if name == 'noop':
        return ''
    elif '.' in name:
        return _translate_object_call(call, **kwargs)
    else:
        return _translate_global_call(call, **kwargs)


def _translate_object_call(call, **kwargs):
    name = parse(call.func)[1:]
    if name.endswith('.intersect'):
        overpasstype = (name.split('.')[0]).replace('Set', '').lower()
        return overpasstype + ''.join((parse(arg) for arg in call.args))
    elif name.endswith('.filter'):
        overpasstype = (name.split('.')[0]).lower()
        return overpasstype + parse(call.args[0])
    elif name.endswith('.recurse_up'):
        return ".{} <".format(name.split('.')[0])
    elif name.endswith('.recurse_down'):
        return ".{} >".format(name.split('.')[0])
    elif name.endswith('.recurse_up_relations'):
        return ".{} <<".format(name.split('.')[0])
    elif name.endswith('.recurse_down_relations'):
        return ".{} >>".format(name.split('.')[0])
    else:
        raise NameError('{} is not a valid Overpass type'.format(name))


def _translate_global_call(call, **kwargs):
    name = parse(call.func)[1:]
    if name == 'out':
        return _call_out(call)
    elif name in {'Set', 'Way', 'Node', 'Area', 'Relation'}:
        return _call_constructor(call, name)
    elif name == 'Regex':
        return 'Regex({})'.format(parse(call.args[0]))
    elif name == 'is_in':
        return _call_is_in(call)
    elif name == 'Around':
        return _call_around(call)
    else:
        raise NameError('{} is not a valid Overpass type'.format(name))


@parse.register(_ast.Attribute)
def _(attr, **kwargs):
    return '{}.{}'.format(parse(attr.value), attr.attr)


@parse.register(_ast.Str)
def _(string, **kwargs):
    return '"{}"'.format(string.s)


@parse.register(_ast.Num)
def _(num, **kwargs):
    return repr(num.n)


@parse.register(_ast.IfExp)
def _(ifExp, **kwargs):
    expr1 = parse(ifExp.body)
    expr2 = parse(ifExp.orelse)
    name = parse(kwargs['name']) if 'name' in kwargs else '._'
    condition = parse(ifExp.test)
    if expr2 == '()':
        return '''({expr1};) -> {name};
        (way{name}(if: {condition}); area{name}(if: {condition}); node{name}(if: {condition}); relation{name}(if: {condition});) -> {name};'''.format(
            expr1=expr1,
            name=name,
            condition=condition
        )
    elif expr2 == 'way':
        return '''({expr1};) -> {name};
        way{name}(if: {condition}) -> {name};'''.format(
            expr1=expr1,
            name=name,
            condition=condition
        )
    elif expr2 == 'area':
        return '''({expr1};) -> {name};
        area{name}(if: {condition}) -> {name};'''.format(
            expr1=expr1,
            name=name,
            condition=condition
        )
    elif expr2 == 'node':
        return '''({expr1};) -> {name};
        node{name}(if: {condition}) -> {name};'''.format(
            expr1=expr1,
            name=name,
            condition=condition
        )
    elif expr2 == 'relation':
        return '''({expr1};) -> {name};
        relation{name}(if: {condition}) -> {name};'''.format(
            expr1=expr1,
            name=name,
            condition=condition
        )
    else:
        tmpname = '.' + TMP_PREFIX + name[1:]
        return '''({expr1};) -> {name};
        (way{name}(if: {condition}); area{name}(if: {condition}); node{name}(if: {condition}); relation{name}(if: {condition});) -> {name};
        ({expr2};) -> {tmpname};
        ({name}; way{tmpname}(if: !({condition})); area{tmpname}(if: !({condition})); node{tmpname}(if: !({condition})); relation{tmpname}(if: !({condition}));) -> {name};'''.format(
            expr1=expr1,
            expr2=expr2,
            name=name,
            tmpname=tmpname,
            condition=condition
        )


@parse.register(_ast.For)
def _(forExp, **kwargs):
    collection = parse(forExp.iter)
    slot = parse(forExp.target)
    return '''foreach{collection}->{slot}(
        {body});'''.format(
        collection=collection,
        slot=slot,
        body="\n".join(parse(expr) for expr in forExp.body)
    )


@parse.register(_ast.Ellipsis)
def _(e, **kwargs):
    return ...


@parse.register(_ast.NameConstant)
def _(const, **kwargs):
    return const.value


@parse.register(_ast.Subscript)
def _(expr, **kwargs):
    return "{}[{}]".format(
        parse(expr.value)[1:],
        parse(expr.slice.value)
    )


def parse_tags(key, value):
    if value is None:
        return '[!"{}"]'.format(key)
    elif value == (...):
        return '["{}"]'.format(key)
    elif value.startswith('Regex('):
        return '["{}"~{}]'.format(key, value[6:-1])
    elif value.startswith('NotRegex('):
        return '["{}"!~{}]'.format(key, value[9:-1])
    else:
        return '["{}"="{}"]'.format(key, value)


def _call_constructor(call, name):
    """This function provides a translation for set construction calls. It is
    extracted from the main call translator in order to provide additional code
    clarity."""
    if name == 'Set':
        return '({})'.format('; '.join(parse(arg) for arg in call.args))
    overpasstype = (name.split('.')[0]).lower()
    tags = "".join(parse_tags(*parse(kwarg)) for kwarg in call.keywords)
    if len(call.args) == 1:
        arg = parse(call.args[0])
        if arg.startswith('around'):
            return '{}{}(around{})'.format(
                overpasstype,
                tags,
                arg[6:]
            )
        elif arg.isnumeric():
            return '{}{}({})'.format(
                overpasstype,
                tags,
                arg
            )
        else:
            return '{}{}({})'.format(
                overpasstype,
                tags,
                'area' + arg
            )
    elif len(call.args) == 0:
        return '{}{}'.format(overpasstype, tags)
    else:
        raise IndexError('Locator calls supports 1 or 0 positional arguments')


def _call_out(call):
    """This function provides a translation for the out statement. It is
    extracted from the main call translator in order to provide additional code
    clarity."""
    if len(call.args) == 0:
        element = '._'
    else:
        element = parse(call.args[0])
    out_channels = {parse(kwarg)[0] for kwarg in call.keywords}
    ret = ''
    if 'count' in out_channels:
        ret += element + ' out count;\n'
        out_channels.remove('count')
        if len(out_channels) == 0:
            return ret
    return ret + element + ' out {};'.format(' '.join(out_channels))


def _call_is_in(call):
    """This function provides a translation for the is_in statement. It is
    extracted from the main call translator in order to provide additional code
    clarity."""
    num = len(call.args)
    if num == 0:
        return 'is_in'
    elif num == 1:
        return parse(call.args[0]) + ' is_in'
    elif num == 2:
        return 'is_in({}, {})'.format(*call.args)
    else:
        raise IndexError("is_in needs 0-2 arguments, {} given".format(num))


def _call_around(call):
    """This function provides a translation for the around statement. It is
    extracted from the main call translator in order to provide additional code
    clarity."""
    args = (parse(arg) for arg in call.args)
    if len(call.args) == 1:
        return 'around:{}'.format(*args)
    elif len(call.args) == 2:
        return 'around{}:{}'.format(*args)
    else:
        return 'around:{},{},{}'.format(*args)
