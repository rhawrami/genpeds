"""12-month instructional hours and reported/estimated FTE across EFIA revisions."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, InstructionalActivity, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_file(directory, year, fields):
    directory.mkdir(exist_ok=True)
    pd.DataFrame(fields).to_csv(directory / f'instructional_activity_{year}.csv', index=False)


def test_early_activity_and_later_fte_remain_distinct(tmp_path):
    directory = tmp_path / 'instructional_activitydata'
    write_file(directory, 2002, {
        'UNITID': [' 100001 '], 'CDACTUA': ['600'], 'CNACTUA': ['900'],
        'CDACTGA': ['120'], 'XCDACTUA': ['R'], 'XCNACTUA': ['R']
    })
    write_file(directory, 2004, {
        'UNITID': ['100001'], 'CDACTUA': ['750'], 'CNACTUA': ['0'],
        'CDACTGA': ['150'], 'EFTEUG': ['30'], 'EFTEGD': ['6'],
        'FTEUG': ['33'], 'FTEGD': ['7'], 'ACTTYPE': ['1'],
        'XEFTEUG': ['G'], 'XFTEUG': ['R'], 'XCNACTUA': ['Z']
    })
    obj = InstructionalActivity()
    data = obj.clean(activity_dir=str(directory))
    assert set(data.columns) == set(obj.get_available_vars())
    assert data['year'].tolist() == [2002, 2004]
    assert data['period_start_year'].tolist() == [2001, 2003]
    early, later = data.iloc[0], data.iloc[1]
    assert early.id == '100001' and early.ug_contact_clock_hours == 900
    assert early.ug_credit_hours == 600 and early.grad_credit_hours == 120
    assert pd.isna(early.ug_estimated_fte) and pd.isna(early.ug_estimated_fte_status)
    assert pd.isna(early.activity_type_code) and pd.isna(early.activity_type)
    assert later.hour_term == 'contact' and later.activity_type == 'Contact hours'
    assert later.ug_estimated_fte == 30 and later.ug_reported_fte == 33
    assert later.ug_estimated_fte_status == 'G' and later.ug_reported_fte_status == 'R'
    assert later.ug_contact_clock_hours == 0 and later.ug_contact_clock_hours_status == 'Z'
    assert pd.isna(later.professional_practice_reported_fte)


def test_clock_terminology_professional_fte_and_year_validation(tmp_path):
    directory = tmp_path / 'instructional_activitydata'
    write_file(directory, 2012, {
        'unitid': ['100001'], 'cdactua': ['800'], 'cnactua': ['1200'],
        'cdactga': ['200'], 'ftedpp': ['5'], 'xftedpp': ['R'], 'acttype': ['3']
    })
    write_file(directory, 2019, {
        'UNITID': ['100001'], 'CDACTUA': ['900'], 'CNACTUA': ['1400'],
        'CDACTGA': ['250'], 'ACTTYPE': ['3']
    })
    old = InstructionalActivity(2012).clean(activity_dir=str(directory)).iloc[0]
    new = InstructionalActivity(2019).clean(activity_dir=str(directory)).iloc[0]
    assert old.professional_practice_reported_fte == 5
    assert old.professional_practice_reported_fte_status == 'R'
    assert old.activity_type == 'Both contact and credit hours'
    assert new.hour_term == 'clock'
    assert new.activity_type == 'Both clock and credit hours'
    assert new.ug_contact_clock_hours == 1400
    assert get_year_iter('instructional_activity') == list(range(2002, 2026))
    with pytest.raises(ValueError, match='2002-2025'):
        InstructionalActivity(2026)
    with pytest.raises(FileNotFoundError, match='2013'):
        InstructionalActivity((2012, 2013)).clean(activity_dir=str(directory))


def test_run_2025_joins_characteristics_and_removes_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'instructional_activitydata'
    write_file(directory, 2025, {
        'UNITID': ['100001'], 'CDACTUA': ['1000'],
        'CNACTUA': ['100'], 'CDACTGA': ['50'], 'ACTTYPE': ['2']
    })
    monkeypatch.setattr(InstructionalActivity, 'scrape',
                        lambda self, see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run',
                        lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2025],
                                      'name': ['Example University']}))
    result = InstructionalActivity(2025).run(merge_with_char=True, rm_disk=True)
    assert result.loc[0, 'name'] == 'Example University'
    assert result.loc[0, 'hour_term'] == 'clock'
    assert result.loc[0, 'activity_type'] == 'Credit hours'
    assert not directory.exists()


@pytest.mark.parametrize('year, root', [
    (2002, 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2025, 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_instructional_activity_download_endpoint_and_cache(tmp_path, monkeypatch, year, root):
    monkeypatch.chdir(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zipped:
        zipped.writestr(f'efia{year}.csv',
                        b'UNITID,CDACTUA,CNACTUA,CDACTGA\n100001,10,20,30\n')
    urls = []

    class Response:
        status_code = 200
        headers = {}
        content = buffer.getvalue()

        def iter_content(self, chunk_size):
            yield self.content

        def close(self):
            pass

    def fake_get(url, **kwargs):
        urls.append(url)
        return Response()

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data('instructional_activity', year, see_progress=False)
    assert urls == [f'{root}EFIA{year}.zip']
    assert (tmp_path / 'instructional_activitydata' /
            f'instructional_activity_{year}.csv').exists()
    scrape_ipeds_data('instructional_activity', year, see_progress=False)
    assert len(urls) == 1
