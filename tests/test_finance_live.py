"""Opt-in NCES integration check: real Finance ZIPs and a Characteristics join.

Run with GENPEDS_LIVE_TESTS=1 pytest tests/test_finance_live.py -q.
The ordinary test suite skips this network-dependent download.
"""

import os

import pytest

from genpeds import Finance


@pytest.mark.skipif(os.environ.get('GENPEDS_LIVE_TESTS') != '1',
                    reason='Set GENPEDS_LIVE_TESTS=1 to download live NCES Finance and HD files')
def test_finance_live_download_clean_and_characteristics_merge(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # isolate all four caches; pytest cleans them up
    finance = Finance(2023)  # a final-release fiscal year, not a moving provisional ZIP
    merged = finance.run(form='all', merge_with_char=True)
    cleaned = finance.clean(form='all')  # reuse the ZIP-derived CSV cache

    assert set(cleaned['form']) == set(merged['form']) == {'f1a', 'f2', 'f3'}
    assert cleaned['source_stem'].unique().tolist() == [
        'F2223_F1A', 'F2223_F2', 'F2223_F3']
    assert not cleaned.duplicated(['id', 'year', 'form']).any()
    assert not merged.duplicated(['id', 'year', 'form']).any()
    assert merged['year'].eq(2023).all() and merged['name'].notna().all()
    assert cleaned['net_tuition_fees'].notna().any()
    assert merged['net_tuition_fees'].notna().any()
    assert len(merged) <= len(cleaned)
    joined = merged.merge(cleaned[['id', 'year', 'form', 'net_tuition_fees']],
                          on=['id', 'year', 'form'], validate='one_to_one',
                          suffixes=('_merged', '_source'))
    assert len(joined) == len(merged)
    assert joined['net_tuition_fees_merged'].equals(joined['net_tuition_fees_source'])
    for subject in ('finance', 'finance_f2', 'finance_f3', 'characteristics'):
        assert (tmp_path / f'{subject}data' / f'{subject}_2023.csv').is_file()
