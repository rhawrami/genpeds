"""Academic Libraries year boundaries, reporting screens and original flags."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import AcademicLibraries, Characteristics, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_year(directory, year, values):
    directory.mkdir(exist_ok=True)
    pd.DataFrame(values).to_csv(directory / f'academic_libraries_{year}.csv', index=False)


def test_collections_staff_and_expense_reporting_boundaries(tmp_path):
    folder = tmp_path / 'academic_librariesdata'
    write_year(folder, 2014, {
        'UNITID': ['100001', '100002'], 'LCOLELYN': ['1', '2'],
        'LPBOOKS': ['15', '0'], 'XLPBOOKS': ['R', 'Z'],
        'LPCLLCT': ['20', '0'], 'XLPCOLLC': ['R', 'Z'],
        'LECLLCT': ['10', '5'], 'XLECOLLC': ['R', 'R'],
        'LSALWAG': ['120000', None], 'XSALWAG': ['R', 'A'],
        'LEXPTOT': ['155000', None], 'XLEXPTOT': ['R', 'A'],
        'LSWMSOM': ['145000', '.'], 'LFRNGBYN': ['1', '-2'],
        'LSUPPVRS': ['2', '-2'], 'LILLDPR': ['2', None],
    })
    write_year(folder, 2015, {'UNITID': ['100001'], 'LPBOOKS': ['18'],
                              'LTCLLCT': ['45'], 'LTCRCLT': ['22'],
                              'LSUPPVRS': ['1'], 'LEXPTOT': ['160000'],
                              'LSWMSOM': ['150000']})
    write_year(folder, 2016, {'UNITID': ['100001'], 'LPBOOKS': ['20'],
                              'LPSERIA': ['3'], 'LESERIA': ['4'],
                              'LILLDYN': ['1'], 'LEXPTOT': ['170000'],
                              'LSWMSOM': ['160000']})
    write_year(folder, 2018, {'UNITID': ['100001'], 'LPBOOKS': ['22'],
                              'LPCLLCT': ['29'], 'LPSERIA': ['10'],
                              'LEXPTOT': ['180000'], 'LSWMSOM ': ['170000']})
    write_year(folder, 2019, {'UNITID': ['100001'], 'LPBOOKS': ['24'],
                              'LPCLLCT': ['40'], 'XLPCOLLC': ['R'],
                              'LEXP100K': ['1 '], 'LEXPTOT': ['190000'],
                              'LSWMSOM ': ['175000']})
    write_year(folder, 2020, {'UNITID': ['100001'], 'LPBOOKS': ['25'],
                              'LEXP100K': ['1'], 'LILSYN': ['1'],
                              'LSTOTAL': ['12.5'], 'XLSTOTAL': ['R'],
                              'LSSTAST': ['2.5'], 'LEXPTOT': ['200000'],
                              'LSWMSOM': ['180000']})
    write_year(folder, 2024, {'UNITID': ['100001'], 'LPBOOKS': ['30'],
                              'LEXP100K': ['1'], 'LILSYN': ['1'],
                              'LSTOTAL': ['14.5'], 'XLSTOTAL': ['R'],
                              'LEXPTOT': ['230000'], 'LSWMSOM': ['205000']})

    api = AcademicLibraries()
    df = api.clean(libraries_dir=str(folder))
    assert len(df) == 8 and set(df.columns) == set(api.get_available_vars())
    early = df.loc[df.year.eq(2014) & df.id.eq('100001')].iloc[0]
    small = df.loc[df.year.eq(2014) & df.id.eq('100002')].iloc[0]
    assert early.physical_books == 15 and early.physical_books_status == 'R'
    assert early.physical_collections_status == 'R'  # XLPCOLLC is not XLPCLLCT
    assert early.salaries_wages_status == 'R'  # XSALWAG is not XLSALWAG
    assert early.electronic_only_collection == 'yes'
    assert early.virtual_reference_services == 'no'
    assert pd.isna(early.expenditure_threshold_code)
    assert pd.isna(early.physical_serials) and pd.isna(early.staff_fte)
    assert pd.isna(early.total_collections)
    assert small.fringe_from_library_budget_code == '-2'
    assert small.fringe_from_library_budget == 'not_applicable'
    assert small.physical_books == 0 and small.physical_books_status == 'Z'
    assert pd.isna(small.total_expenditures) and small.total_expenditures_status == 'A'
    assert pd.isna(small.expenditures_excluding_fringe)
    assert 'expenditures_excluding_fringe_status' not in df
    assert df.loc[df.year.eq(2015), 'total_collections'].item() == 45
    assert df.loc[df.year.eq(2015), 'total_circulations'].item() == 22
    assert pd.isna(df.loc[df.year.eq(2015), 'physical_serials'].item())
    assert df.loc[df.year.eq(2016), 'physical_serials'].item() == 3
    assert pd.isna(df.loc[df.year.eq(2016), 'virtual_reference_services'].item())
    assert df.loc[df.year.eq(2018), 'collection_total_definition'].item() == 'excludes_serials_2014_2018'
    assert df.loc[df.year.eq(2019), 'collection_total_definition'].item() == 'includes_serials_2019_2024'
    assert df.loc[df.year.eq(2019), 'expenditure_threshold_code'].item() == '1'
    assert df.loc[df.year.eq(2019), 'expenditure_threshold'].item() == 'yes'
    assert df.loc[df.year.eq(2020), 'staff_fte'].item() == 12.5
    assert df.loc[df.year.eq(2020), 'student_assistants_fte'].item() == 2.5
    assert df.loc[df.year.eq(2020), 'staff_fte_status'].item() == 'R'
    assert df.loc[df.year.eq(2024), 'expenditures_excluding_fringe'].item() == 205000


def test_missing_years_invalid_csv_and_range(tmp_path):
    folder = tmp_path / 'academic_librariesdata'
    write_year(folder, 2024, {'UNITID': ['100001'], 'LPBOOKS': ['15'],
                              'LEXPTOT': ['100000'], 'LSWMSOM': ['99000']})
    assert get_year_iter('academic_libraries') == list(range(2014, 2025))
    with pytest.raises(ValueError, match='2014-2024'):
        AcademicLibraries(2013)
    with pytest.raises(ValueError, match='2014-2024'):
        AcademicLibraries(2025)
    with pytest.raises(FileNotFoundError, match='2023'):
        AcademicLibraries((2023, 2024)).clean(libraries_dir=str(folder))
    write_year(folder, 2024, {'UNITID': ['100001', '100001'],
                              'LPBOOKS': ['15', '16'], 'LEXPTOT': ['100000', '100001'],
                              'LSWMSOM': ['99000', '99999']})
    with pytest.raises(ValueError, match='duplicate UNITIDs'):
        AcademicLibraries(2024).clean(libraries_dir=str(folder))


def test_run_merges_characteristics_and_removes_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / 'academic_librariesdata'
    write_year(folder, 2024, {'UNITID': ['100001'], 'LPBOOKS': ['15'],
                              'LEXPTOT': ['100000'], 'LSWMSOM': ['99000']})
    monkeypatch.setattr(AcademicLibraries, 'scrape',
                        lambda self, see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run',
                        lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2024],
                                      'name': ['Example University']}))
    row = AcademicLibraries(2024).run(merge_with_char=True, rm_disk=True).iloc[0]
    assert row['name'] == 'Example University'
    assert row['total_expenditures'] == 100000
    assert not folder.exists()


@pytest.mark.parametrize('year,root', [
    (2014, 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'https://nces.ed.gov/ipeds/complete-data-files/'),
])
def test_al_scrape_prefers_revision_and_caches(tmp_path, monkeypatch, year, root):
    monkeypatch.chdir(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(f'al{year}.csv', b'UNITID,LPBOOKS\n100001,10\n')
        archive.writestr(f'al{year}_rv.csv', b'UNITID,LPBOOKS\n100001,11\n')
    urls = []

    class Response:
        status_code = 200
        headers = {}

        def iter_content(self, chunk_size):
            yield buffer.getvalue()

        def close(self):
            pass

    def fake_get(url, **kwargs):
        urls.append(url)
        return Response()

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data('academic_libraries', year, see_progress=False)
    scrape_ipeds_data('academic_libraries', year, see_progress=False)
    assert urls == [root + f'AL{year}.zip']
    output = tmp_path / 'academic_librariesdata' / f'academic_libraries_{year}.csv'
    assert pd.read_csv(output)['LPBOOKS'].item() == 11
