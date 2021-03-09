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

# start script execution timer
startTime = datetime.datetime.now()
print('Start Time: ' + str(startTime))

#---------------------------------------------------------------
# Define file paths and file names
# K-drive path for lookup table and destination (results) file
k_path='K:/Work/Ad-Hoc Analyses/Collision PDF Puller/'
lookup_file = k_path + 'LOOKUP_TABLE/Yonge_Gerrard_Davisville.csv'

# Names of lookup table, destination file
dest_path=k_path + 'destination/'
dest_file = dest_path + 'results.csv'

# Folder containing data files to search through
data_path = '//tssrv7/CollisionsProcessed/Backup/PdfProcessed/'
#---------------------------------------------------------------

# GET IDENTIFIER & DATE INFORMATION FROM LOOKUP TABLE
def get_date():
    min_yr=50 # i.e. if earliest file to be retrieved is from 2015, min_yr = 50
    with open(lookup_file,'r') as lookuplist:
        next(lookuplist) # to skip header
        reader = csv.reader(lookuplist)

        for row in reader:
            identifier = row[0]
            date_found = row[1]

            # File names to look for have a prefix that depends on
            # what the first 2 digits of the identifier are.
            # The logic below will append "15" if the first 2 digits are 15
            # (and similarly for 16, 17, 18, 19)
            # and will append "50" if the first 2 digits are 50
            # (and similarly for 60, 70, 80, 90)
            # If the date range of the files to be found are after 2019
            # or before 2015, this logic needs to be modified.
            this_yr=int(identifier[:2])
            if this_yr >=min_yr:
                pref=str(1) + str(this_yr)[:1]
            else:
                pref=str(this_yr)
                
            identifier=pref+str(this_yr)+identifier[2:]

            logger.info('Pulling for identifier = %s', identifier)

            try:
                copy_file(identifier, date_found)
            except Exception:
                logger.critical(traceback.format_exc())

    # end time
    print('Time elapsed: ' + str(datetime.datetime.now() - startTime))

# NAVIGATE TO THE FILE AND COPY FILES & INDICATE IN THE OUTPUT CSV FILE
def copy_file(identifier, date_found):
    # Check if date format follows the specification below:
    dt=datetime.datetime.strptime(date_found, '%m/%d/%Y %H:%M')
    this_date=str(datetime.date(dt.year, dt.month, dt.day))

    # to get list of files in the folder
    src_folder = os.listdir(data_path) 
    logger.debug('Files found in the data directory are %s' %src_folder)
    ls = []
    for file_name in src_folder:
        # only copy files where filename = identifier
        if file_name.split('.')[0] == identifier:
            print('found file: ', file_name)
            full_file_name = os.path.join(data_path, file_name) # to get full file path
            shutil.copy(full_file_name, dest_path)
            ls.append(file_name)

    logger.info('Updating results csv file for pdf found = %s', ls)
    with open(dest_file, 'a', newline='') as output: # appending the target file & make sure no empty line/row between each resulting row
        writer = csv.writer(output)
        if ls: 
            out = [identifier, date_found, 'Found'] # when file is found
        else: 
            out = [identifier, date_found, 'Missing']  # when file is not found
        writer.writerow(out)

if __name__ == '__main__':
    get_date()
