"""Regenerate the stand-alone API variable and configured-source CSVs.

Run `python codebook/build.py` in the development environment, or use
`python codebook/build.py --check` to check committed CSVs without writing.
Curated history and coding decisions live in harmonization.md / changes.csv;
configuration alone cannot prove per-institution coverage or comparability.
"""

import csv
import io
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

from genpeds.cleaners import (  # noqa: E402
    ADMISSION_CONSIDERATIONS, AID_FIELDS, COMPLETERS_FIELDS, DISTANCE_FIELDS, E12_FIELDS,
    GR200_FIELDS, GR200_FLAG_EXCEPTIONS, OM_FIELDS, TUITION_FIELDS,
    VARIABLE_RENAME, VETERANS_AID_FIELDS,
)


CONFIG = json.loads((ROOT / 'src/genpeds/cfg.json').read_text(encoding='utf-8'))
PUBLIC = {
    'characteristics': 'Characteristics', 'admissions': 'Admissions',
    'enrollment': 'Enrollment', 'distance_enrollment': 'DistanceEnrollment',
    'twelve_month_enrollment': 'TwelveMonthEnrollment',
    'retention': 'Retention', 'tuition': 'Tuition', 'student_aid': 'StudentAid',
    'veterans_aid': 'VeteransAid', 'completion': 'Completion',
    'completers': 'Completers', 'graduation': 'Graduation',
    'graduation200': 'Graduation200', 'outcome_measures': 'OutcomeMeasures',
    'cip': 'Cip',
}
SOURCE_TO_API = {**PUBLIC, 'tuition_program': 'Tuition',
                 'student_aid_net_price': 'StudentAid',
                 'completers_by_award': 'Completers'}
TABLES = {
    'characteristics': 'IC/FA/HD institutional header',
    'admissions': 'IC2001-2013 or ADM2014-2024',
    'enrollment': 'EF fall-enrollment A',
    'distance_enrollment': 'EF fall-enrollment A distance supplement',
    'twelve_month_enrollment': 'EFFY (12-month headcounts)',
    'retention': 'EF fall-enrollment D',
    'tuition': 'IC academic-year/program-year; COST1_2024',
    'student_aid': 'SFA; COST2_2024 for 2023-24 net price',
    'veterans_aid': 'SFAV',
    'completion': 'Completions A (awards by CIP)',
    'completers': 'Completions B (all awards) or C (award level)',
    'graduation': 'GR (150% adjusted cohorts)',
    'graduation200': 'GR200_YY (100/150/200% cohorts)',
    'outcome_measures': 'OM annual cohort/status file',
    'cip': 'Completions A data dictionary CIPCODE frequencies',
}
GRAIN = {
    'characteristics': 'institution × year (1986 placeholder UNITID is nonunique)',
    'admissions': 'institution × year',
    'enrollment': 'institution × fall year × studentlevel',
    'distance_enrollment': 'institution × fall year × EFDELEV student_level (nested rows overlap)',
    'twelve_month_enrollment': 'institution × period-ending year × student_level',
    'retention': 'institution × retention fall year',
    'tuition': 'institution × price starting year × reporter',
    'student_aid': 'institution × aid ending year × reporter',
    'veterans_aid': 'institution × aid ending year',
    'completion': 'institution × award ending year × CIP × selected deglevel/major',
    'completers': 'institution × award ending year (B) OR × award_level_code (C)',
    'graduation': 'institution × reporting year × selected deglevel/cohort',
    'graduation200': 'institution × reporting year × bachelor or less-than-four-year entering cohort',
    'outcome_measures': 'institution × eight-year status year × entry cohort/Pell subgroup',
    'cip': 'CIP code × dictionary year',
}

