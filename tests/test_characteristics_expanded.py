"""Offline checks for historical and modern header-code harmonization."""

import pandas as pd
import pytest

from genpeds import Characteristics
from genpeds.core import _merge_characteristics
from genpeds.downloader import get_year_iter


def write_header(folder, year, rows):
    folder.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(folder / f'characteristics_{year}.csv', index=False)


def test_characteristics_codes_preserve_historical_meanings(tmp_path):
    data = tmp_path / 'characteristicsdata'
    common = {'UNITID': ['100001'], 'INSTNM': ['example college'],
              'ADDR': ['1 main st'], 'CITY': ['boston'], 'STABBR': ['MA'],
              'ZIP': ['02110']}
    write_header(data, 1984, {**common, 'CONTROL': ['2'], 'ICLEVEL': ['7']})
    write_header(data, 1993, {**common, 'CONTROL': ['2'], 'ICLEVEL': ['1'],
                              'SECTOR': ['2'], 'HBCU': [None], 'TRIBAL': [None]})
    write_header(data, 1995, {**common, 'CONTROL': ['2'], 'ICLEVEL': ['1'],
                              'HBCU': ['-1'], 'TRIBAL': ['1'], 'LOCALE': ['1']})
    write_header(data, 2005, {**common, 'CONTROL': ['1'], 'ICLEVEL': ['2'],
                              'HBCU': ['2'], 'TRIBAL': ['2'], 'DEGGRANT': ['1'],
                              'LOCALE': ['21'], 'SECTOR': ['4'], 'WEBADDR': ['example.edu']})
    write_header(data, 2025, {**common, 'CONTROL': ['3'], 'ICLEVEL': ['3'],
                              'HBCU': ['1'], 'TRIBAL': ['2'], 'DEGGRANT': ['2'],
                              'LOCALE': ['43'], 'SECTOR': ['9'], 'C21BASIC': ['15'],
                              'WEBADDR': ['example.edu'], 'LONGITUD': ['-71.0'],
                              'LATITUDE': ['42.0']})

    chars = Characteristics()
    result = chars.clean(char_dir=str(data)).set_index('year')
    assert set(result.reset_index().columns) == set(chars.get_available_vars())
    assert chars.get_available_years() == (1984, 2025)
    assert result.loc[1984, 'control'] == 'Private (profit status unspecified)'
    assert result.loc[1984, 'control_code'] == '2'
    assert pd.isna(result.loc[1984, 'level'])  # early 7 is not <2 years
    assert result.loc[1993, 'control'] == 'Private nonprofit'
    assert result.loc[1993, 'sector'] == 'Private nonprofit, four-year or above'
    assert not result.loc[1993, 'hbcu'] and not result.loc[1993, 'tribal']
    assert pd.isna(result.loc[1995, 'hbcu'])  # -1 is historical nonresponse
    assert result.loc[1995, 'tribal']
    assert result.loc[1995, 'locale_scheme'] == 'legacy'
    assert result.loc[2005, 'locale_scheme'] == 'urban_centric'
    assert result.loc[2005, 'degree_granting']
    assert not result.loc[2025, 'degree_granting']
    assert result.loc[2025, 'hbcu']
    assert result.loc[2025, 'carnegie_2021_basic_code'] == '15'
    assert result.loc[2025, 'longitude'] == '-71.0'


def test_characteristics_2025_year_and_selective_clean(tmp_path):
    assert get_year_iter('characteristics')[-1] == 2025
    with pytest.raises(ValueError, match='1984-2025'):
        get_year_iter('characteristics', 2026)
    data = tmp_path / 'characteristicsdata'
    write_header(data, 2025, {
        'unitid': ['100001'], 'instnm': ['example college'], 'addr': ['main st'],
        'city': ['boston'], 'stabbr': ['MA'], 'zip': ['02110'],
        'webaddr': ['example.edu'], 'longitud': ['-71.0'], 'latitude': ['42.0'],
        'control': ['-3'], 'iclevel': ['1'], 'hbcu': ['2'], 'tribal': ['2']
    })
    row = Characteristics(2025).clean(char_dir=str(data)).iloc[0]
    assert row.state == 'Massachusetts'
    assert pd.isna(row.control) and row.control_code == '-3'
    assert row['name'] == 'Example College'


def test_characteristics_merge_rejects_reused_unitid():
    observations = pd.DataFrame({'id': ['247719'], 'year': [1986], 'count': [10]})
    header = pd.DataFrame({'id': ['247719', '247719'], 'year': [1986, 1986],
                           'name': ['College A', 'College B']})
    with pytest.raises(ValueError, match='non-unique UNITIDs'):
        _merge_characteristics(observations, header)
