"""Optional independent real-file smoke checks for the older subject cleaners.

The detailed transformation/edge-case tests for these subjects use small
local fixtures elsewhere in the suite. These checks use one NCES year each.
"""

import os

import pandas as pd
import pytest

from genpeds import Cip, Enrollment, Graduation, scrape_ipeds_data
from genpeds.cleaners import CLEANERS


def test_historical_enrollment_uses_year_specific_level_rows(tmp_path):
    directory = tmp_path / 'enrollmentdata'
    directory.mkdir()
    pd.DataFrame({'UNITID': ['100001'] * 3, 'LINE': [1, 15, 11],
                  'EFRACE15': [10, 2, 4], 'EFRACE16': [20, 3, 6]}).to_csv(
        directory / 'enrollment_1985.csv', index=False)
    pd.DataFrame({'UNITID': ['100001'] * 3, 'LINE': [8, 22, 14],
                  'EFRACE15': [20, 5, 8], 'EFRACE16': [30, 5, 10]}).to_csv(
        directory / 'enrollment_1986.csv', index=False)
    undergraduate = Enrollment((1985, 1986)).clean(enroll_dir=str(directory))
    graduate = Enrollment((1985, 1986)).clean(student_level='grad', enroll_dir=str(directory))
    assert undergraduate['totmen'].tolist() == [12, 25]
    assert graduate['totmen'].tolist() == [4, 8]
    assert undergraduate.loc[0, 'totmen_share'] == 12 / 35 * 100


def test_graduation_uses_adjusted_cohort_not_sum_of_status_rows(tmp_path):
    directory = tmp_path / 'graduationdata'
    directory.mkdir()
    pd.DataFrame({
        'UNITID': ['100001', '100001', '100001'],
        'SECTION': [2, 2, 2], 'CHRTSTAT': [12, 12, 12],
        'GRTYPE': [8, 9, 10], 'GRTOTLM': [100, 80, 999],
        'GRTOTLW': [120, 90, 999],
        'GRWHITM': [60, 48, 999], 'GRWHITW': [70, 49, 999],
        'GRBKAAM': [20, 16, 999], 'GRBKAAW': [20, 16, 999],
        'GRHISPM': [10, 8, 999], 'GRHISPW': [15, 12, 999],
        'GRASIAM': [10, 8, 999], 'GRASIAW': [15, 12, 999],
    }).to_csv(directory / 'graduation_2023.csv', index=False)
    row = Graduation(2023).clean(grad_dir=str(directory)).iloc[0]
    assert row.totmen == 100 and row.totmen_graduated == 80
    assert row.gradrate_totmen == 80 and row.gradrate_totwomen == 75


def test_cip_dictionary_labels_are_year_specific(tmp_path):
    directory = tmp_path / 'cipdata'
    directory.mkdir()
    with pd.ExcelWriter(directory / 'cip_2023.xlsx') as book:
        pd.DataFrame({'varname': ['CIPCODE', 'CIPCODE', 'AWLEVEL'],
                      'codevalue': ['40.0801', '01.0101', '5'],
                      'valuelabel': ['Physics, General', 'Agricultural Business', 'Bachelor']}).to_excel(
            book, sheet_name='Frequencies', index=False)
    result = Cip(2023).clean(cip_dir=str(directory))
    assert result.loc[result.cip.eq('40.0801'), 'cip_description'].item() == 'Physics, General'
    assert set(result.year) == {2023} and len(result) == 2


@pytest.mark.skipif(os.environ.get('GENPEDS_LIVE_TESTS') != '1',
                    reason='Set GENPEDS_LIVE_TESTS=1 for NCES live tests')
@pytest.mark.parametrize('subject,kwargs,expected', [
    ('characteristics', {'characteristics_dir': 'characteristicsdata'}, 'name'),
    ('admissions', {'admissions_dir': 'admissionsdata'}, 'tot_applied'),
    ('enrollment', {'enrollment_dir': 'enrollmentdata', 'student_level': 'undergrad'}, 'totmen'),
    ('completion', {'completion_dir': 'completiondata', 'level': 'bach'}, 'totmen'),
    ('graduation', {'graduation_dir': 'graduationdata', 'deg_level': 'bach'}, 'gradrate_totmen'),
    ('cip', {'cip_codes_dir': 'cipdata'}, 'cip_description'),
])
def test_one_year_live_cleaner(tmp_path, monkeypatch, subject, kwargs, expected):
    monkeypatch.chdir(tmp_path)
    scrape_ipeds_data(subject, 2023, see_progress=False)
    df = CLEANERS[subject](**kwargs, year_range=2023)
    assert not df.empty
    assert df['year'].eq(2023).all()
    assert expected in df and df[expected].notna().any()
    assert (tmp_path / f'{subject}data').is_dir()
