CREATE OR REPLACE FUNCTION crosic.get_intersection_id(highway2 TEXT, btwn TEXT, not_int_id INT)
RETURNS INT[] AS $$
DECLARE 
oid INT;
lev_sum INT;
int_id_found INT;

BEGIN 
SELECT intersections.objectid, SUM(LEAST(levenshtein(TRIM(intersections.street), TRIM(highway2), 1, 1, 1), levenshtein(TRIM(intersections.street), TRIM(btwn), 1, 1, 1))), intersections.int_id
INTO oid, lev_sum, int_id_found
FROM 
(gis.centreline_intersection_streets LEFT JOIN gis.centreline_intersection USING(objectid)) AS intersections 
 

WHERE (levenshtein(TRIM(intersections.street), TRIM(highway2), 1, 1, 1) < 4 OR levenshtein(TRIM(intersections.street), TRIM(btwn), 1, 1, 1) < 4) AND intersections.int_id  <> not_int_id


GROUP BY intersections.objectid, intersections.int_id
HAVING COUNT(DISTINCT TRIM(intersections.street)) > 1 
ORDER BY AVG(LEAST(levenshtein(TRIM(intersections.street), TRIM(highway2), 1, 1, 1), levenshtein(TRIM(intersections.street),  TRIM(btwn), 1, 1, 1)))

LIMIT 1;

raise notice 'highway2 being matched: % btwn being matched: % not_int_id: % intersection arr: %', highway2, btwn, not_int_id, ARRAY[oid, lev_sum];

RETURN ARRAY[oid, lev_sum, int_id_found]; 

END; 
$$ LANGUAGE plpgsql; 



CREATE OR REPLACE FUNCTION crosic.get_intersection_id_highway_equals_btwn(highway2 TEXT, btwn TEXT, not_int_id INT)
RETURNS INT[] AS $$
DECLARE 
oid INT;
lev_sum INT;
int_id_found INT;

BEGIN 
SELECT intersections.objectid, SUM(LEAST(levenshtein(TRIM(intersections.street), TRIM(highway2), 1, 1, 1))), intersections.int_id
INTO oid, lev_sum, int_id_found
FROM 
(gis.centreline_intersection_streets LEFT JOIN gis.centreline_intersection USING(objectid, classifi6, elevatio10)) AS intersections 
 

WHERE levenshtein(TRIM(intersections.street), TRIM(highway2), 1, 1, 1) < 4 AND intersections.int_id  <> not_int_id AND intersections.classifi6 IN ('SEUML','SEUSL', 'CDSSL', 'LSRSL')


GROUP BY intersections.objectid, intersections.int_id, elevatio10
-- HAVING COUNT(DISTINCT TRIM(intersections.street)) >= 1 
ORDER BY AVG(LEAST(levenshtein(TRIM(intersections.street), TRIM(highway2), 1, 1, 1), levenshtein(TRIM(intersections.street),  TRIM(btwn), 1, 1, 1))), 
(CASE WHEN elevatio10='Cul de sac' THEN 1 WHEN elevatio10='Pseudo' THEN 2 WHEN elevatio10='Laneway' THEN 3 ELSE 4 END),
-- (CASE WHEN classifi6='CDSSL' THEN 1 WHEN classifi6='LSRSL' THEN 2 WHEN classifi6='SEUSL' THEN 3 WHEN classifi6='SEUML' THEN 4 END), 
(SELECT COUNT(*) FROM gis.centreline_intersection_streets WHERE objectid = intersections.objectid) 

LIMIT 1;

raise notice 'highway2 being matched: % btwn being matched: % not_int_id: % intersection arr: %', highway2, btwn, not_int_id, ARRAY[oid, lev_sum];

RETURN ARRAY[oid, lev_sum, int_id_found]; 

END; 
$$ LANGUAGE plpgsql; 





CREATE OR REPLACE FUNCTION crosic.get_intersection_geom(highway2 TEXT, btwn TEXT, direction TEXT, metres FLOAT, not_int_id INT)
RETURNS TEXT[] AS $arr$
DECLARE 
geom TEXT;
int_arr INT[] := (CASE WHEN TRIM(highway2) = TRIM(btwn) THEN (crosic.get_intersection_id_highway_equals_btwn(highway2, btwn, not_int_id))
	ELSE (crosic.get_intersection_id(highway2, btwn, not_int_id))
	END);

