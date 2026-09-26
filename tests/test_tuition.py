"""Offline checks for academic, program, and combined Cost I tuition files."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, Tuition, scrape_ipeds_data
from genpeds.cleaners import clean_tuition
from genpeds.downloader import get_year_iter


def write_csv(path, values):
    path.parent.mkdir(exist_ok=True)
    pd.DataFrame(values).to_csv(path, index=False)


def test_tuition_legacy_and_combined_cost_files(tmp_path):
    academic = tmp_path / 'tuitiondata'
    program = tmp_path / 'tuition_programdata'
    write_csv(academic / 'tuition_2000.csv', {
        'UNITID': [' 100001 '], 'TUITION1': ['2000'], 'FEE1': ['300'],
        'CHG1AY3': ['2400'], 'XTUIT1': ['R'], 'XCHG1AY3': ['R']
    })
    write_csv(program / 'tuition_program_2000.csv', {
        'UNITID': ['100002'], 'CHG1PY3': ['5000'], 'CIPCODE1': ['52.0101'],
        'XCHG1PY3': ['R']
    })
    cost = {
        'UNITID': ['100001', '100002', '100003'],
        'CIPCODE1': ['-2', '52.0101', '51.0801'],
        'TUITION1': ['4000', None, None], 'FEE1': ['500', None, None],
        'CHG1AY3': ['4600', None, None], 'CHG1PY3': [None, '9000', None],
        'CIPTUIT1': [None, None, '6000'], 'XCHG1PY3': [None, 'R', 'A'],
        'XCIPTUI1': [None, 'A', 'R']
    }
    write_csv(academic / 'tuition_2024.csv', cost)
    write_csv(program / 'tuition_program_2024.csv', cost)

    result = Tuition().clean(tuition_dir=str(academic), program_dir=str(program))
    assert len(result) == 5
    assert set(result.columns) == set(Tuition().get_available_vars())
    assert not result.duplicated(['id', 'year']).any()
    ay = result.set_index(['id', 'year']).loc[('100001', 2000)]
    assert ay.reporter == 'academic'
    assert ay.in_district_tuition == 2000
    assert ay.in_district_published_tuition_fees == 2400  # not recomputed as 2300
    assert pd.isna(ay.program_published_tuition_fees)
    py = result.set_index(['id', 'year']).loc[('100003', 2024)]
    assert py.reporter == 'program'
    assert py.largest_program_cip == '51.0801'
    assert pd.isna(py.program_published_tuition_fees)
    assert py.largest_program_tuition_fees_no_ftft == 6000
    assert py.largest_program_tuition_fees_no_ftft_status == 'R'

    selected = Tuition([2024, 2000]).clean(
        reporter='program', program_dir=str(program))
    assert set(selected.reporter) == {'program'}
    assert len(selected) == 3


def test_tuition_validates_reporter_year_and_cache(tmp_path):
    assert get_year_iter('tuition') == list(range(2000, 2025))
    assert get_year_iter('tuition_program', 2024) == [2024]
    with pytest.raises(ValueError, match='2000-2024'):
        Tuition(1999)
    with pytest.raises(ValueError, match='reporter'):
        Tuition(2024).scrape(reporter='unknown')
    academic = tmp_path / 'tuitiondata'
    write_csv(academic / 'tuition_2024.csv', {
        'UNITID': ['123456'], 'CIPCODE1': ['-2'], 'CHG1AY3': ['10000']
    })
    with pytest.raises(FileNotFoundError, match='2023'):
        clean_tuition(tuition_dir=str(academic), reporter='academic',
                      year_range=(2023, 2024))


def test_tuition_filters_early_universe_wide_reporter_files(tmp_path):
    academic = tmp_path / 'tuitiondata'
    program = tmp_path / 'tuition_programdata'
    write_csv(academic / 'tuition_2001.csv', {
        'UNITID': ['100001', '100002'], 'TUITION1': ['3000', None],
        'CHG1AY3': ['3200', None]
    })
    write_csv(program / 'tuition_program_2001.csv', {
        'UNITID': ['100001', '100002'], 'CIPCODE1': ['-2', '12.0401'],
        'CHG1PY3': [None, '5000']
    })
    result = Tuition(2001).clean(tuition_dir=str(academic), program_dir=str(program))
    assert result[['id', 'reporter']].values.tolist() == [
        ['100001', 'academic'], ['100002', 'program']
    ]


def test_tuition_run_merges_characteristics_and_removes_selected_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_csv(tmp_path / 'tuitiondata' / 'tuition_2024.csv', {
        'UNITID': ['100001'], 'CIPCODE1': ['-2'], 'CHG1AY3': ['10000']
    })
    calls = []
    monkeypatch.setattr(Tuition, 'scrape', lambda self, reporter='both', see_progress=False:
                        calls.append((reporter, see_progress)))

    def characteristics_run(self, see_progress=False, rm_disk=False):
        calls.append(('characteristics', see_progress, rm_disk))
        return pd.DataFrame({'id': ['100001'], 'year': [2024], 'name': ['Example College']})

    monkeypatch.setattr(Characteristics, 'run', characteristics_run)
    df = Tuition(2024).run(reporter='academic', see_progress=True,
                           merge_with_char=True, rm_disk=True)
    assert df.loc[0, 'name'] == 'Example College'
    assert calls == [('academic', True), ('characteristics', True, True)]
    assert not (tmp_path / 'tuitiondata').exists()


@pytest.mark.parametrize('year, subject, stem, root', [
    (2000, 'tuition', 'IC2000_AY', 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2000, 'tuition_program', 'IC2000_PY', 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'tuition', 'COST1_2024', 'https://nces.ed.gov/ipeds/complete-data-files/'),
    (2024, 'tuition_program', 'COST1_2024', 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_tuition_download_endpoints_and_cache(tmp_path, monkeypatch, year, subject, stem, root):
    monkeypatch.chdir(tmp_path)
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, 'w') as archive:
        archive.writestr(stem.lower() + '.csv', b'UNITID,CHG1AY3\n100001,5000\n')
    urls = []

    class Response:
        content = zip_bytes.getvalue()
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
    scrape_ipeds_data(subject, year, see_progress=False)
    assert urls == [root + stem + '.zip']
    assert (tmp_path / f'{subject}data' / f'{subject}_{year}.csv').exists()
    scrape_ipeds_data(subject, year, see_progress=False)
    assert len(urls) == 1
