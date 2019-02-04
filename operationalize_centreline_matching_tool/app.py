from psycopg2 import connect
import configparser
import tempfile
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import zipfile
import base64
import datetime
import time
#import json
#import text_to_centreline.py
import pandas as pd
import pandas.io.sql as psql
#import geopandas as gpd
from shapely.wkt import loads, dumps

import shapefile
import csv
import io
import json
import geojson
import flask

from geoJ import GeoJ


CONFIG = configparser.ConfigParser()
CONFIG.read('db.cfg')
dbset = CONFIG['DBSETTINGS']
con = connect(**dbset)

app = dash.Dash(__name__)

server = app.server


app.config.supress_callback_exceptions = True
app.config.update({
    # remove the default of '/'
    #'routes_pathname_prefix': '',

    # remove the default of '/'
    'requests_pathname_prefix': ''
})

app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select a CSV or Excel File')
        ]),
        style={
            'width': '75%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': 'auto'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Div(id='output-data-upload'), 
])


def text_to_centreline(highway, fr, to): 
    if to != None:
        df = psql.read_sql("SELECT con AS confidence, centreline_segments AS geom FROM crosic.text_to_centreline('{}', '{}', '{}')".format(highway, fr, to), con)
    else:
        df = psql.read_sql("SELECT con AS confidence, centreline_segments AS geom FROM crosic.text_to_centreline('{}', '{}', {})".format(highway, fr, 'NULL'), con)
    return [highway, fr, to, df['confidence'].item(), df['geom'].item()]


def load_geoms(row_with_wkt, i):
    geom_wkt = row_with_wkt[i]
    row_with_geom = row_with_wkt[:i]
    if row_with_wkt[i] != None:
    	row_with_geom.append(loads(row_with_wkt[i]))
    else:
    	row_with_geom.append(None)
    return row_with_geom


def get_rows(df):
    rows = []
    for index, row in df.iterrows():
        if df.shape[1] == 3:
            row_with_wkt = text_to_centreline(row[0], row[1], row[2])
	    # replace string WKT representation of geom with an object 
	    row_with_geom = load_geoms(row_with_wkt, 4)
        elif df.shape[1] == 2:
            row_with_null = text_to_centreline(row[0], row[1], None)
	    row_with_wkt = [x for x in row_with_null if x is not None]
            # replace string WKT representation of geom with an object
	    row_with_geom = load_geoms(row_with_wkt, 3)
        #return row_with_geom 
        rows.append(row_with_geom)
    return pd.DataFrame(data=rows)   #gpd.GeoDataFrame(data=rows)



def data2geojson(df):
    features = []
    if df.shape[1] == 3:
	    df.columns = ["Street", "Between", "Confidence", "Geometry"]
	    df.apply(lambda X: features.append(
                geojson.Feature(geometry=X["Geometry"],

		properties=dict(street=X["Street"], btwn=X["Between"], confidence=X["Confidence"]))), axis=1)

    else:
   	    df.columns = ["Street", "From",  "To", "Confidence", "Geometry"]
            df.apply(lambda X: features.append(	
                geojson.Feature(geometry=X["Geometry"],
                properties=dict(street=X["Street"], frm=X["From"],to=X["To"],  confidence=X["Confidence"]))), axis=1)
    return geojson.dumps(features)






def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xlsx' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])
    
    if df.shape[1] not in [2,3]:
        return html.Div('Improper file layout. File must have 2 or 3 columns.')
    
    # in case if there is a random row with a value missing or a row with no values
    df = df.dropna(axis=0) 
    
  
     
    data = get_rows(df)
    
    # change line terminator to a comma to make parsing the file easier later
    # if you dont keep this, then the terminator will be an ampty string
    # would cause it to be way more difficult to figure out where a row ends
    # the last element of a row and the first element of the next row would be cosidered part of the same cell
    csv_string = data.to_csv(index=False, header=False, 
                             encoding='utf-8', line_terminator="~!?")
   
	
    #json_string = data.to_json(orient='split')

    
    # send the csv as a string to the download function 
    # download isnt a callback so we cant really send variables via components
    csv_location =  "downloads/csv_file?value={}".format(csv_string)

	

    geojson_str = '{ "type":"FeatureCollection", "features":' + data2geojson(data) + '}'

    geojson_location = "downloads/geojson?value={}".format(geojson_str)

    
    shp_location = "downloads/shp_zip?value={}".format(geojson_str)

    no_geom = data.drop(['Geometry'], axis=1)

   
    return html.Div([
        html.Div(id='tbl', children=[dash_table.DataTable(
    	id='table',
        columns=[{"name": i, "id": i} for i in no_geom.columns],
    	data=no_geom.to_dict("rows"),
	)]),
        html.Div(id='csv', children=[html.A('Download CSV', href=csv_location)]),
        html.Div(id='geoj', children=[html.A('Download Geojson', href=geojson_location)]),
	html.Div(id='shp', children=[html.A('Download Shapefile', href=shp_location)])
    ])