oid INT := int_arr[1];
int_id_found INT := int_arr[3];
lev_sum INT := int_arr[2];
oid_geom geometry := (
		SELECT ST_Transform(ST_SetSRID(gis.geom, 4326), 26917)
		FROM gis.centreline_intersection gis
		WHERE objectid = oid
		);
arr1 TEXT[] :=  ARRAY(SELECT (
	-- normal case
	CASE WHEN direction IS NULL OR metres IS NULL 
	THEN ST_AsText(oid_geom)
	-- special case
	ELSE (
	(CASE WHEN TRIM(direction) = 'west' THEN ST_AsText(ST_Translate(oid_geom, -metres, 0))
	WHEN TRIM(direction) = 'east' THEN ST_AsText(ST_Translate(oid_geom, metres, 0))
	WHEN TRIM(direction) = 'north' THEN ST_AsText(ST_Translate(oid_geom, 0, metres))
	WHEN TRIM(direction) = 'south' THEN ST_AsText(ST_Translate(oid_geom, 0, -metres))
	END)
	)
	END 
));


arr2 TEXT[] := ARRAY_APPEND(arr1, int_id_found::TEXT);
arr TEXT[] := ARRAY_APPEND(arr2, lev_sum::TEXT);
BEGIN 

raise notice 'get_intersection_geom stuff: oid: % geom: % direction % metres % not_int_id: %', oid, ST_AsText(geom), direction, metres::TEXT, not_int_id;

RETURN arr; 


END; 
$arr$ LANGUAGE plpgsql; 





DROP FUNCTION crosic.get_line_geom(oid1_geom geometry, oid2_geom geometry);
CREATE OR REPLACE FUNCTION crosic.get_line_geom(oid1_geom geometry, oid2_geom geometry)
RETURNS GEOMETRY AS $geom$
DECLARE 
len INT := ST_LENGTH(ST_MakeLine(oid1_geom, oid2_geom)); 
geom GEOMETRY := 
	(
	-- WARNING FOR LEN > 3000 ?????????
	CASE WHEN len > 11 AND len < 10000
	THEN ST_Transform(ST_MakeLine(oid1_geom, oid2_geom), 26917)
	END
	);
BEGIN

raise notice 'LINE geom: % length of line: %', ST_AsText(ST_Transform(geom, 4326)), len;

RETURN geom;


END;
$geom$ LANGUAGE plpgsql; 





CREATE OR REPLACE FUNCTION crosic.match_line_to_centreline(line_geom geometry, highway2 text, metres_btwn1 FLOAT, metres_btwn2 FLOAT)
RETURNS geometry AS $geom$
DECLARE geom geometry := (
	SELECT ST_Transform(ST_LineMerge(ST_UNION(s.geom)), 26917)
	FROM gis.centreline s
	WHERE levenshtein(LOWER(highway2), LOWER(s.lf_name), 1, 1, 2) < 3
	AND 
	(
	(
		-- "normal" case ... i.e. one intersection to another 
		COALESCE(metres_btwn1, metres_btwn2) IS NULL AND 
		ST_DWithin( ST_Transform(s.geom, 26917), ST_BUFFER(line_geom, 3*ST_LENGTH(line_geom), 'endcap=flat join=round') , 10)
		AND ST_Length(st_intersection(ST_BUFFER(line_geom, 3*(ST_LENGTH(line_geom)), 'endcap=flat join=round') , ST_Transform(s.geom, 26917))) /ST_Length(ST_Transform(s.geom, 26917)) > 0.9
	)
	OR 
	(
		-- 10 TIMES LENGTH WORKS .... LOOK INTO POTENTIALLY CHANGING LATER
		COALESCE(metres_btwn1, metres_btwn2) IS NOT NULL AND
		ST_DWithin(ST_Transform(s.geom, 26917), ST_BUFFER(line_geom, 10*COALESCE(metres_btwn1, metres_btwn2), 'endcap=flat join=round'), 30)
	)
	)
);

BEGIN 

RETURN geom;

END;
$geom$ LANGUAGE plpgSQL; 





CREATE OR REPLACE FUNCTION crosic.centreline_case1(direction_btwn2 text, metres_btwn2 FLOAT, centreline_geom geometry, line_geom geometry, oid1_geom geometry)
RETURNS geometry AS $geom$

