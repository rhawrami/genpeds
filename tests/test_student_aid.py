"""Offline checks for SFA aid-year, cohort, and reporter harmonization."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, StudentAid, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_aid(path, records):
    path.parent.mkdir(exist_ok=True)
    pd.DataFrame(records).to_csv(path, index=False)


def test_aid_cohorts_early_and_recent(tmp_path):
    directory = tmp_path / 'student_aiddata'
    write_aid(directory / 'student_aid_2002.csv', {
        'UNITID': ['100001', '100002'],
        'SCFA1N': ['100', None], 'SCFA2': ['900', None],
        'SCFY1N': [None, '20'], 'SCFY2': [None, '200'],
        'XSCFA1N': ['R', 'A'], 'XSCFY1N': ['A', 'R'],
        'ANYAIDN': ['75', '10'], 'ANYAIDP': ['75', '50'],
        'FGRNT_N': ['50', '6'], 'FGRNT_A': ['1800', '2000'],
        'LOAN_N': ['20', '3'], 'LOAN_A': ['4000', '3000'],
        'XANYAIDN': ['R', 'R'], 'XFGRNT_N': ['R', 'R']
    })
    write_aid(directory / 'student_aid_2024.csv', {
        'UNITID': ['100001'],
        'SCFA1N': ['150'], 'SCFA2': ['1200'],
        'SCFY1N': [None], 'SCFY2': [None],
        'SCUGFFN': ['150'], 'SCUGRAD': ['1200'], 'XSCUGFFN': ['R'],
        'ANYAIDN': ['90'], 'ANYAIDP': ['60'], 'AGRNT_N': ['75'],
        'PGRNT_N': ['30'], 'UAGRNTN': ['500'], 'UPGRNTN': ['220'],
        'UFLOANN': ['200'], 'XUPGRNTN': ['R']
    })
    write_aid(tmp_path / 'student_aid_net_pricedata' / 'student_aid_net_price_2024.csv', {
        'UNITID': ['100001'], 'NPIST2': ['10080'], 'XNPIST2': ['R']
    })

    aid = StudentAid()
    df = aid.clean(aid_dir=str(directory), net_price_dir=str(tmp_path / 'student_aid_net_pricedata'))
    assert set(df.columns) == set(aid.get_available_vars())
    assert df[['id', 'year']].values.tolist() == [
        ['100001', 2002], ['100002', 2002], ['100001', 2024]
    ]
    academic, program, recent = (df.iloc[i] for i in range(3))
    assert (academic.reporter, academic.ftft_students, academic.ug_students) == ('academic', 100, 900)
    assert academic.ftft_students_status == 'R'
    assert (program.reporter, program.ftft_students, program.ug_students) == ('program', 20, 200)
    assert program.ftft_any_aid_pct == 50  # reported, not recalculated
    assert pd.isna(program.ug_grant_count) and pd.isna(program.ug_grant_count_status)
    assert pd.isna(academic.ftft_net_price)
    assert recent.aid_year_start == 2023
    assert recent.ftft_net_price == 10080 and recent.ftft_net_price_status == 'R'
    assert recent.ug_grant_count == 500 and recent.ug_pell_count == 220
    assert recent.ug_pell_count_status == 'R'
    assert recent.ftft_pell_count == 30
    assert len(StudentAid(2002).clean(reporter='program', aid_dir=str(directory))) == 1


def test_aid_years_reporter_validation_and_missing_download(tmp_path):
    assert get_year_iter('student_aid') == list(range(2002, 2025))
    assert get_year_iter('student_aid', [2002, 2024]) == [2002, 2024]
    with pytest.raises(ValueError, match='2002-2024'):
        StudentAid(2025)
    with pytest.raises(ValueError, match='reporter'):
        StudentAid(2024).run(reporter='unknown')
    directory = tmp_path / 'student_aiddata'
    write_aid(directory / 'student_aid_2024.csv', {
        'unitid': ['100001'], 'scfa1n': ['100'], 'scfa2': ['1000'],
        'scfy1n': [None], 'scfy2': [None], 'anyaidn': ['80']
    })
    supplement = tmp_path / 'student_aid_net_pricedata'
    with pytest.raises(FileNotFoundError, match='student_aid_net_price_2024'):
        StudentAid(2024).clean(aid_dir=str(directory), net_price_dir=str(supplement))
    write_aid(supplement / 'student_aid_net_price_2024.csv', {
        'unitid': ['100001'], 'npist2': ['9000'], 'xnpist2': ['R']
    })
    with pytest.raises(FileNotFoundError, match='2023'):
        StudentAid((2023, 2024)).clean(aid_dir=str(directory), net_price_dir=str(supplement))


def test_aid_cost_ii_join_keeps_institutions_without_net_price(tmp_path):
    directory = tmp_path / 'student_aiddata'
    supplement = tmp_path / 'student_aid_net_pricedata'
    write_aid(directory / 'student_aid_2024.csv', {
        'unitid': ['100001', '100002'], 'scfa1n': ['100', None],
        'scfa2': ['1000', None], 'scfy1n': [None, '20'],
        'scfy2': [None, '300'], 'anyaidn': ['80', '10']
    })
    write_aid(supplement / 'student_aid_net_price_2024.csv', {
        'unitid': ['100001'], 'npist2': ['9000'], 'xnpist2': ['R']
    })
    result = StudentAid(2024).clean(aid_dir=str(directory), net_price_dir=str(supplement))
    assert result['id'].tolist() == ['100001', '100002']
    assert pd.isna(result.loc[1, 'ftft_net_price'])
    assert pd.isna(result.loc[1, 'ftft_net_price_status'])


def test_aid_run_merges_characteristics_and_removes_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_aid(tmp_path / 'student_aiddata' / 'student_aid_2024.csv', {
        'unitid': ['100001'], 'scfa1n': ['100'], 'scfa2': ['1000'],
        'scfy1n': [None], 'scfy2': [None], 'anyaidn': ['80']
    })
    write_aid(tmp_path / 'student_aid_net_pricedata' / 'student_aid_net_price_2024.csv', {
        'unitid': ['100001'], 'npist2': ['9000'], 'xnpist2': ['R']
    })
    calls = []
    monkeypatch.setattr(StudentAid, 'scrape', lambda self, see_progress=False:
                        calls.append(('aid', see_progress)))

    def char_run(self, see_progress=False, rm_disk=False):
        calls.append(('characteristics', see_progress, rm_disk))
        return pd.DataFrame({'id': ['100001'], 'year': [2024], 'name': ['Example College']})

    monkeypatch.setattr(Characteristics, 'run', char_run)
    result = StudentAid(2024).run(see_progress=True, merge_with_char=True, rm_disk=True)
    assert result.loc[0, 'name'] == 'Example College'
    assert result.loc[0, 'ftft_any_aid_count'] == 80
    assert result.loc[0, 'ftft_net_price'] == 9000
    assert calls == [('aid', True), ('characteristics', True, True)]
    assert not (tmp_path / 'student_aiddata').exists()
    assert not (tmp_path / 'student_aid_net_pricedata').exists()


def test_aid_2024_scrape_includes_cost_ii(monkeypatch):
    calls = []
    monkeypatch.setattr('genpeds.core.scrape_ipeds_data',
                        lambda subject, year_range, see_progress=False:
                        calls.append((subject, year_range)))
    StudentAid(2023).scrape()
    assert calls == [('student_aid', 2023)]
    calls.clear()
    StudentAid([2002, 2024]).scrape()
    assert calls == [('student_aid', [2002, 2024]), ('student_aid_net_price', 2024)]


@pytest.mark.parametrize('year, root', [
    (2002, 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_aid_download_endpoint_and_cache(tmp_path, monkeypatch, year, root):
    monkeypatch.chdir(tmp_path)
    zip_bytes = io.BytesIO()
    name = f'SFA{(year - 1) % 100:02d}{year % 100:02d}'
    with zipfile.ZipFile(zip_bytes, 'w') as archive:
        archive.writestr(f'{name}.csv', b'UNITID,SCFA1N,SCFA2,SCFY1N,SCFY2,ANYAIDN\n100001,1,10,,,1\n')
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
    scrape_ipeds_data('student_aid', year, see_progress=False)
    assert urls == [root + name + '.zip']
    assert (tmp_path / 'student_aiddata' / f'student_aid_{year}.csv').exists()
    scrape_ipeds_data('student_aid', year, see_progress=False)
    assert len(urls) == 1
