# TTS Routing
The following is more of a step-by-step process on how routing was done for the OD pairs found from TTS (Transportation Tomorrow Survey)
database. Walking, cycling and transit (excluding GO) within 5km that are happening within City of Toronto are obtained from the TTS 
database. The goal is to find the shortest routes taken by each OD pair (Origin Destination) for the first round of routing and then the shortest route 
taken by each OD pair once bottlenecks are introduced into the network. 

Note that GIS network was used at first but due to the fact 
that GIS centrelines network do not differentiate the elevation of a centreline, some routes which passes over/underpass can be 
weird where the someone would have to teleport up and down to use the given routes. Therefore, HERE network chosen instead due to 
its distinction of links elevation. *Though, note that HERE network is 3 times bigger than the centreline network and so 
processing time might take wayy longer.*

## First round of routing

### 1. Find distinct OD pairs
Since the data obtained came in 3 different csv files, those three files are combined so that we can find out the flow for each mode
of transport for each distinct OD pair. Query as shown below.
```
CREATE TABLE tts.new_distinct_od_flow AS
WITH combined AS (
SELECT DISTINCT ON (gghv4_orig, gghv4_dest) gghv4_orig, gghv4_dest
FROM tts.tts_2016_cycle
UNION
SELECT DISTINCT ON (gghv4_orig, gghv4_dest) gghv4_orig, gghv4_dest
FROM tts.tts_2016_walk
UNION
SELECT DISTINCT ON (gghv4_orig, gghv4_dest) gghv4_orig, gghv4_dest
FROM tts.tts_2016_transit_5km
	)
SELECT combined.*, COALESCE(cyc.total, 0) AS cycle_total, 
COALESCE(walk.total, 0) AS walk_total, COALESCE(transit.total, 0) AS transit_total,
SUM(COALESCE(cyc.total, 0) + COALESCE(walk.total, 0) + COALESCE(transit.total, 0)) AS total_flow
FROM combined
LEFT JOIN tts.tts_2016_cycle cyc USING (gghv4_orig, gghv4_dest)
LEFT JOIN tts.tts_2016_walk walk USING (gghv4_orig, gghv4_dest)
LEFT JOIN tts.tts_2016_transit_5km transit USING (gghv4_orig, gghv4_dest)
GROUP BY gghv4_orig, gghv4_dest, cycle_total, walk.total, transit.total
ORDER BY gghv4_orig, gghv4_dest
```

### 2. Match centroids to the closest HERE nodes 

Since TTS zones' geometry is an area / shape rather than a point, 
the centroid of a zone is found and that point is then matched to the closest HERE node. We also did a little filter to only include
HERE nodes that are present on the HERE network that we are using for routing. 
The query is shown below and the process took only 5 minutes to run.
```
CREATE TABLE tts.new_centroid_and_here_nodes AS
WITH valid_nodes AS (
--120290 nodes in total
--seprated so that query run wayyyyyy faster
SELECT source AS nodes
FROM here.routing_streets_19_4_ped
UNION 
SELECT target AS nodes
FROM here.routing_streets_19_4_ped
)
, here AS (
--315678 rows
SELECT node_id, geom AS node_geom
FROM here_gis.zlevels_19_4
WHERE intrsect::text = 'Y'::text 
AND node_id IN (SELECT nodes FROM valid_nodes)
)
, tts AS (
SELECT ogc_fid, fid, taz_no, csduid, csdname, cdname, 
shape__area AS shape_area, shape__length AS shape_length, 
wkb_geometry AS shape_geom, ST_Centroid(wkb_geometry) AS centroid
FROM tts.gghv4_zones_2016 
WHERE csdname = 'Toronto'
)
SELECT tts.*,
  found.node_id,
  found.node_geom,
  ST_Distance(ST_Transform(tts.centroid,2952), ST_Transform(found.node_geom,2952)) AS diff
FROM tts
CROSS JOIN LATERAL
(
SELECT node_id, node_geom
FROM here
ORDER BY 
ST_Transform(tts.centroid,2952) <-> ST_Transform(here.node_geom,2952)
LIMIT 1) found
```

