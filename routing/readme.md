# Routing

We have street network layers. We can use [pgrouting]() to route from one (or
more) point(s) to any other point within that network. **PgRouting routes the shortest path between 2 nodes that uses the least cost.**  Cost is normally the length of the centreline/link_dir but we can also define that ourselves. 

This is helpful for determining a user's path but can also be useful for selecting all street
segments between arbitrary points (like intersections). Official documentation on pgRouting can be found [here](http://docs.pgrouting.org/latest/en/pgr_dijkstra.html). 

Note that there are one to one, one to many, many to one and many to many functions in pgRouting. \
There are also the directed and undirected parameters. Directed is when direction is taken into consideration during the routing process. The default is **directed**.

## To begin
We need to prepare three things, \
a) the network (routes) for routing \
b) the starting point \
c) the end point 
> Examples of how the views are prepared can be found [here at routing with traffic data](https://github.com/CityofToronto/bdit_data-sources/tree/master/here#routing-with-traffic-data).

There are currently two networks that we are using: \
i) **HERE** network `here.routing_streets_18_3`
- starting and end points are `px_start` and `px_end`
- `link_dir` is routed

ii) **GIS centrelines** network `gis.centreline_routing_undirected` \
( created using [`view_centreline_undirected.sql`](view_centreline_undirected.sql) which prepares two views for nodes and links that are streets (excluding laneways))
- starting and end points are intersection points \
(`source` and `target` in the network table) or (`fnode` and `tnode` in `gis.centreline`)
- centrelines' `geo_id` is routed

## To use
### i) HERE
Example can be found at [get_links_btwn_px.sql](get_links_btwn_px.sql)
The simplest way to test it out is by using the query below then link it to `here.routing_streets_18_3 ` table to get more information about the links.
```
SELECT * FROM
    pgr_dijkstra('SELECT id, source::int, target::int, length::int as cost from here.routing_streets_18_3', source::int, target::int)
```

The input parameters are:

|Field Name|Data Type|Description|Example|
|----------|---------|-----------|-------|
|id|bigint|`link_dir` in HERE network but F/T are replaced by 0/1 instead|294928170|
|source|integer|`px_start` in HERE network|30326833|
|target|integer|`px_end` in HERE network|30326831|
|cost|integer|length of link_dir|179|

### ii) Centrelines
Example can be found at [get_lines_btwn_interxn.sql]([get_lines_btwn_interxn.sql)
The simplest way to test it out is by using the query below then link it to the `gis.centreline` table to get more information about the centrelines.
```
SELECT int_start, int_end, * FROM
    pgr_dijkstra('SELECT id, source::int, target::int, cost from gis.centreline_routing_undirected', int_start::int, int_end::int, FALSE)
```
The input parameters are:

|Field Name|Data Type|Description|Example|
|----------|---------|-----------|-------|
|id|bigint|centrelines' `geo_id` in GIS centrelines network|30075947|
|source|integer|`fnode` in GIS centrelines network|13470675|
|target|integer|`tnode` in GIS centrelines network|30075940|
|cost|integer|length of centreline|39|

## Results
The results from the simple query above will return 6 columns as shown below

|seq|path_seq|node|edge|cost|agg_cost|
|---|--------|----|----|----|--------|
1|1|2|4|1|0|
2|2|5|8|1|1|
3|3|6|9|1|2|
4|4|9|16|1|3|
5|5|4|3|1|4|

The output parameters are:

|Field Name|Data Type|Description|Example|
|----------|---------|-----------|-------|
|seq|integer|Sequential value starting from 1|2|
|path_seq|integer|Relative position in the path. Has value 1 for the beginning of a path|2|
|node|bigint|corresponds to the source column (`px_start` for HERE network or `int_start` for GIS centreline network)|13470675|
|edge|bigint|corresponds to the routes in the network table (`link_dir` for HERE network or `geo_id` for GIS centreline network)|30075947|
|cost|double precision|Cost to traverse from node using edge to the next node in the path sequence|15|
|agg_cost|double precision|	Aggregate cost from start_v to node (CUMULATIVE)|30|

> (`id` in `here.routing_streets_18_3` can be used to find the `link_dir`) \
> (`id` in `gis.centreline_routing_undirected` is the same as `geo_id` in `gis.centreline`)

We can then use that information to link to their respective tables stated above to get `geom` etc for the routes (links / centrelines).
