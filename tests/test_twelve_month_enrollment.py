"""Unduplicated EFFY headcounts across level and race reporting changes."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, TwelveMonthEnrollment, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_file(folder, year, values):
    folder.mkdir(exist_ok=True)
    pd.DataFrame(values).to_csv(folder / f'twelve_month_enrollment_{year}.csv', index=False)


def test_twelve_month_levels_and_legacy_race(tmp_path):
    folder = tmp_path / 'twelve_month_enrollmentdata'
    write_file(folder, 2002, {
        'UNITID': ['100001'] * 4,
        'LSTUDY': ['999', '1', '2', '3'],
        'FYRACE24': ['30', '20', '2', '8'],
        'FYRACE15': ['12', '8', '1', '3'],
        'FYRACE16': ['18', '12', '1', '5'],
        'FYRACE20': ['4', '2', '1', '1'],
        'XFYRAC24': ['G', 'R', 'R', 'R'],
        'XFYRAC20': ['G', 'R', 'R', 'R']
    })
    annual = TwelveMonthEnrollment(2002)
    df = annual.clean(enroll_dir=str(folder), student_level='all')
    assert set(df.columns) == set(annual.get_available_vars())
    assert set(df.student_level) == {'total', 'undergrad', 'first_professional', 'grad'}
    ug = df.loc[df.student_level == 'undergrad'].iloc[0]
    assert ug.total_students == 20 and ug.men == 8 and ug.women == 12
    assert ug.period_start_year == 2001
    assert ug.asian_pacific == 2 and ug.asian_pacific_status == 'R'
    assert pd.isna(ug.asian) and pd.isna(ug.asian_status)
    assert df.loc[df.student_level == 'total', 'total_students'].item() == 30
    assert annual.clean(enroll_dir=str(folder), student_level='first_professional').total_students.item() == 2


def test_twelve_month_expanded_rows_not_added_together(tmp_path):
    folder = tmp_path / 'twelve_month_enrollmentdata'
    write_file(folder, 2025, {
        'UNITID': ['100001'] * 5,
        'EFFYALEV': ['1', '2', '3', '12', '22'],
        'EFYTOTLT': ['30', '20', '14', '10', '16'],
        'EFYTOTLM': ['12', '8', '6', '4', '7'],
        'EFYTOTLW': ['18', '12', '8', '6', '9'],
        'EFYASIAT': ['3', '2', '1', '1', '2'],
        'EFYNHPIT': ['1', '1', '1', '0', '1'],
        'XEYTOTLT': ['G', 'R', 'R', 'R', 'R'],
        'XEFYASIT': ['G', 'R', 'R', 'R', 'R']
    })
    df = TwelveMonthEnrollment(2025).clean(enroll_dir=str(folder), student_level='all')
    assert len(df) == 3
    assert set(df.source_level_code) == {'1', '2', '12'}
    ug = df.loc[df.student_level == 'undergrad'].iloc[0]
    assert ug.level_code_system == 'effyalev'
    assert ug.total_students == 20 and ug.asian == 2
    assert ug.pacific_islander == 1
    assert pd.isna(ug.asian_pacific)
    assert df.loc[df.student_level == 'total', 'total_students'].item() == 30


def test_twelve_month_years_validation_and_merge(tmp_path, monkeypatch):
    assert get_year_iter('twelve_month_enrollment') == list(range(2002, 2026))
    with pytest.raises(ValueError, match='2002-2025'):
        TwelveMonthEnrollment(2001)
    with pytest.raises(ValueError, match='2002-2010'):
        TwelveMonthEnrollment(2025).clean(student_level='first_professional')
    monkeypatch.chdir(tmp_path)
    write_file(tmp_path / 'twelve_month_enrollmentdata', 2025, {
        'unitid': ['100001'], 'effyalev': ['2'], 'efytotlt': ['20'],
        'efytotlm': ['8'], 'efytotlw': ['12']
    })
    monkeypatch.setattr(TwelveMonthEnrollment, 'scrape', lambda self, see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2025], 'name': ['Example College']}))
    df = TwelveMonthEnrollment(2025).run(merge_with_char=True, rm_disk=True)
    assert df.loc[0, 'name'] == 'Example College'
    assert not (tmp_path / 'twelve_month_enrollmentdata').exists()


@pytest.mark.parametrize('year, root', [
    (2002, 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2025, 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_twelve_month_download_and_cache(tmp_path, monkeypatch, year, root):
    monkeypatch.chdir(tmp_path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(f'effy{year}.csv', b'UNITID,EFFYLEV,LSTUDY\n100001,2,1\n')
    urls = []

    class Response:
        content = archive.getvalue()
        text = ''

    def fake_get(url):
        urls.append(url)
        return Response()

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data('twelve_month_enrollment', year, see_progress=False)
    assert urls == [f'{root}EFFY{year}.zip']
    assert (tmp_path / 'twelve_month_enrollmentdata' /
            f'twelve_month_enrollment_{year}.csv').exists()
    scrape_ipeds_data('twelve_month_enrollment', year, see_progress=False)
    assert len(urls) == 1