### 3. Match OD pairs to nodes for routing 
Once the closest nodes are found for each zone, link them back to the OD pairs and put them in the same table to prepare for routing.
Index is created too so that the routing process can run faster.
```
CREATE TABLE tts.new_distinct_od_flow_nodes AS
WITH origin AS (
SELECT row_number() OVER () AS row_number,
od.gghv4_orig, od.gghv4_dest, od.cycle_total, od.walk_total, od.transit_total, od.total_flow,
nodes.node_id AS start_node, nodes.node_geom AS start_geom
FROM tts.new_distinct_od_flow od
LEFT JOIN tts.new_centroid_and_here_nodes nodes
ON od.gghv4_orig = nodes.taz_no
	)
SELECT origin.*, nodes.node_id AS end_node, nodes.node_geom AS end_geom
FROM origin
LEFT JOIN tts.new_centroid_and_here_nodes nodes
ON origin.gghv4_dest = nodes.taz_no
ORDER BY row_number

--created index too so that they run faster for pgrouting
CREATE INDEX new_distinct_od_flow_nodes_nodes_idx
    ON tts.new_distinct_od_flow_nodes USING btree
    (start_node ASC NULLS LAST, end_node ASC NULLS LAST)
    TABLESPACE pg_default;
```

### 4a. ~Route using ONE-to-ONE routing~ (which got aborted due to long processing time)
Create a function to do the routing and find information about the link_dir routed. 
```
CREATE OR REPLACE FUNCTION tts.new_get_links_btwn_nodes(
	_start_node integer,
	_end_node integer)
    RETURNS TABLE (start_node integer, end_node integer, seq integer, link_dir text, length double precision, geom geometry)
    LANGUAGE 'plpgsql'

    COST 100
    STABLE STRICT 
    ROWS 1000
AS $BODY$

BEGIN
RETURN QUERY

WITH results AS (SELECT * FROM
    pgr_dijkstra('SELECT id, source::int, target::int, length::int as cost 
				 from here.routing_streets_19_4_ped'::TEXT, _start_node::int, _end_node::int)
)
SELECT _start_node, _end_node, results.seq, here.link_dir, here.length, here.geom
FROM results
INNER JOIN here.routing_streets_19_4_ped here on edge=id
ORDER BY _start_node, _end_node, seq;

RAISE NOTICE 'pg_routing done for start_node: % and end_node: %', 
_start_node, _end_node;

END;
$BODY$;
```
Then, route each distinct OD pair but the process is anticipated to take almost 13 hours and so this was aborted.
```
CREATE TABLE tts.new_distinct_od_flow_nodes_routed AS
SELECT ids.row_number, ids.gghv4_orig, ids.gghv4_dest, 
ids.cycle_total, ids.walk_total, ids.transit_total, ids.total_flow,
rout.*
FROM tts.new_distinct_od_flow_nodes ids,
LATERAL tts.new_get_links_btwn_nodes(start_node, end_node) AS rout
```

### 4b. Route using MANY-to-MANY routing 
The process below took only 11 minutes to complete which is such a great improvement compared to 4a.
```
CREATE TABLE tts.new_distinct_od_flow_nodes_routed AS 
SELECT row_number, gghv4_orig, gghv4_dest, start_node, end_node, 
cycle_total, walk_total, transit_total, total_flow,
	routing_results.seq, here.link_dir, here.length AS here_length, 
ST_Length(ST_Transform(here.geom, 2952)) AS geom_length, here.geom
	FROM (SELECT array_agg(source_id)::INT[] as sources, 
			array_agg(target_id)::INT[] as targets 
	  FROM (SELECT row_number, 
			start_node AS source_id, end_node AS target_id 
			FROM tts.new_distinct_od_flow_nodes 
		   ) sample
	 GROUP BY row_number/250 ) ods,
	LATERAL pgr_dijkstra('SELECT id, source::int, target::int, length::int as cost FROM here.routing_streets_19_4_ped',
						 sources, targets, TRUE) routing_results
	INNER JOIN (SELECT row_number, gghv4_orig, gghv4_dest, start_node, end_node,
	cycle_total, walk_total, transit_total, total_flow
	FROM tts.new_distinct_od_flow_nodes
	 ) trips ON start_node = start_vid AND end_node = end_vid
	 INNER JOIN here.routing_streets_19_4_ped here ON routing_results.edge=here.id
	 ORDER BY row_number, seq
```

