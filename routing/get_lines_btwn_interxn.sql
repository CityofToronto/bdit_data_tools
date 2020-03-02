--NOTE: This is a rather specific function for speed limit layer process that returns many columns but that can be edited accordingly

--DROP FUNCTION jchew.get_lines_btwn_interxn(integer, integer);
CREATE or REPLACE FUNCTION jchew.get_lines_btwn_interxn(_int_start int, _int_end int)
RETURNS TABLE (int_start int, int_end int, seq int, geo_id numeric, lf_name varchar, objectid numeric, geom geometry, fcode integer, fcode_desc varchar)
LANGUAGE 'plpgsql' STRICT STABLE
AS $BODY$

BEGIN
RETURN QUERY
WITH 
results AS (SELECT _int_start, _int_end, * FROM
    pgr_dijkstra('SELECT id, source::int, target::int, cost from gis.centreline_routing_undirected', _int_start::int, _int_end::int, FALSE)
)
SELECT results._int_start, results._int_end, results.seq, 
centre.geo_id, centre.lf_name, centre.objectid, centre.geom, centre.fcode, centre.fcode_desc 
FROM results
INNER JOIN gis.centreline centre ON edge=centre.geo_id
ORDER BY int_start, int_end, seq;

RAISE NOTICE 'pg_routing done for int_start: % and int_end: %', 
_int_start, _int_end;

END;
$BODY$;