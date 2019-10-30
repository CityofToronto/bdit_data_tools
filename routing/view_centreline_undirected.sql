DROP VIEW gis.centreline_routing_undirected;
CREATE MATERIALIZED VIEW gis.centreline_routing_undirected AS
SELECT geo_id, fnode AS "source", tnode AS "target", fcode, fcode_desc, ST_Length(ST_TRansform(geom, 98012)) as "cost", geom
	FROM gis.centreline
	WHERE FCODE_DESC IN ('Collector','Collector Ramp','Expressway','Expressway Ramp',
'Local','Major Arterial','Major Arterial Ramp','Minor Arterial',
'Minor Arterial Ramp','Pending');

CREATE INDEX ON gis.centreline_routing_undirected("source");
CREATE INDEX ON gis.centreline_routing_undirected("target");
ANALYZE gis.centreline_routing_undirected;

DROP VIEW IF EXISTS gis.intersections_routing;
CREATE MATERIALIZED VIEW gis.intersections_routing AS
WITH distinct_ints AS (
	SELECT DISTINCT ON (int_id ) gid, int_id, elev_id, intersec5, classifi6, classifi7, num_elev, elevatio9, elevatio10, elev_level, geom
	FROM gis.centreline_intersection
	WHERE classifi6 IN ('MJRML', 'MNRML', 'MNRSL', 'MJRSL') AND elevatio10 IN ('Major', 'Minor')
)
,real_ints AS (
	SELECT int_id
	FROM distinct_ints
	INNER JOIN gis.centreline_routing_undirected ON int_id = "source" OR int_id = "target"
	GROUP BY int_id
	HAVING COUNT(1) > 2 -- Make sure intersections have at least two streets that are routable that connect.
)
SELECT gid, int_id, elev_id, intersec5, classifi6, classifi7, num_elev, elevatio9, elevatio10, elev_level, geom
FROM distinct_ints
NATURAL JOIN real_ints;


COMMENT ON MATERIALIZED VIEW gis.intersections_routing IS 'Filtered distinct intersections for routing';
	