### 5. Find flows for each link_dir 
Each link_dir is assigned with a SUM(flow) depending on which OD pair it is involved in. Query as shown below.
```
CREATE TABLE tts.new_flow_for_each_link AS 
SELECT link_dir, here_length, geom_length, geom, SUM(cycle_total) AS sum_cycle, 
SUM(walk_total) AS sum_walk, SUM(transit_total) AS sum_transit, 
SUM(total_flow) AS sum_total_flow
FROM tts.new_distinct_od_flow_nodes_routed
GROUP BY link_dir, here_length, geom_length, geom
```

## Second round of routing
Re-routing is done again after introducing the bottlenecks to figure out which route would people take if certain
streets are closed.

### 1. Create a cross table function to link bottleneck geo_id and HERE links
Since bottlenecks given are only tagged to geo_id and not HERE id, 
the results of the conflation done between centrelines and HERE links are used as a crosstable to find HERE links found in the 
bottlenecks' geo_id. Query used is shown below.
```
CREATE MATERIALIZED VIEW tts.bottleneck_here_crosstable AS 
SELECT gis.geometry AS centreline_geometry, gis.reference_length AS centreline_length, 
gis.section AS centreline_section, gis.geo_id, gis.direction, gis.score AS centreline_score,
here.wkb_geometry AS here_geometry, here.referencelength AS here_length, here.section AS here_section,
here.pp_link_dir, here.score AS here_score 
FROM gis_shared_streets.centreline_snap gis
INNER JOIN natalie.here_19_4_matched_v2 here
ON gis.reference_id = here.shstreferenceid
WHERE geo_id IN (SELECT geo_id FROM covid_gis.over_under_pass_cl)
```

