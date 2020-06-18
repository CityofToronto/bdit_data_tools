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

# GET IDENTIFIER & DATE INFORMATION FROM LOOKUP TABLE
def get_date():
    with open('Collision Test/lookup.csv','r') as lookuplist:
        next(lookuplist) # or next(reader) ???
        reader = csv.reader(lookuplist)
        dic = {rows[0]:rows[1] for rows in reader}
        ids = dic.keys()

        for identifier in ids:
            date_found = dic.get(str(identifier))
            logger.info('Pulling for identifier = %s', identifier)
            date = datetime.datetime.strptime(str(date_found), '%d-%b-%y').date()
            #accdate = date.strftime("%Y-%m-%d")
            yr =  date.strftime('%Y')
            mth =  date.strftime('%m')

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
            # to get full file path
            full_file_name = os.path.join(file_path, file_name)
            shutil.copy(full_file_name, dest)
            ls.append(file_name)

    logger.info('Updating csv file for image found = %s', ls)
    # when images are found
    if ls:
        with open('destination/results.csv', 'a') as output:
            writer = csv.writer(output)
            out = [identifier, dic[identifier], 'Found']
            writer.writerow(out)

    # when images are not found
    else: 
        with open('destination/results.csv', 'a') as output:
            writer = csv.writer(output)
            out = [identifier, dic[identifier], 'Missing']
            writer.writerow(out)

if __name__ == '__main__':
    get_date()
