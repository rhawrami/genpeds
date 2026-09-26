"""Military benefit reporting is distinct from the main SFA cohort."""

import pandas as pd
import pytest

from genpeds import Characteristics, VeteransAid
from genpeds.downloader import get_year_iter


def test_veterans_aid_keeps_graduate_only_institutions(tmp_path):
    data = tmp_path / 'veterans_aiddata'
    data.mkdir()
    pd.DataFrame({
        'UNITID': ['100001', '100002'],
        'UGPO9_N': ['40', None], 'XUGPO9_N': ['R', 'A'],
        'GPO9_N': ['10', '16'], 'XGPO9_N': ['R', 'R'],
        'GPO9_T': ['18000', '32000'], 'GPO9_A': ['1800', '2000'],
        'UGDOD_N': ['3', None], 'GDOD_N': ['2', '5'],
        'GDOD_A   ': ['2000', '1200']
    }).to_csv(data / 'veterans_aid_2014.csv', index=False)
    result = VeteransAid(2014).clean(aid_dir=str(data))
    assert set(result.columns) == set(VeteransAid().get_available_vars())
    assert result['id'].tolist() == ['100001', '100002']
    assert result['aid_year_start'].tolist() == [2013, 2013]
    graduate_only = result.loc[result['id'] == '100002'].iloc[0]
    assert pd.isna(graduate_only.ug_post911_count)
    assert graduate_only.grad_post911_count == 16
    assert graduate_only.grad_post911_total == 32000
    assert graduate_only.grad_dod_avg == 1200
    assert graduate_only.grad_post911_count_status == 'R'


def test_veterans_aid_years_and_merge(tmp_path, monkeypatch):
    assert get_year_iter('veterans_aid') == list(range(2014, 2025))
    with pytest.raises(ValueError, match='2014-2024'):
        VeteransAid(2013)
    monkeypatch.chdir(tmp_path)
    data = tmp_path / 'veterans_aiddata'
    data.mkdir()
    pd.DataFrame({'unitid': ['100002'], 'ugpo9_n': [None],
                  'gpo9_n': ['16'], 'ugdod_n': [None], 'gdod_n': ['5']}
                 ).to_csv(data / 'veterans_aid_2024.csv', index=False)
    monkeypatch.setattr(VeteransAid, 'scrape', lambda self, see_progress=False: None)
    monkeypatch.setattr(Characteristics, 'run', lambda self, see_progress=False, rm_disk=False:
                        pd.DataFrame({'id': ['100002'], 'year': [2024], 'name': ['Example College']}))
    df = VeteransAid(2024).run(merge_with_char=True, rm_disk=True)
    assert df.loc[0, 'name'] == 'Example College'
    assert not data.exists()
