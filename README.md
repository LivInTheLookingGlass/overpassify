# overpassify
A Python to OverpassQL transpiler

[OverpassQL](http://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) is the language used to query features on OpenStreetMap. Unfortunately, it's not very readable. Here's an example I've written. It finds intersections without traffic signals or stop signs nearby.

```OverpassQL
[timeout:1400];
(area(3600134503); area(3600134502))->.searchArea;
(way["highway"]["highway"!~"track|cycleway|footway|path|service"]["access"!="private"](area.searchArea))->.ways;
// get all nodes in area
>->.nodes;
// filter for nodes only
(node.nodes[!"highway"])->.nodes;
// filter for intersections
foreach.nodes->.x(
  (.x; .x<;) -> .all;
  way.all["highway"]["highway"!~"track|cycleway|footway|path|service"] -> .parents;
  node.all(if: parents.count(ways) > 1);
  foreach._->.point(
    .point;
    node["highway"~"stop|give_way|traffic_signals"](around:20.0);
    node.point(if: count(nodes) < 1);
    out body geom qt;
  );
);
```

The goal here is to enable people to write in a more developer-friendly language, and still have it work on the existing infrastructure.

As of now, `overpassify` can take a snippet like:

```Python
from overpassify import overpassify

@overpassify
def query():
    search = Area(3600134503)
    ways = Way(search)
    nodes = Node(search)
    out(ways, geom=True, count=True)
    out(nodes, geom=True, count=True)
    out()
```

And from that generate
```OverpassQL
(area(3600134503);) -> .search;
(way(area.search);) -> .ways;
(node(area.search);) -> .nodes;
.ways out count;
.ways out geom;
.nodes out count;
.nodes out geom;
```

That last `out()` is because of [issue #2](https://github.com/LivInTheLookingGlass/overpassify/issues/2). And as a note, this library assumes you never use a variable name of the form `tmp*`. That format will probably be changed to something even less likely in the future, but some translations (for instance, a full ternary) *require* the use of temporary variables.

Here's a somewhat-complete feature table:

| Feature            | OverpassQL                        | Python                              |
| ------------------ | --------------------------------- | ----------------------------------- |
| Assignment         | `<expr> -> .name`                 | `name = <expr> `                    |
| Unions             | `(<set>; ...; <set>)`             | `<set> + ... + <set>`               |
| Difference         | `(<set> - <set)`                  | `<set> - <set>`                     |
| Intersection       | `.<set>.<set>`                    | `Set.intersect(<set, <set>)`        |
| Type-filtering     | `way.<set>`                       | `Way.filter(<set)`                  |
| Searching          |                                   |                                     |
| ..By ID            | `area(1)` or `way(7)`             | `Area(1)` or `Way(7)`               |
| ..In an area       | `way(area.<set>)`                 | `Way(<set>)`                        |
| ..By tags          | `way["tag"="value"]`              | `Way(tag=value)`                    |
| ..In area + tag    | `way["highway"="*"](area.<set>)`  | `Way(<set>, highway="*"`            |
| Ternary            | very long                         | `<expr> if <condition> else <expr>` |
| Conditional Filter | `<type>.<set>(if: <condition>)`\* | `<expr> if <condition> else Set()`  |
| For Loop           | `foreach.<set>->.<each>(<body>)`  | `for <each> in <set>:\n    <body>`  |

\* `overpassify` will allow for mixed sets here by repeating for each type. This may be optimized better in the future.
