import os

import pytest
import pandas as pd


from genpeds import Characteristics, Admissions, Enrollment, Completion, Graduation

# classes to test
# - Characteristics
# - Admissions
# - Enrollment
# - Completion (CIP automatically gets tested here, depending on args)
# - Graduation

# non-unique methods to test
# - .get_description()
# - .get_available_years()
# - .get_available_vars()
# - .lookup_var()
# - .scrape()

# unique methods to test
# .clean()
# .run()


def get_iter_range(years):
    '''returns range of years depending on object type.'''
    if isinstance(years, tuple):
        start,end = years
        iter_range = range(start, end + 1)
    elif isinstance(years, list):
        iter_range = years
    elif isinstance(years, int):
        iter_range = [years]
    else:
        raise ValueError('years must be tuple, list or int.')
    return iter_range

@pytest.mark.parametrize('subject_name, subject, year_range', [
    ('characteristics', Characteristics, (2000,2005)), 
    ('admissions', Admissions, [2005,2009,2012,2022]),
    ('enrollment', Enrollment, [1984,1989,1990,2003,2023]),
    ('completion', Completion, (2002,2012)),
    ('graduation', Graduation, (2015,2019))
])
def test_common_methods(subject_name, subject, year_range):
    '''test non-unique methods for genpeds classes'''
    genpeds_class = subject(year_range=year_range)
    # test if .year_range() returns correct ranges
    if isinstance(genpeds_class, (Characteristics, Enrollment, Completion)):
        assert genpeds_class.get_available_years() == (1984,2023) # check if returns appropriate range
    elif isinstance(genpeds_class, Admissions):
        assert genpeds_class.get_available_years() == (2001,2023)
    else:
        assert genpeds_class.get_available_years() == (2000,2023)
    # test if correct description is returned, lazy test but it's fine for now
    assert subject_name in genpeds_class.get_description().lower()
    # test .available_vars()
    assert isinstance(genpeds_class.get_available_vars(), dict)
    assert 'year' in genpeds_class.get_available_vars().keys()
    # test .lookup_var()
    assert 'Institutional unique identifier ID' in  genpeds_class.lookup_var('id') 
    # test .scrape() works, and that all files are downloaded in relevant dirs
    genpeds_class.scrape()
    dir_name = f'{subject_name}data' 
    assert os.path.exists(dir_name) # was subject directory created?
    for yr in get_iter_range(years=year_range):
        f_name = f'{subject_name}_{yr}.csv'
        assert f_name in os.listdir(dir_name) # was each year's file downloaded?

# test .clean() and .run() for subjects that don't take additional args
# e.g., Characteristics and Admissions
@pytest.mark.parametrize('subject, year_range', [
    (Characteristics, [2000,2005, 2010]),
    (Admissions, [2010, 2013, 2017])
])
def test_cleanrun_basic(subject, year_range):
    '''test .clean() and .run() for Characteristics and Admissions.'''
    # test clean first, assuming we still have data in our directory from before
    df1 = subject().clean()

    assert isinstance(df1, pd.DataFrame)
    assert 'id' in df1.columns
    if subject == Characteristics:
        assert 'name' in df1.columns
        assert len(df1.loc[df1['name'] == 'Harvard University']) > 0
        assert df1.loc[df1['name'] == 'Harvard University', 'state'].mode()[0] == 'Massachusetts'
    if subject == Admissions:
        assert 16 < df1['act_eng_25'].mean() < 36
        assert 16 < df1['act_math_25'].mean() < 36

    # test run now
    df2 = subject(year_range=year_range).run()

    assert isinstance(df2, pd.DataFrame)
    if subject == Characteristics:
        assert len(df1.loc[df1['name'] == 'Vanderbilt University']) > 0
        assert df1.loc[df1['name'] == 'Vanderbilt University', 'state'].mode()[0] == 'Tennessee'
    if subject == Admissions:
        assert 16 < df1['act_eng_75'].mean() < 36
        assert 16 < df1['act_math_75'].mean() < 36

# test Enrollment().clean() and Enrollment().run() now
# .clean() and .run() take in a 'student_level' param
# with 'undergrad' and 'grad' as the options
# here, we'll also see if the merge_with_char param works
@pytest.mark.parametrize('lev, year_range', [
    ('undergrad', (1985,1990)),
    ('grad', [1987, 2004, 2012, 2022])
])
def test_enrollment_extended(lev, year_range):
    '''tests Enrollment().clean() and Enrollment().run()'''
    # test Enrollment.clean()
    df1 = Enrollment().clean(student_level=lev) # try both 'undergrad' and 'grad'

    assert isinstance(df1, pd.DataFrame)
    for col in ['totmen_share', 'totwt_share', 
                'totbk_share', 'tothsp_share', 'totasn_share']:
        assert 0 <= df1.loc[df1['id'] == '190150', col].mean() <= 100 
                                           # some may be out of range

    # test Enrollment.run(), with merge_with_char
    df2 = Enrollment(year_range=year_range).run(merge_with_char=True)

    assert 'name' in df2.columns
    assert len(df2.loc[df2['name'] == 'Stanford University']) > 0

# Completion().clean() and Completion().run()
# these methods take the degree_level param 
# options include ['assc', 'bach', 'mast', 'doct']
# run also takes get_cip_codes bool param
@pytest.mark.parametrize('lev, year_range', [
    ('assc', [2012,2022]),
    ('bach', [1990,1994,2000]),
    ('mast', [2015,2016,2019]),
    ('doct', [1999, 2020,2023])
])
def test_completion_extended(lev, year_range):
    '''tests Completion().clean() and Completion().run()'''
    # test Completion.clean()
    df1 = Completion().clean(degree_level=lev) # try all degree levels

    assert isinstance(df1, pd.DataFrame)
    assert 0 <= df1['totmen_share'].mean() <= 100

    # test Completion.run(), with merge_with_char and get_cip_codes
    df2 = Completion(year_range=year_range).run(merge_with_char=True, get_cip_codes=True)

    assert 'name' in df2.columns
    assert len(df2.loc[df2['name'] == 'Stanford University']) > 0
    assert 'cip_description' in df2.columns
    assert len(df2.loc[df2['cip_description'] == 'Physics']) > 0
    
# test Graduation.clean() and Graduation.run()
# Graduation takes degree_level param
# options include 'assc', 'bach'
@pytest.mark.parametrize('lev, year_range', [
    ('assc', [2004,2005,2018,2020]),
    ('bach', [2017,2019,2022,2023])
])
def test_graduation_extended(lev, year_range):
    '''tests Graduation.clean() and Graduation.run()'''
    # Graduation.clean()
    df1 = Graduation().clean(degree_level=lev)
    
    assert isinstance(df1, pd.DataFrame)
    assert 0 <= df1['gradrate_totmen'].mean() <= 100
    assert 0 <= df1['gradrate_totwomen'].mean() <= 100

    # Graduation.run()
    df2 = Graduation(year_range=year_range).run(degree_level=lev, merge_with_char=True)

    assert 'name' in df2.columns # check if Characteristics merge works
    for col in ['gradrate_totmen', 'gradrate_totwomen']:
        for school in ['Carnegie Mellon University', 'Cornell University', 
                                'Princeton University', 'Brown University']:
            if len(df2.loc[df2['name'] == school]) > 0: # these schools don't have assc programs
                assert df2.loc[df2['name'] == school, 
                                             col].mean() > 80 # just a hunch

