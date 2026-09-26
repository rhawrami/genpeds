"""First/second-major selection without inventing pre-2001 major order."""

import pandas as pd
import pytest

from genpeds import Characteristics, Cip, Completion
from genpeds.cleaners import clean_completion
from genpeds.downloader import get_year_iter


def write_completion(folder, year, rows):
    folder.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(folder / f'completion_{year}.csv', index=False)


def test_completion_first_second_and_legacy_unknown(tmp_path):
    directory = tmp_path / 'completiondata'
    write_completion(directory, 2000, {
        'UNITID': ['100001'], 'CIPCODE': ['01.0101'], 'AWLEVEL': ['5'],
        'CRACE15': ['30'], 'CRACE16': ['50']
    })
    write_completion(directory, 2001, {
        'UNITID': ['100001', '100001'], 'CIPCODE': ['01.0101', '01.0101'],
        'AWLEVEL': ['5', '5'], 'MAJORNUM': ['1', '2'],
        'CRACE15': ['10', '2'], 'CRACE16': ['20', '4']
    })
    both = Completion((2000, 2001)).clean(complete_dir=str(directory))
    assert both[['year', 'major_type']].values.tolist() == [
        [2000, 'unspecified'], [2001, 'both']
    ]
    assert both['totmen'].tolist() == [30, 12]
    assert both['totwomen'].tolist() == [50, 24]
    assert set(both.columns) == set(Completion().get_available_vars()) - {
        'wtmen', 'wtwomen', 'bkmen', 'bkwomen', 'hspmen', 'hspwomen',
        'asnmen', 'asnwomen', 'totwt_share', 'totbk_share',
        'tothsp_share', 'totasn_share'
    }

    assert Completion(2001).clean(complete_dir=str(directory), major='first')['totmen'].item() == 10
    assert Completion(2001).clean(complete_dir=str(directory), major='second')['totmen'].item() == 2
    with pytest.raises(ValueError, match='before 2001'):
        Completion((2000, 2001)).clean(complete_dir=str(directory), major='first')
    with pytest.raises(ValueError, match='before 2001'):
        Completion(2000).run(major='second')  # fail before a download


def test_completion_2025_major_options_and_enrichment(tmp_path, monkeypatch):
    assert get_year_iter('completion')[-1] == 2025
    monkeypatch.chdir(tmp_path)
    write_completion(tmp_path / 'completiondata', 2025, {
        'UNITID': ['100001', '100001'], 'CIPCODE': ['01.0101', '01.0101'],
        'AWLEVEL': ['5', '5'], 'MAJORNUM': ['1', '2'],
        'CTOTALM': ['6', '1'], 'CTOTALW': ['7', '2']
    })
    calls = []
    monkeypatch.setattr(Completion, 'scrape', lambda self, see_progress=False:
                        calls.append(('completion', see_progress)))
    monkeypatch.setattr(Characteristics, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100001'], 'year': [2025], 'name': ['Example College']}))
    monkeypatch.setattr(Cip, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'cip': ['01.0101'], 'year': [2025],
                                      'cip_description': ['Agricultural Business']}))
    result = Completion(2025).run(major='second', merge_with_char=True)
    assert result.loc[0, 'totmen'] == 1
    assert result.loc[0, 'major_type'] == 'second'
    assert result.loc[0, 'name'] == 'Example College'
    assert result.loc[0, 'cip_description'] == 'Agricultural Business'
    assert calls == [('completion', False)]


def test_completion_invalid_major(tmp_path):
    directory = tmp_path / 'completiondata'
    directory.mkdir()
    with pytest.raises(ValueError, match='major must'):
        clean_completion(completion_dir=str(directory), major='third')
