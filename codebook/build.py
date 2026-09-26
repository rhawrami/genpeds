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
    GR200_FIELDS, GR200_FLAG_EXCEPTIONS, INSTRUCTIONAL_ACTIVITY_FIELDS,
    OM_FIELDS, TUITION_FIELDS,
    VARIABLE_RENAME, VETERANS_AID_FIELDS,
)
from genpeds.human_resources import (  # noqa: E402
    HR_DATASETS, HR_FIELDS, HR_VARIABLES, HR_CATEGORY_FIELDS,
)
from genpeds.finance import FINANCE_FIELDS, FINANCE_VARIABLES  # noqa: E402
from genpeds.academic_libraries import (  # noqa: E402
    LIBRARY_FIELDS, LIBRARY_SCREENS, LIBRARY_FIELD_YEARS,
    LIBRARY_SCREEN_YEARS, LIBRARY_VARIABLES,
)


CONFIG = json.loads((ROOT / 'src/genpeds/cfg.json').read_text(encoding='utf-8'))
CONFIG['human_resources']['variables'] = HR_VARIABLES
CONFIG['finance']['variables'] = FINANCE_VARIABLES
CONFIG['academic_libraries']['variables'] = LIBRARY_VARIABLES
PUBLIC = {
    'characteristics': 'Characteristics', 'admissions': 'Admissions',
    'enrollment': 'Enrollment', 'distance_enrollment': 'DistanceEnrollment',
    'twelve_month_enrollment': 'TwelveMonthEnrollment',
    'instructional_activity': 'InstructionalActivity',
    'retention': 'Retention', 'tuition': 'Tuition', 'student_aid': 'StudentAid',
    'veterans_aid': 'VeteransAid', 'completion': 'Completion',
    'completers': 'Completers', 'graduation': 'Graduation',
    'graduation200': 'Graduation200', 'outcome_measures': 'OutcomeMeasures',
    'human_resources': 'HumanResources', 'finance': 'Finance',
    'academic_libraries': 'AcademicLibraries',
    'cip': 'Cip',
}
SOURCE_TO_API = {**PUBLIC, 'tuition_program': 'Tuition',
                 'student_aid_net_price': 'StudentAid',
                 'completers_by_award': 'Completers'}