-- i.e. St Mark's Ave and a point 100 m north 

DECLARE geom geometry := (
-- case where the section of street from the intersection in the specified direction is shorter than x metres 
CASE WHEN metres_btwn2 > ST_Length(centreline_geom) AND metres_btwn2 - ST_Length(centreline_geom) < 15 
THEN centreline_geom


-- metres_btwn2/ST_Length(d.geom) is the fraction that is supposed to be cut off from the dissolved centreline segment(s)
-- cut off the first fraction of the dissolved line, and the second and check to see which one is closer to the original interseciton

WHEN ST_LineLocatePoint(centreline_geom, oid1_geom) 
> ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))

THEN ST_LineSubstring(centreline_geom, ST_LineLocatePoint(centreline_geom, oid1_geom) - (metres_btwn2/ST_Length(centreline_geom)), 
ST_LineLocatePoint(centreline_geom, oid1_geom))


WHEN ST_LineLocatePoint(centreline_geom, oid1_geom) < 
ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))
-- take the substring from the intersection to the point x metres ahead of it
THEN ST_LineSubstring(centreline_geom, ST_LineLocatePoint(centreline_geom, oid1_geom), 
ST_LineLocatePoint(centreline_geom, oid1_geom) + (metres_btwn2/ST_Length(centreline_geom))  )



END
);

BEGIN 

raise notice 'IN CASE 1 FUNCTION !!!!!!!!!!!!!!!!!!!  direction_btwn2: %, metres_btwn2: %  centreline_geom: %  line_geom: %  oid1_geom: % llp1: %  llp2: % len centreline geom: %', direction_btwn2, metres_btwn2, ST_ASText(ST_Transform(centreline_geom, 4326)), ST_AsText(ST_Transform(line_geom, 4326)), ST_AsText(ST_Transform(oid1_geom, 4326)), ST_LineLocatePoint(centreline_geom, oid1_geom),  ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1))), ST_Length(centreline_geom);

RETURN geom;

END;
$geom$ LANGUAGE plpgSQL; 





-- this function is used to make sure the lowest linelocatepoint fraction values comes first in the function call to st_linesubstring
-- in line substring lower fraction must come before a higher fraction 
CREATE OR REPLACE FUNCTION line_substring_lower_value_first(geom geometry, value1 float, value2 float)
RETURNS geometry AS $geom$

DECLARE 

geom geometry := (

-- one value may be a value subtracted from another
-- or a value added to another
-- in this case there is a possibility of the fraction being > 1 or < 0
CASE WHEN GREATEST(value1, value2) > 1
THEN ST_LineSubstring(geom, LEAST(value1, value2), 1)

WHEN LEAST(value1, value2) < 0
THEN ST_LineSubstring(geom, 0, GREATEST(value1, value2))

ELSE
ST_LineSubstring(geom, LEAST(value1, value2), GREATEST(value1, value2))

END
);


BEGIN 

RETURN geom;

END; 
$geom$ LANGUAGE plpgSQL; 



CREATE OR REPLACE FUNCTION crosic.centreline_case2(direction_btwn1 text, direction_btwn2 text, metres_btwn1 FLOAT, metres_btwn2 FLOAT, centreline_geom geometry, line_geom geometry, oid1_geom geometry, oid2_geom geometry)
RETURNS geometry AS $geom$


-- i.e. St Marks Ave and 100 metres north of St. John's Ave 


DECLARE 


