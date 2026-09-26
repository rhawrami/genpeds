"""GR200 cohorts and published 100/150/200% measures stay distinct from GR."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, Graduation200, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_file(folder, year, values):
    folder.mkdir(exist_ok=True)
    pd.DataFrame(values).to_csv(folder / f'graduation200_{year}.csv', index=False)


def test_gr200_cohort_types_and_early_missing_fields(tmp_path):
    folder = tmp_path / 'graduation200data'
    write_file(folder, 2008, {
        'UNITID': ['100001', '100002'],
        'BAREVCT': ['100', None], 'L4REVCT': [None, '40'],
        'BAAC150': ['95', None], 'L4AC150': [None, '38'],
        'BAAC200': ['94', None], 'L4AC200': [None, '37'],
        'BANC100': ['60', None], 'L4NC100': [None, '10'],
        'BAGR100': ['63', None], 'L4GR100': [None, '26'],
        'BANC150': ['75', None], 'L4NC150': [None, '20'],
        'BAGR150': ['79', None], 'L4GR150': [None, '53'],
        'BANC200A': ['5', None], 'L4NC200A': [None, '4'],
        'XBANC20A': ['R', None], 'XL4NC20A': [None, 'R'],
        'BANC200': ['80', None], 'L4NC200': [None, '24'],
        'BAGR200': ['85', None], 'L4GR200': [None, '65']
    })
    gr = Graduation200(2008)
    result = gr.clean(graduation_dir=str(folder))
    assert set(result.columns) == set(gr.get_available_vars())
    assert result['cohort_type'].tolist() == ['bachelor', 'less_than_four_year']
    bachelor, short = result.iloc[0], result.iloc[1]
    assert (bachelor.year, bachelor.cohort_year, bachelor.collection_phase) == (2008, 2000, 'supplemental')
    assert (short.year, short.cohort_year) == (2008, 2004)
    assert bachelor.completed_150_to_200 == 5
    assert bachelor.completed_150_to_200_status == 'R'
    assert short.completed_150_to_200_status == 'R'
    assert short.adjusted_cohort_150 == 38 and short.adjusted_cohort_200 == 37
    assert pd.isna(bachelor.still_enrolled) and pd.isna(bachelor.still_enrolled_status)
    assert gr.clean(graduation_dir=str(folder), cohort_type='bachelor')['id'].tolist() == ['100001']


def test_gr200_2011_still_enrolled_and_published_rate(tmp_path):
    folder = tmp_path / 'graduation200data'
    write_file(folder, 2011, {
        'UNITID': ['100001'], 'BAREVCT': ['100'], 'L4REVCT': [None],
        'BASTEND': ['5'], 'XBASTEND': ['R'],
        'BAGR100': ['196'], 'XBAGR100': ['R'], 'BAGR200': ['80'],
        'L4GR200': [None]
    })
    row = Graduation200(2011).clean(graduation_dir=str(folder), cohort_type='bachelor').iloc[0]
    assert row.still_enrolled == 5 and row.still_enrolled_status == 'R'
    assert row.rate_100 == 196  # retain a reported value, rather than silently clamp it
    assert row.rate_100_status == 'R'
    assert row.cohort_year == 2003


def test_gr200_year_validation_and_merge(tmp_path, monkeypatch):
    assert get_year_iter('graduation200') == list(range(2008, 2025))
    with pytest.raises(ValueError, match='2008-2024'):
        Graduation200(2007)
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / 'graduation200data'
    write_file(folder, 2024, {
        'unitid': ['100001'], 'barevct': ['100'], 'l4revct': [None],
        'baac200': ['90'], 'bagr200': ['80'], 'bastend': ['2'],
        'l4gr200': [None]
    })
    monkeypatch.setattr(Graduation200, 'scrape', lambda self, see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2024], 'name': ['Example College']}))
    result = Graduation200(2024).run(cohort_type='bachelor',
                                     merge_with_char=True, rm_disk=True)
    assert result.loc[0, 'name'] == 'Example College'
    assert result.loc[0, 'cohort_year'] == 2016
    assert not folder.exists()


@pytest.mark.parametrize('year, stem, root', [
    (2008, 'GR200_08', 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'GR200_24', 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_gr200_download_and_cache(tmp_path, monkeypatch, year, stem, root):
    monkeypatch.chdir(tmp_path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(stem.lower() + '.csv', b'UNITID,BAREVCT,L4REVCT\n100001,100,\n')
    urls = []

    class Response:
        content = archive.getvalue()
        status_code = 200
        headers = {}

        def iter_content(self, chunk_size):
            yield self.content

        def close(self):
            pass

    def fake_get(url, **kwargs):
        urls.append(url)
        return Response()

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data('graduation200', year, see_progress=False)
    assert urls == [f'{root}{stem}.zip']
    assert (tmp_path / 'graduation200data' / f'graduation200_{year}.csv').exists()
    scrape_ipeds_data('graduation200', year, see_progress=False)
    assert len(urls) == 1
