"""This is the syntax transformation file. It contains functions which
translate some more complicated Python syntaxes into simpler (if less
performant) ones which can be implemented in OverpassQL. All code which is left
after this process can be translated by the functions in overpassify.py.

It contains two relevant functions:

transform(body: list) -> list
    The "public" facing function which provides all transformation services

scan(body: Union[list, _ast.If], **kwargs) -> Bool
    The function which scans for ternery statemenets in the underlying
    structure. If none is seen, it returns False.
"""

import ast
import _ast
from copy import copy, deepcopy
from functools import singledispatch
from random import randint

from pprint import pprint

TMP_PREFIX = 'tmp'


def transform(body):
    """This is the main syntax transformation function. It takes Python
    syntaxes which cannot be directly implemented in OverpassQL, and translates
    them to a logical equivalent. This normally results in less efficient
    operations, with many temporary variables."""
    changed = True
    transformed = []
    # pprint(body)
    while changed:
        changed = _transform(body, body=transformed, top=True)
        body, transformed = transformed, []
        # pprint(body)
    return body


@singledispatch
def _transform(item, body=None, top=False):
    if top:
        body.append(copy(item))
    return False


@_transform.register(list)
def _(item, body=None, top=False):
    changed = False
    for statement in item:
        changed = _transform(statement, body=body, top=True) or changed
    return changed


@_transform.register(_ast.For)
def _(item, body=None, top=False):
    new_body = []
    if scan(item.body, _ast.Break):
        body.extend(transform_break(item))
        return True
    elif scan(item.body, _ast.Continue):
        body.extend(transform_continue(item))
        return True
    elif _transform(item.body, body=new_body, top=True):
        item.body = new_body
        body.append(item)
        return True
    elif not isinstance(item.iter, _ast.Name):
        syntax = ast.parse('tmpfor{} = _'.format(randint(0, 2**32))).body[0]
        syntax.value = item.iter
        item.iter = syntax.targets[0]
        body.extend((syntax, item))
        return True
    elif top:
        body.append(item)
        return False


@_transform.register(_ast.If)
def _(item, body=None, top=False):
    if_id = 'tmpif{}'.format(randint(0, 2**32))
    syntax = ('{tmpname}r = Relation(2186646)\n'
    '{tmpname} = {tmpname}r if test else Set()\n'
    'for tmp_ in {tmpname}:    a()').format(tmpname=if_id)
    init, test, loop = ast.parse(syntax).body
    test.value.test = item.test
    loop.body = item.body
    body.extend((init, test, loop))
    if len(item.orelse) > 0:
        syntax = ('{tmpname} = {tmpname}r if not (test) else Set()\n'
        'for tmp_ in {tmpname}:    a()').format(tmpname=if_id)
        test2, loop2 = ast.parse(syntax).body
        test2.value.test = item.test
        loop2.body = item.orelse
        body.extend((test2, loop2))
    return True


@_transform.register(_ast.Expr)
def _(item, body=None, top=False):
    new_body = []
    if _transform(item.value, body=new_body, top=top):
        body.extend(new_body)
        return True
    else:
        body.append(item)
        return False


@_transform.register(_ast.Assign)
def _(item, body=None, top=False):
    new_body = []
    if _transform(item.value, body=new_body, top=top):
        item.value = new_body[-1]
        new_body = new_body[:-1] + [item]
        body.extend(new_body)
        return True
    else:
        body.append(item)
        return False


@_transform.register(_ast.Call)
def _(item, body=None, top=False):
    if top and len(item.args) != 0:
        if isinstance(item.args[0], _ast.Call):
            _transform(item.args[0], body=body, top=top)
        if not isinstance(item.args[0], (_ast.Name, _ast.Num)):
            num = randint(0, 2**32)
            syntax = ast.parse('tmpcall{} = b'.format(num)).body[0]
            syntax.value = item.args[0]
            item.args[0] = syntax.targets[0]
            body.extend((syntax, item))
            return True
    return False


@singledispatch
def scan(body, item_class):
    return False


@scan.register(list)
def _(body, item_class):
    for statement in body:
        if isinstance(statement, item_class) or scan(statement, item_class):
            return True


@scan.register(_ast.If)
def _(item, item_class):
    for part in (item.body, item.orelse):
        if isinstance(part, item_class) or scan(part, item_class):
            return True


def transform_break(item, name=''):
    if name == '':
        name = 'tmpbreak{}'.format(randint(0, 2**32))
    assignment = ast.parse('{} = Relation(2186646)'.format(name)).body[0]
    condition = ast.parse('for _ in {}: a()'.format(name)).body[0]
    body = [assignment, item]
    new_body = []
    for statement in item.body:
        cond = deepcopy(condition)
        if isinstance(statement, _ast.If):
            statement = transform_break(statement, name=name)[1]
        elif isinstance(statement, _ast.Break):
            statement = ast.parse('{0} = Way.filter({0})'.format(name)).body[0]
        cond.body = [statement]
        new_body.append(cond)
    item.body = new_body
    if len(item.orelse) > 0:
        assignment = ast.parse('{}else=Relation(2186646)'.format(name)).body[0]
        didbreak = ast.parse('for _ in {}: a()'.format(name)).body[0]
        didbreak.body = ast.parse('{0}else=Way.filter({0})'.format(name)).body
        condition = ast.parse('for _ in {}else: a()'.format(name)).body[0]
        condition.body = item.orelse
        body += [assignment, didbreak, condition]
        item.orelse = []
    return body


def transform_continue(item, name=''):
    if name == '':
        name = 'tmpcontinue{}'.format(randint(0, 2**32))
    assignment = ast.parse('{} = Relation(2186646)'.format(name)).body[0]
    condition = ast.parse('for _ in {}: a()'.format(name)).body[0]
    body = [item]
    new_body = [assignment]
    for statement in item.body:
        cond = deepcopy(condition)
        if isinstance(statement, _ast.If):
            statement = transform_continue(statement, name=name)[1]
        elif isinstance(statement, _ast.Continue):
            statement = ast.parse('{0} = Way.filter({0})'.format(name)).body[0]
        cond.body = [statement]
        new_body.append(cond)
    item.body = new_body
    return body
