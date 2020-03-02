# Routing

We have street network layers. We can use [pgrouting]() to route from one (or
more) point(s) to any other point within that network. This is helpful for
determining a user's path but can also be useful for selecting all street
segments between arbitrary points (like intersections). Official documentation on pgRouting can be found [here](http://docs.pgrouting.org/latest/en/pgr_dijkstra.html). 

Note that there are one to one, one to many, many to one and many to many functions in pgRouting. \
There are also the directed and undirected parameters. Directed is when direction is taken in to consideration when routing. The default is **directed**.

## To begin
We need to prepare three things, \
a) the network (routes) for routing \
b) the start point \
c) the end point 

There are currently two networks that we are using: \
i) HERE network `here.routing_streets_18_3`
- start and end points are `px_start` and `px_end`
- `link_dir` is routed

ii) GIS centrelines network `gis.centreline_routing_undirected` \
( created using [`view_centreline_undirected.sql`](view_centreline_undirected.sql) prepares two views for nodes and links that are streets (excluding laneways))
- start and end points are intersection points \
(`source` and `target` in the network table) or (`fnode` and `tnode` in `gis.centreline`)
- centrelines' `geo_id` is routed

## To use
### i) HERE
Example can be found at [get_links_btwn_px.sql](get_links_btwn_px.sql)
The simplest way to test it out is by using
```
SELECT * FROM
    pgr_dijkstra('SELECT id, source::int, target::int, length::int as cost from here.routing_streets_18_3', source::int, target::int)
```

Then, we can link it to `here.routing_streets_18_3 ` table to get more information about the links.


### ii) Centrelines
Example can be found at [get_lines_btwn_interxn.sql]([get_lines_btwn_interxn.sql)
The simplest way to test it out is by using
```
SELECT int_start, int_end, * FROM
    pgr_dijkstra('SELECT id, source::int, target::int, cost from gis.centreline_routing_undirected', int_start::int, int_end::int, FALSE)
```

Then, we can link it to the `gis.centreline` table to get more information about the centrelines.

## Results
The results from the simple query above will return 6 columns as shown below

|seq|path_seq|node|edge|cost|agg_cost|
|---|--------|----|----|----|--------|
1|1|2|4|1|0|
2|2|5|8|1|1|
3|3|6|9|1|2|
4|4|9|16|1|3|
5|5|4|3|1|4|

Column `node` correspond to the source column (`px_start` or `int_start`) \
Column `egde` correspond to the routes in network table 
(`id` in `here.routing_streets_18_3` which can be used to find the `link_dir`)
(`id` in `gis.centreline_routing_undirected` which is the same as `geo_id` in `gis.centreline`)

We can then link to their respective tables stated above to get `geom` etc for the routes (links / centrelines)
