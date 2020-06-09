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
i) **HERE** network \
(*NOTE:* `px_start` & `px_end` are traffic lights whereas `source` & `target` are nodes that connect the `link_dir` \
Ideally, finding the nodes and route them gives us better results rather than finding the closest nodes from px aka traffic light aka intersection then route them. Although, px's are the ones provided when people are requesting for data)

- network: mat view `here.routing_streets_19_4` or `here.routing_streets_19_4_ped` or other depending on your usage
- starting and end points are `px_start` and `px_end`
- `link_dir` is routed

ii) **GIS centrelines** network  \
( created using [`view_centreline_undirected.sql`](view_centreline_undirected.sql) which prepares two views for nodes and links that are streets (excluding laneways))

- network: mat view `gis.centreline_directional` or `gis.centreline_routing_undirected_lfname` or other depending on your usage
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




## Difference between ONE-to-ONE and MANY-to-MANY routing

Official documentation on pgRouting can be found [here](http://docs.pgrouting.org/latest/en/pgr_dijkstra.html). We normally use directional ONE-to-ONE routing for most of the routing but the process may take up a long time. It sounds pretty counterintuitive but MANY-to-MANY routing is actually much faster when you have many pairs of source and target to route. For example, a ONE-to-ONE routing takes about 2.5 seconds for a pair of source and target whereas a MANY-to-MANY routing takes about 2.3 seconds for 10 pairs of source and target. The reason is that every single time the ONE-to-ONE routing process is run, **pgr_dijkstra** will reload the whole network and route the pair of source and target. Whereas if one does MANY-to-MANY routing, the process will use the same network and try to route every `source` in the `source_array` to every `target` in the `target_array`. \
**Note:** I'm using `source` and `target` here but they are applicable in both HERE and GIS network.

### Steps to do MANY-to-MANY routing
It's the same as what has stated above but the only main difference is that we need to prepare an array of `source` and an array of `target`. We might also want to use `path_seq` instead of `seq` in order to know the sequence of the path routed since `seq` represents the sequence of all paths resulted from the array of sources and targets and not the particular pair of source and target.

An example of that can be shown [here](https://github.com/CityofToronto/bdit_data_analysis/blob/tts/tts/sql/bottleneck/create-function-new_get_links_btwn_nodes_for_cluster.sql) which is a function to route TTS zones/centroid. A little summary on how the code works is shown below.

#### i) L21 - L28 
```
FROM (SELECT array_agg(source_id)::INT[] as sources, 
        array_agg(target_id)::INT[] as targets 
  FROM (SELECT dense_rank() OVER(ORDER BY od.row_number) as id, 
        od.start_node AS source_id, od.end_node AS target_id 
        FROM tts.cluster_id_to_od_pairs od
        WHERE cluster_id = _cluster_id
       ) sample
 GROUP BY id/250 ) ods,
```
shows how we are reading each pair of source and target and put that in an array.
**NOTE:** It's utterly important to make sure that the array contains only **DISTINCT** source or target in order to prevent the same route from being routed twice. (which was not implemented in the code above)

#### ii) L29 - L35 
```
LATERAL pgr_dijkstra(format('SELECT id, source::int, target::int, length::int as cost 
                     FROM here.routing_streets_19_4_ped
                     WHERE link_dir NOT IN 
                     (SELECT link_dir
                        FROM tts.cluster_id_to_here_links  
                        WHERE cluster_id = %s)', _cluster_id),
                     sources, targets, TRUE) routing_results
```
shows how we are inputting `sources` and `targets` into pgr_dijkstra, `TRUE` indicates that it's directional routing whereas the SELECT statement is selecting the network that we want (which in this case, excluding link_dir found in another table where cluster_id matches). Note that the same network will then be used for the arrays of sources and targets. Therefore, if network is changing for each pair of source and target, one might want to consider grouping them together. For this case shown here, we're grouping them according to cluster_id. 

#### iii) L36 - L39
```
INNER JOIN (SELECT flow.row_number, flow.gghv4_orig, flow.gghv4_dest, flow.start_node, flow.end_node,
flow.cycle_total, flow.walk_total, flow.transit_total, flow.total_flow
FROM tts.new_distinct_od_flow_nodes flow
 ) trips ON trips.start_node = routing_results.start_vid AND trips.end_node = routing_results.end_vid
 ```
shows how we are then filtering the results by making sure that the pair of start_vid & end_vid is the same as the pair of start_node & end_node that we want to route at the first place.

#### iv) L40
```
INNER JOIN here.routing_streets_19_4_ped here ON routing_results.edge=here.id
```
allows us to retrieve all information that we want to know about the link_dir routed from the network table. For example, the length, geometry etc.


## How to optimize routing
For 20,000 pairs of sources and targets, running a ONE-to-ONE routing process may take up to 14 hours where running a MANY-to-MANY routing may take up to 2 hours to complete. Therefore, using a MANY-to-MANY routing process is highly encouraged when one has many pairs to route. However, if that process still takes too long to run, one can try to use `ThreadedConnectionPool` for the routing process where there are about 4 to 6 workers (you define it) in the connection pool that will carry out the processing. Examples on that can be found [here](https://github.com/CityofToronto/bdit_vfh/blob/master/routing/route.py) where it was used to 5-minutes bin for the VFH project.
