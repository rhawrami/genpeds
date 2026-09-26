"""OM initial and expanded cohort schemas must not be conflated."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, OutcomeMeasures, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_file(directory, year, records):
    directory.mkdir(exist_ok=True)
    pd.DataFrame(records).to_csv(directory / f'outcome_measures_{year}.csv', index=False)


def test_2015_initial_cohorts_and_inconsistency_flag(tmp_path):
    directory = tmp_path / 'outcome_measuresdata'
    write_file(directory, 2015, {
        'UNITID': ['100001'] * 4, 'OMCHRT': ['1', '2', '3', '4'],
        'OMRCHT6': ['100', '30', '20', '10'], 'OMEXCL6': ['2', '0', '1', '0'],
        'OMACHT6': ['98', '30', '19', '10'], 'OMRCHT8': ['100', '30', '20', '10'],
        'OMEXCL8': ['3', '0', '2', '0'], 'OMACHT8': ['97', '30', '18', '10'],
        'OMAWDN6': ['60', '12', '10', '2'], 'OMAWDP6': ['61', '40', '53', '20'],
        'OMAWDN8': ['75', '15', '14', '3'], 'OMAWDP8': ['77', '50', '78', '30'],
        'XOMAWDN8': ['R'] * 4, 'OMFLAG': ['1', '0', '0', '0']
    })
    obj = OutcomeMeasures(2015)
    result = obj.clean(outcomes_dir=str(directory))
    assert set(result.columns) == set(obj.get_available_vars())
    assert result.cohort_type.tolist() == [
        'first_time_full_time', 'first_time_part_time',
        'non_first_time_full_time', 'non_first_time_part_time'
    ]
    first = result.iloc[0]
    assert (first.schema_version, first.pell_group) == ('initial', 'not_collected')
    assert first.entering_year_start == 2007 and first.entering_year_end == 2008
    assert first.adjusted_cohort_6 == 98 and first.adjusted_cohort_8 == 97
    assert first.awards_8 == 75 and first.awards_8_pct == 77  # published, not recomputed
    assert first.awards_8_status == 'R'
    assert first.inconsistency_flag_label == 'Data inconsistencies'
    assert pd.isna(first.awards_4) and pd.isna(first.adjusted_cohort)
    with pytest.raises(ValueError, match='from 2017'):
        OutcomeMeasures(2015).run(pell_group='pell')  # fail before scraping
    with pytest.raises(ValueError, match='from 2017'):
        OutcomeMeasures(2015).clean(outcomes_dir=str(directory), cohort_type='total')


def test_2016_revised_eight_year_cohort_not_reported(tmp_path):
    directory = tmp_path / 'outcome_measuresdata'
    write_file(directory, 2016, {
        'UNITID': ['100001'], 'OMCHRT': ['1'],
        'OMRCHT6': ['100'], 'OMACHT6': ['98'],
        'OMEXCL8': ['1'], 'OMACHT8': ['97'], 'OMAWDN8': ['70']
    })
    row = OutcomeMeasures(2016).clean(outcomes_dir=str(directory)).iloc[0]
    assert pd.isna(row.revised_cohort_8) and pd.isna(row.revised_cohort_8_status)
    assert row.adjusted_cohort_8 == 97
    assert pd.isna(row.inconsistency_flag)


def test_expanded_total_and_pell_cohorts_are_separate(tmp_path):
    directory = tmp_path / 'outcome_measuresdata'
    write_file(directory, 2024, {
        'UNITID': ['100001'] * 7,
        'OMCHRT': ['10', '11', '12', '30', '31', '50', '51'],
        'OMRCHRT': ['100', '40', '60', '20', '8', '120', '48'],
        'OMEXCLS': ['2', '1', '1', '0', '0', '2', '1'],
        'OMACHRT': ['98', '39', '59', '20', '8', '118', '47'],
        'OMAWDN4': ['50', '18', '32', '10', '4', '60', '22'],
        'OMAWDP4': ['51', '46', '54', '50', '50', '51', '47'],
        'OMAWDN6': ['60', '25', '35', '15', '6', '75', '31'],
        'OMAWDN8': ['75', '30', '45', '18', '7', '93', '37'],
        'OMAWDP8': ['77', '77', '76', '90', '88', '79', '79'],
        'OMCERT8': ['2', '1', '1', '1', '0', '3', '1'],
        'OMASSC8': ['5', '2', '3', '2', '1', '7', '3'],
        'OMBACH8': ['68', '27', '41', '15', '6', '83', '33'],
        'OMENRYI': ['5', '2', '3', '1', '0', '6', '2'],
        'OMENRAI': ['4', '1', '3', '0', '0', '4', '1'],
        'XOMAWDN8': ['R'] * 7
    })
    obj = OutcomeMeasures(2024)
    baseline = obj.clean(outcomes_dir=str(directory))
    assert set(baseline.source_cohort_code) == {'10', '30', '50'}
    assert baseline.pell_group.eq('total').all()
    row = obj.clean(cohort_type='non_first_time_full_time', pell_group='pell',
                    outcomes_dir=str(directory)).iloc[0]
    assert row.source_cohort_code == '31'
    assert row.cohort_type == 'non_first_time_full_time' and row.pell_group == 'pell'
    assert row.schema_version == 'expanded' and row.entering_year_start == 2016
    assert row.adjusted_cohort == 8 and row.bachelor_8 == 6
    assert row.awards_8_pct == 88
    assert pd.isna(row.adjusted_cohort_8)
    all_groups = obj.clean(cohort_type='all', pell_group='all', outcomes_dir=str(directory))
    assert len(all_groups) == 7  # 50 overlaps 10/30; Pell overlaps total


def test_outcome_measures_years_merge_and_remove_cache(tmp_path, monkeypatch):
    assert get_year_iter('outcome_measures') == list(range(2015, 2025))
    with pytest.raises(ValueError, match='2015-2024'):
        OutcomeMeasures(2025)
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'outcome_measuresdata'
    write_file(directory, 2024, {
        'unitid': ['100001'], 'omchrt': ['50'], 'omrchrt': ['100'],
        'omawdn8': ['80'], 'omawdp8': ['80']
    })
    monkeypatch.setattr(OutcomeMeasures, 'scrape', lambda self, see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2024], 'name': ['Example College']}))
    result = OutcomeMeasures(2024).run(cohort_type='total',
                                        merge_with_char=True, rm_disk=True)
    assert result.loc[0, 'name'] == 'Example College'
    assert result.loc[0, 'cohort_type'] == 'total'
    assert not directory.exists()


@pytest.mark.parametrize('year, root', [
    (2015, 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_outcome_measures_download_endpoint_and_cache(tmp_path, monkeypatch, year, root):
    monkeypatch.chdir(tmp_path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(f'om{year}.csv', b'UNITID,OMCHRT,OMAWDN8\n100001,1,80\n')
    urls = []

    class Response:
        status_code = 200
        headers = {}
        content = archive.getvalue()

        def iter_content(self, chunk_size):
            yield self.content

        def close(self):
            pass

    def fake_get(url, **kwargs):
        urls.append(url)
        return Response()

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data('outcome_measures', year, see_progress=False)
    assert urls == [f'{root}OM{year}.zip']
    assert (tmp_path / 'outcome_measuresdata' / f'outcome_measures_{year}.csv').exists()
    scrape_ipeds_data('outcome_measures', year, see_progress=False)
    assert len(urls) == 1