### 2. Find clusters with flow > 500
Courtesy of Raph to cluster the bottlenecks for easier/faster routing, we would have to then find the HERE links involved in the 
bottlenecks and then the cluster_id related and find those clusters with flow > 500. Those clusters are then used for routing.
A little fact/summary on the data can be found 
[here](https://github.com/CityofToronto/bdit_data_analysis/issues/144#issuecomment-639087035).
```
CREATE VIEW tts.cluster_id_flow_greater_500 AS
WITH links AS (
SELECT geo_id, cluster_id, pp_link_dir
FROM (
SELECT geo_id, cluster_id 
FROM covid_gis.pinchpoints_bridge_underpass_min pin
JOIN covid_gis.over_under_pass_cl bottle
ON pin.gid::numeric = bottle.geo_id AND pin.the_geom = bottle.geom
	) clust
LEFT JOIN tts.bottleneck_here_crosstable
USING (geo_id)
	)
, combined AS (
SELECT * FROM tts.new_flow_for_each_link
WHERE link_dir IN (SELECT pp_link_dir FROM links)
AND sum_total_flow > 500 	--might change later depending on the results
)
SELECT DISTINCT (cluster_id)
FROM combined
LEFT JOIN links 
ON combined.link_dir = links.pp_link_dir
```

### 3. Create cross tables required for routing purposes
#### 3a. Link cluster id to HERE links 
```
CREATE VIEW tts.cluster_id_to_here_links AS
WITH links AS (
SELECT geo_id, cluster_id, pp_link_dir
FROM (
SELECT geo_id, cluster_id 
FROM covid_gis.pinchpoints_bridge_underpass_min pin
JOIN covid_gis.over_under_pass_cl bottle
ON pin.gid::numeric = bottle.geo_id AND pin.the_geom = bottle.geom
	) clust
LEFT JOIN tts.bottleneck_here_crosstable
USING (geo_id)
	)
, combined AS (
SELECT * FROM tts.new_flow_for_each_link
WHERE link_dir IN (SELECT pp_link_dir FROM links)
)
SELECT links.geo_id, links.cluster_id, combined.link_dir, combined.geom_length, combined.sum_total_flow
FROM combined
LEFT JOIN links 
ON combined.link_dir = links.pp_link_dir
```
#### 3b. Link cluster id to OD pairs 
```
CREATE VIEW tts.cluster_id_to_od_pairs AS
WITH links AS (
SELECT geo_id, cluster_id, pp_link_dir
FROM (
SELECT geo_id, cluster_id 
FROM covid_gis.pinchpoints_bridge_underpass_min pin
JOIN covid_gis.over_under_pass_cl bottle
ON pin.gid::numeric = bottle.geo_id AND pin.the_geom = bottle.geom
	) clust
LEFT JOIN tts.bottleneck_here_crosstable
USING (geo_id)
	)
, combined AS (
SELECT * FROM tts.new_distinct_od_flow_nodes_routed
WHERE link_dir IN (SELECT pp_link_dir FROM links)
)
SELECT DISTINCT ON (links.cluster_id, combined.row_number) 
links.cluster_id, combined.row_number, combined.gghv4_orig, combined.gghv4_dest,
combined.start_node, combined.end_node
FROM combined
LEFT JOIN links 
ON combined.link_dir = links.pp_link_dir
ORDER BY cluster_id, row_number
```

### 4. Create function for MANY-to-MANY routing
```
CREATE OR REPLACE FUNCTION tts.new_get_links_btwn_nodes_for_cluster(
	_cluster_id integer)
    RETURNS TABLE
	(row_number bigint, gghv4_orig integer, gghv4_dest integer, start_node integer, end_node integer, 
	 cycle_total integer, walk_total integer, transit_total integer, total_flow bigint,
	seq integer, link_dir text, length double precision, geom_length double precision, geom geometry)
	LANGUAGE 'plpgsql'

    COST 100
    STABLE STRICT 
    ROWS 1000
AS $BODY$

BEGIN
RETURN QUERY

SELECT trips.row_number, trips.gghv4_orig, trips.gghv4_dest, trips.start_node, trips.end_node, 
trips.cycle_total, trips.walk_total, trips.transit_total, trips.total_flow,
	routing_results.seq, here.link_dir, here.length, 
ST_Length(ST_Transform(here.geom, 2952)) AS geom_length, here.geom
	FROM (SELECT array_agg(source_id)::INT[] as sources, 
			array_agg(target_id)::INT[] as targets 
	  FROM (SELECT dense_rank() OVER(ORDER BY od.row_number) as id, 
			od.start_node AS source_id, od.end_node AS target_id 
			FROM tts.cluster_id_to_od_pairs od
			WHERE cluster_id = _cluster_id
		   ) sample
	 GROUP BY id/250 ) ods,
	LATERAL pgr_dijkstra(format('SELECT id, source::int, target::int, length::int as cost 
						 FROM here.routing_streets_19_4_ped
						 WHERE link_dir NOT IN 
						 (SELECT link_dir
							FROM tts.cluster_id_to_here_links  
							WHERE cluster_id = %s)', _cluster_id),
						 sources, targets, TRUE) routing_results
	INNER JOIN (SELECT flow.row_number, flow.gghv4_orig, flow.gghv4_dest, flow.start_node, flow.end_node,
	flow.cycle_total, flow.walk_total, flow.transit_total, flow.total_flow
	FROM tts.new_distinct_od_flow_nodes flow
	 ) trips ON trips.start_node = routing_results.start_vid AND trips.end_node = routing_results.end_vid
	 INNER JOIN here.routing_streets_19_4_ped here ON routing_results.edge=here.id
	 ORDER BY row_number, seq;
	 
RAISE NOTICE 'pg_routing done for cluster: %', _cluster_id;

END;
$BODY$;
```

### 5. Route only for cluster_id with flow > 500 
Out of 18814 routable ones, 929 of them do not need to reroute. Route those cluster_id with the function created above.
```
CREATE TABLE tts.new_distinct_od_flow_nodes_routed_no_bottleneck AS
SELECT ids.*, rout.*
FROM tts.cluster_id_flow_greater_500 ids,
LATERAL tts.new_get_links_btwn_nodes_for_cluster(cluster_id) AS rout
```

### 6. Calculate bottleneck metrics
This step is not exactly part of the routing but I'm including it for entirety. Will update this section once the method has been 
finalised.
