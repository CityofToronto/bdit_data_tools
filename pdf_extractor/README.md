# PDF Extractor

The [Python script](pull_collision_pdf.py) in this folder is used to pull collision PDFs from the data drive based on a set of requested files listed in a lookup table. 

Inputs:
- a lookup table in the form of a `CSV` file.

Outputs:
- A results `CSV` file is appended with the requested file name, collision date, and status of whether the file was found or missing.
- If a match is found between the requested file and PDF filenames in the data drive, the PDF is copied from the data drive to a destination folder. 

**Disclaimer**: PDFs only exist for collisions after a certain year.

## How to use the PDF Extractor
You need a lookup table with a list of collisions that are to be extracted. The script will read this table, search for matches in the collision database, pull the matching PDFs, store them in a destination folder, and write to the results file. 

Follow the steps below to set up and execute this process.

### 1) Set up files and folders 

#### 1.1 Validate format of the lookup table
The lookup table is a `CSV` file that contains a list of collisions that are to be pulled and must have the following columns:

- column 0: the `ACCNB` identifier number (e.g. `178005881`)
- column 1: the `ACCDATE` in format `02/07/2017 0:00`. If the date format is different in your lookup table, either change the format in your table or modify the script (See **Section 2.4**).

These columns are read in the `for` loop L45-L47 of `pull_collision_pdf.py`:

```
45 for row in reader:
46    identifier = row[0]
37    date_found = row[1]
```

It doesn't matter if the lookup table contains other columns - these are not read in by the script.

**NOTE**: The `identifier` itself is insufficient to find the collision in the database. A prefix corresponding to the collision year needs to be added to the `identifier`; it is this `prefix + identifier` that the script then tries to match in searching the database. See **Section 2.3**.

**ANOTHER NOTE**: The date in `ACCDATE` is not actually used in the search for a match. It is simply copied over into the results file. According to those in the know, `ACCDATE` is not reliable enough to use as the collision date. The collision date is best inferred from the `identifier` (but this is not obvious; see **Section 2.3**).

**LAST NOTE**: the column names of the lookup table can be anything, as long as they are in the correct order and format as explained above.

Here is an example of the lookup table:

|ACCNB| ACCDATE|
|--|--|
|178005881| 02/07/2017 0:00|
|178008044 |02/21/2017 0:00|
|178019533 |05/03/2017 0:00|
|9000639983|  04/09/2019 0:00|
|9000639983 | 04/09/2019 0:00|
|158028663 |07/09/2015 0:00|


#### 1.2 Create a destination folder and initialize the results file

  - create a folder named `destination` (to which will be transferred the found PDFs) inside the root folder. Default root folder:
  ` \\trafic\Documents\TDCSB\PROJECT\REQUESTS\_CONTRACTED_SERVICES\Work Packages\Image_Puller`
  - create a folder called `LOOKUP_TABLE` inside `destination/` that contains the lookup table `CSV` file you set up in the previous step.
  - in the `destination/` folder, create an empty `CSV` file called `results.csv` that only contains 3 column headers: `ACCNB`, `ACCDATE`, `STATUS`


### 2) Customize the script parameters 
The script itself uses hard-coded parameters (yes bad) that need to be modified for your specific files.

#### 2.1 Define the file paths and names

Section L25-35 of `pull_collision_pdf.py` needs the path of the lookup table, the name of the lookup table, and the path of the `destination` folder and results file. (The path of the `destination` folder and results file is the same.)

```
24 #---------------------------------------------------------------
25 # Define file paths and file names
26 # K-drive path for lookup table and destination (results) file
27 k_path='K:/Work/Ad-Hoc Analyses/Collision PDF Puller/'
28 lookup_file = k_path + 'LOOKUP_TABLE/Yonge_Gerrard_Davisville.csv'
29
30 # Names of lookup table, destination file
31 dest_path=k_path + 'destination/'
32 dest_file = dest_path + 'results.csv'
33
34 # Folder containing data files to search through
35 data_path = '//tssrv7/CollisionsProcessed/Backup/PdfProcessed/'
36 #---------------------------------------------------------------
```

#### 2.2 Figure out the filename to search for based on the first 2 digits of `identifier`
The script is set up assuming the following naming convention. **If your files use a different naming system, you must modify the code accordingly.**

The first two digits of the `identifier` in the lookup table are cryptically related to the filenames of PDFs in the database.

EXAMPLE: if `identifier = 178005881`, then the file to look for is `17178005881`. If `identifier = 6002116588`, then the file to look for is `166002116588`. That is, the prefix `17` (former case) and `16` (latter case) was added to the `identifier`.

The logic in lines L57-L63 of `pull_collision_pdf.py` determines the prefix to add to `identifier` , adds it, and then passes this modified value to `copy_file()` that searches for a match. 

#### 2.3 Figure out the minimum year to be searched

If your file naming system follows the logic explained in **2.2**, then set the minimum year in the `min_yr` variable in L40 of the `get_date()` function. `min_yr` is NOT THE YEAR ITSELF, rather it is a number that *represents* the minimum year. The best way to explain this is by example. If the minimum year to be searched is 2015, set `min_yr` to `50`. If it is 2016, `min_yr` is `60`, and so on. I don't know what happens if the minimum year is > 2019.

If you are following a different naming convention altogether, you may not need `min_yr` and you can replace L57-L63 with the proper logic.

#### 2.4 Ensure the date format in `copy_file()` is correct

L78 of `pull_collision_pdf.py`, in the `copy_file()` function, assumes the format of the date column in the lookup table is:

`datetime.datetime.strptime(date_found, '%m/%d/%Y %H:%M')`. 

If your lookup table date column follows a different format, either modify the lookup table to follow the above format, or modify this line of code to follow your format.

### 3) Run script with the command line
Finally, you are ready to run the script.

```cmd
python pull_collision_pdf.py get-date
```

### 4) Results
If a match is found in the data drive, the PDF is copied to the destination folder. 

In the `results.csv` file, all requested filenames are appended (first column), along with the original `ACCDATE` from the lookup table (second column) and the status ("Found" or "Missing", third column).


_**Note**: Every 3000 rows take about an hour to complete. The execution time is printed to screen when the script finishes running._
