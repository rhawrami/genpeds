"""Curated IPEDS Finance fiscal-year statements by accounting form.

Amounts are nominal institutional dollars. Form- and era-specific accounting
rules are part of the data: shared column names do not create a historical
GASB/FASB crosswalk.
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd

from genpeds.downloader import get_year_iter


FINANCE_FORMS = {'f1a': 'finance', 'f2': 'finance_f2', 'f3': 'finance_f3'}
ACCOUNTING_BASIS = {
    'f1a': 'public_gasb',
    'f2': 'nonprofit_or_public_fasb',
    'f3': 'for_profit_fasb',
}

# Explicit dictionary-checked source concepts, not an automated label match.
# F1A's revenues include other additions; F2/F3 include investment return.
FINANCE_FIELDS = {
    'f1a': {
        'f1a06': 'total_assets', 'f1a13': 'total_liabilities',
        'f1a18': 'net_position', 'f1b01': 'net_tuition_fees',
        'f1e08': 'tuition_discounts', 'f1b09': 'operating_revenues',
        'f1b19': 'nonoperating_revenues', 'f1b25': 'revenues_and_additions',
        'f1c011': 'instruction_expenses', 'f1c191': 'total_expenses',
        'f1b11': 'state_appropriations', 'f1e12': 'pell_discounts',
    },
    'f2': {
        'f2a02': 'total_assets', 'f2a03': 'total_liabilities',
        'f2a06': 'net_assets', 'f2d01': 'net_tuition_fees',
        'f2c08': 'tuition_discounts', 'f2d16': 'revenues_and_investment_return',
        'f2e011': 'instruction_expenses', 'f2e131': 'total_expenses',
        'f2d03': 'state_appropriations', 'f2c12': 'pell_discounts',
    },
    'f3': {
        'f3a01': 'total_assets', 'f3a02': 'total_liabilities',
        'f3a03': 'equity', 'f3d01': 'net_tuition_fees',
        'f3c06': 'tuition_discounts', 'f3d09': 'revenues_and_investment_return',
        'f3e011': 'instruction_expenses', 'f3b02': 'total_expenses',
        'f3e071': 'functional_expenses',
        'f3d03a': 'state_appropriations', 'f3c12': 'pell_discounts',
    },
}

FINANCE_MEASURES = dict.fromkeys(
    name for fields in FINANCE_FIELDS.values() for name in fields.values())
FINANCE_META = {
    'id': 'Institutional UNITID string; a form-specific institution/fiscal-year key.',
    'year': 'Fiscal year ending in this calendar year (F2324 describes fiscal year 2024).',
    'form': 'NCES Finance accounting form: f1a, f2 or f3. Different forms are not additive.',
    'accounting_basis': 'F1A public GASB; F2 nonprofit and some public FASB; F3 for-profit FASB.',
    'accounting_regime': '2004-09 prealigned, 2010+ aligned, with F3 redesigned from fiscal 2014; use with form to interpret trends.',
    'source_stem': 'Exact NCES file stem for the fiscal year and form.',
}
FINANCE_VARIABLES = {
    **FINANCE_META,
    'total_assets': 'Year-end assets in nominal dollars; values and valuation rules differ by accounting form.',
    'total_liabilities': 'Year-end liabilities in nominal dollars; GASB pension/OPEB rules also change over time.',
    'net_position': 'F1A public GASB net position (F1A18; earlier dictionaries call it total net assets); not FASB equity.',
    'net_assets': 'F2 nonprofit/some public FASB net assets (F2A06).',
    'equity': 'F3 for-profit FASB equity (F3A03).',
    'net_tuition_fees': 'Tuition and fees after discounts/allowances (F1B01/F2D01/F3D01), not published tuition or student net price.',
    'tuition_discounts': 'Scholarship/aid discounts applied to tuition and fees (F1E08/F2C08/F3C06); do not add to net tuition as independent revenue.',
    'operating_revenues': 'F1A public GASB operating revenues (F1B09); government appropriations are generally nonoperating.',
    'nonoperating_revenues': 'F1A public GASB nonoperating revenues (F1B19).',
    'revenues_and_additions': 'F1A public GASB total revenues and other additions (F1B25), including capital/endowment additions.',
    'revenues_and_investment_return': 'F2/F3 FASB total revenues and investment return (F2D16/F3D09); not the F1A other-additions total.',
    'instruction_expenses': 'Functional instruction expenses (F1C011/F2E011/F3E011), available on F3 from fiscal 2014; form/era definitions differ.',
    'total_expenses': 'F1A expenses and deductions (F1C191); F2 expenses (F2E131); F3 statement expenses (F3B02, not applicable for some F3 reporters).',
    'functional_expenses': 'F3 total expenses by function (F3E071), fiscal 2014 onward. Differs from F3B02 for some reporters; no automatic substitution.',
    'state_appropriations': 'Source state appropriations (F1B11/F2D03/F3D03A where present), not all state grants and contracts.',
    'pell_discounts': 'Total discounts/allowances funded by Pell grants (F1E12/F2C12/F3C12); first collected in fiscal 2020.',
}
for _name in FINANCE_MEASURES:
    FINANCE_VARIABLES[_name + '_status'] = (
        f'NCES X* reporting/imputation flag for {_name}; codes depend on the source-year dictionary.')


def form_vars(form: str):
    """Columns applicable to one form (some begin partway through its history)."""
    if form not in FINANCE_FORMS:
        raise ValueError(f'form must be one of {sorted(FINANCE_FORMS)} or all')
    names = set(FINANCE_FIELDS[form].values())
    return {name: description for name, description in FINANCE_VARIABLES.items()
            if name in FINANCE_META or name in names or
            (name.endswith('_status') and name.removesuffix('_status') in names)}


def _regime(form: str, year: int) -> str:
    if year < 2010:
        return 'prealigned_2004_2009'
    if form == 'f3' and year >= 2014:
        return 'aligned_f3_revised_2014_onward'
    return 'aligned_2010_onward'


def clean_finance(form: str = 'all',
                  year_range: Optional[Union[Tuple[int, int], List[int], int]] = None,
                  finance_dir: Optional[str] = None) -> pd.DataFrame:
    """Read selected form caches; preserve missing values and original X flags.

    ``finance_dir`` overrides the selected form's cache for local/offline work.
    For ``form='all'``, each form uses its own standard directory.
    """
    if form != 'all' and form not in FINANCE_FORMS:
        raise ValueError(f'form must be one of {sorted(FINANCE_FORMS)} or all')
    if form == 'all' and finance_dir is not None:
        raise ValueError("finance_dir requires a single form; 'all' has three cache directories")
    years = set(get_year_iter('finance', year_range)) if year_range is not None else None
    forms = FINANCE_FORMS if form == 'all' else {form: FINANCE_FORMS[form]}
    with (Path(__file__).parent / 'cfg.json').open(encoding='utf-8') as handle:
        cfg = json.load(handle)
    frames = []
    for selected, subject in forms.items():
        directory = Path(finance_dir or f'{subject}data')
        if not directory.is_dir():
            raise FileNotFoundError(f'No {selected} Finance cache directory: {directory}')
        found = set()
        fields = FINANCE_FIELDS[selected]
        raw = {'unitid', *fields, *('x' + source for source in fields)}
        for file in sorted(directory.iterdir()):
            match = re.fullmatch(rf'{subject}_(\d{{4}})\.csv', file.name, flags=re.IGNORECASE)
            if not match:
                continue
            year = int(match.group(1))
            if not 2004 <= year <= 2024 or (years is not None and year not in years):
                continue
            data = pd.read_csv(file, dtype=str, index_col=False, low_memory=False,
                               usecols=lambda col: col.strip().lower() in raw)
            data.columns = data.columns.str.strip().str.lower()
            if data.columns.duplicated().any():
                raise ValueError(f'{file} contains duplicate Finance columns after trimming')
            required = {'unitid', *(source for source, name in fields.items()
                                    if name in ('total_assets', 'net_tuition_fees', 'total_expenses'))}
            if not required.issubset(data.columns):
                raise ValueError(f'{file} is missing Finance fields: {sorted(required - set(data.columns))}')
            identifiers = data['unitid'].astype('string').str.strip()
            if identifiers.isna().any() or identifiers.eq('').any() or identifiers.duplicated().any():
                raise ValueError(f'{file} has missing or duplicate UNITIDs within its accounting form')
            output = pd.DataFrame({'id': identifiers, 'year': year, 'form': selected,
                                   'accounting_basis': ACCOUNTING_BASIS[selected],
                                   'accounting_regime': _regime(selected, year),
                                   'source_stem': cfg[subject]['endpoints'][str(year)]})
            for source, name in fields.items():
                # These concepts were not collected before their documented introductions.
                applicable = not ((name == 'pell_discounts' and year < 2020) or
                                  (selected == 'f3' and name in ('instruction_expenses',
                                                                 'functional_expenses')
                                   and year < 2014))
                output[name] = (pd.to_numeric(data[source], errors='coerce')
                                if applicable and source in data else
                                pd.Series(float('nan'), index=data.index))
                flag = 'x' + source
                output[name + '_status'] = (data[flag].astype('string').str.strip()
                                            if applicable and flag in data else
                                            pd.Series(pd.NA, index=data.index, dtype='string'))
            frames.append(output)
            found.add(year)
        if years is not None and years - found:
            raise FileNotFoundError(f'Missing downloaded {selected} Finance fiscal years: {sorted(years - found)}')
    if not frames:
        raise FileNotFoundError('No Finance CSV files found for the selected forms/years')
    result = pd.concat(frames, ignore_index=True)
    # A stable schema allows comparison without accidentally interpreting absent
    # F1A/F2/F3-specific fields as zero; every measure has a matching flag.
    return result.reindex(columns=list(FINANCE_VARIABLES))