geom geometry := (
	CASE WHEN (metres_btwn2 IS NOT NULL AND metres_btwn2 > ST_Length(centreline_geom) AND metres_btwn2 - ST_Length(centreline_geom) < 15)
	OR (metres_btwn1 IS NOT NULL AND metres_btwn1 > ST_Length(centreline_geom) AND metres_btwn1 - ST_Length(centreline_geom) < 15)
	THEN centreline_geom


	-- Case 1: direction_btwn1 IS NULL 
	-- find substring between intersection 1 and the point x metres away from intersection 2
	WHEN direction_btwn1 IS NULL
		THEN (
		-- when the intersection is after the rough line
		CASE WHEN ST_LineLocatePoint(centreline_geom, oid2_geom)
		> ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))
		-- take the line from intersection 1 to x metres before intersection 2 
		THEN 
		line_substring_lower_value_first(centreline_geom, 
		ST_LineLocatePoint(centreline_geom, oid1_geom),  
		ST_LineLocatePoint(centreline_geom, oid2_geom) - (metres_btwn2/ST_Length(centreline_geom)))


		-- when its before the closest point from rough line 
		WHEN  ST_LineLocatePoint(centreline_geom, oid2_geom)
		< ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))
		-- take the line from intersection 1 to x metres after intersection 2
			THEN 
			line_substring_lower_value_first(centreline_geom, 
			ST_LineLocatePoint(centreline_geom, oid1_geom),  
			ST_LineLocatePoint(centreline_geom, oid2_geom)+ (metres_btwn2/ST_Length(centreline_geom)))


		END
		)


	-- When direction 2 IS NULL 
	-- means that the zone is between interseciton 2 and x metres away from intersection 1
	WHEN direction_btwn2 IS NULL

		THEN (
		-- when the intersection is after the rough line
		CASE WHEN ST_LineLocatePoint(centreline_geom, oid2_geom)
		> ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0, 0.000001))) -- ST_LineSubstring(line_geom, 0.99999, 1)))
		-- take the line from intersection 2 to x metres before intersection 1
			THEN 
			line_substring_lower_value_first(centreline_geom, 
			ST_LineLocatePoint(centreline_geom, oid1_geom)- (metres_btwn1/ST_Length(centreline_geom)),
			ST_LineLocatePoint(centreline_geom, oid2_geom))


		WHEN ST_LineLocatePoint(centreline_geom, oid2_geom)
		< ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0, 0.000001))) -- ST_LineSubstring(line_geom, 0.99999, 1)))
			THEN 
			line_substring_lower_value_first(centreline_geom, 
			ST_LineLocatePoint(centreline_geom, oid1_geom)+ (metres_btwn1/ST_Length(centreline_geom)), 
			ST_LineLocatePoint(centreline_geom, oid2_geom))

		END)


	-- when both are not null 
	-- the zone is between the point x metres away from int 1 and y metres away from int 2
	ELSE (
		-- both times the intersection occurs after (higher fraction) than the point closest to the end of the rough line 
		(CASE WHEN ST_LineLocatePoint(centreline_geom, oid2_geom)
		> ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))
		AND  ST_LineLocatePoint(centreline_geom, oid1_geom)
		> ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, line_geom))
			THEN 
			-- so line substring wont give error 
			line_substring_lower_value_first(centreline_geom, 
			ST_LineLocatePoint(centreline_geom, oid1_geom)- (metres_btwn1/ST_Length(centreline_geom)),
			ST_LineLocatePoint(centreline_geom, oid2_geom)- (metres_btwn2/ST_Length(centreline_geom)))


		-- both before 
		WHEN ST_LineLocatePoint(centreline_geom, oid2_geom)
		< ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))
		AND  ST_LineLocatePoint(centreline_geom, oid1_geom)
		< ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, line_geom))

			THEN 
			line_substring_lower_value_first(centreline_geom, 
			ST_LineLocatePoint(centreline_geom, oid1_geom)+ (metres_btwn1/ST_Length(centreline_geom)),
			ST_LineLocatePoint(centreline_geom, oid2_geom)+ (metres_btwn2/ST_Length(centreline_geom)))


		-- int 2 before (+), int 1 after (-)
		WHEN ST_LineLocatePoint(centreline_geom, oid2_geom)
		< ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))
		AND  ST_LineLocatePoint(centreline_geom, oid1_geom)
		> ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, line_geom))
			THEN 
			-- all of these cases are so the line_substring wont get mad ( 2nd arg must be smaller then 3rd arg) 

			line_substring_lower_value_first(centreline_geom, 
			ST_LineLocatePoint(centreline_geom, oid1_geom)- (metres_btwn1/ST_Length(centreline_geom)),
			ST_LineLocatePoint(centreline_geom, oid2_geom)+ (metres_btwn2/ST_Length(centreline_geom)))


		-- int 2 before (+), int 1 after (-)
		WHEN ST_LineLocatePoint(centreline_geom, oid2_geom)
		< ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))
		AND  ST_LineLocatePoint(centreline_geom, oid1_geom)
		> ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, line_geom))
			THEN 
			-- so line substring wont give error
			line_substring_lower_value_first(centreline_geom, 
			ST_LineLocatePoint(centreline_geom, oid1_geom)+ (metres_btwn1/ST_Length(centreline_geom)),
			ST_LineLocatePoint(centreline_geom, oid2_geom)- (metres_btwn2/ST_Length(centreline_geom)))


		END
		) )



	END);



