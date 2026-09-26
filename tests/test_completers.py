"""Completers count people, independently of awards and first/second majors."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, Completers, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_file(folder, prefix, year, rows):
    folder.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(folder / f'{prefix}_{year}.csv', index=False)


def test_completers_all_people_and_age_by_award_are_distinct(tmp_path):
    overall = tmp_path / 'completersdata'
    awards = tmp_path / 'completers_by_awarddata'
    write_file(overall, 'completers', 2012, {
        'UNITID': ['100001'], 'CSTOTLT': ['8'], 'CSTOTLM': ['3'],
        'CSTOTLW': ['5'], 'CSWHITT': ['4'], 'XCSTOTLT': ['R']
    })
    write_file(awards, 'completers_by_award', 2012, {
        'UNITID': ['100001', '100001'], 'AWLEVELC': ['03', '05'],
        'CSTOTLT': ['6', '4'], 'CSTOTLM': ['2', '1'],
        'CSTOTLW': ['4', '3'], 'CS18_24': ['2', '3'],
        'CS25_39': ['4', '1'], 'XCSTOTLT': ['R', 'R'],
        'XCS18_24': ['R', 'R']
    })

    obj = Completers(2012)
    total = obj.clean(completers_dir=str(overall))
    assert set(total.columns) == set(obj.get_available_vars())
    assert total.loc[0, 'total_completers'] == 8
    assert total.loc[0, 'source_table'] == 'B'
    assert pd.isna(total.loc[0, 'age_18_to_24'])
    assert pd.isna(total.loc[0, 'age_18_to_24_status'])
    by_level = obj.clean(degree_level='award_levels', award_dir=str(awards))
    assert by_level['total_completers'].tolist() == [6, 4]
    assert by_level['award_level_code'].tolist() == ['3', '5']
    assert by_level['source_award_code'].tolist() == ['03', '05']
    assert by_level['award_level'].tolist() == ['assc', 'bach']
    assert by_level.loc[0, 'age_18_to_24_status'] == 'R'
    assert obj.clean(degree_level='bach', award_dir=str(awards))['total_completers'].item() == 4
    # A person with both an associate's and a bachelor's can occur in both
    # award-level counts; their sum need not equal the unduplicated B count.
    assert by_level['total_completers'].sum() > total.loc[0, 'total_completers']


def test_completers_2025_certificate_codes_and_merge(tmp_path, monkeypatch):
    assert get_year_iter('completers')[-1] == 2025
    assert get_year_iter('completers_by_award', [2012, 2025]) == [2012, 2025]
    with pytest.raises(ValueError, match='2012-2025'):
        Completers(2011)
    monkeypatch.chdir(tmp_path)
    awards = tmp_path / 'completers_by_awarddata'
    write_file(awards, 'completers_by_award', 2025, {
        'unitid': ['100001', '100001'], 'awlevelc': ['11', '12'],
        'cstotlt': ['2', '3'], 'cstotlm': ['1', '1'], 'cstotlw': ['1', '2'],
        'csund18': ['0', '0'], 'cs18_24': ['1', '2']
    })
    monkeypatch.setattr(Completers, 'scrape', lambda self, degree_level='all', see_progress=False:
                        None)
    monkeypatch.setattr(Characteristics, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2025], 'name': ['Example College']}))
    result = Completers(2025).run(degree_level='award_levels',
                                   merge_with_char=True, rm_disk=True)
    assert result['award_level'].tolist() == [
        'certificate_under_12_weeks', 'certificate_12_weeks_to_1_year'
    ]
    assert result['name'].tolist() == ['Example College', 'Example College']
    assert not awards.exists()
    with pytest.raises(ValueError, match='degree_level'):
        Completers(2025).clean(degree_level='unknown')


@pytest.mark.parametrize('year, subject, stem, root', [
    (2012, 'completers', 'C2012_B', 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2012, 'completers_by_award', 'C2012_C', 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2025, 'completers', 'C2025_B', 'https://nces.ed.gov/ipeds/complete-data-files/'),
    (2025, 'completers_by_award', 'C2025_C', 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_completer_download_urls_and_cache(tmp_path, monkeypatch, year, subject, stem, root):
    monkeypatch.chdir(tmp_path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(stem.lower() + '.csv', b'UNITID,CSTOTLT\n100001,2\n')
    urls = []

    class Response:
        content = archive.getvalue()
        text = ''

    def fake_get(url):
        urls.append(url)
        return Response()

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data(subject, year, see_progress=False)
    assert urls == [root + stem + '.zip']
    assert (tmp_path / f'{subject}data' / f'{subject}_{year}.csv').exists()
    scrape_ipeds_data(subject, year, see_progress=False)
    assert len(urls) == 1
