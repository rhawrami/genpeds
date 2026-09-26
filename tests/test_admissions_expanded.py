"""Admissions counts and year-specific policy labels remain distinct."""

import pandas as pd
import pytest

from genpeds import Admissions


def write_file(directory, year, rows):
    directory.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(directory / f'admissions_{year}.csv', index=False)


def test_admissions_2001_keeps_women_and_builds_only_missing_totals(tmp_path):
    directory = tmp_path / 'admissionsdata'
    write_file(directory, 2001, {
        'UNITID': ['100001'],
        'APPLCNM': ['100'], 'APPLCNW': ['200'],
        'ADMSSNM': ['50'], 'ADMSSNW': ['100'],
        'ENRLFTM': ['20'], 'ENRLPTM': ['5'],
        'ENRLFTW': ['30'], 'ENRLPTW': ['10'],
        'SATNUM': ['45'], 'ACTNUM': ['12'],
        'ADMCON1': ['1'], 'ADMCON7': ['2']
    })
    row = Admissions(2001).clean(admit_dir=str(directory)).iloc[0]
    assert row.women_applied == 200 and row.women_admitted == 100
    assert row.women_enrolled == 40 and row.men_enrolled == 25
    assert row.tot_applied == 300 and row.tot_admitted == 150
    assert row.tot_ft_enrolled == 50 and row.tot_pt_enrolled == 15
    assert row.tot_enrolled == 65
    assert row.accept_rate_total == 50
    assert row.yield_rate_women == 40
    assert row.num_submit_sat == 45
    assert row.consider_gpa_code == '1' and row.consider_gpa == 'Required'
    assert row.consider_test_scores == 'Recommended'
    assert pd.isna(row.sat_math_50) and pd.isna(row.consider_legacy)


def test_admissions_2024_uses_published_totals_and_preserves_supplements(tmp_path):
    directory = tmp_path / 'admissionsdata'
    write_file(directory, 2024, {
        'UNITID': ['100001', '100002'],
        'APPLCNM': ['100', '0'], 'APPLCNW': ['100', '0'],
        'APPLCNAN': ['3', None], 'APPLCNUN': ['2', None],
        'ADMSSNM': ['50', '0'], 'ADMSSNW': ['40', '0'],
        'ADMSSNAN': ['1', None], 'ADMSSNUN': ['1', None],
        'ENRLM': ['30', '0'], 'ENRLW': ['20', '0'],
        'APPLCN': ['205', '0'], 'ADMSSN': ['92', '0'], 'ENRLT': ['52', '0'],
        'ENRLFT': ['43', '0'], 'ENRLPT': ['9', '0'],
        'SATNUM': ['85', '0'], 'SATMT50': ['610', None],
        'ADMCON1': ['3', None], 'ADMCON7': ['5', None], 'ADMCON12': ['5', None]
    })
    df = Admissions(2024).clean(admit_dir=str(directory))
    assert set(df.columns) == set(Admissions().get_available_vars())
    row = df.iloc[0]
    assert row.tot_applied == 205  # published total; do not reconstruct from binary counts
    assert row.tot_admitted == 92 and row.tot_enrolled == 52
    assert row.another_gender_applied == 3 and row.gender_unknown_applied == 2
    assert row.accept_rate_total == pytest.approx(92 / 205 * 100)
    assert row.yield_rate_total == pytest.approx(52 / 92 * 100)
    assert row.sat_math_50 == 610
    assert row.consider_test_scores_code == '5'
    assert row.consider_test_scores == 'Test optional (considered if submitted)'
    assert row.consider_gpa == 'Not considered even if submitted'
    assert row.consider_legacy == 'Considered if submitted'
    assert pd.isna(df.loc[1, 'accept_rate_total'])
    assert pd.isna(df.loc[1, 'yield_rate_total'])


def test_admissions_policy_code_meaning_changes_and_cache_is_complete(tmp_path):
    directory = tmp_path / 'admissionsdata'
    shared = {'UNITID': ['100001'], 'APPLCNM': ['1'], 'APPLCNW': ['1'],
              'ADMSSNM': ['1'], 'ADMSSNW': ['1']}
    write_file(directory, 2016, {**shared, 'ADMCON7': ['5']})
    assert (Admissions(2016).clean(admit_dir=str(directory))
            .loc[0, 'consider_test_scores'] == 'Considered but not required')
    with pytest.raises(FileNotFoundError, match='2017'):
        Admissions((2016, 2017)).clean(admit_dir=str(directory))
