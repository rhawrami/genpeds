"""Finance forms and accounting-era boundaries must remain explicit."""

import io
import zipfile

import pandas as pd
import pytest

from genpeds import Characteristics, Finance, scrape_ipeds_data
from genpeds.downloader import get_year_iter
from genpeds.finance import FINANCE_FORMS


def write_form(directory, form, year, values):
    directory.mkdir(exist_ok=True)
    pd.DataFrame(values).to_csv(directory / f'{FINANCE_FORMS[form]}_{year}.csv', index=False)


def test_form_specific_measures_and_year_breaks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_form(tmp_path / 'financedata', 'f1a', 2019, {
        'UNITID': ['100001'], 'F1A06': ['1000'], 'F1A13': ['400'],
        'F1A18': ['600'], 'F1B01': ['200'], 'F1B25': ['700'],
        'F1B09': ['300'], 'F1B19': ['250'], 'F1C011': ['90'],
        'F1C191': ['500'], 'XF1B01': ['R'], 'F1E08': ['50'],
    })
    write_form(tmp_path / 'financedata', 'f1a', 2020, {
        'UNITID': ['100001'], 'F1A06': ['1100'], 'F1B01': ['220'],
        'F1C191': ['520'], 'F1E12': ['35'], 'XF1E12': ['Z'],
    })
    write_form(tmp_path / 'finance_f2data', 'f2', 2019, {
        'UNITID': ['200001'], 'F2A02': ['1800'], 'F2A03': ['500'],
        'F2A06': ['1300'], 'F2D01': ['400'], 'F2D16': ['800'],
        'F2E131': ['600'], 'F2E011': ['150'], 'XF2D01': ['A'],
    })
    write_form(tmp_path / 'finance_f2data', 'f2', 2020, {
        'UNITID': ['200001'], 'F2A02': ['1850'], 'F2D01': ['440'],
        'F2E131': ['650'], 'F2C12': ['12'],
    })
    write_form(tmp_path / 'finance_f3data', 'f3', 2019, {
        'UNITID': ['300001'], 'F3A01': ['900'], 'F3A02': ['700'],
        'F3A03': ['200'], 'F3D01': ['100'], 'F3D09': ['500'],
        'F3B02': ['400'], 'F3E011': ['60'], 'F3E071': ['410'],
        'XF3B02': ['R'], 'XF3E071': ['R'],
    })
    write_form(tmp_path / 'finance_f3data', 'f3', 2020, {
        'UNITID': ['300001'], 'F3A01': ['950'], 'F3D01': ['120'],
        'F3B02': ['410'], 'F3C12': ['8'],
    })
    df = Finance([2019, 2020]).clean()
    assert len(df) == 6
    assert set(df.columns) == set(Finance().get_available_vars())
    assert not df.duplicated(['id', 'year', 'form']).any()
    public = df.loc[df.form.eq('f1a') & df.year.eq(2019)].iloc[0]
    nonprofit = df.loc[df.form.eq('f2') & df.year.eq(2019)].iloc[0]
    forprofit = df.loc[df.form.eq('f3') & df.year.eq(2019)].iloc[0]
    assert public.net_position == 600 and public.net_tuition_fees_status == 'R'
    assert public.revenues_and_additions == 700
    assert pd.isna(public.revenues_and_investment_return)
    assert nonprofit.net_assets == 1300 and nonprofit.net_tuition_fees_status == 'A'
    assert nonprofit.revenues_and_investment_return == 800
    assert forprofit.equity == 200 and forprofit.total_expenses_status == 'R'
    assert forprofit.total_expenses == 400 and forprofit.functional_expenses == 410
    assert pd.isna(forprofit.net_assets) and pd.isna(forprofit.net_position)
    assert df.loc[df.year.eq(2019), 'pell_discounts'].isna().all()
    assert df.loc[df.year.eq(2020), 'pell_discounts'].tolist() == [35, 12, 8]
    assert df.loc[df.year.eq(2020) & df.form.eq('f1a'),
                  'pell_discounts_status'].item() == 'Z'
    assert df.loc[df.year.eq(2019), 'source_stem'].tolist() == [
        'F1819_F1A', 'F1819_F2', 'F1819_F3']
    assert df.loc[df.form.eq('f1a'), 'accounting_basis'].unique().tolist() == ['public_gasb']
    assert 'equity' not in Finance().get_form_vars('f1a')
    assert 'equity' in Finance().get_form_vars('f3')


