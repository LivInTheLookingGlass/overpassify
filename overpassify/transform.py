import ast, _ast
from copy import copy
from functools import singledispatch
from random import randint

from pprint import pprint

TMP_PREFIX = 'tmp'


def transform(body):
    changed = True
   # print(id(body))
    transformed = []
    pprint(body)
    while changed:
        changed = _transform(body, body=transformed, top=True)
        body, transformed = transformed, []
        pprint(body)
    return body


@singledispatch
def _transform(item, body=None, top=False):
    if top:
        body.append(copy(item))
    return False


@_transform.register(list)
def _(item, body=None, top=False):
    changed = False
   # print("iterating")
    for statement in item:
       # print(statement)
        changed = _transform(statement, body=body, top=True) or changed
    return changed


@_transform.register(_ast.For)
def _(item, body=None, top=False):
    new_body = []
   # print(id(new_body))
    if _transform(item.body, body=new_body, top=True):
        item.body = new_body
        body.append(item)
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