# Rules for fields whose availability and meaning were checked against yearly
# source dictionaries/headers. Other rows say explicitly that field-level
# coverage was not audited; subject years alone do not imply field presence.
CHAR_FIRST = {
    'webaddress': 1999, 'longitude': 2009, 'latitude': 2009,
    'sector_code': 1986, 'sector': 1986,
    'hbcu_code': 1992, 'hbcu': 1992,
    'tribal_code': 1993, 'tribal': 1993,
    'degree_granting_code': 2000, 'degree_granting': 2000,
    'locale_code': 1995, 'locale_scheme': 1995,
    'carnegie_2021_basic_code': 2021,
}


def availability(subject, variable):
    start, end = CONFIG[subject]['years_available']
    base = variable.removesuffix('_status')
    if subject == 'characteristics':
        return f"{CHAR_FIRST.get(base, start)}-{end}; selected field may be missing for some institutions"
    if subject == 'admissions':
        if base in ('id', 'year'):
            return f'{start}-{end}'
        if base.startswith(('another_gender_', 'gender_unknown_')):
            return '2022-2024; supplemental reporting does not form a disjoint total'
        if base.startswith('consider_'):
            if base in ('consider_other_tests', 'consider_other_tests_code'):
                return '2005-2024; category code semantics vary'
            if base in ('consider_work_experience', 'consider_work_experience_code',
                        'consider_essay', 'consider_essay_code',
                        'consider_legacy', 'consider_legacy_code'):
                return '2022-2024; required/optional/not considered codes'
            return '2001-2024; codes change in 2016 and 2022'
        if base in ('sat_rw_50', 'sat_math_50', 'act_comp_50',
                    'act_eng_50', 'act_math_50'):
            return '2022-2024; score medians introduced'
        if base.startswith('num_submit_'):
            return '2001-2024; applicability varies by institution'
        if base.startswith(('sat_', 'act_', 'share_submit_')):
            return 'varies by year; score/submitter field not universal'
        return f'{start}-{end}; some totals reconstructed in early years'
    if subject == 'enrollment':
        if base.startswith(('wt', 'bk', 'hsp', 'asn', 'totwt', 'totbk', 'tothsp', 'totasn')):
            return 'varies by year; race categories and raw columns change'
        return f'{start}-{end}; selected LINE codes change by year'
    if subject == 'distance_enrollment':
        return '2012-2024; source EFDELEV totals and UG subsets overlap'
    if subject == 'twelve_month_enrollment':
        if base == 'asian_pacific':
            return '2002-2007 only'
        if base in ('asian', 'pacific_islander', 'two_or_more'):
            return '2008-2025; distinct categories'
        if base in ('source_level_code', 'level_code_system', 'student_level'):
            return '2002-2019 LSTUDY; 2020-2025 EFFYALEV; first_professional only through 2010'
        return '2002-2025; original category definitions can change'
    if subject == 'retention':
        if 'inclusions' in base:
            return '2016-2024'
        if any(x in base for x in ('cohort', 'exclusions', 'retained')) and base != 'cohort_year':
            return '2007-2024'
        return '2003-2024'
    if subject == 'tuition':
        if base == 'largest_program_tuition_fees_no_ftft':
            return '2006-2024; program-year reporters only'
        if base.startswith('program_') or base == 'largest_program_cip':
            return '2000-2024; program-year reporters only'
        if base.startswith(('in_district_', 'in_state_', 'out_of_state_')):
            return '2000-2024; academic-year reporters only'
        return '2000-2024; reporter-specific columns are nullable'
    if subject == 'student_aid':
        if base == 'ftft_net_price':
            return '2009-2024; 2009-2023 SFA, 2024 COST2_2024'
        if base.startswith('ug_') and base not in ('ug_students',):
            return '2009-2024'
        if base.startswith(('ftft_grant_', 'ftft_pell_', 'ftft_federal_loan_')):
            return ('2009-2024' if base.endswith('_total') else '2008-2024')
        if base.endswith('_total'):
            return '2009-2024'
        return '2002-2024; academic/program denominators differ'
    if subject == 'veterans_aid':
        return '2014-2024; participation, institution knowledge and applicability vary'
    if subject == 'completion':
        if base == 'major_type':
            return '1984-2000 unspecified; MAJORNUM first/second from 2001-2025'
        if base.startswith(('wt', 'bk', 'hsp', 'asn', 'totwt', 'totbk', 'tothsp', 'totasn')):
            return '1995-2025; older race categories/columns differ'
        return '1984-2025; some award and CIP definitions change'
    if subject == 'completers':
        if base.startswith('age_'):
            return '2012-2025 C award-level rows only; missing in B'
        if base in ('award_level', 'award_level_code', 'source_award_code'):
            return '2012-2025 C only for codes; B is all_awards'
        return '2012-2025 B/C; population differs by table'
    if subject == 'graduation':
        if base.startswith(('wt', 'bk', 'hsp', 'asn', 'gradrate_wt', 'gradrate_bk',
                            'gradrate_hsp', 'gradrate_asn')):
            return 'year-specific race fields; verify before comparing'
        return '2000-2024; selected cohorts and source codes vary'
    if subject == 'graduation200':
        if base == 'still_enrolled':
            return '2011-2024; missing in 2008-2010'
        if base == 'collection_phase':
            return '2008 supplemental; 2009-2024 standard'
        return '2008-2024; bachelor/less-than-four-year columns differ'
    if subject == 'outcome_measures':
        if base in ('inconsistency_flag', 'inconsistency_flag_label', 'revised_cohort_8'):
            return '2015 only'
        if base in ('revised_cohort_6', 'exclusions_6', 'adjusted_cohort_6',
                    'exclusions_8', 'adjusted_cohort_8'):
            return '2015-2016; initial scheme (8-year exclusions change description)'
        if base in ('revised_cohort', 'exclusions', 'adjusted_cohort',
                    'enrollment_unknown_8_pct') or base.startswith((
                        'awards_4', 'certificate_', 'associate_', 'bachelor_')):
            return '2017-2024 expanded scheme'
        if base in ('pell_group', 'cohort_type', 'source_cohort_code', 'schema_version'):
            return '2015-2016 initial codes; 2017-2024 expanded cohorts and Pell groups'
        return '2015-2024; entering cohort is year-8'
    if subject == 'cip':
        return '1984-2025; code definitions/versions vary by year'
    raise KeyError(subject)


