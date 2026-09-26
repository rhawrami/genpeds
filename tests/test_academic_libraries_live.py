"""Opt-in NCES Academic Libraries download/clean/Characteristics merge."""

import os

import pytest

from genpeds import AcademicLibraries


@pytest.mark.skipif(os.environ.get('GENPEDS_LIVE_TESTS') != '1',
                    reason='Set GENPEDS_LIVE_TESTS=1 to download live NCES AL and HD files')
def test_al_live_download_clean_and_characteristics_merge(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    libraries = AcademicLibraries(2023)  # final fiscal-year release
    joined = libraries.run(merge_with_char=True)
    raw = libraries.clean()
    assert len(raw) > 1000 and 0 < len(joined) <= len(raw)
    assert not raw.duplicated(['id', 'year']).any()
    assert joined['year'].eq(2023).all()
    assert joined['name'].notna().any()
    assert raw['physical_books'].notna().any()
    assert raw['staff_fte'].notna().any()
    assert raw['expenditure_threshold_code'].isin(['1', '2']).any()
    verified = joined.merge(raw[['id', 'year', 'total_expenditures']],
                            on=['id', 'year'], validate='one_to_one',
                            suffixes=('_merged', '_source'))
    assert len(verified) == len(joined)
    assert verified['total_expenditures_merged'].equals(verified['total_expenditures_source'])
    for subject in ('academic_libraries', 'characteristics'):
        assert (tmp_path / f'{subject}data' / f'{subject}_2023.csv').is_file()