SOURCE_TO_API.update({subject: 'HumanResources' for subject in HR_DATASETS.values()})
SOURCE_TO_API.update({'finance_f2': 'Finance', 'finance_f3': 'Finance'})
TABLES = {
    'characteristics': 'IC/FA/HD institutional header',
    'admissions': 'IC2001-2013 or ADM2014-2024',
    'enrollment': 'EF fall-enrollment A',
    'distance_enrollment': 'EF fall-enrollment A distance supplement',
    'twelve_month_enrollment': 'EFFY (12-month headcounts)',
    'instructional_activity': 'EFIA (12-month instructional activity and FTE)',
    'retention': 'EF fall-enrollment D',
    'tuition': 'IC academic-year/program-year; COST1_2024',
    'student_aid': 'SFA; COST2_2024 for 2023-24 net price',
    'veterans_aid': 'SFAV',
    'completion': 'Completions A (awards by CIP)',
    'completers': 'Completions B (all awards) or C (award level)',
    'graduation': 'GR (150% adjusted cohorts)',
    'graduation200': 'GR200_YY (100/150/200% cohorts)',
    'outcome_measures': 'OM annual cohort/status file',
    'human_resources': 'EAP; S*_OC/IS/SIS/NH; SAL*_IS/NIS (selected dataset)',
    'finance': 'F*_F1A (GASB), F*_F2/F3 (FASB); selected form',
    'academic_libraries': 'AL2014-AL2024 annual Academic Libraries',
    'cip': 'Completions A data dictionary CIPCODE frequencies',
}
GRAIN = {
    'characteristics': 'institution × year (1986 placeholder UNITID is nonunique)',
    'admissions': 'institution × year',
    'enrollment': 'institution × fall year × studentlevel',
    'distance_enrollment': 'institution × fall year × EFDELEV student_level (nested rows overlap)',
    'twelve_month_enrollment': 'institution × period-ending year × student_level',
    'instructional_activity': 'institution × 12-month period-ending year',
    'retention': 'institution × retention fall year',
    'tuition': 'institution × price starting year × reporter',
    'student_aid': 'institution × aid ending year × reporter',
    'veterans_aid': 'institution × aid ending year',
    'completion': 'institution × award ending year × CIP × selected deglevel/major',
    'completers': 'institution × award ending year (B) OR × award_level_code (C)',
    'graduation': 'institution × reporting year × selected deglevel/cohort',
    'graduation200': 'institution × reporting year × bachelor or less-than-four-year entering cohort',
    'outcome_measures': 'institution × eight-year status year × entry cohort/Pell subgroup',
    'human_resources': 'dataset-dependent: institution × year × occupation/staff/tenure/rank code',
    'finance': 'institution × fiscal year × accounting form',
    'academic_libraries': 'institution × library fiscal year',
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
    if subject == 'instructional_activity':
        if base == 'professional_practice_reported_fte':
            return '2012-2025; separately reported professional-practice FTE'
        if base.endswith('_fte') or base in ('activity_type_code', 'activity_type'):
            return '2004-2025; missing in 2002-2003'
        if base in ('ug_contact_clock_hours', 'hour_term'):
            return '2002-2018 contact; 2019-2025 clock source wording'
        return '2002-2025; academic/program applicability varies'
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
    if subject == 'human_resources':
        if base in ('hire_window_months', 'hire_period_start_year'):
            return '2012-2017 four-month hires; 2018-2024 twelve-month hires'
        if base == 'salary_regime':
            return '2012-2015 weighted months; 2016-2024 explicit months'
        if base.startswith(('average_months_', 'months_worked_')):
            return '2012-2017 instructional salary source; absent from 2018+'
        if (base.startswith(('equated_9_month_', 'instructional_staff_',
                             'staff_under9_', 'average_salary_'))
                or (base.startswith('salary_outlay_') and '_month_' in base)):
            return '2016-2024 instructional salary source only'
        if base.startswith('staff_') and '_month_' in base:
            return '2012-2024 instructional salary source only'
        if base in ('staff_count', 'salary_outlay'):
            return '2012-2024 noninstructional salary source only; no sex split'
        families = sorted({dataset for dataset, fields in HR_FIELDS.items()
                           if base in fields.values()})
        if families:
            return f"2012-2024; source dataset(s): {'/'.join(families)}"
        return '2012-2024 modern HR; category population/coverage depends on dataset'
    if subject == 'finance':
        if base == 'pell_discounts':
            return '2020-2024; all three forms; missing before the field was added'
        if base == 'functional_expenses':
            return '2014-2024; F3 only; not interchangeable with F3B02'
        if base == 'instruction_expenses':
            return '2004-2024 F1A/F2; 2014-2024 F3 (different regimes)'
        if base in ('net_position', 'revenues_and_additions',
                    'operating_revenues', 'nonoperating_revenues'):
            return '2004-2024; public GASB F1A only'
        if base == 'net_assets':
            return '2004-2024; nonprofit/some public FASB F2 only'
        if base == 'equity':
            return '2004-2024; for-profit FASB F3 only'
        if base == 'revenues_and_investment_return':
            return '2004-2024; FASB F2/F3 only'
        return '2004-2024; form-specific source, applicability, and accounting regime'
    if subject == 'academic_libraries':
        for raw, (name, flag) in LIBRARY_FIELDS.items():
            if name == base:
                first = LIBRARY_FIELD_YEARS.get(raw, 2014)
                return (f'{first}-2024; survey eligibility and definition vary'
                        + ('; no raw X flag' if not flag else ''))
        for raw, name in LIBRARY_SCREENS.items():
            if name == base or name + '_code' == base:
                start, end = LIBRARY_SCREEN_YEARS.get(raw, (2014, 2024))
                return f'{start}-{end}; source screening code (1 yes / 2 no / -2 not applicable)'
        if base == 'collection_total_definition':
            return '2014-2018 excludes serials; 2019-2024 includes serials in collection totals'
        return '2014-2024; annual AL fiscal-year records'
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
    elif subject == 'human_resources':
        fields = [((('X' if status else '') + raw.upper()))
                  for group in HR_FIELDS.values()
                  for raw, output in group.items() if output == name]
    elif subject == 'finance':
        fields = [(('X' if status else '') + raw.upper())
                  for group in FINANCE_FIELDS.values()
                  for raw, output in group.items() if output == name]
    elif subject == 'academic_libraries':
        fields = [(flag if status else raw).upper()
                  for raw, (output, flag) in LIBRARY_FIELDS.items()
                  if output == name and (not status or flag)]
        fields += [raw.upper() for raw, output in LIBRARY_SCREENS.items()
                   if name in (output, output + '_code')]
    elif subject == 'instructional_activity':
        fields = [(('X' if status else '') + raw.upper())
                  for raw, output in INSTRUCTIONAL_ACTIVITY_FIELDS.items()
                  if output == name]
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
        'instructional_activity': {
            'activity_type_code': ('ACTTYPE', 'raw activity type from 2004; -2 not applicable'),
            'activity_type': ('ACTTYPE', 'year-aware credit/contact/clock label'),
            'hour_term': ('CNACTUA|source file year', 'contact through 2018; clock from 2019'),
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
        'human_resources': {
            'category_code': ('EAPCAT|STAFFCAT|SISCAT|SNHCAT', 'source dataset-specific category code'),
            'category_label': ('EAPCAT|STAFFCAT|SISCAT|SNHCAT', 'year-specific label from packaged NCES dictionaries'),
            'occupation_code': ('OCCUPCAT|SANIN01-14', 'occupation code varies by selected dataset'),
            'occupation_label': ('OCCUPCAT|SANIN01-14', 'year-specific NCES dictionary label'),
            'faculty_status_code': ('FACSTAT', 'source faculty/tenure status code'),
            'faculty_status_label': ('FACSTAT', 'year-specific NCES label'),
            'ftpt_code': ('FTPT', 'source full-/part-time status code'),
            'ftpt_label': ('FTPT', 'year-specific NCES label'),
            'rank_code': ('ARANK', 'rank code 0 is all ranks in staff; 7 is all ranks in salary'),
            'rank_label': ('ARANK', 'year-specific NCES rank label'),
            'women_share': ('HRTOTLM|HRTOTLW', 'women / (men + women) × 100; zero denominator -> NA'),
            'hire_window_months': ('source file year', 'four months through 2017; twelve from 2018'),
            'hire_period_start_year': ('source file year', 'year through 2017; year - 1 from 2018'),
            'academic_year_end': ('source file year', 'year + 1 for SAL source files'),
            'salary_regime': ('source file year', '2012-15 weighted versus 2016+ explicit months'),
            'staff_count': ('SANIN01-14', 'noninstructional count for the selected occupation code'),
            'staff_count_status': ('XSANIN01-14', 'NCES noninstructional count flags'),
            'salary_outlay': ('SANIT01-14', 'noninstructional annual outlay for selected occupation'),
            'salary_outlay_status': ('XSANIT01-14', 'NCES noninstructional outlay flags'),
        },
        'finance': {
            'form': ('source F*_F1A/F2/F3 stem', 'source accounting form, not a CONTROL lookup'),
            'accounting_basis': ('source form', 'F1A GASB; F2 nonprofit/some public FASB; F3 for-profit FASB'),
            'accounting_regime': ('source form|fiscal year', '2004-09 prealigned; 2010+ aligned; F3 revised from FY2014'),
            'source_stem': ('configured source file', 'exact NCES ZIP filename stem'),
        },
        'academic_libraries': {
            'collection_total_definition': ('source year|LPCLLCT|LECLLCT',
                                            '2014-18 omit serials; 2019+ include serials'),
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
    if subject == 'human_resources' and status and name in ('staff_count', 'salary_outlay'):
        fields = ['XSANIN01-14' if name == 'staff_count' else 'XSANIT01-14']
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
    if subject == 'human_resources':
        if variable in ('year', 'hire_period_start_year', 'academic_year_end'):
            return 'calendar year'
        if variable.startswith(('average_months_', 'months_worked_')) or variable == 'hire_window_months':
            return 'months'
        if ('salary' in variable or 'outlay' in variable) and variable != 'salary_regime':
            return 'nominal dollars (institution aggregates or rank average)'
        if variable in ('women_share',):
            return 'percent (0-100)'
        if any(variable == output for fields in HR_FIELDS.values()
                for output in fields.values()) or variable == 'staff_count':
            return 'people'
    if subject == 'finance' and variable in FINANCE_MEASURE_NAMES:
        return 'nominal institutional dollars (form/era-specific)'
    if subject == 'academic_libraries':
        if variable in (name for raw, (name, _) in LIBRARY_FIELDS.items()
                        if raw in ('lstotal', 'lslibrn', 'lsoprof', 'lsopaid', 'lsstast')):
            return 'full-time equivalent library staff (not people headcount)'
        if variable in (name for raw, (name, _) in LIBRARY_FIELDS.items()
                        if raw in ('lsalwag', 'lfrngbn', 'lexmsbb', 'lexmscs',
                                   'lexmsot', 'lexmstl', 'lexomps', 'lexomot',
                                   'lexomtl', 'lexptot', 'lswmsom')):
            return 'nominal dollars'
        if variable in (name for raw, (name, _) in LIBRARY_FIELDS.items()):
            return 'library items, uses, loans or branches (see description)'
    if subject == 'instructional_activity':
        if variable.endswith('_hours'):
            return 'instructional credit/contact/clock hours (not unique students)'
        if variable.endswith('_fte'):
            return 'full-time-equivalent students (estimated or reported)'
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


FINANCE_MEASURE_NAMES = {name for fields in FINANCE_FIELDS.values()
                         for name in fields.values()}


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
                        evidence=('data and dictionary ZIP HTTP HEAD 200 on 2026-09-26; sample dictionaries and CSVs inspected'
                                  if subject == 'academic_libraries' else
                                  'data ZIP HTTP HEAD 200 on 2026-09-26; dictionaries checked for sampled years'
                                  if subject.startswith('finance') else
                                  'configured endpoint in src/genpeds/cfg.json; URL not independently rechecked by this CSV'))


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
