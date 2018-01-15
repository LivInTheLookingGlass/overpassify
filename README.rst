overpassify
===========

A Python to OverpassQL transpiler, now on both `GitHub 
<https://github.com/LivInTheLookingGlass/overpassify>`__ and `GitLab
<https://gitlab.com/LivInTheLookingGlass/overpassify>`__

`OverpassQL <http://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL>`__
is the language used to query features on OpenStreetMap. Unfortunately,
it's not very readable.

The goal here is to enable people to write in a more developer-friendly
language, and still have it work on the existing infrastructure. As of
now, ``overpassify`` can take a snippet like:

.. code:: python

    from overpassify import overpassify

    @overpassify
    def query():
        search = Area(3600134503)
        ways = Way(search, highway=...)
        nodes = Node(search)
        out(ways, geom=True, count=True)
        out(nodes, geom=True, count=True)
        noop()

And from that generate:

.. code::

    (area(3600134503);) -> .search;
    (way["highway"](area.search);) -> .ways;
    (node(area.search);) -> .nodes;
    .ways out count;
    .ways out geom;
    .nodes out count;
    .nodes out geom;

That last ``noop()`` is because of `issue
#2 <https://github.com/LivInTheLookingGlass/overpassify/issues/2>`__. And as a
note, this library assumes you never use a variable name of the form
``tmp*``. That format will probably be changed to something even less
likely in the future, but some translations (for instance, a full
ternary) *require* the use of temporary variables.

Overview
--------

I'll say this from the outset: ``overpassify`` will support a subset of
Python. Some things are just too difficult (and maybe impossible) to
automatically translate. Functions are an example of that.

On the other hand, it will try to support a superset of easily-usable
OverpassQL. Some of those extra features won't be as efficient as their
Python counterparts, but they will be available.

Currently ``overpassify`` supports 41/56 of the features listed in the
OverpassQL guide, and additionally supports ternary statements, ``if`` blocks,
``break``, and ``continue``.

Classes
-------

This library provides wrappers for five types. ``Set()``, ``Node()``,
``Way()``, ``Area()``, and ``Relation()``. Those last four are *all*
considered subclasses of ``Set()``.

This library also provides support for strings and numbers. In the
future it will provide support for regex and other things in specific
places.

(Note: Currently nested constructors have some problems in
implementation)

Assignment
----------

This works about the way you'd expect it to. There are a couple caveats
though.

#. You cannot assign a non-\ ``Set()`` to a variable. This means only
   those five classes listed above.
#. You cannot assign multiple variables in one line. No ``a, b = b, a``,
   and the like. This could *potentially* be changed later.

Number and Set Arithmetic
-------------------------

Another supported feature is the ability to manipulate these sets and
numbers.

Adding sets will produce the union of those sets. Adding numbers will
produce their sum.

Subtracting **two** sets will produce their difference. Subtracting
numbers will do the same.

Set Filtering
-------------

You are also allowed to filter a ``Set()``'s contents by type. For
instance, ``Way.filter(<some set>)`` would yield all the ways within
``<some set>``.

Set intersections
-----------------

A similar process will allow you to take the intersection of arbitrary
numbers of **named** sets. So ``Set.intersect(a, b)`` will yield all
elements common between ``a`` and ``b``. You cannot, at the moment, use
an expression inside this function. It **must** be predefined.

You can also use this in tandem with Set Filtering. So
``Area.intersect(a, b)`` would yield only the areas common between ``a``
and ``b``.

Searching for Sets
------------------

This library also supports *most* of the ways OverpassQL can search for
information. This currently includes:

#. Checking within an area (or set of areas)
#. Fetching by ID
#. Tag matching
#. Conditional filters (see next section)

The first two are just given as arguments to the constructor. If you put
in ``Way(12345)``, that will find the Way with ID 12345. If you put in
``Way(<some area>)``, it will return all ways within that area.

