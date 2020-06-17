import csv
import click
import datetime
import logging
import traceback
import os
import shutil

def logger():
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter=logging.Formatter('%(asctime)s     	%(levelname)s    %(message)s', datefmt='%d %b %Y %H:%M:%S')
    file_handler = logging.FileHandler('logging.log')
    file_handler.setFormatter(formatter)
    logger.handlers.clear()
    stream_handler=logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
        
    with open('logging.log', 'w'):
        pass
    return logger

logger=logger()
logger.debug('Start')

# SET UP CLICK OPTION TO SPECIFY IDENTIFIER
CONTEXT_SETTINGS = dict(
    default_map={'get_images': {'flag': 0}}
)

@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    pass
@cli.command()
@click.option('--identifier', default = None, help='8 digits under the column ACCNB')
# Add ', multiple=True' if reading in a list instead of a string

# GET DATE INFORMATINO FROM LOOKUP TABLE
def get_date(identifier):

    logger.info('Pulling for identifier = %s', identifier)

    with open('Collision Test/lookup.csv','r') as lookuplist:
        reader = csv.reader(lookuplist)
        dic = {rows[0]:rows[1] for rows in reader}
        str_found = dic[str(identifier)] 

        date = datetime.datetime.strptime(str(str_found), '%d-%b-%y').date()
        #accdate = date.strftime("%Y-%m-%d")
        yr =  date.strftime('%Y')
        mth =  date.strftime('%m')

    try:
        copy_file(yr, mth)
    except Exception:
        logger.critical(traceback.format_exc())

# NAVIGATE TO THE FILE AND COPY FILES & INDICATE IN OUTPUT CSV FILE
def copy_file(yr, mth):
    logger.info('Copying files found for year = %s and month = %s into destination folder' %(yr, mth))

    file_path = '/home/jchew/local/file_extractor/Collision Test/' + yr + '/' + mth + '/'
    dest = '/home/jchew/local/file_extractor/destination/'
    # results_file = '/home/jchew/local/file_extractor/destination/results.csv'

    # to get list of files in the folder
    src_folder = os.listdir(file_path) 
    logger.debug('Files found from the directory are %s' %src_folder)

    ls = []
    for file_name in src_folder:
        # to get full file path
        full_file_name = os.path.join(file_path, file_name)

        # to only copy any regular files and not sub-directories
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, dest)
            ls.append(file_name)

    try:
        update_csv(ls)
    except Exception:
        logger.critical(traceback.format_exc())

def update_csv(ls):
    # record down whether the image is found or missing
    with open('Collision Test/lookup.csv', 'r') as input_file:
        with open('destination/results.csv', 'w') as output:
            reader = csv.reader(input_file)
            writer = csv.writer(output)
            for file_name in ls:
                for item in reader:
                    if file_name[0:8] == item[0]:
                        item.append('Found')
                        writer.writerow(item)
                    # else:
                    #     item.append('Missing')
                    #     writer.writerow(item)

if __name__ == '__main__':
    cli()