def source_fields(subject, variable):
    status = variable.endswith('_status')
    name = variable.removesuffix('_status') if status else variable
    fields = []
    method = 'source column (renamed)'
    if subject in VARIABLE_RENAME:
        fields = [raw.upper() for raw, output in VARIABLE_RENAME[subject].items()
                  if output == name]

    if subject == 'twelve_month_enrollment' and name in E12_FIELDS:
        raw_old, flag_old, raw_new, flag_new = E12_FIELDS[name]
        fields = [v.upper() for v in ((flag_old, flag_new) if status else
                                     (raw_old, raw_new)) if v]
    elif subject == 'distance_enrollment':
        fields = [(('X' if status else '') + raw.upper())
                  for raw, output in DISTANCE_FIELDS.items() if output == name]
    elif subject == 'graduation200' and name in GR200_FIELDS:
        raws = GR200_FIELDS[name]
        fields = [(GR200_FLAG_EXCEPTIONS.get(raw, 'x' + raw) if status else raw).upper()
                  for raw in raws]
    elif subject == 'outcome_measures' and name in OM_FIELDS:
        fields = [(('X' if status else '') + raw.upper())
                  for output, raw in OM_FIELDS.items() if output == name]
    elif subject == 'tuition':
        for spec in TUITION_FIELDS.values():
            fields += [v.upper() for raw, (target, flag) in spec.items()
                       for v in [flag if status else raw] if target == name]
    elif subject == 'student_aid':
        fields = [(('X' if status else '') + raw.upper())
                  for raw, output in AID_FIELDS.items() if output == name]
        if name in ('ftft_students', 'ug_students'):
            fields = (['SCUGFFN', 'SCFA1N', 'SCFY1N'] if name == 'ftft_students'
                      else ['SCUGRAD', 'SCFA2', 'SCFY2'])
            if status:
                fields = ['X' + field for field in fields]
            method = 'year/reporter-dependent source field'
    elif subject == 'veterans_aid':
        fields = [(('X' if status else '') + raw.upper())
                  for raw, output in VETERANS_AID_FIELDS.items() if output == name]
    elif subject == 'completers':
        fields = [(('X' if status else '') + raw.upper())
                  for output, raw in COMPLETERS_FIELDS.items() if output == name]
    elif subject == 'retention' and status:
        fields = ['X' + raw.upper() for raw, output in VARIABLE_RENAME['retention'].items()
                  if output == name]

    calculations = {
        'characteristics': {
            'state': ('STABBR', 'abbreviation expanded to state name'),
            'control': ('CONTROL', 'year-aware code-to-label mapping'),
            'level': ('ICLEVEL', 'recognized code-to-label mapping'),
            'sector': ('SECTOR', 'recognized code-to-label mapping'),
            'hbcu': ('HBCU', 'nullable boolean; early blank/no differs from nonresponse'),
            'tribal': ('TRIBAL', 'nullable boolean; early blank/no differs from nonresponse'),
            'degree_granting': ('DEGGRANT', 'nullable boolean for codes 1 and 2'),
            'locale_scheme': ('LOCALE', 'legacy 1995-2004, urban_centric 2005 onward'),
        },
        'admissions': {
            'tot_applied': ('APPLCN|APPLCNM|APPLCNW', 'reported total or men_applied + women_applied if absent'),
            'tot_admitted': ('ADMSSN|ADMSSNM|ADMSSNW', 'reported total or men_admitted + women_admitted if absent'),
            'tot_enrolled': ('ENRLT|ENRLM|ENRLW', 'reported total or men_enrolled + women_enrolled if absent'),
            'men_enrolled': ('ENRLM|ENRLFTM|ENRLPTM', '2001 FT + PT; otherwise source total'),
            'women_enrolled': ('ENRLW|ENRLFTW|ENRLPTW', '2001 FT + PT; otherwise source total'),
            'tot_ft_enrolled': ('ENRLFT|ENRLFTM|ENRLFTW', 'reported total; in 2001 sum FT men and women'),
            'tot_pt_enrolled': ('ENRLPT|ENRLPTM|ENRLPTW', 'reported total; in 2001 sum PT men and women'),
            'accept_rate_men': ('ADMSSNM|APPLCNM', 'men_admitted / men_applied × 100; zero denominator -> NA'),
            'accept_rate_women': ('ADMSSNW|APPLCNW', 'women_admitted / women_applied × 100; zero denominator -> NA'),
            'accept_rate_total': ('ADMSSN|APPLCN', 'tot_admitted / tot_applied × 100; zero denominator -> NA'),
            'yield_rate_men': ('ENRLM|ENRLFTM|ENRLPTM|ADMSSNM', 'men_enrolled / men_admitted × 100; zero denominator -> NA'),
            'yield_rate_women': ('ENRLW|ENRLFTW|ENRLPTW|ADMSSNW', 'women_enrolled / women_admitted × 100; zero denominator -> NA'),
            'yield_rate_total': ('ENRLT|ADMSSN', 'tot_enrolled / tot_admitted × 100; zero denominator -> NA'),
            'men_applied_share': ('APPLCNM|APPLCN', 'men_applied / tot_applied × 100'),
            'men_admitted_share': ('ADMSSNM|ADMSSN', 'men_admitted / tot_admitted × 100'),
        },
        'enrollment': {
            'studentlevel': ('LINE', 'year-dependent row filter; FT and PT sums'),
            'totmen_share': ('TOTMEN|TOTWOMEN', 'totmen / (totmen + totwomen) × 100'),
            **{f'tot{x}_share': (f'{x.upper()}MEN|{x.upper()}WOMEN|TOTMEN|TOTWOMEN',
                                  f'({x}men + {x}women) / (totmen + totwomen) × 100')
               for x in ('wt', 'bk', 'hsp', 'asn')},
        },
        'completion': {
            'deglevel': ('AWLEVEL', 'award-level filter; doctoral code rule changes in 2010'),
            'major_type': ('MAJORNUM', 'first=1, second=2 from 2001; earlier unspecified'),
            'totmen_share': ('TOTMEN|TOTWOMEN', 'totmen / (totmen + totwomen) × 100'),
            **{f'tot{x}_share': (f'{x.upper()}MEN|{x.upper()}WOMEN|TOTMEN|TOTWOMEN',
                                  f'({x}men + {x}women) / (totmen + totwomen) × 100')
               for x in ('wt', 'bk', 'hsp', 'asn')},
        },
        'completers': {
            'source_table': ('C*_B|C*_C', 'B all unique people, C unique within level'),
            'award_level': ('AWLEVELC', 'year-specific award-level labels; B=all_awards'),
            'award_level_code': ('AWLEVELC', 'strip leading zeroes on C; unavailable in B'),
            'source_award_code': ('AWLEVELC', 'source code retained verbatim for C'),
        },
        'graduation': {
            'deglevel': ('SECTION|GRTYPE|CHRTSTAT', 'bachelor 2/8-9 or associate 4/29-30; status 12-13'),
        },
        'cip': {
            'cip': ('CIPCODE CodeValue|HTML dictionary', 'year-specific dictionary code'),
            'cip_description': ('CIPCODE ValueLabel|HTML dictionary', 'dictionary label, title-cased and prefix trimmed'),
        },
        'distance_enrollment': {
            'student_level': ('EFDELEV', 'select total/UG/graduate or nested UG subgroup row'),
            'source_level_code': ('EFDELEV', 'trim and preserve original level code'),
            'exclusive_share': ('EFDEEXC|EFDETOT', 'exclusive_distance / total_students × 100; zero denominator -> NA'),
            'some_share': ('EFDESOM|EFDETOT', 'some_distance / total_students × 100; zero denominator -> NA'),
            'no_distance_share': ('EFDENON|EFDETOT', 'no_distance / total_students × 100; zero denominator -> NA'),
        },
        'graduation200': {
            'cohort_type': ('BAREVCT|L4REVCT', 'select the applicable source cohort'),
            'cohort_year': ('source file year', 'year - 8 (bachelor) or year - 4 (less-than-four-year)'),
            'collection_phase': ('source file year', '2008 supplemental; 2009+ standard'),
        },
        'outcome_measures': {
            'source_cohort_code': ('OMCHRT', 'preserve initial or expanded cohort code'),
            'cohort_type': ('OMCHRT', 'map entry status/attendance to year-specific cohort'),
            'pell_group': ('OMCHRT', 'not_collected before 2017; total/Pell/non-Pell from 2017'),
            'schema_version': ('source file year', '2015-16 initial; 2017+ expanded'),
            'inconsistency_flag': ('OMFLAG', '2015 raw flag: 0 no issues or 1 data inconsistencies'),
            'inconsistency_flag_label': ('OMFLAG', '2015 code-to-label mapping'),
            'entering_year_start': ('source file year', 'year - 8'),
            'entering_year_end': ('source file year', 'year - 7'),
        },
    }
    if name in calculations.get(subject, {}):
        raw, method = calculations[subject][name]
        fields = raw.split('|')
        if subject in ('enrollment', 'completion') and name.endswith('_share'):
            race = name[3:-6]  # totwt_share -> wt; totmen_share is handled below
            components = (['totmen', 'totwomen'] if name == 'totmen_share' else
                          [race + 'men', race + 'women', 'totmen', 'totwomen'])
            fields = [raw.upper() for raw, output in VARIABLE_RENAME[subject].items()
                      if output in components]
    if subject == 'admissions' and name in ADMISSION_CONSIDERATIONS:
        raw = [source.upper() for source, output in VARIABLE_RENAME['admissions'].items()
               if output == ADMISSION_CONSIDERATIONS[name]]
        fields, method = raw, 'year-aware label for raw ADMCON code; see codes.csv'
    if subject == 'graduation':
        suffix = name.removesuffix('_graduated').removeprefix('gradrate_')
        if name.endswith('_graduated') or name.startswith('gradrate_'):
            fields = [raw.upper() for raw, output in VARIABLE_RENAME['graduation'].items()
                      if output == suffix]
            fields += ['GRTYPE', 'CHRTSTAT', 'SECTION']
            method = ('numerator / adjusted cohort × 100 (NCES cohort rows)'
                      if name.startswith('gradrate_') else 'GR graduated-count pivot')

    if subject == 'tuition' and name == 'largest_program_cip':
        fields, method = ['CIPCODE1'], 'CIP of largest program at program reporters'
    if subject == 'tuition' and name == 'reporter':
        fields, method = ['source AY/PY', 'CIPCODE1 (2024)'], 'reporter classification'
    if subject == 'student_aid' and name == 'reporter':
        fields, method = ['SCFA1N', 'SCFA2', 'SCFY1N', 'SCFY2'], 'academic/program reporter classification'
    if subject == 'twelve_month_enrollment' and name in ('student_level', 'source_level_code', 'level_code_system'):
        fields, method = ['LSTUDY', 'EFFYALEV'], 'selected non-overlapping source rows; coding switches in 2020'

    if name == 'id':
        fields, method = ['UNITID'], 'source identifier, trimmed'
    elif name == 'year':
        fields, method = ['source file year'], 'file/period year; see guide for period alignment'
    elif name in ('period_start_year', 'aid_year_start', 'cohort_year') and subject != 'graduation200':
        fields, method = ['year'], 'year - 1'
    if status:
        method = 'NCES raw reporting/imputation flag; see year-specific dictionary'
    if not fields:
        method = 'computed or source-specific; see harmonization guide'
    # Inverse mappings occasionally contain duplicates intentionally (old/new names).
    return '; '.join(dict.fromkeys(fields)), method