You can also define areas using the ``Around()`` function. This has two
useful overloads. The first takes the form
``Around(<some set>, <radius in meters>)``. The second takes the form
``Around(<radius in meters>, <latitude>, <longitude>)``.

Tag matching can be done with keyword arguments. So if you look for
``Node(highway="stop")``, that will find you all stop signs. It also
supports existence checking (``Way(highway=...)``), and non-existence
checking (``Area(landuse=None)``), and regex matching
(``Way(highway=Regex("path|cycleway|sidewalk"))``).

You can also search by both an area and a filter. For instance:
``Way(<your hometown>, maxspeed=None)``.

Ternary Expressions and Conditional Filters
-------------------------------------------

You can also filter using the familiar ``a if b else c``. This would
mean that if ``b`` is truthy, ``a`` should become ``b``, and otherwise
become ``c``.

Unfortunately, since this is not a native feature to OverpassQL, it ends
up evaluating both sides of that statement.

If you want ``c`` to be an empty set, however, we can optimize that. So
``foo = a if b else <type>()`` is the syntax to use there.

Additional performance is lost because OverpassQL does not support a
conditional being the *only* filter. This means that we need to provide
some other filter, and one in current use is to divide it by type and
reconstruct. Because of this, filtering down to the appropriate set type yields
significantly batter performance.

Returning Data
--------------

In OverpassQL, data can be returned in pieces throughout the function.
It's more equivalent to Python's ``yield`` than ``return``. The function
we use for that here is ``out()``.

``out()`` takes in one positional argument, and many possible keyword
arguments. It yields data for the positional argument using all the
types defined in the keywords.

For instance ``out(<set of nodes>, geom=True, body=True, qt=True)``
would return all the data that MapRoulette needs to draw those points on
their map.

As a sidenote, the value given for these keywords is never actually
checked. It could as easily be ``geom=False`` as ``geom=True``, and
``overpassify`` will not care.

For-Each Loop
-------------

Here you can use the traditional Python for loop:

.. code:: python

    for way in ways:
        out(way, geom=True)

It does not yet support the else clause, and though it supports ``break`` and
``continue``, please be aware that this will dramatically slow runtime in that
loop.

If Statements
-------------

This is a feature that OverpassQL cannot do without some emulation. So
what we do here is:

#. Grab an individual item that will probably be stable over long
   periods of time; in this case, the ``Relation()`` representing
   Antarctica
#. Use a conditional filter on that relation to get a one item or zero
   item ``Set()``
#. Iterate over that in a for loop
#. If there is an else clause, use a conditional filter with the
   negation of the test given to get a one item or zero item ``Set()``
#. Iterate over the else clause in a for loop

Settings
--------

We also provide a wrapper for the option headers. Note that this will
raise an error if it's not on the first line of your query.

The valid keywords for ``Settings()`` are as follows:

-  ``timeout``: The maximum number of seconds you would like your query
   to run for
-  ``maxsize``: The maximum number of bytes you would like your query to
   return
-  ``out``: The format to return in. It defaults to XML, but you can set
   it to ``"json"`` or a variant on ``"csv"``, as described `in the
   OverpassQL
   spec <http://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#Output_Format_.28out.29>`__
-  ``bbox``: The string describing a global bounding box. It is used to
   limit the area your query can encompass, and should take the form
   ``"<southern lat>,<western lon>,<northern lat>,<eastern lon>"``
-  ``date``: The string describing what date you would like to query
   for. This allows you to look at past database states. Note that it
   needs an extra set of quotes, so it would look like
   ``date='"2012-09-12T06:55:00Z"'``
-  ``diff``: Similar to the above, except it will return the difference
   between that query run at each time. If you give one time, it will
   assume you want to compare to now. It would look like
   ``diff='"2012-09-12T06:55:00Z","2014-12-24T13:33:00Z"'``
-  ``adiff``: Similar to the above, except that it tells you what
   happened to each absent element

