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

# GET DATE INFORMATION FROM LOOKUP TABLE
def get_date(identifier):

    with open('Collision Test/lookup.csv','r') as lookuplist:
        reader = csv.reader(lookuplist)
        dic = {rows[0]:rows[1] for rows in reader}
        str_found = dic.get(str(identifier))

        if str_found:
            logger.info('Pulling for identifier = %s', identifier)
            date = datetime.datetime.strptime(str(str_found), '%d-%b-%y').date()
            #accdate = date.strftime("%Y-%m-%d")
            yr =  date.strftime('%Y')
            mth =  date.strftime('%m')

            try:
                copy_file(identifier, yr, mth)
            except Exception:
                logger.critical(traceback.format_exc())

        else: 
            logger.warning('Identifier = %s is not found', identifier)
            with open('destination/results.csv', 'a') as output:
                writer = csv.writer(output)
                out = [identifier, 'Missing in the lookup table']
                writer.writerow(out)

# NAVIGATE TO THE FILE AND COPY FILES & INDICATE IN THE OUTPUT CSV FILE
def copy_file(identifier, yr, mth):
    logger.info('Navigating to folder where year = %s and month = %s' %(yr, mth))

    file_path = '/home/jchew/local/file_extractor/Collision Test/' + yr + '/' + mth + '/'
    dest = '/home/jchew/local/file_extractor/destination/'

    # to get list of files in the folder
    src_folder = os.listdir(file_path) 
    logger.debug('Files found from the directory are %s' %src_folder)

    ls = []
    for file_name in src_folder:
        # only copy files where name = identifier
        if file_name.split('.')[0] == identifier:
            # to get full file path
            full_file_name = os.path.join(file_path, file_name)
            shutil.copy(full_file_name, dest)
            ls.append(file_name)

    logger.info('Updating csv file for image found = %s', ls)
    # when images are found
    if ls:
        with open('destination/results.csv', 'a') as output:
            writer = csv.writer(output)
            out = [identifier, 'Found']
            writer.writerow(out)

    # when images are not found
    else: 
        with open('destination/results.csv', 'a') as output:
            writer = csv.writer(output)
            out = [identifier, 'Missing in the folder']
            writer.writerow(out)

if __name__ == '__main__':
    cli()
