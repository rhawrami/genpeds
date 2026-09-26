"""Year-aware cleaners for the seven modern IPEDS HR file families.

These files have different row grains. Their NCES total, occupation, tenure,
rank, and contract categories overlap; the cleaners preserve rows and source
codes rather than summing them into a misleading institution total.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
import re
from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from genpeds.downloader import get_year_iter


HR_DATASETS = {
    'staff': 'human_resources',
    'employees': 'hr_employees',
    'instructional_staff': 'hr_instructional_staff',
    'faculty_ranks': 'hr_faculty_ranks',
    'new_hires': 'hr_new_hires',
    'instructional_salaries': 'hr_instructional_salaries',
    'noninstructional_salaries': 'hr_noninstructional_salaries',
}

HR_PEOPLE = {'hrtotlt': 'people_total', 'hrtotlm': 'men', 'hrtotlw': 'women'}
for code, name in {
    'hraian': 'american_indian', 'hrasia': 'asian', 'hrbkaa': 'black',
    'hrhisp': 'hispanic', 'hrnhpi': 'pacific_islander', 'hrwhit': 'white',
    'hr2mor': 'two_or_more', 'hrunkn': 'race_unknown',
    'hrnral': 'nonresident',
}.items():
    HR_PEOPLE.update({code + suffix: name + '_' + target
                      for suffix, target in (('t', 'total'), ('m', 'men'), ('w', 'women'))})

HR_EMPLOYEES = {
    'eaptot': 'employees_total', 'eaptyp': 'employees_nonmedical',
    'eapmed': 'employees_medical', 'eapft': 'full_time_total',
    'eapfttyp': 'full_time_nonmedical', 'eapftmed': 'full_time_medical',
    'eappt': 'part_time_total', 'eappttyp': 'part_time_nonmedical',
    'eapptmed': 'part_time_medical',
}

HR_FACULTY_RANKS = {
    'sistotl': 'faculty_total', 'sisprof': 'professors',
    'sisascp': 'associate_professors', 'sisastp': 'assistant_professors',
    'sisinst': 'instructors', 'sislect': 'lecturers', 'sisnork': 'no_rank',
}

HR_SALARIES = {}
for suffix, group in (('t', 'total'), ('m', 'men'), ('w', 'women')):
    HR_SALARIES.update({
        'satotl' + suffix: 'staff_9to12_' + group,
        'sainst' + suffix: 'instructional_staff_' + group,
        'sa_9mc' + suffix: 'staff_under9_' + group,
        'saoutl' + suffix: 'salary_outlay_' + group,
        'saeq9a' + suffix: 'equated_9_month_salary_' + group,
        'saeq9o' + suffix: 'equated_9_month_outlay_' + group,
        'saavmn' + suffix: 'average_months_' + group,
        'samnth' + suffix: 'months_worked_' + group,
    })
    for months in (9, 10, 11, 12):
        code = f'{months:02d}'
        HR_SALARIES['sa' + code + 'mc' + suffix] = f'staff_{months}_month_{group}'
        HR_SALARIES['sa' + code + 'mo' + suffix] = f'salary_outlay_{months}_month_{group}'
        HR_SALARIES['sa' + code + 'ma' + suffix] = f'average_salary_{months}_month_{group}'

HR_FIELDS = {
    'staff': HR_PEOPLE,
    'instructional_staff': HR_PEOPLE,
    'new_hires': HR_PEOPLE,
    'employees': HR_EMPLOYEES,
    'faculty_ranks': HR_FACULTY_RANKS,
    'instructional_salaries': HR_SALARIES,
}

HR_CATEGORY_FIELDS = {
    'staff': {'staffcat': 'category', 'occupcat': 'occupation', 'ftpt': 'attendance'},
    'employees': {'eapcat': 'category', 'occupcat': 'occupation',
                  'facstat': 'faculty_status'},
    'instructional_staff': {'siscat': 'category', 'facstat': 'faculty_status',
                            'arank': 'rank'},
    'faculty_ranks': {'facstat': 'faculty_status'},
    'new_hires': {'snhcat': 'category', 'occupcat': 'occupation',
                  'facstat': 'faculty_status'},
    'instructional_salaries': {'arank': 'rank'},
}
HR_CODE_OUTPUT = {'category': ('category_code', 'category_label'),
                  'occupation': ('occupation_code', 'occupation_label'),
                  'faculty_status': ('faculty_status_code', 'faculty_status_label'),
                  'attendance': ('ftpt_code', 'ftpt_label'),
                  'rank': ('rank_code', 'rank_label')}


HR_VARIABLES = {
    'id': 'Institutional UNITID identifier.',
    'year': 'Fall staff snapshot year or starting year of the instructional/noninstructional salary academic year (2012-2024).',
    'dataset': 'Selected HR file family; row grain and reporting population depend on this value.',
    'category_code': 'Original EAPCAT/STAFFCAT/SISCAT/SNHCAT code; total and detail codes can overlap.',
    'category_label': 'Year-specific NCES dictionary label for category_code.',
    'occupation_code': 'Original OCCUPCAT or noninstructional salary occupation code (01-14).',
    'occupation_label': 'Year-specific NCES dictionary label for occupation_code.',
    'faculty_status_code': 'Original FACSTAT code; totals and tenure/contract subcategories can overlap.',
    'faculty_status_label': 'Year-specific NCES dictionary label for faculty_status_code.',
    'ftpt_code': 'Original FTPT code; 1 all staff, 2 full-time, 3 part-time, 4 graduate assistants.',
    'ftpt_label': 'Year-specific NCES dictionary label for ftpt_code.',
    'rank_code': 'Original ARANK code; all-ranks code is 0 in staff counts versus 7 in salaries.',
    'rank_label': 'Year-specific NCES dictionary label for rank_code.',
    'women_share': 'Women / (men + women) × 100 within the selected staff/category row; denominator zero gives missing.',
    'hire_window_months': '4 for 2012-17 new-hire cohorts (July-October); 12 from 2018 (previous November-current October).',
    'hire_period_start_year': 'Starting calendar year of the reported new-hire window.',
    'academic_year_end': 'Ending year of the salary academic year (year plus one).',
    'salary_regime': '2012-2015 weighted-month versus 2016-onward explicit-month salary collection; nine-month-equivalent pay is not provided in 2012-15 files.',
    'staff_count': 'Full-time noninstructional staff count for this occupation (SANIN01-14); code 01 is an overlapping total.',
    'salary_outlay': 'Annual noninstructional salary outlay for this occupation in nominal dollars (SANIT01-14); no sex breakdown.',
    'staff_count_status': 'Source XSANIN## reporting/imputation status for staff_count.',
    'salary_outlay_status': 'Source XSANIT## reporting/imputation status for salary_outlay.',
}
for dataset, fields in HR_FIELDS.items():
    for raw, name in fields.items():
        if name not in HR_VARIABLES:
            note = (' Counts people in the selected occupational/faculty/new-hire row.'
                    if dataset in ('staff', 'instructional_staff', 'new_hires',
                                   'employees', 'faculty_ranks') else
                    ' Source annual pay/contract measure; compare within the specified salary regime.')
            HR_VARIABLES[name] = name.replace('_', ' ').capitalize() + f' (NCES {raw.upper()}).' + note
        HR_VARIABLES[name + '_status'] = f'NCES X{raw.upper()} reporting/imputation status for {name}.'


def dataset_vars(dataset):
    '''Return documented columns for a particular HR dataset.'''
    if dataset not in HR_DATASETS:
        raise ValueError(f'dataset must be one of {sorted(HR_DATASETS)}')
    fields = HR_FIELDS.get(dataset, {})
    keys = {'id', 'year', 'dataset', *fields.values(),
            *(name + '_status' for name in fields.values())}
    for category in HR_CATEGORY_FIELDS.get(dataset, {}).values():
        keys.update(HR_CODE_OUTPUT[category])
    if dataset in ('staff', 'instructional_staff', 'new_hires'):
        keys.add('women_share')
    if dataset == 'new_hires':
        keys.update(('hire_window_months', 'hire_period_start_year'))
    if dataset in ('instructional_salaries', 'noninstructional_salaries'):
        keys.add('academic_year_end')
    if dataset == 'instructional_salaries':
        keys.add('salary_regime')
    if dataset == 'noninstructional_salaries':
        keys.update(('occupation_code', 'occupation_label', 'staff_count',
                     'staff_count_status', 'salary_outlay', 'salary_outlay_status'))
    return {name: HR_VARIABLES[name] for name in HR_VARIABLES if name in keys}


@lru_cache(maxsize=1)
def _labels():
    with (Path(__file__).parent / 'hr_labels.json').open(encoding='utf-8') as handle:
        return json.load(handle)


def _numeric_fields(frame, raw_fields):
    for source, name in raw_fields.items():
        frame[name] = pd.to_numeric(frame[source], errors='coerce')
        frame[name + '_status'] = frame['x' + source].astype('string').str.strip()
    return frame


def clean_human_resources(dataset: str = 'staff',
                          hr_dir: Optional[str] = None,
                          year_range: Optional[Union[Tuple[int, int], List[int], int]] = None,
                          category_codes: Optional[List[str]] = None) -> pd.DataFrame:
    '''Clean modern HR source records without aggregating overlapping rows.'''
    if dataset not in HR_DATASETS:
        raise ValueError(f'dataset must be one of {sorted(HR_DATASETS)}')
    subject = HR_DATASETS[dataset]
    requested = set(get_year_iter(subject, year_range)) if year_range is not None else None
    if category_codes is not None:
        if not isinstance(category_codes, list) or any(not isinstance(x, (str, int)) for x in category_codes):
            raise TypeError('category_codes must be a list of category-code strings or integers')
        category_codes = {str(x).strip() for x in category_codes}
    directory = hr_dir or f'{subject}data'
    fields = HR_FIELDS.get(dataset, {})
    categories = HR_CATEGORY_FIELDS.get(dataset, {})
    raw = {'unitid', *fields, *('x' + name for name in fields), *categories}
    if dataset == 'noninstructional_salaries':
        raw |= {f'{stem}{num:02d}' for stem in ('sanin', 'sanit', 'xsanin', 'xsanit')
                for num in range(1, 15)}
    if dataset == 'noninstructional_salaries':
        category_field = None
    else:
        category_field = next(iter(categories))  # e.g. STAFFCAT, EAPCAT, SISCAT
    if dataset == 'faculty_ranks':
        category_field = 'facstat'
    if dataset == 'instructional_salaries':
        category_field = 'arank'

    frames = []
    found = set()
    for file in sorted(os.listdir(directory)):
        match = re.fullmatch(rf'{subject}_(\d{{4}})\.csv', file, flags=re.IGNORECASE)
        if not match:
            continue
        year = int(match.group(1))
        if requested is not None and year not in requested:
            continue
        if not 2012 <= year <= 2024:
            continue
        df = pd.read_csv(os.path.join(directory, file), dtype=str, index_col=False,
                         low_memory=False, usecols=lambda col: col.lower().strip() in raw)
        df.columns = df.columns.str.lower().str.strip()
        required = {'unitid', *categories}
        if dataset == 'noninstructional_salaries':
            required |= {'sanin01', 'sanit01'}
        elif dataset in ('staff', 'instructional_staff', 'new_hires'):
            required |= {'hrtotlt', 'hrtotlm', 'hrtotlw'}
        elif dataset == 'employees':
            required |= {'eaptot', 'eapft', 'eappt'}
        elif dataset == 'faculty_ranks':
            required.add('sistotl')
        else:
            required |= {'satotlt', 'saoutlt'}
        if not required.issubset(df.columns):
            raise ValueError(f'{file} is missing HR fields: {sorted(required - set(df.columns))}')
        df = df.reindex(columns=sorted(raw))
        df['unitid'] = df['unitid'].str.strip()

        if dataset == 'noninstructional_salaries':
            chunks = []
            for num in range(1, 15):
                code = f'{num:02d}'
                if category_codes is not None and code not in category_codes:
                    continue
                counts, dollars = f'sanin{code}', f'sanit{code}'
                output = pd.DataFrame({'id': df['unitid'], 'year': year,
                                       'dataset': dataset,
                                       'academic_year_end': year + 1,
                                       'occupation_code': code,
                                       'occupation_label': _labels()[dataset][str(year)]['occupation'][code]})
                output['staff_count'] = pd.to_numeric(df[counts], errors='coerce')
                output['staff_count_status'] = df['x' + counts].astype('string').str.strip()
                output['salary_outlay'] = pd.to_numeric(df[dollars], errors='coerce')
                output['salary_outlay_status'] = df['x' + dollars].astype('string').str.strip()
                chunks.append(output)
            if chunks:
                frames.append(pd.concat(chunks, ignore_index=True))
        else:
            if category_codes is not None:
                df = df.loc[df[category_field].astype('string').str.strip().isin(category_codes)].copy()
            output = pd.DataFrame({'id': df['unitid'], 'year': year, 'dataset': dataset})
            for source, category in categories.items():
                raw_code, label = HR_CODE_OUTPUT[category]
                output[raw_code] = df[source].astype('string').str.strip()
                code_labels = _labels()[dataset][str(year)][source]
                output[label] = output[raw_code].map(code_labels).astype('string')
            measures = _numeric_fields(df.copy(), fields)
            output = output.join(measures.loc[:, [
                *fields.values(), *(name + '_status' for name in fields.values())]])
            if dataset in ('staff', 'instructional_staff', 'new_hires'):
                output['women_share'] = (output['women'] /
                                         (output['men'] + output['women']).replace(0, np.nan) * 100)
            if dataset == 'new_hires':
                output['hire_window_months'] = 4 if year < 2018 else 12
                output['hire_period_start_year'] = year if year < 2018 else year - 1
            if dataset == 'instructional_salaries':
                output['academic_year_end'] = year + 1
                output['salary_regime'] = ('2012-2015_weighted_months' if year < 2016 else
                                           '2016_onward_explicit_months')
            frames.append(output)
        found.add(year)
    if requested is not None and requested - found:
        raise FileNotFoundError(f'Missing downloaded {dataset} HR years: {sorted(requested - found)}')
    if not frames:
        raise FileNotFoundError(f'No {dataset} HR CSV files found in {directory}')
    return pd.concat(frames, ignore_index=True)
