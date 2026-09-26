"""Offline tests for the first-year retention API and year-specific schemas."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, Retention, scrape_ipeds_data
from genpeds.cleaners import clean_retention
from genpeds.downloader import get_year_iter


def write_file(directory, year, fields):
    directory.mkdir(exist_ok=True)
    pd.DataFrame(fields).to_csv(directory / f'retention_{year}.csv', index=False)


def test_retention_cleaner_harmonizes_old_and_new_fields(tmp_path):
    data = tmp_path / 'retentiondata'
    write_file(data, 2004, {
        'UNITID': [' 100001 '], 'RET_PCF': ['71'], 'RET_PCP ': ['0'],
        'XRET_PCF': ['R'], 'XRET_PCP': ['Z']
    })
    write_file(data, 2007, {
        'unitid': ['100001'], 'ret_pcf': ['78'], 'ret_pcp': ['52'],
        'rrftct': ['100'], 'rrftex': ['4'], 'rrftcta': ['96'], 'ret_nmf': ['75'],
        'rrptct': ['20'], 'rrptex': ['0'], 'rrptcta': ['20'], 'ret_nmp': ['10'],
        'xrrftct': ['R'], 'xret_pcf': ['R'], 'xret_pcp': ['R']
    })
    write_file(data, 2016, {
        'UNITID': ['100002'], 'RET_PCF': ['80.2'], 'RET_PCP': ['40'],
        'RRFTCT': ['100'], 'RRFTEX': ['3'], 'RRFTIN': ['2'],
        'RRFTCTA': ['99'], 'RET_NMF': ['79'], 'XRRFTIN': ['R'],
        'RRPTCT': ['10'], 'RRPTEX': ['0'], 'RRPTIN': ['1'],
        'RRPTCTA': ['11'], 'RET_NMP': ['4'], 'XRET_PCF': ['R']
    })

    retention = Retention()
    result = retention.clean(retention_dir=str(data))
    assert list(result['year']) == [2004, 2007, 2016]
    assert list(result['cohort_year']) == [2003, 2006, 2015]
    assert list(result['id']) == ['100001', '100001', '100002']
    assert set(result.columns) == set(retention.get_available_vars())
    early, middle, recent = (result.iloc[i] for i in range(3))
    assert early.ft_retention_rate == 71
    assert early.pt_retention_rate == 0
    assert early.pt_retention_rate_status == 'Z'
    assert pd.isna(early.ft_cohort) and pd.isna(early.ft_cohort_status)
    assert middle.ft_adjusted_cohort == 96
    assert middle.ft_retained == 75
    assert pd.isna(middle.ft_inclusions) and pd.isna(middle.ft_inclusions_status)
    assert recent.ft_inclusions == 2
    assert recent.ft_adjusted_cohort == 99
    assert recent.ft_inclusions_status == 'R'
    assert recent.pt_adjusted_cohort == 11

    selected = Retention([2016, 2004]).clean(retention_dir=str(data))
    assert selected['year'].tolist() == [2004, 2016]
    assert pd.isna(selected.iloc[0].pt_cohort_status)


def test_retention_invalid_year_and_incomplete_cache(tmp_path):
    assert get_year_iter('retention') == list(range(2003, 2025))
    assert get_year_iter('retention', (2003, 2004)) == [2003, 2004]
    assert get_year_iter('retention', [2024, 2003]) == [2024, 2003]
    assert get_year_iter('retention', 2024) == [2024]
    with pytest.raises(ValueError, match='2003-2024'):
        Retention(2002)
    with pytest.raises(ValueError, match='2003-2024'):
        Retention([2024, 2025])
    data = tmp_path / 'retentiondata'
    write_file(data, 2004, {'unitid': ['123456'], 'ret_pcf': ['75'], 'ret_pcp': ['']})
    with pytest.raises(FileNotFoundError, match='2005'):
        Retention((2004, 2005)).clean(retention_dir=str(data))
    with pytest.raises(ValueError, match='ret_pcp'):
        write_file(data, 2005, {'unitid': ['123456'], 'ret_pcf': ['75']})
        clean_retention(str(data), 2005)


def test_retention_run_joins_characteristics_and_removes_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_file(tmp_path / 'retentiondata', 2024, {
        'unitid': ['100001'], 'ret_pcf': ['80'], 'ret_pcp': ['60'],
        'xret_pcf': ['R'], 'xret_pcp': ['R']
    })
    calls = []
    monkeypatch.setattr(Retention, 'scrape', lambda self, see_progress=False:
                        calls.append(('retention', see_progress)))

    def characteristics_run(self, see_progress=False, rm_disk=False):
        calls.append(('characteristics', see_progress, rm_disk))
        return pd.DataFrame({'id': ['100001'], 'year': [2024], 'name': ['Example College']})

    monkeypatch.setattr(Characteristics, 'run', characteristics_run)
    result = Retention(2024).run(see_progress=True, merge_with_char=True, rm_disk=True)
    assert result.loc[0, 'name'] == 'Example College'
    assert result.loc[0, 'ft_retention_rate'] == 80
    assert calls == [('retention', True), ('characteristics', True, True)]
    assert not (tmp_path / 'retentiondata').exists()


@pytest.mark.parametrize('year, root', [
    (2003, 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_retention_scrape_downloads_ef_d_and_uses_cache(tmp_path, monkeypatch, year, root):
    monkeypatch.chdir(tmp_path)
    csv_content = b'UNITID,RET_PCF,RET_PCP\n100001,80,40\n'
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(f'ef{year}d.csv', csv_content)
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
    scrape_ipeds_data('retention', year, see_progress=False)
    assert urls == [f'{root}EF{year}D.zip']
    assert (tmp_path / 'retentiondata' / f'retention_{year}.csv').read_bytes() == csv_content
    scrape_ipeds_data('retention', year, see_progress=False)
    assert len(urls) == 1
