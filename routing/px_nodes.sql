-- this view finds the closest here node for each traffic signal in gis.traffic_signal
CREATE OR REPLACE VIEW here_gis.px_nodes AS
 SELECT traffic_signal.px::integer AS px,
    traffic_signal.geom,
    nodes.node_id,
    st_transform(nodes.node_geom, 4326) AS node_geom
   FROM gis.traffic_signal
     CROSS JOIN LATERAL ( SELECT z.node_id,
            st_transform(z.geom, 98012) AS node_geom
           FROM here_gis.zlevels_18_3 z
          WHERE z.intrsect::text = 'Y'::text
          ORDER BY (z.geom <-> traffic_signal.geom)
         LIMIT 1) nodes;
