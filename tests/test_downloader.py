import os
import shutil

import pytest

from genpeds import scrape_ipeds_data

@pytest.mark.parametrize('subject, year_range_char', [
    # characteristics
    ('characteristics', (1990,2003)),
    ('characteristics', [2002,2004,2006,2008]),
    ('characteristics', 2023),
    # admissions
    ('admissions', (2008,2012)),
    ('admissions', [2001,2014,2018]),
    ('admissions', 2022),
    # enrollment
    ('enrollment', (1985,1990)),
    ('enrollment', [2018,2020,2023]),
    ('enrollment', 2002),
    # completion
    ('completion', (1984,1989)),
    ('completion', [2003,2015,2023]),
    ('completion', 2010),
    # graduation
    ('graduation', (2000,2005)),
    ('graduation', [2008,2013,2017,2019]),
    ('graduation', 2022)

])

def test_subject_downloads(subject, year_range_char):
    '''test IPEDS variable-subject data scraping'''
    download_dir = f'{subject}data'
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)

    try:
        scrape_ipeds_data(subject=subject, year_range=year_range_char)
        assert os.path.exists(download_dir), f'{subject.title()} directory not found.'
        # tuple range
        if isinstance(year_range_char, tuple):
            start,end = year_range_char
            for yr in range(start, end + 1):
                f_name = f'{subject}_{yr}.csv'
                assert f_name in os.listdir(download_dir), f'File {f_name} not found.'
        # list range
        elif isinstance(year_range_char, list):
            for yr in year_range_char:
                f_name = f'{subject}_{yr}.csv'
                assert f_name in os.listdir(download_dir), f'File {f_name} not found.'
        # single year
        else:
            f_name = f'{subject}_{year_range_char}.csv'
            assert f_name in os.listdir(download_dir), f'File {f_name} not found.'
    finally:
        shutil.rmtree(download_dir)

# you're reading this? 
# well, you should be reading 'The Master and Margarita' by Mikhail Bulgakov instead.
# you won't regret it friend :)