def units(subject, variable):
    if variable.endswith('_status'):
        return 'NCES status code'
    if variable in ('year', 'period_start_year', 'aid_year_start', 'cohort_year',
                    'entering_year_start', 'entering_year_end'):
        return 'year'
    if variable == 'id':
        return 'UNITID string'
    if variable in ('longitude', 'latitude'):
        return 'decimal degrees (string in current API)'
    if variable in ('cip', 'largest_program_cip'):
        return 'CIP code (string)'
    if variable.endswith('_code') or variable in ('source_level_code', 'source_award_code'):
        return 'categorical source code'
    if variable in ('hbcu', 'tribal', 'degree_granting'):
        return 'nullable boolean'
    if variable.startswith(('sat_', 'act_')) and variable.endswith(('_25', '_50', '_75')):
        return 'test-score points'
    if variable.startswith(('gradrate_', 'rate_')) or variable.endswith(('_share', '_rate', '_pct')) or variable.startswith('share_submit_'):
        return 'percent (0-100)'
    if variable.startswith(('accept_rate_', 'yield_rate_')):
        return 'percent (0-100)'
    if subject == 'tuition' and ('tuition' in variable or 'fees' in variable):
        return 'nominal dollars'
    if subject in ('student_aid', 'veterans_aid') and (
        variable.endswith(('_avg', '_total')) or variable == 'ftft_net_price'):
        return 'nominal dollars'
    if subject in ('student_aid', 'veterans_aid') and 'count' in variable:
        return 'people'
    if subject == 'student_aid' and variable in ('ftft_students', 'ug_students'):
        return 'people'
    if subject in ('completion',) and (variable.endswith(('men', 'women')) or variable == 'totmen'):
        return 'awards by CIP (not unique people)'
    if subject in ('enrollment', 'distance_enrollment', 'twelve_month_enrollment', 'retention', 'completers', 'graduation', 'graduation200', 'outcome_measures') and (
        variable.endswith(('men', 'women', '_graduated')) or variable in ('total_students', 'total_completers')
        or variable.startswith(('age_', 'ft_', 'pt_', 'completed_', 'adjusted_cohort_',
                                 'additional_exclusions_', 'exclusions_')) or variable in (
            'white', 'black', 'asian', 'american_indian', 'hispanic', 'two_or_more',
            'nonresident', 'race_unknown', 'pacific_islander', 'asian_pacific',
            'revised_cohort', 'still_enrolled', 'exclusive_distance', 'some_distance',
            'no_distance', 'exclusive_same_state', 'exclusive_other_us_state',
            'exclusive_us_state_unknown', 'exclusive_outside_us', 'exclusive_location_unknown')
        or (subject == 'outcome_measures' and variable in OM_FIELDS
            and not variable.endswith('_pct'))):
        return 'people'
    if subject == 'admissions' and variable.startswith(('tot_', 'men_')):
        return 'applicants/admittees/enrollees'
    if subject == 'admissions' and variable.startswith((
        'women_', 'another_gender_', 'gender_unknown_', 'num_submit_')):
        return 'applicants/admittees/enrollees or score submitters'
    return 'category, text, or source-specific measure'


