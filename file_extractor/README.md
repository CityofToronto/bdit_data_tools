# File Extractor

The [Python script](pull_collision_images.py) in this folder is used to pull collision images from L Drive based on the `identifiers` and `dates` from a csv file provided. 
It will first find the image from certain folders based on the year and month from the `date` given as well as the `identifier`, copy the found image to a destination folder 
and lastly in a new csv file, record down the status of whether the image was found or missing.
However, it is very customizable where one can change the source file or target file or file path or date format etc. More will be discussed below.

# How to use it

**1) Create a couple of folders/file**
  - a folder named destination (which acts as a main folder that contains folders of images to be found)
  - folders named P04 / P05 / P06 / whatever_the_project_id_is etc (these are the folders where images belonging to each project will be put into)
  - an empty csv file named results.csv with only a single row with 4 columns which are PROJECT_ID , ACCNB , ACCDATE , STATUS


**2) Fix the file path and date format in the script**
  - L21: name of source_file (csv file)
  - L22: name of target_file (csv file)
  - L50: the file_path (where the images are stored)
  - L51: name of destination folder (where we want to copy those images to)
  - L44: date format

**3) Run script with the command line**

`python pull_collision_images.py get-date`



*Note: Every 3000 rows take about an hour to complete.*
