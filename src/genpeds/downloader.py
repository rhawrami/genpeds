import concurrent.futures
import time
import random
import zipfile
import os
import tempfile
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


SUBJECTS = {
    'characteristics', 'admissions', 'enrollment', 'distance_enrollment',
    'twelve_month_enrollment', 'instructional_activity', 'retention', 'tuition', 'tuition_program',
    'student_aid', 'student_aid_net_price', 'veterans_aid', 'completion',
    'completers', 'completers_by_award', 'cip', 'graduation', 'graduation200',
    'outcome_measures', 'finance', 'finance_f2', 'finance_f3', 'academic_libraries',
    'human_resources', 'hr_employees',
    'hr_instructional_staff', 'hr_faculty_ranks', 'hr_new_hires',
    'hr_instructional_salaries', 'hr_noninstructional_salaries'
}
MAX_ZIP_BYTES = 256 * 1024 * 1024
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_ZIP_MEMBERS = 1000
MAX_REQUESTED_YEARS = 1000
REQUEST_TIMEOUT = (10, 120)  # connect and per-read timeouts, in seconds


def get_year_iter(subject: str,
                  year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> List[int]:
    '''
    get year iterable based on subject and year input

    :param subject: configured subject name; see SUBJECTS for accepted source families.
    
    :param year_range: tuple of year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from. Retention is available for 2003-2024; other subjects have their own year ranges. Defaults to all available years for a subject.
    '''
    if not isinstance(subject, str):
        raise TypeError('subject must be a string')
    subject = subject.lower()
    if subject not in SUBJECTS:
        raise ValueError(f'Unknown IPEDS subject: {subject}')

    if year_range is None:
        if subject == 'characteristics':
            start, end = 1984, 2025
            iter_range = list(range(start, end + 1))
        elif subject in ('twelve_month_enrollment', 'instructional_activity'):
            start, end = 2002, 2025
            iter_range = list(range(start, end + 1))
        elif subject == 'distance_enrollment':
            start, end = 2012, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'graduation200':
            start, end = 2008, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'outcome_measures':
            start, end = 2015, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'human_resources' or subject.startswith('hr_'):
            start, end = 2012, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'finance' or subject.startswith('finance_'):
            iter_range = list(range(2004, 2025))
        elif subject == 'academic_libraries':
            iter_range = list(range(2014, 2025))
        elif subject in ('completion', 'cip'):
            start, end = 1984, 2025
            iter_range = list(range(start, end + 1))
        elif subject in ('completers', 'completers_by_award'):
            start, end = 2012, 2025
            iter_range = list(range(start, end + 1))
        elif subject in ('tuition', 'tuition_program'):
            start, end = 2000, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'student_aid_net_price':
            iter_range = [2024]
        elif subject == 'veterans_aid':
            start, end = 2014, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'student_aid':
            start, end = 2002, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'retention':
            start, end = 2003, 2024
            iter_range = list(range(start, end + 1))
        elif subject == 'graduation':
            start, end = 2000, 2024
            iter_range = list(range(start, end + 1))  # default for graduation data
        elif subject == 'admissions':
            start, end = 2001, 2024
            iter_range = list(range(start, end + 1))  # default for admissions data
        else:
            start, end = 1984, 2024
            iter_range = list(range(start, end + 1))  # default for all other data
    else:
        if isinstance(year_range, tuple):
            if len(year_range) != 2 or any(type(year) is not int for year in year_range):
                raise TypeError('Year range must be a (start, end) tuple of integers')
            start, end = year_range
            if end < start or end - start + 1 > MAX_REQUESTED_YEARS:
                raise ValueError('Year range is reversed or too large')
            iter_range = list(range(start, end + 1))  # tuple follows regular range
        elif isinstance(year_range, list):
            if len(year_range) > MAX_REQUESTED_YEARS:
                raise ValueError('Too many requested years')
            if any(type(year) is not int for year in year_range):
                raise TypeError('Year list must contain integers')
            iter_range = year_range  # list remains list
        elif type(year_range) is int:
            start = year_range
            iter_range = [start]  # integer becomes one-element list
        else:
            raise TypeError('Please enter a tuple range, list of integers, or a single integer')
    
    if subject == 'retention' and any(year < 2003 or year > 2024 for year in iter_range):
        raise ValueError('Retention data is available for years 2003-2024')
    if subject == 'characteristics' and any(year < 1984 or year > 2025 for year in iter_range):
        raise ValueError('Characteristics data is available for years 1984-2025')
    if subject == 'twelve_month_enrollment' and any(year < 2002 or year > 2025 for year in iter_range):
        raise ValueError('12-month enrollment headcounts are available for years 2002-2025')
    if subject == 'instructional_activity' and any(year < 2002 or year > 2025 for year in iter_range):
        raise ValueError('12-month instructional activity is available for years 2002-2025')
    if subject == 'distance_enrollment' and any(year < 2012 or year > 2024 for year in iter_range):
        raise ValueError('Fall distance enrollment data is available for years 2012-2024')
    if subject == 'graduation200' and any(year < 2008 or year > 2024 for year in iter_range):
        raise ValueError('GR200 data is available for reporting years 2008-2024')
    if subject == 'outcome_measures' and any(year < 2015 or year > 2024 for year in iter_range):
        raise ValueError('Outcome Measures data is available for reporting years 2015-2024')
    if (subject == 'human_resources' or subject.startswith('hr_')) and any(
            year < 2012 or year > 2024 for year in iter_range):
        raise ValueError('Modern Human Resources files are available for years 2012-2024')
    if (subject == 'finance' or subject.startswith('finance_')) and any(
            year < 2004 or year > 2024 for year in iter_range):
        raise ValueError('Finance F1A/F2/F3 files are available for fiscal years 2004-2024')
    if subject == 'academic_libraries' and any(year < 2014 or year > 2024 for year in iter_range):
        raise ValueError('Annual Academic Libraries files are available for fiscal years 2014-2024')
    if subject in ('completion', 'cip') and any(year < 1984 or year > 2025 for year in iter_range):
        raise ValueError('Completion and CIP files are available for years 1984-2025')
    if subject in ('completers', 'completers_by_award') and any(year < 2012 or year > 2025 for year in iter_range):
        raise ValueError('Distinct-completer files are available for years 2012-2025')
    if subject in ('tuition', 'tuition_program') and any(year < 2000 or year > 2024 for year in iter_range):
        raise ValueError('Tuition data is available for years 2000-2024')
    if subject == 'student_aid' and any(year < 2002 or year > 2024 for year in iter_range):
        raise ValueError('Student aid data is available for aid years ending 2002-2024')
    if subject == 'student_aid_net_price' and any(year != 2024 for year in iter_range):
        raise ValueError('Cost II net price supplement is available for aid year 2024')
    if subject == 'veterans_aid' and any(year < 2014 or year > 2024 for year in iter_range):
        raise ValueError('Veterans aid data is available for aid years ending 2014-2024')

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
    if subject not in SUBJECTS:
        raise ValueError(f'Unknown IPEDS subject: {subject}')
    directory = Path(f'{subject}data')
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f'Download directory must be a regular directory: {directory}')

    spec_prefix = 'https://nces.ed.gov/ipeds/complete-data-files/' if year > 2022 else 'https://nces.ed.gov/ipeds/datacenter/data/'
    if subject != 'cip':
        url_template = spec_prefix + '{}.zip'
    else:
        url_template = spec_prefix + '{}_Dict.zip'
    
    endpoint = get_file_endpoint(subject, year, cfg) 
    if endpoint is None or not re.fullmatch(r'[A-Za-z0-9_-]+', endpoint):
        raise ValueError(f'No safe endpoint configured for {subject} in {year}')
    endpoint_url = url_template.format(endpoint)

    zipped_file = None
    extracted_file = None
    try:
        response = requests.get(endpoint_url, stream=True, allow_redirects=False,
                                timeout=REQUEST_TIMEOUT)
        try:
            if response.status_code != 200:
                response.raise_for_status()
                raise ValueError(f'Unexpected HTTP {response.status_code} for {endpoint_url}')
            length = response.headers.get('Content-Length')
            if length and int(length) > MAX_ZIP_BYTES:
                raise ValueError(f'ZIP exceeds download limit for {subject} in {year}')
            with tempfile.NamedTemporaryFile(dir=directory, prefix='.genpeds-',
                                             suffix='.zip', delete=False) as target:
                zipped_file = Path(target.name)
                size = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    size += len(chunk)
                    if size > MAX_ZIP_BYTES:
                        raise ValueError(f'ZIP exceeds download limit for {subject} in {year}')
                    target.write(chunk)
        finally:
            response.close()

        allowed = {'.html', '.xls', '.xlsx'} if subject == 'cip' else {'.csv'}
        with zipfile.ZipFile(zipped_file) as archive:
            if len(archive.infolist()) > MAX_ZIP_MEMBERS:
                raise ValueError(f'ZIP has too many members for {subject} in {year}')
            candidates = [entry for entry in archive.infolist()
                          if not entry.is_dir() and Path(entry.filename).suffix.lower() in allowed]
            if not candidates:
                raise ValueError(f'No expected data file in {endpoint_url}')
            member = max(candidates, key=lambda entry: (
                Path(entry.filename).stem.lower().endswith('_rv'), entry.filename.lower()))
            if member.file_size > MAX_EXTRACTED_BYTES:
                raise ValueError(f'Extracted file exceeds limit for {subject} in {year}')
            extension = Path(member.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(dir=directory, prefix='.genpeds-',
                                             suffix='.part', delete=False) as target:
                extracted_file = Path(target.name)
                with archive.open(member) as source:
                    size = 0
                    for chunk in iter(lambda: source.read(64 * 1024), b''):
                        size += len(chunk)
                        if size > MAX_EXTRACTED_BYTES:
                            raise ValueError(f'Extracted file exceeds limit for {subject} in {year}')
                        target.write(chunk)
        os.replace(extracted_file, directory / f'{subject}_{year}{extension}')
    finally:
        for path in (zipped_file, extracted_file):
            if path is not None:
                path.unlink(missing_ok=True)
    
    return f'IPEDS {subject.title()} ({year}) successfully downloaded and extracted'


def scrape_ipeds_data(subject: str = 'characteristics', 
                      year_range: Optional[Union[Tuple[int,int], List[int], int]] = None, 
                      see_progress: bool = True) -> None:
    '''
    downloads NCES IPEDS data on specified years for a defined subject.
    
    :param subject: configured subject name; see SUBJECTS for accepted source families.
    
    :param year_range: tuple of year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from. Retention is available for 2003-2024; other subjects have their own year ranges. Defaults to all available years for a subject.

    :param see_progress: boolean that, when true, prints completion statement for extraction of each year. If false, no messages printed.
    
    ## available data

    - :characteristics: institutional characteristics, like a school's name, address, control, sector, and location. Certain variables, like coordinates, are only available in later years. Available for years 1984-2025.

    - :admissions: Admissions data, like number of applications and acceptances by gender. Available for years 2001-2024.

    - :enrollment: fall enrollment by gender and institutional level (e.g., 4-year undergraduate program), with most years including enrollment by race and gender. Available for years 1984-2024.

    - :distance_enrollment: fall counts for students in exclusively/some/no distance education courses and locations of exclusively distance students, 2012-2024 (EF*A_DIST).

    - :twelve_month_enrollment: unduplicated 12-month student headcounts, ending years 2002-2025 (EFFY files). Separate from the fall enrollment snapshot.

    - :instructional_activity: 12-month credit/contact-or-clock hours and (from 2004) estimated/reported FTE for periods ending 2002-2025 (EFIA files).

    - :retention: first-year full-time and part-time undergraduate retention rates and (from 2007) cohort counts. Available for years 2003-2024 in the Fall Enrollment D files.

    - :tuition: published academic-year tuition and fees (IC academic-year files through 2023, Cost I in 2024). Use :tuition_program: for program-year reporters; available for 2000-2024.

    - :student_aid: SFA counts and amounts, indexed by the ending year of the aid period, 2002-2024 (SFA0102 to SFA2324).

    - :veterans_aid: Post-9/11 GI Bill and DoD Tuition Assistance recipients and dollars, by undergraduate/graduate level, aid years ending 2014-2024 (SFAV files).

    - :completion: completion of degrees by gender, level of degree and subject field (e.g., Bachelor's in Economics), with most years including completion by race and gender. Available for years 1984-2025.

    - :completers: distinct people receiving any award (C*_B), 2012-2025. Use :completers_by_award: for distinct completers within each award level and age band (C*_C).

    - :cip: CIP, or Classification of Instructional Programs, are key-value pairs for subject study fields. CIP's vary by year, and are relevant to identify subject field in completion data. Available for years 1984-2025.

    - :graduation: number of cohorts and graduates by gender, institutional level and graduation measure (e.g., students earning a bachelor's degree within 6 years of entering). Available for years 2000-2024.

    - :graduation200: distinct bachelor and less-than-four-year cohort measures at 100/150/200% of normal time, GR200_08–GR200_24 (2008-2024).

    - :outcome_measures: undergraduate 4/6/8-year awards and eight-year enrollment outcomes by entry cohort, 2015-2024 (OM files).

    - :human_resources: staff by occupation/attendance and sex/race, 2012-2024 (S*_OC). Internal hr_* subjects download the other modern HR families selected by HumanResources.run(dataset=...).

    - :finance: public GASB finance (F*_F1A), fiscal years 2004-2024. Internal finance_f2 and finance_f3 subjects download the FASB forms selected by Finance.run(form=...).

    - :academic_libraries: annual AL2014-AL2024 institution-level library collections, services, staffing and expenditures, by fiscal year. The collection was retired after 2024-25.
    '''
    if not isinstance(subject, str):
        raise TypeError('subject must be a string')
    subject = subject.lower()
    # Determine the years to download
    iter_range = get_year_iter(subject=subject,
                               year_range=year_range)
    iter_range = list(dict.fromkeys(iter_range))  # avoid concurrent writes for repeated years

    # open endpoint cfg
    pkg_dir = Path(__file__).parent
    endpoint_path = pkg_dir / 'cfg.json'
    with open(endpoint_path, 'r') as cfgjf:
        cfg = json.load(cfgjf)
    for year in iter_range:
        endpoint = get_file_endpoint(subject, year, cfg)
        if endpoint is None or not re.fullmatch(r'[A-Za-z0-9_-]+', endpoint):
            raise ValueError(f'No safe endpoint configured for {subject} in {year}')

    directory = Path(f'{subject}data')
    if directory.is_symlink():
        raise ValueError(f'Download directory must not be a symlink: {directory}')
    directory.mkdir(exist_ok=True)
    if not directory.is_dir():
        raise ValueError(f'Download path must be a directory: {directory}')
    cached = {path.name for path in directory.iterdir()
              if path.is_file() and not path.is_symlink() and path.stat().st_size > 0}
    extensions = ('.html', '.xls', '.xlsx') if subject == 'cip' else ('.csv',)
    if any((directory / f'{subject}_{year}{extension}').is_symlink()
           for year in iter_range for extension in extensions):
        raise ValueError(f'Download cache must not contain symlinked {subject} data files')
    iter_range = [year for year in iter_range if not any(
        f'{subject}_{year}{extension}' in cached for extension in extensions)]

    # multithread to speed up the process
    failures = []
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
                failures.append((yr, exc))
    if failures:
        years = sorted(year for year, _ in failures)
        raise RuntimeError(f'IPEDS {subject} download failed for years {years}') from failures[0][1]
