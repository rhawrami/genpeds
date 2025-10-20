import concurrent.futures
import time
import random
import zipfile
import os
from pathlib import Path
import json
import warnings
import re
from typing import (Optional, 
                    Union, 
                    List, 
                    Tuple,
                    Dict)

import requests


def get_year_iter(subject: str,
                  year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> List[int]:
    '''
    get year iterable based on subject and year input

    :param subject: string identifying which subject data to download. The subjects available are:
     ['characteristics', 'admissions', 'enrollment', 'completion', 'cip', 'graduation']
    
    :param year_range: tuple of year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from. Data for 'characteristics', 'enrollment' and 'completion' are available for years 1984-2023, while 'graduation' is available for years 2000-2023. Defaults to all available years for a subject.
    '''
    subject = subject.lower()

    if not year_range:
        if subject == 'graduation':
            start, end = 2000, 2023
            iter_range = list(range(start, end + 1))  # default for graduation data
        elif subject == 'admissions':
            start, end = 2001, 2023
            iter_range = list(range(start, end + 1))  # default for admissions data
        else:
            start, end = 1984, 2023
            iter_range = list(range(start, end + 1))  # default for all other data
    else:
        if isinstance(year_range, tuple):
            start, end = year_range
            iter_range = list(range(start, end + 1))  # tuple follows regular range
        elif isinstance(year_range, list):
            iter_range = year_range  # list remains list
        elif isinstance(year_range, int):
            start = year_range
            iter_range = [start]  # integer becomes one-element list
        else:
            raise TypeError('Please enter a tuple range, list of integers, or a single integer')
    
    return iter_range


def get_file_endpoint(subject: str, 
                      year: int,
                      cfg: Dict[str, str]) -> Optional[str]:
    '''
    returns endpoint for a given subject in a given year.
    
    :param year: year for file; available years vary by subject.
    :param subject: subject.
    :param cfg: dict with subject-year endpoints
    '''
    try:
        endpoint = cfg[subject]["endpoints"][str(year)]
    except KeyError:
        warnings.warn(f'No endpoint for year {year}')
        return None
    return endpoint


def download_a_file(subject: str, 
                    year: int,
                    cfg: Dict[str,str]) -> Optional[str]:
    '''
    downloads an IPEDS subject-year data file.

    :param year: year for file; available years vary by subject.
    :param subject: subject.
    :param cfg: dict with subject-year endpoints
    '''
    dir = f'{subject}data'  # directory subject name
    prefix = subject    # file subject prefix

    if subject != 'cip':
        url_template = 'https://nces.ed.gov/ipeds/datacenter/data/{}.zip'
    else:
        url_template = 'https://nces.ed.gov/ipeds/datacenter/data/{}_Dict.zip'
    
    endpoint = get_file_endpoint(subject, year, cfg) 
    endpoint_url = url_template.format(endpoint)

    try:
        r = requests.get(endpoint_url)  
    except requests.HTTPError as er:
        return f"Year {year}: Error - {str(er)}"
        
    if '404 - File or directory not found' in r.text:
        return f"Year {year}: 404 - File not found"
    
    zipped_file = os.path.join(dir, f'{prefix}_{year}.zip')
    
    with open(zipped_file, 'wb') as f:
        f.write(r.content)

    with zipfile.ZipFile(zipped_file, 'r') as zfile:
        # there will at least be one file in each zip folder
        # to not have to deal with varying extensions, case, etc.
        # just pull the last file (in lex. order)
        # this way, we can also get the revised files instead of OG ones (they have '^.*_rv' in them)
        file_to_extract = sorted(zfile.namelist())[-1]
        zfile.extract(file_to_extract, dir)

        old = os.path.join(dir, file_to_extract)
        new = os.path.join(dir, re.sub(r'^.*\.', f'{prefix}_{year}.', old))

        os.rename(old, new)
        os.remove(zipped_file)
    
    return f'IPEDS {subject.title()} ({year}) successfully downloaded and extracted'


def scrape_ipeds_data(subject: str = 'characteristics', 
                      year_range: Optional[Union[Tuple[int,int], List[int], int]] = None, 
                      see_progress: bool = True) -> None:
    '''
    downloads NCES IPEDS data on specified years for a defined subject.
    
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
    dir = f'{subject}data'
    prefix = subject
    # Determine the years to download
    iter_range = get_year_iter(subject=subject,
                               year_range=year_range)
    
    # check if data already downloaded, if so, drop from download list
    if os.path.isdir(dir): 
        iter_range2 = []
        stripped_list = [
            re.sub(r'\.(csv|html|xlsx|xls)','',ff) 
            for ff 
            in sorted(os.listdir(dir))
        ]
        for yr in iter_range:
            if f'{prefix}_{yr}' not in stripped_list:
                iter_range2.append(yr)
        iter_range = iter_range2
    else:
        os.makedirs(dir, exist_ok=True) # create subject dir

    # open endpoint cfg
    pkg_dir = Path(__file__).parent
    endpoint_path = pkg_dir / 'cfg.json'
    with open(endpoint_path, 'r') as cfgjf:
        cfg = json.load(cfgjf)

    # multithread to speed up the process
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as exec:
        future_to_year = {exec.submit(download_a_file, subject, year, cfg): year for year in iter_range}
        for future in concurrent.futures.as_completed(future_to_year):
            yr = future_to_year[future]
            try:
                result = future.result()
                if see_progress:
                    print(result) # if you want to see the progress
                time.sleep(random.uniform(0.05, 0.2)) # you're welcome NCES :)
            except Exception as exc:
                print(f"Year {yr} generated an exception: {exc}")
