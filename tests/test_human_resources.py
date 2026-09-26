"""Modern HR tables have distinct populations, grains, and salary regimes."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, HumanResources, scrape_ipeds_data
from genpeds.human_resources import HR_DATASETS
from genpeds.downloader import get_year_iter


def write_file(directory, dataset, year, values):
    directory.mkdir(exist_ok=True)
    pd.DataFrame(values).to_csv(directory / f'{HR_DATASETS[dataset]}_{year}.csv', index=False)


def test_staff_totals_and_occupation_labels_are_not_summed(tmp_path):
    directory = tmp_path / 'human_resourcesdata'
    write_file(directory, 'staff', 2012, {
        'UNITID': ['100001'], 'STAFFCAT': ['1250'], 'OCCUPCAT': ['250'],
        'FTPT': ['1'], 'HRTOTLT': ['50'], 'HRTOTLM': ['20'],
        'HRTOTLW': ['30'], 'HRWHITW': ['15'],
        'XHRTOTLT': ['R'], 'XHRWHITW': ['R']
    })
    write_file(directory, 'staff', 2024, {
        'UNITID': ['100001', '100001'],
        'STAFFCAT': ['1100', '1250'], 'OCCUPCAT': ['100', '250'],
        'FTPT': ['1', '1'], 'HRTOTLT': ['100', '50'],
        'HRTOTLM': ['40', '20'], 'HRTOTLW': ['60', '30'],
        'XHRTOTLT': ['R', 'R']
    })
    hr = HumanResources()
    result = hr.clean(dataset='staff', hr_dir=str(directory))
    assert set(result.columns) == set(hr.get_dataset_vars('staff'))
    assert set(result.columns).issubset(hr.get_available_vars())
    assert len(result) == 3
    early = result.loc[result.year.eq(2012)].iloc[0]
    later = result.loc[result.year.eq(2024) & result.category_code.eq('1250')].iloc[0]
    assert early.occupation_code == later.occupation_code == '250'
    assert early.occupation_label != later.occupation_label  # source classification wording changed
    assert early.white_women == 15 and early.white_women_status == 'R'
    assert later.women_share == 60
    assert result.loc[result.year.eq(2024) & result.category_code.eq('1100'),
                      'people_total'].item() == 100
    assert result.loc[result.year.eq(2024) & result.category_code.eq('1250'),
                      'people_total'].item() == 50
    assert HumanResources(2024).clean(dataset='staff', hr_dir=str(directory),
                                      category_codes=['1100']).category_code.tolist() == ['1100']


def test_instructional_salary_months_and_noninstructional_outlays(tmp_path):
    salary_dir = tmp_path / 'hr_instructional_salariesdata'
    write_file(salary_dir, 'instructional_salaries', 2012, {
        'UNITID': ['100001'], 'ARANK': ['1'], 'SATOTLT': ['10'],
        'SATOTLM': ['6'], 'SATOTLW': ['4'],
        'SAOUTLT': ['1000000'], 'SAOUTLM': ['600000'],
        'SAOUTLW': ['400000'], 'SAAVMNM': ['9.2'],
        'XSAOUTLT': ['R']
    })
    write_file(salary_dir, 'instructional_salaries', 2016, {
        'UNITID': ['100001'], 'ARANK': ['1'], 'SATOTLT': ['10'],
        'SAOUTLT': ['1200000'], 'SAEQ9AM': ['130000'],
        'SAEQ9AW': ['120000'], 'XSAEQ9AW': ['R'],
        'SA09MCM': ['6'], 'SA09MCW': ['4'],
        'SA09MAM': ['110000'], 'SA09MAW': ['100000']
    })
    write_file(salary_dir, 'instructional_salaries', 2024, {
        'UNITID': ['100001'], 'ARANK': ['1'], 'SATOTLT': ['10'],
        'SAOUTLT': ['1400000'], 'SAEQ9AM': ['150000'],
        'SAEQ9AW': ['135000']
    })
    df = HumanResources().clean(dataset='instructional_salaries', hr_dir=str(salary_dir))
    assert set(df.columns) == set(HumanResources().get_dataset_vars('instructional_salaries'))
    old, newer, recent = (df.iloc[i] for i in range(3))
    assert old.rank_label == 'Professor'
    assert old.staff_9to12_total == 10
    assert old.salary_outlay_men == 600000
    assert old.average_months_men == 9.2
    assert pd.isna(old.equated_9_month_salary_men)
    assert old.salary_regime == '2012-2015_weighted_months'
    assert newer.equated_9_month_salary_women == 120000
    assert newer.equated_9_month_salary_women_status == 'R'
    assert newer.average_salary_9_month_men == 110000
    assert newer.salary_regime == '2016_onward_explicit_months'
    assert pd.isna(recent.average_months_men)
    assert recent.academic_year_end == 2025

    nis_dir = tmp_path / 'hr_noninstructional_salariesdata'
    write_file(nis_dir, 'noninstructional_salaries', 2024, {
        'UNITID': ['100001'], 'SANIN01': ['50'], 'SANIT01': ['5000000'],
        'SANIN05': ['10'], 'SANIT05': ['1500000'],
        'XSANIN05': ['R'], 'XSANIT05': ['R']
    })
    nis = HumanResources(2024).clean(dataset='noninstructional_salaries',
                                     category_codes=['01', '05'], hr_dir=str(nis_dir))
    assert nis['occupation_code'].tolist() == ['01', '05']
    assert nis.loc[1, 'occupation_label'] == 'Management'
    assert nis.loc[1, 'staff_count'] == 10
    assert nis.loc[1, 'salary_outlay'] == 1500000
    assert 'women' not in nis.columns  # no sex-specific noninstructional outlays


def test_all_other_hr_families_and_new_hire_window(tmp_path):
    records = [
        ('employees', 2024, {'UNITID': ['100001'], 'EAPCAT': ['10000'],
                             'OCCUPCAT': ['100'], 'FACSTAT': ['0'],
                             'EAPTOT': ['100'], 'EAPFT': ['75'], 'EAPPT': ['25']}),
        ('instructional_staff', 2024,
         {'UNITID': ['100001'], 'SISCAT': ['101'], 'FACSTAT': ['10'],
          'ARANK': ['1'], 'HRTOTLT': ['20'], 'HRTOTLM': ['12'], 'HRTOTLW': ['8']}),
        ('faculty_ranks', 2024,
         {'UNITID': ['100001'], 'FACSTAT': ['20'],
          'SISTOTL': ['20'], 'SISPROF': ['8'], 'SISASCP': ['6']}),
        ('new_hires', 2017, {'UNITID': ['100001'], 'SNHCAT': ['10000'],
                             'OCCUPCAT': ['100'], 'FACSTAT': ['0'],
                             'HRTOTLT': ['12'], 'HRTOTLM': ['5'], 'HRTOTLW': ['7']}),
        ('new_hires', 2018, {'UNITID': ['100001'], 'SNHCAT': ['10000'],
                             'OCCUPCAT': ['100'], 'FACSTAT': ['0'],
                             'HRTOTLT': ['14'], 'HRTOTLM': ['6'], 'HRTOTLW': ['8']}),
    ]
    for dataset, year, values in records:
        directory = tmp_path / f'{HR_DATASETS[dataset]}data'
        write_file(directory, dataset, year, values)

    hr = HumanResources()
    emp = hr.clean(dataset='employees', hr_dir=str(tmp_path / 'hr_employeesdata'))
    assert emp.loc[0, 'employees_total'] == 100
    assert emp.loc[0, 'full_time_total'] == 75
    inst = hr.clean(dataset='instructional_staff',
                    hr_dir=str(tmp_path / 'hr_instructional_staffdata'))
    assert inst.loc[0, 'rank_label'] == 'Professors'
    assert inst.loc[0, 'women_share'] == 40
    faculty = hr.clean(dataset='faculty_ranks',
                       hr_dir=str(tmp_path / 'hr_faculty_ranksdata'))
    assert faculty.loc[0, 'professors'] == 8
    assert 'women' not in faculty.columns
    hires = hr.clean(dataset='new_hires', hr_dir=str(tmp_path / 'hr_new_hiresdata'))
    assert hires['hire_window_months'].tolist() == [4, 12]
    assert hires['hire_period_start_year'].tolist() == [2017, 2017]


def test_hr_run_merges_characteristics_and_removes_selected_cache(tmp_path, monkeypatch):
    assert get_year_iter('human_resources') == list(range(2012, 2025))
    assert get_year_iter('hr_instructional_salaries', 2024) == [2024]
    with pytest.raises(ValueError, match='2012-2024'):
        HumanResources(2025)
    monkeypatch.chdir(tmp_path)
    data = tmp_path / 'human_resourcesdata'
    write_file(data, 'staff', 2024, {'unitid': ['100001'], 'staffcat': ['1100'],
                                    'occupcat': ['100'], 'ftpt': ['1'],
                                    'hrtotlt': ['100'], 'hrtotlm': ['40'],
                                    'hrtotlw': ['60']})
    monkeypatch.setattr(HumanResources, 'scrape',
                        lambda self, dataset='staff', see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run',
                        lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2024],
                                      'name': ['Example College']}))
    d = HumanResources(2024).run(category_codes=['1100'], merge_with_char=True,
                                 rm_disk=True)
    assert d.loc[0, 'name'] == 'Example College'
    assert d.loc[0, 'people_total'] == 100
    assert not data.exists()
    with pytest.raises(ValueError, match='dataset'):
        HumanResources(2024).run(dataset='invalid')


@pytest.mark.parametrize('year, subject, stem, root', [
    (2012, 'human_resources', 'S2012_OC', 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'hr_instructional_salaries', 'SAL2024_IS',
     'https://nces.ed.gov/ipeds/complete-data-files/'),
])
def test_hr_scrape_endpoints_and_cache(tmp_path, monkeypatch, year, subject, stem, root):
    monkeypatch.chdir(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zipped:
        zipped.writestr(stem.lower() + '.csv', b'UNITID,ARANK\n100001,1\n')
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
    scrape_ipeds_data(subject, year, see_progress=False)
    assert urls == [root + stem + '.zip']
    assert (tmp_path / f'{subject}data' / f'{subject}_{year}.csv').exists()
    scrape_ipeds_data(subject, year, see_progress=False)
    assert len(urls) == 1
