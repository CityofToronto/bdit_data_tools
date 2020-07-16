import csv
import datetime
import logging
import traceback
import os
import shutil

def logger(): 
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter=logging.Formatter('%(asctime)s    %(levelname)s    %(message)s', datefmt='%d %b %Y %H:%M:%S')
    logger.handlers.clear()
    stream_handler=logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger
logger=logger()
logger.debug('Start')

# DEFINE SOURCE AND TARGET FILE
source_file = 'Collision Test/lookup.csv'
target_file = 'destination/results.csv'

# GET IDENTIFIER & DATE INFORMATION FROM LOOKUP TABLE
def get_date():
    with open(source_file,'r') as lookuplist:
        next(lookuplist) # to skip header
        reader = csv.reader(lookuplist)

        for row in reader:
            dic = {row[0]:row[1]} # as I need this dic for the next function
            identifier = row[0]
            date_found = row[1]
            logger.info('Pulling for identifier = %s', identifier)
            date = datetime.datetime.strptime(str(date_found), '%d-%b-%y').date() # if date format is '10-Apr-17'
            #date = datetime.datetime.strptime(str(date_found), '%m/%d/%Y') .date() # if date format is '04/10/17'
            yr =  date.strftime('%Y')
            mth =  date.strftime('%m')
            logger.debug('Date found = %s', date)

            try:
                copy_file(identifier, dic, yr, mth)
            except Exception:
                logger.critical(traceback.format_exc())

# NAVIGATE TO THE FILE AND COPY FILES & INDICATE IN THE OUTPUT CSV FILE
def copy_file(identifier, dic, yr, mth):
    logger.info('Navigating to folder where year = %s and month = %s' %(yr, mth))
    file_path = '/home/jchew/local/file_extractor/Collision Test/' + yr + '/' + mth + '/'
    dest = '/home/jchew/local/file_extractor/destination/'

    # to get list of files in the folder
    src_folder = os.listdir(file_path) 
    logger.debug('Files found from the directory are %s' %src_folder)
    ls = []
    for file_name in src_folder:
        # only copy files where filename = identifier
        if file_name.split('.')[0] == identifier:
            full_file_name = os.path.join(file_path, file_name) # to get full file path
            shutil.copy(full_file_name, dest)
            ls.append(file_name)

    logger.info('Updating csv file for image found = %s', ls)
    with open(target_file, 'a') as output: # appending the target file
        writer = csv.writer(output)
        if ls: 
            out = [identifier, dic[identifier], 'Found'] # when image is found
        else: 
            out = [identifier, dic[identifier], 'Missing']  # when image is not found
        writer.writerow(out)

if __name__ == '__main__':
    get_date()
