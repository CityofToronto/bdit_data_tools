# PDF Extractor

The [Python script](pull_collision_pdf.py) in this folder is used to pull collision PDFs from the data drive based on the `identifiers` in the **first column** of the  provided lookup table (CSV file). The first column in the lookup table should contain the name of the file to be searched for, and the second column should contain the date. The format of these dates might be different for each lookup table, therefore the user must check (see User-defined parameters below).

The script goes through the following steps:

- reads the `identifier` from the first column of the lookup table
- appends to the `identifier` a prefix that is either one of `15`, `16`,
`17`, `18`, `19`, or one of `50`, `60`, `70`, `80`, `90`, depending on the first 2 digits
of the `identifier`. The logic here is that if the `identifier` starts with `15`,..., `19`, this means the collision year was `2015`, ..., `2019` and the collision file was recorded by doubling the digits: 
`1515`, ..., `1919`. If, however, the first 2 digits of the `identifier` start on a decade, e.g. `50`, ..., `90`, then the collision file was recorded by adding the year `15`,..., `19` as a prefix. EXAMPLE: if `identifier=178005881`, then the file to look for is `17178005881`. If `identifier=6002116588`, then the file to look for is `166002116588`. **If this naming system changes, the code to add a prefix to the
identifier needs to be modified accordingly.**
- if a match is found between the identifier and one of the PDF files in the data drive, the PDF file is copied to a destination folder.
- a results CSV file is then appended to record the status of whether the file was found or missing.


## How to use the script

### 1) Create a destination folder and initialize the results file

  - create a folder named `destination` (to which will be transferred the found PDFs)
  - created a folder called `LOOKUP_TABLE` inside `destination/` that contains the lookup table csv file
  - in the destination folder, create an empty csv file called `results.csv` that only contains 3 column
  headers: ACCNB, ACCDATE, STATUS


### 2) User-defined parameters

  - Section L25-35: Define the file paths and file names
  - in `get_date()`, check that `min_yr` corresponds to the earliest year to be searched. For example, if 
  the date range is from 2015 to 2019, `min_yr` should be set to `50`.
  - also in `get_date()`, the complicated logic to add a prefix to `identifier` is defined. **This should be changed if the file naming strategy follows a different logic.**
  - in `copy_file()`, the format of the date in the lookup table (second column) follows this format:
  `datetime.datetime.strptime(date_found, '%m/%d/%Y %H:%M')`. **Please modify accordingly if the date format in the lookup table is different from this.**

### 3) Run script with the command line

```cmd
python pull_collision_pdf.py get-date
```

_**Note**: Every 3000 rows take about an hour to complete. The execution time is printed to screen when the script finishes running._
