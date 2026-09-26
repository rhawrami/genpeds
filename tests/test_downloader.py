"""Offline download/cache integration for year selectors and NCES ZIP roots."""

import io
import json
import zipfile
from pathlib import Path

import pytest

from genpeds import scrape_ipeds_data
from genpeds.downloader import get_year_iter


@pytest.mark.parametrize('subject,year_range', [
    ('characteristics', (2000, 2002)),
    ('admissions', [2001, 2014, 2023]),
    ('enrollment', 2024),
    ('completion', [1984, 2024]),
    ('graduation', (2022, 2023)),
    ('academic_libraries', [2014, 2024]),
])
def test_year_selection_endpoint_revision_and_cache(tmp_path, monkeypatch, subject, year_range):
    monkeypatch.chdir(tmp_path)
    with (Path(__file__).resolve().parents[1] / 'src/genpeds/cfg.json').open() as handle:
        cfg = json.load(handle)
    years = get_year_iter(subject, year_range)
    requested_urls = []

    class Response:
        status_code = 200
        headers = {}

        def __init__(self, stem):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                archive.writestr(f'{stem.lower()}.csv', b'UNITID\n100001\n')
                archive.writestr(f'{stem.lower()}_rv.csv', b'UNITID\n100002\n')
            self.content = buffer.getvalue()

        def iter_content(self, chunk_size):
            yield self.content

        def close(self):
            pass

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        return Response(url.rsplit('/', 1)[-1].removesuffix('.zip'))

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data(subject, year_range, see_progress=False)
    scrape_ipeds_data(subject, year_range, see_progress=False)  # cached
    expected = {
        ('https://nces.ed.gov/ipeds/complete-data-files/' if year > 2022 else
         'https://nces.ed.gov/ipeds/datacenter/data/') +
        cfg[subject]['endpoints'][str(year)] + '.zip' for year in years
    }
    assert set(requested_urls) == expected and len(requested_urls) == len(years)
    for year in years:
        csv = tmp_path / f'{subject}data' / f'{subject}_{year}.csv'
        assert csv.is_file() and b'100002' in csv.read_bytes()
