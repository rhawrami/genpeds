import os
import glob
import shutil

import pandas as pd
import pytest

from genpeds.cleaners import CLEANERS
from genpeds import scrape_ipeds_data
from genpeds.config import VARIABLE_DICT

def download_data_for_test():
    '''downloads data for test, assuming not already downloaded'''
    downloads = [
        ('characteristics', [2000,2010,2020]),
        ('admissions', (2001,2005)),
        ('enrollment', (1985,1990)),
        ('completion', [2002,2022,2023]),
        ('cip', [2002,2022,2023]),
        ('graduation', (2003,2008))
    ]
    for sbjct, yrs in downloads:
        if os.path.exists(f'{sbjct}data'):
            if isinstance(yrs, tuple):
                start,end = yrs
                iter_range = range(start, end + 1)
            else:
                iter_range = yrs
            for yr in iter_range:
                pattern = os.path.join(f'{sbjct}data', f'{sbjct}_{yr}.*')
                matches = glob.glob(pattern)
                if not matches:
                    scrape_ipeds_data(subject=sbjct, year_range=yr, see_progress=False)
                else:
                    continue
        else:
            scrape_ipeds_data(subject=sbjct, year_range=yrs, see_progress=False)

# some subjects take no arguments (other than directory path)
# test these together
@pytest.mark.parametrize('subject', [
    'characteristics',
    'admissions',
    'cip'
])
def test_basic_cleaners(subject):
    '''test cleaner functions that take no arguments'''
    download_data_for_test() # scrape data if needed

    subject_cleaner = CLEANERS[subject] # subject-specific cleaner function
    subject_var_dict = VARIABLE_DICT[subject].keys() # expected variables returned

    try:
        df = subject_cleaner()
        assert isinstance(df, pd.DataFrame), f'{subject} dataframe not returned.' # check that Pandas DataFrame is returned

        for col in df.columns:
            assert col in subject_var_dict # check if attributes are in expected attributes
        shutil.rmtree(f'{subject}data')
    finally:
        pass

# test enrollment, with variable arguments
@pytest.mark.parametrize('lev', [
    'undergrad',
    'grad'
])
def test_enrollment_cleaner(lev):
    '''test enrollment cleaning function'''
    download_data_for_test() # scrape data if needed

    subject_cleaner = CLEANERS['enrollment'] # enrollment cleaner function
    subject_var_dict = VARIABLE_DICT['enrollment'].keys() # expected variables returned

    try:
        df = subject_cleaner(student_level=lev) # tries 'undergrad' and 'grad'
        assert isinstance(df, pd.DataFrame), f'Enrollment dataframe not returned.' # check that Pandas DataFrame is returned

        for col in df.columns:
            assert col in subject_var_dict # check if attributes are in expected attributes
        shutil.rmtree(f'enrollmentdata')
    finally:
        pass

# test completion
@pytest.mark.parametrize('lev', [
    'assc', 
    'bach', 
    'mast', 
    'doct'
])
def test_completion_cleaner(lev):
    '''test completion cleaning function'''
    download_data_for_test() # scrape data if needed

    subject_cleaner = CLEANERS['completion'] # completion cleaner function
    subject_var_dict = VARIABLE_DICT['completion'].keys() # expected variables returned

    try:
        df = subject_cleaner(level=lev) # tries 'assc', 'bach', 'mast', 'doct'
        assert isinstance(df, pd.DataFrame), f'Completion dataframe not returned.' # check that Pandas DataFrame is returned

        for col in df.columns:
            assert col in subject_var_dict # check if attributes are in expected attributes
        shutil.rmtree(f'completiondata')
    finally:
        pass

# test graduation
@pytest.mark.parametrize('lev', [
    'assc', 
    'bach'
])
def test_graduation_cleaner(lev):
    '''test graduation cleaning function'''
    download_data_for_test() # scrape data if needed

    subject_cleaner = CLEANERS['graduation'] # graduation cleaner function
    subject_var_dict = VARIABLE_DICT['graduation'].keys() # expected variables returned

    try:
        df = subject_cleaner(deg_level=lev) # tries 'undergrad' and 'grad'
        assert isinstance(df, pd.DataFrame), f'Graduation dataframe not returned.' # check that Pandas DataFrame is returned

        for col in df.columns:
            assert col in subject_var_dict # check if attributes are in expected attributes
        shutil.rmtree(f'graduationdata')
    finally:
        pass