BEGIN 

raise notice 'IN THE CASE TWO FUNCTION !!!!!';
raise notice 'CASE 2 PARAMETERS  direction_btwn1 %, direction_btwn2 %, metres_btwn1 %, metres_btwn2 %, centreline_geom %, line_geom %, oid1_geom %, oid2_geom % output geom: %',direction_btwn1, direction_btwn2, metres_btwn1, metres_btwn2, ST_AsText(ST_Transform(centreline_geom, 4326)), ST_AsText(ST_Transform(line_geom, 4326)), ST_AsText(ST_Transform(oid1_geom, 4326)), ST_AsText(ST_Transform(oid2_geom, 4326)), ST_AsText(ST_Transform(geom, 4326));
raise notice 'centreline line location of oid2_geom: %  centreline line location of end of line_geom %', ST_LineLocatePoint(centreline_geom, oid2_geom)::TEXT, ST_LineLocatePoint(centreline_geom, ST_ClosestPoint(centreline_geom, ST_LineSubstring(line_geom, 0.99999, 1)))::TEXT;

RETURN geom;

END;
$geom$ LANGUAGE plpgSQL; 





CREATE OR REPLACE FUNCTION crosic.text_to_centreline(highway TEXT, frm TEXT, t TEXT) 
RETURNS TABLE(centreline_segments TEXT, con TEXT) AS $$ 
DECLARE 


	-- clean data 

	
	-- when the input was btwn instead of from and to 
	
	btwn1 TEXT := CASE WHEN t IS NULL THEN 
	gis.abbr_street(regexp_REPLACE(regexp_REPLACE(regexp_REPLACE(split_part(split_part(regexp_REPLACE(frm, '[0123456789.]* metres (north|south|east|west|East) of ', '', 'g'), ' to ', 1), ' and ', 1), '\(.*\)', '', 'g'), 'Between ', '', 'g'), 'A point', '', 'g'))
	ELSE gis.abbr_street(regexp_REPLACE(regexp_REPLACE(frm, '[0123456789.]* metres (north|south|east|west|East) of ', '', 'g'), 'A point', '', 'g')) 
	END; 

	btwn2_orig TEXT := CASE WHEN t IS NULL THEN 
			(CASE WHEN split_part(frm, ' and ', 2) <> ''
			THEN gis.abbr_street(regexp_REPLACE(regexp_REPLACE(split_part(regexp_REPLACE(frm, '[0123456789.]* metres (north|south|east|west|East) of ', '', 'g'), ' and ', 2), 'Between ', '', 'g'), 'A point', '', 'g'))
			WHEN split_part(frm, ' to ', 2) <> ''
			THEN gis.abbr_street(regexp_REPLACE(regexp_REPLACE(split_part(regexp_REPLACE(frm, '[0123456789.]* metres (north|south|east|west|East) of ', '', 'g'), ' to ', 2), 'Between ', '', 'g'), 'A point', '', 'g'))
			END)
			
			ELSE 
			gis.abbr_street(regexp_REPLACE(t, '[0123456789.]* metres (north|south|east|west|East) of ', '', 'g'))
			END ; 


				
	highway2 TEXT :=  gis.abbr_street(highway);
	
	direction_btwn1 TEXT := CASE WHEN t IS NULL THEN 
				(
				CASE WHEN btwn1 LIKE '% m %'
				OR gis.abbr_street( regexp_REPLACE(split_part(split_part(frm, ' to ', 1), ' and ', 1), 'Between ', '', 'g')) LIKE '% m %'
				THEN split_part(split_part(gis.abbr_street(regexp_REPLACE(split_part(split_part(frm, ' to ', 1), ' and ', 1), 'Between ', '', 'g')), ' m ', 2), ' of ', 1)
				ELSE NULL
				END )
				ELSE 
				(
				CASE WHEN btwn1 LIKE '% m %'
				OR gis.abbr_street(frm) LIKE '% m %'
				THEN split_part(split_part(gis.abbr_street(frm), ' m ', 2), ' of ', 1)
				ELSE NULL
				END )
				END;

				
	direction_btwn2 TEXT := CASE WHEN t IS NULL THEN (
				CASE WHEN btwn2_orig LIKE '% m %'
				OR 
				(
					CASE WHEN split_part(frm, ' and ', 2) <> ''
					THEN gis.abbr_street( regexp_REPLACE(split_part(frm, ' and ', 2), 'Between ', '', 'g'))
					WHEN split_part(frm, ' to ', 2) <> ''
					THEN gis.abbr_street( regexp_REPLACE(split_part(frm, ' to ', 2), 'Between ', '', 'g'))
					END
				) LIKE '% m %'
				THEN 
				(
					CASE WHEN split_part(frm, ' and ', 2) <> ''
					THEN split_part(split_part( gis.abbr_street(regexp_REPLACE(split_part(frm, ' and ', 2), 'Between ', '', 'g')), ' m ', 2), ' of ', 1)
					WHEN split_part(frm, ' to ', 2) <> ''
					THEN split_part(split_part(gis.abbr_street(regexp_REPLACE(split_part(frm, ' to ', 2), 'Between ', '', 'g')), ' m ', 2), ' of ', 1)
					END
				)
				ELSE NULL
				END)
				ELSE 
				(
				CASE WHEN btwn2_orig LIKE '% m %'
				OR gis.abbr_street(t) LIKE '% m %'
				THEN 
				split_part(split_part(gis.abbr_street(t), ' m ', 2), ' of ', 1)
				ELSE NULL
				END
				)
				END;

					
	metres_btwn1 FLOAT :=	(CASE WHEN t IS NULL THEN 
				(
				CASE WHEN btwn1 LIKE '% m %'
				OR gis.abbr_street(regexp_REPLACE(split_part(split_part(frm, ' to ', 1), ' and ', 1), 'Between ', '', 'g')) LIKE '% m %'
				THEN regexp_REPLACE(regexp_REPLACE(split_part(gis.abbr_street(regexp_REPLACE(split_part(split_part(frm, ' to ', 1), ' and ', 1), 'Between ', '', 'g')), ' m ' ,1), 'a point ', '', 'g'), 'A point', '', 'g')::FLOAT
				ELSE NULL
				END
				)
				ELSE 
				(
				CASE WHEN btwn1 LIKE '% m %'
				OR gis.abbr_street(frm) LIKE '% m %'
				THEN regexp_REPLACE(regexp_REPLACE(split_part(gis.abbr_street(frm), ' m ' ,1), 'a point ', '', 'g'), 'A point', '', 'g')::FLOAT
				ELSE NULL
				END
				)
				END)::FLOAT;

				
	metres_btwn2 FLOAT :=	(CASE WHEN t IS NULL THEN 
				( CASE WHEN btwn2_orig LIKE '% m %' OR 
				(
					CASE WHEN split_part(frm, ' and ', 2) <> ''
					THEN gis.abbr_street( regexp_REPLACE(regexp_REPLACE(split_part(frm, ' and ', 2), '\(.*\)', '', 'g'), 'Between ', '', 'g'))
					WHEN split_part(frm, ' to ', 2) <> ''
					THEN gis.abbr_street( regexp_REPLACE(regexp_REPLACE(split_part(frm, ' to ', 2), '\(.*\)', '', 'g'), 'Between ', '', 'g'))
					END
				) 
				LIKE '% m %'
				THEN 
				(
				CASE WHEN split_part(frm, ' and ', 2) <> ''
				THEN regexp_REPLACE(regexp_REPLACE(split_part( gis.abbr_street( regexp_REPLACE(regexp_REPLACE(split_part(frm, ' and ', 2), '\(.*\)', '', 'g'), 'Between ', '', 'g')), ' m ', 1), 'a point ', '', 'g'), 'A point', '', 'g')::FLOAT
				WHEN split_part(frm, ' to ', 2) <> ''
				THEN regexp_REPLACE(regexp_REPLACE(split_part(gis.abbr_street( regexp_REPLACE(regexp_REPLACE(split_part(frm, ' to ', 2), '\(.*\)', '', 'g'), 'Between ', '', 'g')), ' m ', 1), 'a point ', '', 'g'), 'A point', '', 'g')::FLOAT
				END
				)
				ELSE NULL
				END )
				
				ELSE 
				( 
				CASE WHEN btwn2_orig LIKE '% m %' 
				OR gis.abbr_street(t) LIKE '% m %'
				THEN 
				regexp_REPLACE(regexp_REPLACE(split_part(gis.abbr_street(t), ' m ', 1), 'a point ', '', 'g'), 'A point', '', 'g')::FLOAT
				ELSE NULL
				END 
				)
				END)::FLOAT;



	-- to help figure out if the row is case 1 
	-- i.e. Watson road from St. Mark's Road to a point 100 metres north
	-- we want the btwn2 to be St. Mark's Road (which is also btwn1)
	-- there are also cases like: street= Arundel Avenue  and  btwn=  Danforth Avenue and a point 44.9 metres north of Fulton Avenue
	-- we need to be able to differentiate the two cases
	-- the difference between the two is that one of the cases has a 'of' to describe the second road that intersects with "street"/"highway2"
	btwn2_check TEXT := CASE WHEN t IS NULL THEN 
			(CASE WHEN split_part(frm, ' and ', 2) <> ''
			THEN gis.abbr_street(regexp_REPLACE(regexp_REPLACE(split_part(frm, ' and ', 2), 'Between ', '', 'g'), 'A point', '', 'g'))
			WHEN split_part(frm, ' to ', 2) <> ''
			THEN gis.abbr_street(regexp_REPLACE(regexp_REPLACE(split_part(frm, ' to ', 2), 'Between ', '', 'g'), 'A point', '', 'g'))
			END)
			
			ELSE 
			gis.abbr_street(t)
			END ; 



	-- for case one 
	-- i.e. Watson road from St. Mark's Road to a point 100 metres north
	-- we want the btwn2 to be St. Mark's Road (which is also btwn1)
	btwn2 TEXT := (
	CASE WHEN btwn2_orig LIKE '%point%' AND (btwn2_check NOT LIKE '% of %' OR btwn2_check LIKE ('% of ' || TRIM(btwn1)))
	THEN btwn1
	ELSE regexp_replace(btwn2_orig , 'a point', '', 'g')
	END
	);






	-- get intersection geoms

	text_arr_oid1 TEXT[]:= crosic.get_intersection_geom(highway2, btwn1, direction_btwn1::TEXT, metres_btwn1::FLOAT, 0);

	int_id1 INT := (text_arr_oid1[2])::INT;
	
	oid1_geom GEOMETRY := ST_GeomFromText(text_arr_oid1[1], 26917);

	text_arr_oid2 TEXT[] := (CASE WHEN btwn2_orig LIKE '%point%' AND (btwn2_check NOT LIKE '% of %' OR btwn2_check LIKE ('% of ' || TRIM(btwn1)))
				THEN crosic.get_intersection_geom(highway2, btwn2, direction_btwn2::TEXT, metres_btwn2::FLOAT, 0)
				ELSE crosic.get_intersection_geom(highway2, btwn2, direction_btwn2::TEXT, metres_btwn2::FLOAT, int_id1)
				END);

	oid2_geom  GEOMETRY = ST_GeomFromText(text_arr_oid2[1], 26917);


	-- create a line between the two intersection geoms
	line_geom geometry = crosic.get_line_geom(oid1_geom, oid2_geom);

	-- match the lines to centreline segments
	centreline_segments geometry := ( 
				CASE WHEN COALESCE(metres_btwn1, metres_btwn2) IS NULL
				THEN 
				(
				SELECT * 
				FROM crosic.match_line_to_centreline(line_geom, highway2, metres_btwn1, metres_btwn2)
				)

				WHEN btwn1 = btwn2 
				THEN 
				(
				SELECT *  
				FROM crosic.centreline_case1(direction_btwn2, metres_btwn2, crosic.match_line_to_centreline(line_geom, highway2, metres_btwn1, metres_btwn2), line_geom, 
				ST_GeomFromText((crosic.get_intersection_geom(highway2, btwn1, NULL::TEXT, NULL::FLOAT, 0))[1], 26917) )
				)

				ELSE 
				(
				SELECT * 
				FROM crosic.centreline_case2(direction_btwn1, direction_btwn2, metres_btwn1, metres_btwn2, crosic.match_line_to_centreline(line_geom, highway2, metres_btwn1, metres_btwn2), line_geom, 
				-- get the original intersection geoms (not the translated ones) 
				ST_GeomFromText((crosic.get_intersection_geom(highway2, btwn1, NULL::TEXT, NULL::FLOAT, 0))[1], 26917),(CASE WHEN btwn2_orig LIKE '%point%' AND (btwn2_check NOT LIKE '% of %' OR btwn2_check LIKE ('% of ' || TRIM(btwn1)))
				THEN ST_GeomFromText((crosic.get_intersection_geom(highway2, btwn2, NULL::TEXT, NULL::FLOAT, 0))[1], 26917)
				ELSE ST_GeomFromText((crosic.get_intersection_geom(highway2, btwn2, NULL::TEXT, NULL::FLOAT, int_id1))[1], 26917)
				END))
				)
				END
				);


	-- sum of the levenshtein distance of both of the intersections matched
	lev_sum INT := text_arr_oid1[3]::INT + text_arr_oid2[3]::INT; -- (crosic.get_intersection_id(highway2, btwn1))[2] + (crosic.get_intersection_id(highway2, btwn2))[2];

	-- confidence value
	con TEXT := (
		CASE WHEN lev_sum IS NULL 
		THEN 'No Match'
		WHEN lev_sum = 0 
		THEN 'Very High (100% match)'
		WHEN lev_sum = 1
		THEN 'High (1 character difference)'
		WHEN lev_sum IN (2,3)
		THEN FORMAT('Medium (%s character difference)', lev_sum::TEXT)
		ELSE FORMAT('Low (%s character difference)', lev_sum::TEXT)
		END
	);
	