Rough Translation Table
-----------------------

+-----------------------+---------------------------------------+----------------------------------------------------+
| Feature               | OverpassQL                            | Python                                             |
+=======================+=======================================+====================================================+
| Assignment            | ``<expr> -> .name``                   | ``name = <expr>``                                  |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Unions                | ``(<set>; ...; <set>)``               | ``<set> + ... + <set>``                            |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Difference            | ``(<set> - <set>)``                   | ``<set> - <set>``                                  |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Intersection          | ``.<set>.<set>``                      | ``Set.intersect(<set>, <set>)``                    |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Type-filtering        | ``way.<set>``                         | ``Way.filter(<set>)``                              |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Searching             |                                       |                                                    |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..By ID               | ``area(1)`` or ``way(7)``             | ``Area(1)`` or ``Way(7)``                          |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..In an area          | ``way(area.<set>)``                   | ``Way(<set>)``                                     |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..By tags             | ``way["tag"="value"]``                | ``Way(tag=value)``                                 |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..By tag existence    | ``way["tag"]``                        | ``Way(tag=...)``                                   |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..By tag nonexistence | ``way[!"tag"]``                       | ``Way(tag=None)``                                  |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..By regex            | ``way["highway"~"a|b"](area.<set>)``  | ``Way(<set>, highway=Regex("a|b"))``               |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..By inverse regex    | ``way["highway"!~"a|b"](area.<set>)`` | ``Way(<set>, highway=NotRegex("a|b"))``            |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..In area + tag       | ``way["highway"](area.<set>)``        | ``Way(<set>, highway=...)``                        |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Ternary               | very long                             | ``<expr> if <condition> else <expr>``              |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Conditional Filter    | ``<type>.<set>(if: <condition>)``     | ``<expr> if <condition> else <type>()``            |
+-----------------------+---------------------------------------+----------------------------------------------------+
| For Loop              | ``foreach.<set>->.<each>(<body>)``    | ``for <each> in <set>:\n    <body>``               |
+-----------------------+---------------------------------------+----------------------------------------------------+
| If Statement          | very long                             | ``if <condition>:\n    <body>\nelse:\n    <body>`` |
+-----------------------+---------------------------------------+----------------------------------------------------+
| Recursing             |                                       |                                                    |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..Up                  | ``.a <`` or ``.a < -> .b``            | ``a.recurse_up()`` or ``b = a.recurse_up()``       |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..Up (w/ relations)   | ``.a <<`` or ``.a << -> .b``          | ``a.recurse_up_relations()``                       |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..Down                | ``.a >`` or ``.a > -> .b``            | ``a.recurse_down()``                               |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..Down (w/ relations) | ``.a >>`` or ``.a >> -> .b``          | ``a.recurse_down_relations()``                     |
+-----------------------+---------------------------------------+----------------------------------------------------+
| is_in filers          |                                       |                                                    |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..On a set            | ``.a is_in -> .areas_with_part_of_a`` | ``areas_containing_part_of_a = is_in(a)``          |
+-----------------------+---------------------------------------+----------------------------------------------------+
| ..On a lat/lon pair   | ``is_in(0, 0) -> .areas_with_0_0``    | ``areas_containing_0_0 = is_in(0, 0)``             |
+-----------------------+---------------------------------------+----------------------------------------------------+

Features Not Yet Implemented
----------------------------

#. Filters

   #. Recursion Functions
   #. Filter By Bounding Box
   #. Filter By Polygon
   #. Filter By "newer"
   #. Filter By Date Of Change
   #. Filter By User
   #. Filter By Area Pivot

#. ID Evaluators

   #. id() And type()
   #. is\_tag() And Tag Fetching
   #. Property Count Functions

#. Aggregators

   #. Union and Set
   #. Min and Max
   #. Sum
   #. Statistical Counts

#. Number Normalizer
#. Date Normalizer
