# how to run file : use anaconda
# https://dash.plot.ly/getting-started

# how to run file : use anaconda
# https://dash.plot.ly/getting-started

from psycopg2 import connect
import configparser

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table

import base64

#import json
#import text_to_centreline.py
import pandas as pd
import pandas.io.sql as psql

import io


import flask


CONFIG = configparser.ConfigParser()
CONFIG.read('db.cfg')
dbset = CONFIG['DBSETTINGS']
con = connect(**dbset)

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__) #, external_stylesheets=external_stylesheets)
server = app.server

app.config.supress_callback_exceptions = True
app.config.update({
    # remove the default of '/'
    #'routes_pathname_prefix': '/download/newFile',

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


def get_rows(df):
    rows = []
    for index, row in df.iterrows():
        if df.shape[1] == 3:
            row_with_geom = text_to_centreline(row[0], row[1], row[2])
        elif df.shape[1] == 2:
            row_with_geom = text_to_centreline(row[0], row[1], None)
        #return row_with_geom 
        rows.append(row_with_geom)
    df = pd.DataFrame(data=rows)
    return df
    

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
    
    data = get_rows(df)
    
    #tbl = dash_table.DataTable(
    #id='table',
   #columns=[{"name": i, "id": i} for i in df.columns],
    #data=df.to_dict("rows"),
   # )
   
   
       
    #json_string = data.to_json(orient='split')
    
    
    
    # change line terminator to a comma to make parsing the file easier later
    # if you dont keep this, then the terminator will be an ampty string
    # would cause it to be way more difficult to figure out where a row ends
    # the last element of a row and the first element of the next row would be cosidered part of the same cell
    csv_string = data.to_csv(index=False, header=False, 
                             encoding='utf-8', line_terminator="~!?")

    
    # send the csv as a string to the download function 
    # download isnt a callback so we cant really send variables via components
    location =  "/download/newfile?value={}".format(csv_string)

    return html.Div([
        html.H5(filename),
        html.H6(df.shape),
        #html.H6(json_string),
        html.A('Download CSV', href=location),
        html.Hr(),  # horizontal line
    ])

# where I got inspiration from 
# https://community.plot.ly/t/allowing-users-to-download-csv-on-click/5550/17
@app.server.route("/download/newfile")
# this function will get run if "/download/newfile" is used 
def download():
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
        

if __name__ == '__main__':
    app.run_server(debug=True, port=8051)
    
    
    
