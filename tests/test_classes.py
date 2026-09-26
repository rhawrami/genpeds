"""Public subject contracts and optional one-year NCES integration checks.

Each live case uses its own temporary working directory. It does not depend
on any other test having downloaded a file or on files in the repository.
"""

import os

import pytest

from genpeds import Admissions, Characteristics, Completion, Enrollment, Graduation


SUBJECTS = [
    ('characteristics', Characteristics, (1984, 2025)),
    ('admissions', Admissions, (2001, 2024)),
    ('enrollment', Enrollment, (1984, 2024)),
    ('completion', Completion, (1984, 2025)),
    ('graduation', Graduation, (2000, 2024)),
]
LIVE = pytest.mark.skipif(os.environ.get('GENPEDS_LIVE_TESTS') != '1',
                          reason='Set GENPEDS_LIVE_TESTS=1 for NCES live tests')


@pytest.mark.parametrize('subject,cls,years', SUBJECTS)
def test_subject_metadata(subject, cls, years):
    api = cls(2023)
    assert api.get_available_years() == years
    assert subject in api.get_description().lower()
    assert 'id' in api.get_available_vars() and 'year' in api.get_available_vars()
    assert api.lookup_var('id') == api.get_available_vars()['id']


@LIVE
@pytest.mark.parametrize('subject,cls,years', SUBJECTS)
def test_one_year_live_run_and_characteristics_join(tmp_path, monkeypatch, subject, cls, years):
    monkeypatch.chdir(tmp_path)
    api = cls(2023)
    if cls is Characteristics:
        result = api.run()
    elif cls is Completion:
        result = api.run(merge_with_char=True, get_cip_codes=False)
    else:
        result = api.run(merge_with_char=True)
    assert not result.empty and result['year'].eq(2023).all()
    assert result['id'].notna().all()
    assert (tmp_path / f'{subject}data' / f'{subject}_2023.csv').is_file()
    assert 'name' in result
    if cls is not Characteristics:
        assert (tmp_path / 'characteristicsdata' / 'characteristics_2023.csv').is_file()
