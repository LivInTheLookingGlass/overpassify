import ast, _ast
from copy import copy
from functools import singledispatch
from random import randint

TMP_PREFIX = 'tmp'


def transform(body):
    changed = True
    transformed = []
    while changed:
        changed = False
        for statement in body:
            changed = changed or _transform(statement, body=transformed, top=True)
        body, transformed = transformed, []
    return body


@singledispatch
def _transform(item, body=None, top=False):
    if top:
        body.append(copy(item))
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