VAR_HEADERS = ('api_class', 'subject', 'variable', 'description', 'subject_years',
               'field_availability', 'row_grain', 'unit', 'source_tables',
               'source_fields', 'harmonization', 'status_of')
FILE_HEADERS = ('api_class', 'download_subject', 'configured_year', 'source_stem',
                'data_zip_url', 'dictionary_zip_url', 'reference_period', 'evidence')


def variable_rows():
    for subject, api_class in PUBLIC.items():
        config = CONFIG[subject]
        start, end = config['years_available']
        for variable, description in config['variables'].items():
            fields, method = source_fields(subject, variable)
            yield dict(api_class=api_class, subject=subject, variable=variable,
                       description=description, subject_years=f'{start}-{end}',
                       field_availability=availability(subject, variable),
                       row_grain=GRAIN[subject], unit=units(subject, variable),
                       source_tables=TABLES[subject], source_fields=fields,
                       harmonization=method,
                       status_of=variable.removesuffix('_status')
                       if variable.endswith('_status') else '')


def file_rows():
    for subject, config in CONFIG.items():
        for year_text, stem in config['endpoints'].items():
            year = int(year_text)
            root = ('https://nces.ed.gov/ipeds/complete-data-files/' if year > 2022
                    else 'https://nces.ed.gov/ipeds/datacenter/data/')
            dictionary = root + stem + '_Dict.zip'
            data = dictionary if subject == 'cip' else root + stem + '.zip'
            period = ('institution/collection year; some measures have other dates'
                      if subject in ('characteristics', 'admissions', 'enrollment', 'retention', 'graduation')
                      else 'see subject year definition in variables.csv / harmonization.md')
            yield dict(api_class=SOURCE_TO_API[subject], download_subject=subject,
                       configured_year=year, source_stem=stem, data_zip_url=data,
                       dictionary_zip_url=dictionary, reference_period=period,
                       evidence='configured endpoint in src/genpeds/cfg.json; URL not independently rechecked by this CSV')


def render(headers, rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=headers, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main():
    artifacts = {
        'variables.csv': render(VAR_HEADERS, list(variable_rows())),
        'source_files.csv': render(FILE_HEADERS, list(file_rows())),
    }
    checking = '--check' in sys.argv
    for name, content in artifacts.items():
        path = HERE / name
        if checking:
            if not path.exists() or path.read_text(encoding='utf-8') != content:
                raise SystemExit(f'{path} is stale; run python codebook/build.py')
        else:
            path.write_text(content, encoding='utf-8')
        print(name, len(content.splitlines()) - 1, 'data rows', 'checked' if checking else 'written')


if __name__ == '__main__':
    main()
