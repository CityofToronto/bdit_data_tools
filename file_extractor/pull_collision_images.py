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
source_file = 'K:/tra/GM Office/Big Data Group/Work/Ad Hoc Analyses/Collision Image Puller/Batch01.csv'
target_file = 'K:/tra/GM Office/Big Data Group/Work/Ad Hoc Analyses/Collision Image Puller/destination/results.csv'

# GET IDENTIFIER & DATE INFORMATION FROM LOOKUP TABLE
def get_date():
    with open(source_file,'r') as lookuplist:
        next(lookuplist) # to skip header
        reader = csv.reader(lookuplist)

        for row in reader:
            project_id = row[0]
            identifier = row[1]
            date_found = row[2]
            logger.info('Pulling for identifier = %s', identifier)

            try:
                copy_file(project_id, identifier, date_found) #dic, yr, mth)
            except Exception:
                logger.critical(traceback.format_exc())

# NAVIGATE TO THE FILE AND COPY FILES & INDICATE IN THE OUTPUT CSV FILE
def copy_file(project_id, identifier, date_found):
    # date = datetime.datetime.strptime(str(date_found), '%d-%b-%y').date() # if date format is '10-Apr-17'
    date = datetime.datetime.strptime(str(date_found), '%m/%d/%Y') .date() # if date format is '04/10/17'
    yr =  date.strftime('%Y')
    mth =  date.strftime('%m')
    logger.debug('Navigating to folder where year = %s and month = %s' %(yr, mth))

    #\\tssrv7\CrashData\DataBase\
    file_path = '//tssrv7/CrashData/DataBase/' + yr + '/' + mth + '/'
    dest = 'K:/tra/GM Office/Big Data Group/Work/Collision Image Puller/destination/' + project_id + '/'

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
    with open(target_file, 'a', newline='') as output: # appending the target file & make sure no empty line/row between each resulting row
        writer = csv.writer(output)
        if ls: 
            out = [project_id, identifier, date_found, 'Found'] # when image is found
        else: 
            out = [project_id, identifier, date_found, 'Missing']  # when image is not found
        writer.writerow(out)

if __name__ == '__main__':
    get_date()
