import ast, _ast
from functools import singledispatch
from inspect import getsource
from types import FunctionType

from dill.source import getsource as dillgetsource

TMP_PREFIX = 'tmp'

@singledispatch
def overpassify(query):
    raise TypeError('Overpassify does not support {}.'.format(type(query)))


@overpassify.register(str)
def _(source):
    return parse(source)


@overpassify.register(FunctionType)
def _(func):
    try:
        source = getsource(func)
    except Exception:
        source = dillgetsource(func)
    return overpassify(source)


@singledispatch
def parse(source, **kwargs):
    print(source)


@parse.register(str)
def _(source, **kwargs):
    tree = ast.parse(source).body[0].body
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
    return options + '\n'.join(parse(expr) for expr in tree)


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
    return parse(
        operation.op,
        left=operation.left,
        right=operation.right
    )


@parse.register(_ast.UnaryOp)
def _(operation, **kwargs):
    return parse(operation.op, value=operation.operand)


@parse.register(_ast.Add)  # TODO: make work with count()
def _(_, **kwargs):
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
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} * {}'.format(left, right)


@parse.register(_ast.Div)  # TODO: make work with count()
def _(_, **kwargs):
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} / {}'.format(left, right)


@parse.register(_ast.And)
def _(_, **kwargs):
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} && {}'.format(left, right)


@parse.register(_ast.Or)
def _(_, **kwargs):
    left, right = parse(kwargs['left']), parse(kwargs['right'])
    return '{} || {}'.format(left, right)


@parse.register(_ast.USub)
def _(_, **kwargs):
    return "-{}".format(parse(kwargs['value']))


@parse.register(_ast.Not)
def _(_, **kwargs):
    return "!{}".format(parse(kwargs['value']))


@parse.register(_ast.Compare)
def _(comp, **kwargs):
    return parse(
        comp.ops[0],
        left=comp.left,
        right=comp.comparators[0]
    )


@parse.register(_ast.Eq)
def _(_, **kwargs):
    return "{} == {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.NotEq)
def _(_, **kwargs):
    return "{} != {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.GtE)
def _(_, **kwargs):
    return "{} >= {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.Gt)
def _(_, **kwargs):
    return "{} > {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.LtE)
def _(_, **kwargs):
    return "{} <= {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.Lt)
def _(_, **kwargs):
    return "{} < {}".format(parse(kwargs['left']), parse(kwargs['right']))


@parse.register(_ast.keyword)
def _(keyword, **kwargs):
    return keyword.arg, parse(keyword.value)


@parse.register(_ast.Call)
def _(call, **kwargs):
    name = parse(call.func)[1:]
    if name.endswith('.intersect'):
        overpasstype = (name.split('.')[0]).replace('set', '').lower()
        return overpasstype + ''.join((parse(arg) for arg in call.args))
    elif name.endswith('.filter'):
        overpasstype = (name.split('.')[0]).lower()
        return overpasstype + parse(call.args[0])
    elif name == 'out':
        return call_out(call)
    elif name in {'Set', 'Way', 'Node', 'Area', 'Relation'}:
        return call_constructor(call, name)
    elif name == 'Regex':
        return 'Regex({})'.format(parse(call.args[0]))
    elif name == 'Around':
        args = (parse(arg) for arg in call.args)
        if len(call.args) == 1:
            return 'around:{}'.format(*args)
        elif len(call.args) == 2:
            return 'around{}:{}'.format(*args)
        else:
            return 'around:{},{},{}'.format(*args)
    else:
        raise NameError('{} is not the name of a valid Overpass type'.format(name))


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
    if expr2 != '()':
        tmpname = '.' + TMP_PREFIX + name[1:]
        return '''{expr1} -> {name};
        (way{name}(if: {condition}); area{name}(if: {condition}); node{name}(if: {condition}); relation{name}(if: {condition});) -> {name};
        {expr2} -> {tmpname};
        ({name}; way{tmpname}(if: !({condition})); area{tmpname}(if: !({condition})); node{tmpname}(if: !({condition})); relation{tmpname}(if: !({condition}));) -> {name};'''.format(
            expr1=expr1,
            expr2=expr2,
            name=name,
            tmpname=tmpname,
            condition=condition
        )
    else:
        return '''{expr1} -> {name};
        (way{name}(if: {condition}); area{name}(if: {condition}); node{name}(if: {condition}); relation{name}(if: {condition});) -> {name};'''.format(
            expr1=expr1,
            name=name,
            condition=condition
        )


@parse.register(_ast.If)
def _(ifBlock, **kwargs):
    tmpname = TMP_PREFIX + 'if'
    test = parse(ifBlock.test)
    ret = '''(relation(2186646);) -> .{tmpname};
    (relation.{tmpname}(if: {test});) -> .{tmpname}body;
    foreach.{tmpname}body(
        {body});'''.format(
        tmpname=tmpname,
        test=test,
        body='\n        '.join(parse(expr) for expr in ifBlock.body)
    )
    if len(ifBlock.orelse) > 0:
        ret += '''
        (relation.{tmpname}(if: !({test}));) -> .{tmpname}else;
        foreach.{tmpname}else(
            {body});'''.format(
            tmpname=tmpname,
            test=test,
            body='\n        '.join(parse(expr) for expr in ifBlock.orelse)
        )
    return ret


@parse.register(_ast.For)
def _(forExp, **kwargs):
    collection = parse(forExp.iter)
    slot = parse(forExp.target)
    orelse = forExp.orelse
    if len(orelse) > 0:
        raise SyntaxError("overpassify does not yet support for-each-if")
    tmpfor = TMP_PREFIX + 'for'
    return '''({collection};) -> .{tmpfor};
    foreach.{tmpfor}->{slot}(
        {body});'''.format(
        collection=collection,
        slot=slot,
        body=";\n".join(parse(expr) for expr in forExp.body),
        tmpfor=tmpfor
    )


@parse.register(_ast.Ellipsis)
def _(e, **kwargs):
    return ...


@parse.register(_ast.NameConstant)
def _(const, **kwargs):
    return const.value


def parse_tags(filters):
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


def call_constructor(call, name):
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
        raise IndexError('Calls to locators do not support multiple positional arguments')


def call_out(call):
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