# where I got inspiration from 
# https://community.plot.ly/t/allowing-users-to-download-csv-on-click/5550/17
@app.server.route("/downloads/csv_file")
# this function will get run if "/download/newfile" is used 
def download_csv():
    csv_string = flask.request.args.get('value')

    csv_string = csv_string.replace("~!?", '\n')
      
    str_io = io.StringIO(csv_string)
    
    mem = io.BytesIO()
    mem.write(str_io.getvalue().encode('utf-8'))
    mem.seek(0)
    str_io.close()
    return flask.send_file(mem,
                           mimetype='text/csv',
                           attachment_filename='downloadFile.csv',
                           as_attachment=True)
     
     
       

      
@app.server.route("/downloads/geojson")
def download_geojson(): 
    
    json_string = flask.request.args.get('value') 
    
    str_io = io.StringIO(json_string)
    
    mem = io.BytesIO()
    mem.write(str_io.getvalue().encode('utf-8'))
    mem.seek(0)
    str_io.close()
    return flask.send_file(mem,
                           mimetype='application/json',
                           attachment_filename='downloadFile.geojson',
                           as_attachment=True)




# This method is used to create the columns names read from the geoJSON file
def createColumns(columnsList, w):
    for i in columnsList:
    	# Field names cannot be unicode.
    	# That is why I cast it to string.
    	w.field(str(i), 'C')

def createPrjFile(str_io):
 	prjStr = 'PROJCS["NAD_1983_UTM_Zone_17N",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-81],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["Meter",1]]'
        str_io.write(prjStr)

@app.server.route("/downloads/shp_zip")
def download_shp():
    
    json_string = flask.request.args.get('value')
    #geojson_io = io.StringIO(json_string)
    #gJ = GeoJ(geojson_io)
    geojson_file = json.loads(json_string)
    # imitialize io
    shp = io.BytesIO()
    shx = io.BytesIO()
    dbf = io.BytesIO()
    prj = io.BytesIO()


    # parse the geojson 
    columnsList = geojson_file['features'][0]['properties'].keys()
    geometries = [] 
    attributes = []
    attributesPerF = []
    for i in geojson_file['features']:
    

    	if i['geometry'] is not None and i['geometry']['type'] == 'LineString':
                geometries.append(i['geometry']['coordinates'])
        	for j in columnsList:
                	attributesPerF.append(str(i['properties'][str(j)]))
        	attributes.append(attributesPerF)
        	attributesPerF = []
    # create line
    with tempfile.NamedTemporaryFile() as tmp:
    	tmp_name = tmp.name 
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf)
    createColumns(columnsList, w)
    for i in geometries:
    	w.line([i])

    for j in attributes:
    	w.record(*j)


    # now save the created shapefile from writer 
    w.close()
    

    # create prj file 
    createPrjFile(prj)

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w') as zf:
    	filenames = ['centreline_download.dbf', 'centreline_download.shp', 'centreline_download.shx', 'centreline_download.prj']
        files = [dbf, shp, shx, prj]
    	for i in range(0, len(filenames)): 
        	data = zipfile.ZipInfo(filenames[i])
        	data.date_time = time.localtime(time.time())[:6]
        	data.compress_type = zipfile.ZIP_DEFLATED
        	zf.writestr(data, files[i].getvalue())


    # mem.write(str_io.getvalue().encode('utf-8'))
    #mem.write(shp.getvalue())
    mem.seek(0)
    prj.close()
    shx.close()
    dbf.close()
    shp.close()
    #str_io.close()
    return flask.send_file(mem,
                           attachment_filename='downloadFile1.zip',
                           as_attachment=True)






    
@app.callback(
    Output(component_id='output-data-upload', component_property='children'),
    [Input(component_id= 'upload-data', component_property='filename')], 
    [State('upload-data', 'contents')]
)
def update_output_div(filename_list, contents_list):
    if filename_list == None:
        return ''
    else:
        if filename_list[0].split('.')[1] == 'csv' or filename_list[0].split('.')[1] == 'xlsx':
           new_file = [parse_contents(c, f) for c, f in zip(contents_list, filename_list)]
           return new_file 
        else:
             return 'Insuffient file format, please enter a CSV or Excel file'

            
