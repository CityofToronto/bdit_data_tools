CREATE or REPLACE FUNCTION here_gis.get_links_btwn_px(_px_start int, _px_end int)
RETURNS TABLE (px_start int, px_end int, seq int, link_dir text)
AS $$
WITH lookup as (
    SELECT _px_start, _px_end, origin.node_id as source, dest.node_id as target
    FROM 
    here_gis.px_nodes origin
    , here_gis.px_nodes dest
	where _px_start = origin.px and _px_end = dest.px
)
, results as (SELECT * FROM
    lookup 
    cross join lateral pgr_dijkstra('SELECT id, source::int, target::int, length::int as cost from here.routing_streets_18_3', source::int, target::int)
)

SELECT _px_start, _px_end, seq, link_dir
from results
inner join here.routing_streets_18_3 on edge=id
order by _px_start, _px_end, seq
$$
LANGUAGE SQL STRICT STABLE;
