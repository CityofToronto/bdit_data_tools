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
    'requests_pathname_prefix': '/centreline-matcher/'
})


app.layout = html.Div(className='page-container',
children=[
    html.Div(className='header-split', children=
    [
    html.Header(children=[
        html.Img(id='logo', src='data:image/png;base64,{}'.format(base64.b64encode(open('assets/images/logo_with_centreline.PNG', 'rb').read())), width=100, height=75),
        html.H1('Toronto Centreline Matcher'),
	html.H5(children=['Convert text descriptions of locations to Toronto Centreline geometry'])


    ]),

    html.Div(className='split left', children=[

    dcc.Upload(
        id='upload-data',
        className='upload_class',
        children=html.Div([
            'Drag and Drop a (.csv or.xlsx) file or ',
            html.A(id='select_file', children='click here')
        ]),
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Details([
    	html.Summary("Help"),
    	html.H4(id='input_description', children=["Examples of correctly formatted files:"]),   # 250 300 with 100 height 
    	html.Img(src='data:image/png;base64,{}'.format(base64.b64encode(open('assets/images/from_to_image.png', 'rb').read())), width=500, height=150, style={'marginLeft':90,'marginBottom':5, 'marginRight':'50%'}),
    	html.Img(src='data:image/png;base64,{}'.format(base64.b64encode(open('assets/images/btwn_image.png', 'rb').read())), width=600, height=150, style={'marginLeft':90, 'marginRight':'50%'})
    ])
	]
   #	, 
   #   style={'background-image':url("/centreline-matcher/assets/images/greyscale_background.PNG")}, 
   #html.Img(src='data:image/png;base64,{}'.format(base64.b64encode(open('images/greyscale_background.PNG', 'rb').read())))}
	), 
	html.Div(className="right-page"), 

	]), 
    #html.Div(id='view2') 
    html.Div(id='output-data-upload')

])


@app.server.route('/static/<path:path>')
def static_file(path):
    static_folder = os.path.join(os.getcwd(), 'static')
    return send_from_directory(static_folder, path)





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

def get_headers(df):
    if len(df.columns) == 5:
    	return ['Id', 'Street', 'Between', 'Confidence', 'Geometry']
    if len(df.columns) == 6:
        return ['Id', 'Street','From', 'To', 'Confidence', 'Geometry']
    else:
	return True


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
    if df.shape[1] == 5:
	    df.columns = ["Id", "Street", "Between", "Confidence", "Geometry"]
	    df.apply(lambda X: features.append(
                geojson.Feature(geometry=X["Geometry"],

		properties=dict(ID=X["Id"],street=X["Street"], btwn=X["Between"], confidence=X["Confidence"]))), axis=1)

    else:
   	    df.columns = ["Id", "Street", "From",  "To", "Confidence", "Geometry"]
            df.apply(lambda X: features.append(	
                geojson.Feature(geometry=X["Geometry"],
                properties=dict(ID=X["Id"], street=X["Street"], frm=X["From"],to=X["To"],  confidence=X["Confidence"]))), axis=1)
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

    data.insert(loc=0,column=1000, value=pd.Series(data=[i for i in range(0, len(data.columns))]))
    

    # change line terminator to a comma to make parsing the file easier later
    # if you dont keep this, then the terminator will be an ampty string
    # would cause it to be way more difficult to figure out where a row ends
    # the last element of a row and the first element of the next row would be cosidered part of the same cell
    csv_string = data.to_csv(index=False, header=get_headers(data), 
                             encoding='utf-8', line_terminator="~!?")
   
	
    #json_string = data.to_json(orient='split')

    
    # send the csv as a string to the download function 
    # download isnt a callback so we cant really send variables via components
    csv_location =  "downloads/csv_file?value={}".format(csv_string)

	

    geojson_str = '{"type":"FeatureCollection", "features":' + data2geojson(data) + '}'

    geojson_location = "downloads/geojson?value={}".format(geojson_str)
    
    shp_location = "downloads/shp_zip?value={}".format(geojson_str)

    no_geom = data.drop(['Geometry'], axis=1)

   
    return html.Div(className="output", children=[
	
	html.Div(className="split right", children=[
	html.H3("Preview Your Data:"),
	html.A("Preview", href="#table", className='download_button'),
	html.H3("Or"),
	html.H3("Download your data:"),
        	html.Div(className='download_links',
                	children=[html.A('Download CSV', href=csv_location, className='download_button'),
                	html.A('Download Geojson', href=geojson_location, className='download_button'),
                	html.A('Download Shapefile', href=shp_location, className='download_button' ), 
]
        	)]), 

	html.Div(className="review-contents", 
        children=[html.Div(className='tbl', children=[dash_table.DataTable(
    	id='table',
        columns=[{"name": i, "id": i} for i in no_geom.columns],
    	data=no_geom.to_dict("rows"),  
        style_as_list_view=True,
        style_cell={'font-family':'Open Sans, sans-serif', 'height':75},
        style_header={'fontWeight':'bold'},

	)])])
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
    now = datetime.datetime.now()
    now = str(now).replace('.', '_', 4)
    now = str(now).replace(' ', '_', 4)
    now = str(now).replace('-', '_', 4)

    return flask.send_file(mem,
                           mimetype='text/csv',
                           attachment_filename='centreline_matcher_{}.csv'.format(now),
                           as_attachment=True)
     
     
       

      
@app.server.route("/downloads/geojson")
def download_geojson(): 
    
    json_string = flask.request.args.get('value') 
    
    str_io = io.StringIO(json_string)
    
    mem = io.BytesIO()
    mem.write(str_io.getvalue().encode('utf-8'))
    mem.seek(0)
    str_io.close()
    now = str(datetime.datetime.now())
    now = now.replace('.', '_', 4)
    now = now.replace(' ', '_', 4)    
    now = now.replace('-', '_', 4)

    return flask.send_file(mem,
                           mimetype='application/json',
                           attachment_filename='centreline_matcher_{}.geojson'.format(now),
                           as_attachment=True)



def get_indexes(columnsList):
    if 'to' in columnsList:
    	return [columnsList.index('ID'), columnsList.index('Street'), columnsList.index('To'), columnsList.index('From'), columnsList.index('Confidence'), columnsList.index('Geometry')]
    else:
	return [columnsList.index('ID'), columnsList.index('Street'), columnsList.index('Between'), columnsList.index('Confidence'), columnsList.index('Geometry')]

def get_columns_list(columnsList): 
    if 'to' in columnsList:
        return ['ID', 'street', 'to', 'frm', 'confidence']
    else:
        return ['ID', 'street', 'between', 'confidence']


# This method is used to create the columns names read from the geoJSON file
def createColumns(columnsList, w):
    if 'To' in columnsList:
	ordered_col_lst = ['ID', 'Street', 'To', 'From', 'Confidence', 'Geometry']
    else:
        ordered_col_lst = ['ID', 'Street', 'Between', 'Confidence', 'Geometry']
    for i in ordered_col_lst:
    	# Field names cannot be unicode.
    	# That is why I cast it to string.
    	w.field(str(i), 'C')

def createPrjFile(str_io):
 	prjStr = 'PROJCS["MTM_3Degree",GEOGCS["GCS_North_American_1927",DATUM["D_North_American_1927",SPHEROID["Clarke_1866",6378206.4,294.9786982]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.017453292519943295]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",304800.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-79.5],PARAMETER["Scale_Factor",0.9999],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
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
        	for j in get_columns_list(columnsList):
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

    now = str(datetime.datetime.now())
    now = now.replace('.', '_', 4)
    now = now.replace(' ', '_', 4)
    now = now.replace('-', '_', 4)

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w') as zf:
    	filenames = ['centreline_matcher_{}.dbf'.format(now), 'centreline_matcher_{}.shp'.format(now), 'centreline_matcher_{}.shx'.format(now), 'centreline_matcher_{}.prj'.format(now)]
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
                           attachment_filename='centreline_matcher_{}.zip'.format(now),
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

            
