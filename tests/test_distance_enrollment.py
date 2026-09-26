"""Distance-enrollment rows are overlapping levels, not fall-enrollment totals."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, DistanceEnrollment, scrape_ipeds_data
from genpeds.downloader import get_year_iter


def write_file(folder, year, values):
    folder.mkdir(exist_ok=True)
    pd.DataFrame(values).to_csv(folder / f'distance_enrollment_{year}.csv', index=False)


def test_distance_levels_locations_and_shares(tmp_path):
    directory = tmp_path / 'distance_enrollmentdata'
    write_file(directory, 2012, {
        'UNITID': ['100001'] * 5,
        'EFDELEV': [' 1', ' 2', ' 3', '11', '12'],
        'EFDETOT': ['100', '70', '50', '20', '30'],
        'EFDEEXC': ['40', '30', '25', '5', '10'],
        'EFDESOM': ['20', '20', '15', '5', '0'],
        'EFDENON': ['40', '20', '10', '10', '20'],
        'EFDEEX1': ['20', '15', '10', '5', '5'],
        'EFDEEX2': ['10', '8', '8', '0', '2'],
        'EFDEEX5 ': ['10', '7', '7', '0', '3'],
        'XEFDETOT': ['R'] * 5,
        'XEFDEEXC': ['R'] * 5,
        'XEFDEEX5': ['R'] * 5
    })
    data = DistanceEnrollment(2012).clean(student_level='all', distance_dir=str(directory))
    assert set(data.columns) == set(DistanceEnrollment().get_available_vars())
    assert set(data.student_level) == {
        'total', 'undergrad', 'degree_seeking', 'non_degree', 'grad'
    }
    ug = data.loc[data.student_level == 'undergrad'].iloc[0]
    assert ug.source_level_code == '2'
    assert ug.total_students == 70
    assert ug.exclusive_distance == 30
    assert ug.exclusive_location_unknown == 7
    assert ug.exclusive_share == pytest.approx(30 / 70 * 100)
    assert ug.some_share == pytest.approx(20 / 70 * 100)
    assert ug.exclusive_distance_status == 'R'
    assert data.loc[data.student_level == 'degree_seeking', 'total_students'].item() == 50
    assert len(DistanceEnrollment(2012).clean(distance_dir=str(directory))) == 1


def test_distance_null_denominator_and_characteristics_merge(tmp_path, monkeypatch):
    assert get_year_iter('distance_enrollment') == list(range(2012, 2025))
    with pytest.raises(ValueError, match='2012-2024'):
        DistanceEnrollment(2025)
    monkeypatch.chdir(tmp_path)
    write_file(tmp_path / 'distance_enrollmentdata', 2024, {
        'unitid': ['100001'], 'efdelev': ['2'], 'efdetot': ['0'],
        'efdeexc': ['0'], 'efdesom': ['0'], 'efdenon': ['0']
    })
    monkeypatch.setattr(DistanceEnrollment, 'scrape', lambda self, see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2024], 'name': ['Example College']}))
    data = DistanceEnrollment(2024).run(merge_with_char=True, rm_disk=True)
    assert data.loc[0, 'name'] == 'Example College'
    assert pd.isna(data.loc[0, 'exclusive_share'])
    assert not (tmp_path / 'distance_enrollmentdata').exists()


@pytest.mark.parametrize('year, root', [
    (2012, 'https://nces.ed.gov/ipeds/datacenter/data/'),
    (2024, 'https://nces.ed.gov/ipeds/complete-data-files/')
])
def test_distance_download_and_cache(tmp_path, monkeypatch, year, root):
    monkeypatch.chdir(tmp_path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(f'ef{year}a_dist.csv', b'UNITID,EFDELEV,EFDETOT\n100001,2,100\n')
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
    scrape_ipeds_data('distance_enrollment', year, see_progress=False)
    assert urls == [f'{root}EF{year}A_DIST.zip']
    assert (tmp_path / 'distance_enrollmentdata' /
            f'distance_enrollment_{year}.csv').exists()
    scrape_ipeds_data('distance_enrollment', year, see_progress=False)
    assert len(urls) == 1
