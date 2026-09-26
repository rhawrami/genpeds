"""Offline request, archive, and cache-failure checks for the shared downloader."""

import io
import zipfile

import pytest
import requests

from genpeds import scrape_ipeds_data
from genpeds.core import _remove_download_dir
from genpeds.downloader import download_a_file


class FakeResponse:
    def __init__(self, content=b'', status_code=200, headers=None, error=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.error = error
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'HTTP {self.status_code}')

    def iter_content(self, chunk_size):
        midpoint = len(self.content) // 2
        yield self.content[:midpoint]
        if self.error:
            raise self.error
        yield self.content[midpoint:]

    def close(self):
        self.closed = True


def zipped(**members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_invalid_subject_and_endpoint_do_not_create_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match='Unknown IPEDS subject'):
        scrape_ipeds_data('../../elsewhere', 2024, see_progress=False)
    with pytest.warns(UserWarning, match='No endpoint for year 9999'):
        with pytest.raises(ValueError, match='No safe endpoint'):
            scrape_ipeds_data('enrollment', 9999, see_progress=False)
    with pytest.raises(ValueError, match='too large'):
        scrape_ipeds_data('enrollment', (1984, 10**9), see_progress=False)
    with pytest.raises(TypeError, match='integers'):
        scrape_ipeds_data('enrollment', ['2024'], see_progress=False)
    with pytest.warns(UserWarning, match='No endpoint for year 0'):
        with pytest.raises(ValueError, match='No safe endpoint'):
            scrape_ipeds_data('enrollment', 0, see_progress=False)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('status', [404, 503, 302])
def test_http_failures_are_raised_without_leaving_files(tmp_path, monkeypatch, status):
    monkeypatch.chdir(tmp_path)
    response = FakeResponse(status_code=status)
    monkeypatch.setattr('genpeds.downloader.requests.get', lambda url, **kwargs: response)
    with pytest.raises(RuntimeError, match='2024'):
        scrape_ipeds_data('enrollment', 2024, see_progress=False)
    assert response.closed
    assert not list((tmp_path / 'enrollmentdata').iterdir())


def test_zip_paths_are_never_extracted_and_revised_csv_is_preferred(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = zipped(**{
        '../../escaped.csv': b'not chosen',
        'ef2024a.csv': b'original',
        'nested/ef2024a_rv.csv': b'updated',
        'z_readme.txt': b'not data'
    })
    response = FakeResponse(data)
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setattr('genpeds.downloader.requests.get', fake_get)
    scrape_ipeds_data('enrollment', [2024, 2024], see_progress=False)
    assert (tmp_path / 'enrollmentdata' / 'enrollment_2024.csv').read_bytes() == b'updated'
    assert not (tmp_path / 'escaped.csv').exists()
    assert not (tmp_path / 'enrollmentdata' / 'nested').exists()
    assert not list((tmp_path / 'enrollmentdata').glob('.genpeds-*'))
    assert calls == [{'stream': True, 'allow_redirects': False, 'timeout': (10, 120)}]


@pytest.mark.parametrize('response', [
    FakeResponse(b'not a ZIP'),
    FakeResponse(b'partial', error=requests.Timeout('read timed out')),
    FakeResponse(status_code=200, headers={'Content-Length': '999999999999'}),
    FakeResponse(zipped(**{'notes.txt': b'not a data file'}))
])
def test_malformed_oversized_or_interrupted_download_leaves_no_cache(tmp_path, monkeypatch, response):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('genpeds.downloader.requests.get', lambda url, **kwargs: response)
    with pytest.raises(RuntimeError, match='2024'):
        scrape_ipeds_data('enrollment', 2024, see_progress=False)
    assert response.closed
    assert not list((tmp_path / 'enrollmentdata').iterdir())


def test_oversized_zip_member_fails_before_extraction(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    content = zipped(**{'ef2024a.csv': b'x' * 20})
    monkeypatch.setattr('genpeds.downloader.MAX_EXTRACTED_BYTES', 10)
    response = FakeResponse(content)
    monkeypatch.setattr('genpeds.downloader.requests.get', lambda url, **kwargs: response)
    with pytest.raises(RuntimeError, match='2024'):
        scrape_ipeds_data('enrollment', 2024, see_progress=False)
    assert not list((tmp_path / 'enrollmentdata').iterdir())


def test_archive_member_count_is_bounded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = FakeResponse(zipped(**{'ef2024a.csv': b'data', 'extra.csv': b'extra'}))
    monkeypatch.setattr('genpeds.downloader.MAX_ZIP_MEMBERS', 1)
    monkeypatch.setattr('genpeds.downloader.requests.get', lambda url, **kwargs: response)
    with pytest.raises(RuntimeError, match='2024'):
        scrape_ipeds_data('enrollment', 2024, see_progress=False)
    assert not list((tmp_path / 'enrollmentdata').iterdir())


def test_symlink_cache_and_dangerous_rm_disk_paths_are_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / 'enrollmentdata').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        scrape_ipeds_data('enrollment', 2024, see_progress=False)
    assert not list(outside.iterdir())
    with pytest.raises(ValueError, match='Unsafe'):
        _remove_download_dir('.')
    with pytest.raises(ValueError, match='Unsafe'):
        _remove_download_dir('..')
    assert tmp_path.exists()

    (tmp_path / 'enrollmentdata').unlink()
    directory = tmp_path / 'enrollmentdata'
    directory.mkdir()
    other_file = outside / 'other.csv'
    other_file.write_bytes(b'not IPEDS data')
    (directory / 'enrollment_2024.csv').symlink_to(other_file)
    with pytest.raises(ValueError, match='symlinked'):
        scrape_ipeds_data('enrollment', 2024, see_progress=False)
    assert other_file.read_bytes() == b'not IPEDS data'


def test_endpoint_from_configuration_cannot_supply_a_url_or_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'enrollmentdata'
    directory.mkdir()
    with pytest.raises(ValueError, match='No safe endpoint'):
        download_a_file('enrollment', 2024, {
            'enrollment': {'endpoints': {'2024': '../untrusted'}}
        })
    assert not list(directory.iterdir())


def test_existing_cache_survives_a_failed_redownload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'enrollmentdata'
    directory.mkdir()
    target = directory / 'enrollment_2024.csv'
    target.write_bytes(b'previous-good-data')
    # A direct re-download can replace a cached year; failure must not do so.
    response = FakeResponse(b'broken ZIP')
    monkeypatch.setattr('genpeds.downloader.requests.get', lambda url, **kwargs: response)
    with pytest.raises(zipfile.BadZipFile):
        download_a_file('enrollment', 2024, {'enrollment': {'endpoints': {'2024': 'EF2024A'}}})
    assert target.read_bytes() == b'previous-good-data'
    assert not list(directory.glob('.genpeds-*'))
