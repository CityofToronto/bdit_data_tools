# Routing

We have street network layers. We can use [pgrouting]() to route from one (or
more) point(s) to any other point within that network. This is helpful for
determining a user's path but can also be useful for selecting all street
segments between arbitrary points (like intersections).

## HERE

## The centreline

[`view_centreline_undirected.sql`](view_centreline_undirected.sql) prepares two
views for nodes and links that are streets (excluding laneways). 