BEGIN 


	raise notice 'btwn1: % btwn2: % btwn2_check: %  highway2: % metres_btwn1: %  metres_btwn2: % direction_btwn1: % direction_btwn2: % cntreline_segments: %', btwn1, btwn2, btwn2_check, highway2, metres_btwn1, metres_btwn2, direction_btwn1, direction_btwn2, ST_ASText(ST_Transform(centreline_segments, 4326));
	

RETURN QUERY (SELECT ST_AsText(centreline_segments), con);


END;
$$ LANGUAGE plpgsql; 





-- assumes highway_arr and btwn_arr are the same size
CREATE OR REPLACE FUNCTION crosic.make_geom_table(highway_arr TEXT[], frm_arr TEXT[], to_arr TEXT[]) 
RETURNS TABLE (
highway TEXT,
frm TEXT, 
t TEXT,
confidence TEXT,
geom TEXT
)
AS $$
BEGIN 

DROP TABLE IF EXISTS inputs;
CREATE TEMP TABLE inputs AS (
SELECT UNNEST(highway_arr) AS highway, UNNEST(frm_arr) AS frm, UNNEST(to_arr) AS t
);


RETURN QUERY  
SELECT i.highway, i.frm AS from, i.t AS to, (SELECT con FROM crosic.text_to_centreline(i.highway, i.frm, i.t)) AS confidence, 
(SELECT centreline_segments FROM crosic.text_to_centreline(i.highway, i.frm, i.t)) AS geom

FROM inputs i;


END; 
$$ LANGUAGE plpgsql;



-- old version with btwn instead of from and to
DROP TABLE IF EXISTS crosic.centreline_geoms_test;
SELECT * 
INTO crosic.centreline_geoms_test
FROM crosic.make_geom_table(ARRAY['Watson Avenue', 'Watson Avenue', 'Watson Avenue', 'North Queen Street'],
ARRAY['Between St Marks Road and St Johns Road', 'Between St Marks Road and a point 100 metres north', 'Between St Marks Road and 100 metres north of St Johns Road', 'Between Shorncliffe Road and Kipling Ave'],
ARRAY[NULL, NULL, NULL, NULL]);


/*
DROP TABLE IF EXISTS crosic.centreline_geoms_test;
SELECT * 
INTO crosic.centreline_geoms_test
FROM crosic.make_geom_table(ARRAY['Watson Avenue', 'Watson Avenue', 'Watson Avenue', 'North Queen Street'],
ARRAY['St Marks Road', 'St Marks Road', 'St Marks Road', 'Shorncliffe Road'], 
ARRAY['St Johns Road', 'a point 100 metres north', '100 metres north of St Johns Road', 'Kipling Ave'] );
*/




SELECT * FROM crosic.centreline_geoms_test;