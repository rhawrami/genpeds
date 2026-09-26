"""IPEDS Academic Libraries fiscal-year collections, services, staffing and costs.

The annual AL series begins in 2014 and ends in 2024. Earlier ALS surveys are
separate biennial collections, not earlier observations of this AL schema.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd

from genpeds.downloader import get_year_iter


# raw measure -> (public column, source X flag); calculated LSWMSOM has no flag.
LIBRARY_FIELDS = {
    'lpbooks': ('physical_books', 'xlpbooks'),
    'lebooks': ('electronic_books', 'xlebooks'),
    'ledatab': ('electronic_databases', 'xledatab'),
    'lpmedia': ('physical_media', 'xlpmedia'),
    'lemedia': ('electronic_media', 'xlemedia'),
    'lpseria': ('physical_serials', 'xlpseria'),
    'leseria': ('electronic_serials', 'xleseria'),
    'lpcllct': ('physical_collections', 'xlpcollc'),
    'lecllct': ('electronic_collections', 'xlecollc'),
    'ltcllct': ('total_collections', 'xltcllct'),
    'lpcrclt': ('physical_circulations', 'xlpcrclt'),
    'lecrclt': ('electronic_circulations', 'xlecrclt'),
    'ltcrclt': ('total_circulations', 'xltcrclt'),
    'lilldpr': ('interlibrary_loans_provided', 'xlilldpr'),
    'lilldrc': ('interlibrary_loans_received', 'xlilldrc'),
    'lstotal': ('staff_fte', 'xlstotal'),
    'lslibrn': ('librarians_fte', 'xlslibrn'),
    'lsoprof': ('other_professionals_fte', 'xlsoprof'),
    'lsopaid': ('other_paid_staff_fte', 'xlsopaid'),
    'lsstast': ('student_assistants_fte', 'xlsstast'),
    'lbranch': ('branch_libraries', 'xlbranch'),
    'lsalwag': ('salaries_wages', 'xsalwag'),
    'lfrngbn': ('fringe_benefits', 'xlfrngbn'),
    'lexmsbb': ('one_time_materials', 'xlexmsbb'),
    'lexmscs': ('subscriptions', 'xlexmscs'),
    'lexmsot': ('other_materials_services', 'xlexmsot'),
    'lexmstl': ('materials_services_total', 'xlexmstl'),
    'lexomps': ('preservation', 'xlexomps'),
    'lexomot': ('other_operations_maintenance', 'xlexomot'),
    'lexomtl': ('operations_maintenance_total', 'xlexomtl'),
    'lexptot': ('total_expenditures', 'xlexptot'),
    'lswmsom': ('expenditures_excluding_fringe', None),
}
LIBRARY_SCREENS = {
    'lexp100k': 'expenditure_threshold',
    'lcolelyn': 'electronic_only_collection',
    'lilldyn': 'interlibrary_loan_services',
    'lilsyn': 'has_library_staff',
    'lfrngbyn': 'fringe_from_library_budget',
    'lsuppvrs': 'virtual_reference_services',
}
LIBRARY_SCREEN_YEARS = {
    'lexp100k': (2019, 2024), 'lilldyn': (2016, 2024),
    'lilsyn': (2020, 2024), 'lsuppvrs': (2014, 2015),
}
LIBRARY_FIELD_YEARS = {
    'lpseria': 2016, 'leseria': 2016,
    'ltcllct': 2015, 'ltcrclt': 2015,
    **{raw: 2020 for raw in ('lstotal', 'lslibrn', 'lsoprof', 'lsopaid', 'lsstast')},
}
LIBRARY_META = {
    'id': 'Institutional UNITID string.',
    'year': 'Fiscal year ending in this calendar year; AL2024 is fiscal 2024 (2024-25 collection).',
    'collection_total_definition': '2014-2018 source physical/electronic collection totals omit serials; 2019-2024 include them.',
}
LIBRARY_DESCRIPTIONS = {
    'physical_books': 'Number of physical books (LPBOOKS); collection counts, not circulation.',
    'electronic_books': 'Number of digital/electronic books (LEBOOKS); licensed access can be included.',
    'electronic_databases': 'Number of digital/electronic databases (LEDATAB).',
    'physical_media': 'Number of physical media (LPMEDIA).',
    'electronic_media': 'Number of digital/electronic media (LEMEDIA).',
    'physical_serials': 'Number of physical serials (LPSERIA), available from 2016.',
    'electronic_serials': 'Number of electronic serials (LESERIA), available from 2016.',
    'physical_collections': 'Source calculated LPCLLCT: books/media through 2018; includes serials from 2019.',
    'electronic_collections': 'Source calculated LECLLCT: books/databases/media through 2018; includes e-serials from 2019.',
    'total_collections': 'Source calculated physical + electronic collection total (LTCLLCT), from 2015; inherits the 2019 serials break.',
    'physical_circulations': 'Physical books/media circulations (LPCRCLT), not holdings.',
    'electronic_circulations': 'Electronic book/media circulations (LECRCLT); definitions and vendor reporting can vary.',
    'total_circulations': 'Source calculated physical + electronic circulation total (LTCRCLT), from 2015.',
    'interlibrary_loans_provided': 'Interlibrary loans/documents supplied to other libraries (LILLDPR).',
    'interlibrary_loans_received': 'Filled interlibrary loans/documents received from other libraries (LILLDRC).',
    'staff_fte': 'Total library staff full-time equivalents (LSTOTAL), including student assistants, from 2020; not HR headcount.',
    'librarians_fte': 'Librarian full-time equivalents (LSLIBRN), from 2020.',
    'other_professionals_fte': 'Other professional full-time equivalents (LSOPROF), from 2020.',
    'other_paid_staff_fte': 'Other paid staff FTE except student assistants (LSOPAID), from 2020.',
    'student_assistants_fte': 'Student assistant full-time equivalents (LSSTAST), from 2020.',
    'branch_libraries': 'Number of branches and independent libraries (LBRANCH).',
    'salaries_wages': 'Salaries and wages paid from the library budget (LSALWAG); nominal dollars.',
    'fringe_benefits': 'Fringe benefits paid from the library budget (LFRNGBN); nominal dollars.',
    'one_time_materials': 'One-time books/backfiles/other materials expenditure (LEXMSBB); nominal dollars.',
    'subscriptions': 'Ongoing subscription commitments (LEXMSCS); nominal dollars.',
    'other_materials_services': 'Other materials/services spending (LEXMSOT); nominal dollars.',
    'materials_services_total': 'Source total materials/services expenditure (LEXMSTL); includes its detail fields.',
    'preservation': 'Preservation services spending (LEXOMPS); nominal dollars.',
    'other_operations_maintenance': 'Other operations and maintenance spending (LEXOMOT); nominal dollars.',
    'operations_maintenance_total': 'Source total operations and maintenance spending (LEXOMTL); includes its detail fields.',
    'total_expenditures': 'Source calculated library expenses including fringe (LEXPTOT); nominal dollars. Detailed reporting requires the $100k threshold.',
    'expenditures_excluding_fringe': 'Source calculated LSWMSOM = salaries/wages + materials/services + operations/maintenance; excludes fringe, no X flag.',
}
LIBRARY_VARIABLES = {**LIBRARY_META}
for _source, _name in LIBRARY_SCREENS.items():
    LIBRARY_VARIABLES[_name + '_code'] = (
        f'Original {_source.upper()} code: 1 yes, 2 no, -2 not applicable (where supplied).')
    LIBRARY_VARIABLES[_name] = (
        f'Readable label for {_source.upper()} (yes/no/not applicable); absent before the source field exists.')
LIBRARY_VARIABLES.update({
    'expenditure_threshold_code': 'NCES LEXP100K from 2019: 1 expenses at least $100,000, 2 below $100,000; absent earlier.',
    'expenditure_threshold': 'Whether annual library expenses reach $100,000 (yes/no), from 2019; earlier years unknown.',
    'electronic_only_collection': 'Whether all library collections are digital/electronic (LCOLELYN yes/no).',
    'interlibrary_loan_services': 'Whether interlibrary loan services are provided (LILLDYN yes/no), from 2016.',
    'has_library_staff': 'Whether the institution has library staff (LILSYN yes/no), from 2020.',
    'fringe_from_library_budget': 'Whether fringe benefits are paid from the library budget (LFRNGBYN yes/no/not applicable).',
    'virtual_reference_services': 'Whether virtual reference services are supported (LSUPPVRS), only 2014-15.',
})
for _raw, (_name, _flag) in LIBRARY_FIELDS.items():
    LIBRARY_VARIABLES[_name] = LIBRARY_DESCRIPTIONS[_name]
    if _flag:
        LIBRARY_VARIABLES[_name + '_status'] = (
            f'Original NCES {_flag.upper()} reporting/imputation flag for {_name}.')


def clean_academic_libraries(
        libraries_dir: str = 'academic_librariesdata',
        year_range: Optional[Union[Tuple[int, int], List[int], int]] = None) -> pd.DataFrame:
    """Read AL institution-years, retaining source screens and X flags."""
    requested = set(get_year_iter('academic_libraries', year_range)) if year_range is not None else None
    directory = Path(libraries_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f'No Academic Libraries cache directory: {directory}')
    raw = {'unitid', *LIBRARY_FIELDS, *LIBRARY_SCREENS,
           *(flag for _, flag in LIBRARY_FIELDS.values() if flag)}
    frames, found = [], set()
    for file in sorted(directory.iterdir()):
        match = re.fullmatch(r'academic_libraries_(\d{4})\.csv', file.name,
                             flags=re.IGNORECASE)
        if not match:
            continue
        year = int(match.group(1))
        if not 2014 <= year <= 2024 or (requested is not None and year not in requested):
            continue
        data = pd.read_csv(file, dtype=str, index_col=False, low_memory=False,
                           usecols=lambda col: col.strip().lower() in raw)
        data.columns = data.columns.str.strip().str.lower()
        if data.columns.duplicated().any():
            raise ValueError(f'{file} contains duplicate Academic Libraries columns')
        required = {'unitid', 'lpbooks', 'lexptot', 'lswmsom'}
        if not required.issubset(data.columns):
            raise ValueError(f'{file} is missing Academic Libraries fields: {sorted(required - set(data.columns))}')
        identifiers = data['unitid'].astype('string').str.strip()
        if identifiers.isna().any() or identifiers.eq('').any() or identifiers.duplicated().any():
            raise ValueError(f'{file} has missing or duplicate UNITIDs')
        output = pd.DataFrame({
            'id': identifiers, 'year': year,
            'collection_total_definition': ('excludes_serials_2014_2018' if year < 2019
                                            else 'includes_serials_2019_2024'),
        })
        for source, name in LIBRARY_SCREENS.items():
            start, end = LIBRARY_SCREEN_YEARS.get(source, (2014, 2024))
            code = (data[source].astype('string').str.strip()
                    if start <= year <= end and source in data else
                    pd.Series(pd.NA, index=data.index, dtype='string'))
            output[name + '_code'] = code
            output[name] = code.map({'1': 'yes', '2': 'no', '-2': 'not_applicable'}).astype('string')
        for source, (name, flag) in LIBRARY_FIELDS.items():
            available = year >= LIBRARY_FIELD_YEARS.get(source, 2014)
            output[name] = (pd.to_numeric(data[source], errors='coerce')
                            if available and source in data else
                            pd.Series(float('nan'), index=data.index))
            if flag:
                output[name + '_status'] = (data[flag].astype('string').str.strip()
                                            if available and flag in data else
                                            pd.Series(pd.NA, index=data.index, dtype='string'))
        frames.append(output)
        found.add(year)
    if requested is not None and requested - found:
        raise FileNotFoundError(f'Missing downloaded Academic Libraries fiscal years: {sorted(requested - found)}')
    if not frames:
        raise FileNotFoundError(f'No Academic Libraries CSV files found in {directory}')
    return pd.concat(frames, ignore_index=True).reindex(columns=list(LIBRARY_VARIABLES))