def test_early_for_profit_instruction_is_unavailable_and_missing_cache_errors(tmp_path):
    directory = tmp_path / 'finance_f3data'
    write_form(directory, 'f3', 2004, {
        'UNITID': ['123456'], 'F3A01': ['200'], 'F3D01': ['90'],
        'F3B02': ['80'], 'XF3B02': ['B'],
    })
    write_form(directory, 'f3', 2014, {
        'UNITID': ['123456'], 'F3A01': ['250'], 'F3D01': ['110'],
        'F3B02': ['100'], 'F3E011': ['60'], 'XF3E011': ['R'],
    })
    df = Finance([2004, 2014]).clean(form='f3', finance_dir=str(directory))
    assert df.loc[0, 'accounting_regime'] == 'prealigned_2004_2009'
    assert df.loc[1, 'accounting_regime'] == 'aligned_f3_revised_2014_onward'
    assert pd.isna(df.loc[0, 'instruction_expenses'])
    assert pd.isna(df.loc[0, 'instruction_expenses_status'])
    assert pd.isna(df.loc[0, 'functional_expenses'])
    assert df.loc[0, 'total_expenses'] == 80
    assert df.loc[1, 'instruction_expenses'] == 60
    assert df.loc[1, 'instruction_expenses_status'] == 'R'
    with pytest.raises(FileNotFoundError, match='2005'):
        Finance((2004, 2005)).clean(form='f3', finance_dir=str(directory))
    with pytest.raises(ValueError, match='single form'):
        Finance(2004).clean(form='all', finance_dir=str(directory))
    with pytest.raises(ValueError, match='missing or duplicate UNITIDs'):
        write_form(directory, 'f3', 2004, {
            'UNITID': ['123456', '123456'], 'F3A01': ['200', '300'],
            'F3D01': ['90', '100'], 'F3B02': ['80', '90']})
        Finance(2004).clean(form='f3', finance_dir=str(directory))


def test_finance_run_merge_cleanup_and_validation(tmp_path, monkeypatch):
    assert get_year_iter('finance') == list(range(2004, 2025))
    with pytest.raises(ValueError, match='2004-2024'):
        Finance(2003)
    with pytest.raises(ValueError, match='2004-2024'):
        Finance(2025)
    with pytest.raises(ValueError, match='form'):
        Finance(2024).run(form='invalid')
    monkeypatch.chdir(tmp_path)
    write_form(tmp_path / 'financedata', 'f1a', 2024, {
        'unitid': ['123456'], 'f1a06': ['500'], 'f1b01': ['90'],
        'f1c191': ['100'], 'f1e12': ['5'],
    })
    monkeypatch.setattr(Finance, 'scrape', lambda self, form='all', see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run',
                        lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['123456'], 'year': [2024],
                                      'name': ['Example College']}))
    df = Finance(2024).run(form='f1a', merge_with_char=True, rm_disk=True)
    assert df.loc[0, 'name'] == 'Example College'
    assert df.loc[0, 'source_stem'] == 'F2324_F1A'
    assert df.loc[0, 'pell_discounts'] == 5
    assert not (tmp_path / 'financedata').exists()


@pytest.mark.parametrize('subject,stem', [
    ('finance', 'F2324_F1A'), ('finance_f2', 'F2324_F2'),
    ('finance_f3', 'F2324_F3'),
])
def test_finance_downloads_from_configured_stem_and_caches(tmp_path, monkeypatch, subject, stem):
    monkeypatch.chdir(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(stem.lower() + '.csv', b'UNITID\n123456\n')
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
    scrape_ipeds_data(subject, 2024, see_progress=False)
    scrape_ipeds_data(subject, 2024, see_progress=False)
    assert urls == [f'https://nces.ed.gov/ipeds/complete-data-files/{stem}.zip']
    assert (tmp_path / f'{subject}data' / f'{subject}_2024.csv').exists()
