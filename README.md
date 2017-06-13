# overpassify
A Python to OverpassQL transpiler

[OverpassQL](http://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) is the language used to query features on OpenStreetMap. Unfortunately, it's not very readable.

The goal here is to enable people to write in a more developer-friendly language, and still have it work on the existing infrastructure. As of now, `overpassify` can take a snippet like:

```Python
from overpassify import overpassify

@overpassify
def query():
    search = Area(3600134503)
    ways = Way(search, highway=...)
    nodes = Node(search)
    out(ways, geom=True, count=True)
    out(nodes, geom=True, count=True)
    out()
```

And from that generate:

```OverpassQL
(area(3600134503);) -> .search;
(way["highway"](area.search);) -> .ways;
(node(area.search);) -> .nodes;
.ways out count;
.ways out geom;
.nodes out count;
.nodes out geom;
```

That last `out()` is because of [issue #2](https://github.com/LivInTheLookingGlass/overpassify/issues/2). And as a note, this library assumes you never use a variable name of the form `tmp*`. That format will probably be changed to something even less likely in the future, but some translations (for instance, a full ternary) *require* the use of temporary variables.

## Overview

I'll say this from the outset: `overpassify` will support a subset of Python. Some things are just too difficult (and maybe impossible) to automatically translate. Functions are an example of that.

On the other hand, it will try to support a superset of easily-usable OverpassQL. Some of those extra features won't be as efficient as their Python counterparts, but they will be available.

## Classes

This library provides wrappers for five types. `Set()`, `Node()`, `Way()`, `Area()`, and `Relation()`. Those last four are *all* considered subclasses of `Set()`.

This library also provides support for strings and numbers. In the future it will provide support for regex and other things in specific places.

(Note: Currently nested constructors have some problems in implementation)

## Assignment

This works about the way you'd expect it to. There are a couple caveats though.

1. You cannot assign a non-`Set()` to a variable. This means only those five classes listed above.
2. You cannot assign multiple variables in one line. No `a, b = b, a`, and the like. This could *potentially* be changed later.

## Number and Set Arithmetic

Another supported feature is the ability to manipulate these sets and numbers.

Adding sets will produce the union of those sets. Adding numbers will produce their sum.

Subtracting **two** sets will produce their difference. Subtracting numbers will do the same.

## Set Filtering

You are also allowed to filter a `Set()`'s contents by type. For instance, `Way.filter(<some set>)` would yield all the ways within `<some set>`.

## Set intersections

A similar process will allow you to take the intersection of arbitrary numbers of **named** sets. So `Set.intersect(a, b)` will yield all elements common between `a` and `b`. You cannot, at the moment, use an expression inside this function. It **must** be predefined.

You can also use this in tandem with Set Filtering. So `Area.intersect(a, b)` would yield only the areas common between `a` and `b`.

## Searching for Sets

This library also supports *most* of the ways OverpassQL can search for information. This currently includes:

1. Checking within an area (or set of areas)
2. Fetching by ID
3. Tag matching
4. Conditional filters (see next section)

The first two are just given as arguments to the constructor. If you put in `Way(12345)`, that will find the Way with ID 12345. If you put in `Way(<some area>)`, it will return all ways within that area.

Tag matching can be done with keyword arguments. So if you look for `Node(highway="stop")`, that will find you all stop signs. It also supports existence checking (`Way(highway=...)`), and non-existence checking (`Area(landuse=None)`). In the future this will support regex matching (`Way(highway=Regex("path|cycleway|sidewalk"))`).

You can also search by both an area and a filter. For instance: `Way(<your hometown>, maxspeed=None)`.

## Ternary Expressions and Conditional Filters

You can also filter using the familiar `a if b else c`. This would mean that if `b` is truthy, `a` should become `b`, and otherwise become `c`.

Unfortunately, since this is not a native feature to OverpassQL, it ends up evaluating both sides of that statement.

If you want `c` to be an empty set, however, we can optimize that. So `foo = a if b else Set()` is the syntax to use there.

Additional performance is lost because OverpassQL does not support a conditional being the *only* filter. This means that we need to provide some other filter, and one in current use is to divide it by type and reconstruct. There is some progress which can be made here, but it's not yet a priority.

## Returning Data

In OverpassQL, data can be returned in pieces throughout the function. It's more equivalent to Python's `yield` than `return`. The function we use for that here is `out()`.

`out()` takes in one positional argument, and many possible keyword arguments. It yields data for the positional argument using all the types defined in the keywords.

For instance `out(<set of nodes>, geom=True, body=True, qt=True)` would return all the data that MapRoulette needs to draw those points on their map.

As a sidenote, the value given for these keywords is never actually checked. It could as easily be `geom=False` as `geom=True`, and `overpassify` will not care.

## For-Each Loop

Here you can use the traditional Python for loop:

```Python
for way in ways:
    out(way, geom=True)
```

It does not yet support the else clause, and I'm not certain that it will, as there isn't a `break` equivalent in OverpassQL.

## If Statements

This is a feature that OverpassQL cannot do without some emulation. So what we do here is:

1. Grab an individual item that will probably be stable over long periods of time; in this case, the `Relation()` representing Antarctica
2. Use a conditional filter on that relation to get a one item or zero item `Set()`
3. Iterate over that in a for loop
4. If there is an else clause, use a conditional filter with the negation of the test given to get a one item or zero item `Set()`
5. Iterate over the else clause in a for loop

That would be why I say that some of these operations are less efficient than their Python counterparts.

## Rough Translation Table

| Feature            | OverpassQL                        | Python                                           |
| ------------------ | --------------------------------- | ------------------------------------------------ |
| Assignment         | `<expr> -> .name`                 | `name = <expr> `                                 |
| Unions             | `(<set>; ...; <set>)`             | `<set> + ... + <set>`                            |
| Difference         | `(<set> - <set)`                  | `<set> - <set>`                                  |
| Intersection       | `.<set>.<set>`                    | `Set.intersect(<set>, <set>)`                    |
| Type-filtering     | `way.<set>`                       | `Way.filter(<set>)`                              |
| Searching          |                                   |                                                  |
| ..By ID            | `area(1)` or `way(7)`             | `Area(1)` or `Way(7)`                            |
| ..In an area       | `way(area.<set>)`                 | `Way(<set>)`                                     |
| ..By tags          | `way["tag"="value"]`              | `Way(tag=value)`                                 |
| ..In area + tag    | `way["highway"="*"](area.<set>)`  | `Way(<set>, highway="*")`                        |
| Ternary            | very long                         | `<expr> if <condition> else <expr>`              |
| Conditional Filter | `<type>.<set>(if: <condition>)`\* | `<expr> if <condition> else Set()`               |
| For Loop           | `foreach.<set>->.<each>(<body>)`  | `for <each> in <set>:\n    <body>`               |
| If Statement       | very long                         | `if <condition>:\n    <body>\nelse:\n    <body>` |

\* `overpassify` will allow for mixed sets here by repeating for each type. This may be optimized better in the future.
