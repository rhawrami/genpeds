import concurrent.futures
import time
import random
import requests
import zipfile
import os
import warnings
import re
from genpeds.config import DATASETS

def get_file_endpoint(subject, year):
    '''returns endpoint for a given subject in a given year.
    
    :param year: year for file; available years vary by subject.
    :param subject: subject.
    '''
    format_rules = DATASETS[subject]['format_rules'] # rules for each subject-year combination
    endpoint_template = DATASETS[subject]['file_template'] # endpoint template

    lag0, lag1, lead1 = year-1900, year-1901, year-1899 # needed for format rules
    for cond,frmt in format_rules:
        if cond(year):
            yr_format = frmt.format(year=year, 
                                        lag0=str(lag0), 
                                        lag1 = str(lag1), 
                                        lead1 = str(lead1))
            endpoint = endpoint_template.format(yr_format) # formatted endpoint
            break
    else:
            warnings.warn(f'No formatted rule for year {year}')
            return None
    
    return endpoint

def download_a_file(subject, year):
    '''downloads an IPEDS subject-year data file.

    :param year: year for file; available years vary by subject.
    :param subject: subject.
    '''
    relevant_dir = DATASETS[subject]['dir'] # directory subject name
    relevant_prefix = DATASETS[subject]['file_prefix'] # file subject prefix

    endpoint = get_file_endpoint(subject, year) # get endpoint for a subject-year combination

    try:
        r = requests.get(endpoint)  # try request
    except requests.HTTPError as er:
        return f"Year {year}: Error - {str(er)}"
        
    if '404 - File or directory not found' in r.text:
        return f"Year {year}: 404 - File not found"
    
    zipped_file = os.path.join(relevant_dir, f'{relevant_prefix}_{year}.zip')
    # Use context manager to ensure proper file handling
    with open(zipped_file, 'wb') as f:
        f.write(r.content)
    
    with zipfile.ZipFile(zipped_file, 'r') as zfile:
        if subject == 'cip':
            file_to_extract = endpoint.split('/')[-1].replace('_Dict.zip', '').lower()
            for ext in ['.html', '.xls', '.xlsx']:  # diff file formats, try each one
                try:
                    zfile.extract(file_to_extract + ext, relevant_dir)
                    # remove & remove zipped file
                    old_name_file = os.path.join(relevant_dir, f'{file_to_extract}{ext}')
                    new_name_file = os.path.join(relevant_dir, f'cipcodes_{year}{ext}')
                    os.rename(old_name_file, new_name_file)
                    os.remove(zipped_file)
                    break
                except KeyError:
                    continue
        else:
            file_to_extract = endpoint.split('/')[-1].replace('.zip', '').lower() + '.csv'
            zfile.extract(file_to_extract, relevant_dir)
            # remove & remove zipped file
            old_name_file = os.path.join(relevant_dir, file_to_extract)
            new_name_file = os.path.join(relevant_dir, f'{relevant_prefix}_{year}.csv')
            os.rename(old_name_file, new_name_file)
            os.remove(zipped_file)

    return(f'IPEDS {subject.title()} ({year}) successfully downloaded and extracted')


def scrape_ipeds_data(subject='characteristics', year_range = None, see_progress = True):
    '''downloads NCES IPEDS data on specified years for a defined subject.
    
    :param subject: string identifying which subject data to download. The subjects available are:
     ['characteristics', 'admissions', 'enrollment', 'completion', 'cip', 'graduation']
    
    :param year_range: tuple of year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from. Data for 'characteristics', 'enrollment' and 'completion' are available for years 1984-2023, while 'graduation' is available for years 2000-2023. Defaults to all available years for a subject.

    :param see_progress: boolean that, when true, prints completion statement for extraction of each year. If false, no messages printed.
    
    ## available data

    - :characteristics: institutional characteristics, like a school's name, address. Certain variables, like a school's longitude and latitude are only available in later years. Available for years 1984-2023.

    - :admissions: Admissions data, like number of applications and acceptances by gender. Available for years 2001-2023.

    - :enrollment: fall enrollment by gender and institutional level (e.g., 4-year undergraduate program), with most years including enrollment by race and gender. Available for years 1984-2023.

    - :completion: completion of degrees by gender, level of degree and subject field (e.g., Bachelor's in Economics), with most years including completion by race and gender. Available for years 1984-2023.

    - :cip: CIP, or Classification of Instructional Programs, are key-value pairs for subject study fields. CIP's vary by year, and are relevant to identify subject field in completion data. Available for years 1984-2023.

    - :graduation: number of cohorts and graduates by gender, institutional level and graduation measure (e.g., students earning a bachelor's degree within 6 years of entering). Available for years 2000-2023.
    '''
    subject = subject.lower()
    relevant_dir = DATASETS[subject]['dir']
    relevant_prefix = DATASETS[subject]['file_prefix'] # file subject prefix
    # Determine the years to download
    if not year_range:
        if subject == 'graduation':
            start, end = 2000, 2023
            iter_range = range(start, end + 1)  # default for graduation data
        elif subject == 'admissions':
            start, end = 2001, 2023
            iter_range = range(start, end + 1)  # default for admissions data
        else:
            start, end = 1984, 2023
            iter_range = range(start, end + 1)  # default for all other data
    else:
        if isinstance(year_range, tuple):
            start, end = year_range
            iter_range = range(start, end + 1)  # tuple follows regular range
        elif isinstance(year_range, list):
            iter_range = year_range  # list remains list
        elif isinstance(year_range, int):
            start = year_range
            iter_range = [start]  # integer becomes one-element list
        else:
            raise ValueError('Please enter a tuple range, list of integers, or a single integer')
    
    if os.path.isdir(relevant_dir): # so we don't need to redownload if it isn't necessary
        iter_range2 = []
        stripped_list = [re.sub(r'\.csv|\.html|\.xlsx|\.xlsx','',ff) 
                             for ff in sorted(os.listdir(relevant_dir))]
        for yr in iter_range:
            if f'{relevant_prefix}_{yr}' not in stripped_list:
                iter_range2.append(yr)
        iter_range = iter_range2
    else:
        os.makedirs(relevant_dir, exist_ok=True) # create subject directory, where unzipped files will be stored

    # multithread to speed up the process
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as exec:
        future_to_year = {exec.submit(download_a_file, subject, year): year for year in iter_range}
        for future in concurrent.futures.as_completed(future_to_year):
            yr = future_to_year[future]
            try:
                result = future.result()
                if see_progress:
                    print(result) # if you want to see the progress
                time.sleep(random.uniform(0.1, 0.3)) # you're welcome NCES :)
            except Exception as exc:
                print(f"Year {yr} generated an exception: {exc}")

