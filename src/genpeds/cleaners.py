import os
import re
import warnings
from typing import Dict, Optional, List, Tuple, Union

from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import us 

from genpeds.downloader import get_year_iter


VARIABLE_RENAME = {
    'characteristics' : {
        'unitid' : 'id', 'instnm' : 'name',
          'addr' : 'address', 'city' : 'city', 'stabbr' : 'state', 'zip' : 'zipcode', 
          'webaddr' : 'webaddress', 
          'longitud' : 'longitude', 'latitude' : 'latitude',
          'control': 'control_code', 'iclevel': 'level_code',
          'sector': 'sector_code', 'hbcu': 'hbcu_code',
          'tribal': 'tribal_code', 'deggrant': 'degree_granting_code',
          'locale': 'locale_code', 'c21basic': 'carnegie_2021_basic_code'
    },

    'admissions' : {
        'unitid' : 'id', 
        'applcnm' : 'men_applied', 'applcnw' : 'women_applied', 
        'admssnm' : 'men_admitted', 'admssnw' : 'women_admitted',
        'satpct' : 'share_submit_sat', 'actpct' : 'share_submit_act',                                      
        'satvr25' : 'sat_rw_25', 'satvr75' : 'sat_rw_75', 
        'satmt25' : 'sat_math_25', 'satmt75' : 'sat_math_75', 
        'actcm25' : 'act_comp_25', 'actcm75' : 'act_comp_75',
        'acten25' : 'act_eng_25', 'acten75' : 'act_eng_75', 
        'actmt25' : 'act_math_25', 'actmt75' : 'act_math_75',
        'enrlftm' : 'men_ft_enrolled', 'enrlftw' : 'women_ft_enrolled',
        'enrlptm' : 'men_pt_enrolled', 'enrlptw' : 'women_pt_enrolled',
        'enrlm' : 'men_enrolled', 'enrlw' : 'women_enrolled',
        'applcn' : 'tot_applied', 'admssn' : 'tot_admitted', 'enrlt' : 'tot_enrolled',
        'acten50' : 'act_eng_50', 'actmt50' : 'act_math_50', 'actcm50' : 'act_comp_50',
        'satvr50' : 'sat_rw_50', 'satmt50' : 'sat_math_50'
    },

    'enrollment' : {
        'unitid' : 'id', 'line' : 'line', 'efrace15' : 'totmen', 'efrace16' : 'totwomen',
        'eftotlm' : 'totmen', 'eftotlw' : 'totwomen', 'efwhitm' : 'wtmen', 'efwhitw' : 'wtwomen',
        'efbkaam' : 'bkmen', 'efbkaaw' : 'bkwomen', 'efhispm' : 'hspmen', 'efhispw' : 'hspwomen', 
        'efasiam' : 'asnmen', 'efasiaw' : 'asnwomen', 'eftotlw' : 'totwomen',
        'efrace11' : 'wtmen', 'efrace12' : 'wtwomen', 'efrace03' : 'bkmen', 'efrace04' : 'bkwomen', 
        'efrace09' : 'hspmen', 'efrace10' : 'hspwomen', 'efrace07' : 'asnmen', 'efrace08' : 'asnwomen'
    },

    'retention' : {
        'rrftct': 'ft_cohort', 'rrftex': 'ft_exclusions',
        'rrftin': 'ft_inclusions', 'rrftcta': 'ft_adjusted_cohort',
        'ret_nmf': 'ft_retained', 'ret_pcf': 'ft_retention_rate',
        'rrptct': 'pt_cohort', 'rrptex': 'pt_exclusions',
        'rrptin': 'pt_inclusions', 'rrptcta': 'pt_adjusted_cohort',
        'ret_nmp': 'pt_retained', 'ret_pcp': 'pt_retention_rate'
    },

    'completion' : {
        'unitid' : 'id', 'cipcode' : 'cip', 'awlevel' : 'awlevel',
        'crace15' : 'totmen', 'crace16' : 'totwomen',
        'ctotalm' : 'totmen', 'ctotalw' : 'totwomen', 
        'cwhitm' : 'wtmen', 'cwhitw' : 'wtwomen', 'cbkaam' : 'bkmen', 'cbkaaw' : 'bkwomen', 
        'chispm' : 'hspmen', 'chispw' : 'hspwomen', 'casiam' : 'asnmen', 'casiaw' : 'asnwomen',
        'crace11' : 'wtmen', 'crace12' : 'wtwomen', 'crace03' : 'bkmen', 'crace04' : 'bkwomen', 
        'crace09' : 'hspmen', 'crace10' : 'hspwomen', 'crace07' : 'asnmen', 'crace08' : 'asnwomen'
    },

    'cip' : {
        # nothing needed for now.
    },

    'graduation' : {
        'grtotlm' : 'totmen', 'grtotlw' : 'totwomen', 
        'grwhitm' : 'wtmen', 'grwhitw' : 'wtwomen',
        'grbkaam' : 'bkmen', 'grbkaaw' : 'bkwomen', 
        'grhispm' : 'hspmen', 'grhispw' : 'hspwomen', 
        'grasiam' : 'asnmen', 'grasiaw' : 'asnwomen', 
        'grrace15' : 'totmen', 'grrace16' : 'totwomen',
        'grrace11' : 'wtmen', 'grrace12' : 'wtwomen', 
        'grrace03' : 'bkmen', 'grrace04' : 'bkwomen', 
        'grrace09' : 'hspmen', 'grrace10' : 'hspwomen', 
        'grrace07' : 'asnmen', 'grrace08' : 'asnwomen',
        'chrtstat' : 'chrtstat', 'section' : 'section', 
        'cohort' : 'cohort', 'unitid' : 'id', 'grtype' : 'grtype'
    }
}


TUITION_FIELDS = {
    'academic': {
        'tuition1': ('in_district_tuition', 'xtuit1'),
        'fee1': ('in_district_fees', 'xfee1'),
        'chg1ay3': ('in_district_published_tuition_fees', 'xchg1ay3'),
        'tuition2': ('in_state_tuition', 'xtuit2'),
        'fee2': ('in_state_fees', 'xfee2'),
        'chg2ay3': ('in_state_published_tuition_fees', 'xchg2ay3'),
        'tuition3': ('out_of_state_tuition', 'xtuit3'),
        'fee3': ('out_of_state_fees', 'xfee3'),
        'chg3ay3': ('out_of_state_published_tuition_fees', 'xchg3ay3')
    },
    'program': {
        'chg1py3': ('program_published_tuition_fees', 'xchg1py3'),
        'ciptuit1': ('largest_program_tuition_fees_no_ftft', 'xciptui1')
    }
}


AID_FIELDS = {
    'npist2': 'ftft_net_price',
    'anyaidn': 'ftft_any_aid_count', 'anyaidp': 'ftft_any_aid_pct',
    'fgrnt_n': 'ftft_federal_grant_count', 'fgrnt_a': 'ftft_federal_grant_avg',
    'fgrnt_t': 'ftft_federal_grant_total',
    'sgrnt_n': 'ftft_state_local_grant_count', 'sgrnt_a': 'ftft_state_local_grant_avg',
    'sgrnt_t': 'ftft_state_local_grant_total',
    'igrnt_n': 'ftft_institutional_grant_count', 'igrnt_a': 'ftft_institutional_grant_avg',
    'igrnt_t': 'ftft_institutional_grant_total',
    'loan_n': 'ftft_student_loan_count', 'loan_a': 'ftft_student_loan_avg',
    'loan_t': 'ftft_student_loan_total',
    'agrnt_n': 'ftft_grant_count', 'agrnt_a': 'ftft_grant_avg',
    'agrnt_t': 'ftft_grant_total',
    'pgrnt_n': 'ftft_pell_count', 'pgrnt_a': 'ftft_pell_avg',
    'pgrnt_t': 'ftft_pell_total',
    'floan_n': 'ftft_federal_loan_count', 'floan_a': 'ftft_federal_loan_avg',
    'floan_t': 'ftft_federal_loan_total',
    'uagrntn': 'ug_grant_count', 'uagrnta': 'ug_grant_avg',
    'uagrntt': 'ug_grant_total',
    'upgrntn': 'ug_pell_count', 'upgrnta': 'ug_pell_avg',
    'upgrntt': 'ug_pell_total',
    'ufloann': 'ug_federal_loan_count', 'ufloana': 'ug_federal_loan_avg',
    'ufloant': 'ug_federal_loan_total'
}


VETERANS_AID_FIELDS = {
    'ugpo9_n': 'ug_post911_count', 'ugpo9_t': 'ug_post911_total',
    'ugpo9_a': 'ug_post911_avg',
    'gpo9_n': 'grad_post911_count', 'gpo9_t': 'grad_post911_total',
    'gpo9_a': 'grad_post911_avg',
    'ugdod_n': 'ug_dod_count', 'ugdod_t': 'ug_dod_total',
    'ugdod_a': 'ug_dod_avg',
    'gdod_n': 'grad_dod_count', 'gdod_t': 'grad_dod_total',
    'gdod_a': 'grad_dod_avg'
}


SECTOR_LABELS = {
    '0': 'Administrative unit',
    '1': 'Public, four-year or above', '2': 'Private nonprofit, four-year or above',
    '3': 'Private for-profit, four-year or above', '4': 'Public, two-year',
    '5': 'Private nonprofit, two-year', '6': 'Private for-profit, two-year',
    '7': 'Public, less-than-two-year', '8': 'Private nonprofit, less-than-two-year',
    '9': 'Private for-profit, less-than-two-year'
}


E12_FIELDS = {
    'total_students': ('fyrace24', 'xfyrac24', 'efytotlt', 'xeytotlt'),
    'men': ('fyrace15', 'xfyrac15', 'efytotlm', 'xeytotlm'),
    'women': ('fyrace16', 'xfyrac16', 'efytotlw', 'xeytotlw'),
    'nonresident': ('fyrace17', 'xfyrac17', 'efynralt', 'xeynralt'),
    'black': ('fyrace18', 'xfyrac18', 'efybkaat', 'xefybkat'),
    'american_indian': ('fyrace19', 'xfyrac19', 'efyaiant', 'xefyaiat'),
    'asian_pacific': ('fyrace20', 'xfyrac20', None, None),
    'hispanic': ('fyrace21', 'xfyrac21', 'efyhispt', 'xefyhist'),
    'white': ('fyrace22', 'xfyrac22', 'efywhitt', 'xefywhit'),
    'race_unknown': ('fyrace23', 'xfyrac23', 'efyunknt', 'xeyunknt'),
    'asian': (None, None, 'efyasiat', 'xefyasit'),
    'pacific_islander': (None, None, 'efynhpit', 'xefynhpt'),
    'two_or_more': (None, None, 'efy2mort', 'xefy2mot')
}


COMPLETERS_FIELDS = {
    'total_completers': 'cstotlt', 'men': 'cstotlm', 'women': 'cstotlw',
    'american_indian': 'csaiant', 'asian': 'csasiat', 'black': 'csbkaat',
    'hispanic': 'cshispt', 'pacific_islander': 'csnhpit', 'white': 'cswhitt',
    'two_or_more': 'cs2mort', 'race_unknown': 'csunknt',
    'nonresident': 'csnralt',
    'age_under_18': 'csund18', 'age_18_to_24': 'cs18_24',
    'age_25_to_39': 'cs25_39', 'age_40_plus': 'csabv40', 'age_unknown': 'csunkn'
}

COMPLETER_AWARD_LEVELS = {
    '2': 'certificate_1_to_4_years', '3': 'assc', '5': 'bach',
    '7': 'mast', '9': 'doct', '10': 'postgraduate_certificate',
    '11': 'certificate_under_12_weeks', '12': 'certificate_12_weeks_to_1_year'
}


def clean_characteristics(characteristics_dir: str = 'characteristicsdata',
                           year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''
    cleans institution characteristics data and returns complete characteristics data

    :param characteristics_dir: directory where raw enrollment data is located
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    '''
    warnings.filterwarnings('ignore', category=FutureWarning)
    sorted_files = sorted(os.listdir(characteristics_dir))
    rename_dict = VARIABLE_RENAME['characteristics']
    state_mappings = us.states.mapping('abbr', 'name') # get abbr -> names for states
    state_mappings['DC'] = 'District of Columbia' # add Washington D.C. to state mapping

    master_df = pd.DataFrame()

    for file in sorted_files:
        file_path = os.path.join(characteristics_dir, file)
        year_num = re.split(r'_|\.', f'{file}')[1]
        
        if year_range:
            year_iter = get_year_iter(subject='characteristics',
                                      year_range=year_range)
            if int(year_num) not in year_iter:
                continue

        df = pd.read_csv(file_path, dtype=str, index_col=False,
                         encoding_errors='replace', low_memory=False)
        df.columns = df.columns.str.lower().str.strip()
        
        if int(year_num) > 1998:
            if int(year_num) > 2008:
                filt_col = ['unitid', 'instnm', 'addr', 'city', 'stabbr', 'zip', 'webaddr', 'longitud', 'latitude']
            else:
                filt_col = ['unitid', 'instnm', 'addr', 'city', 'stabbr', 'zip', 'webaddr'] # long/lat NA for before 2008
        else:
            filt_col = ['unitid', 'instnm', 'addr', 'city', 'stabbr', 'zip'] # for years < 1999
        filt_col.extend(['control', 'iclevel', 'sector', 'hbcu', 'tribal',
                         'deggrant', 'locale', 'c21basic'])
        df_filtered = df.reindex(columns=filt_col).copy()
        
        for col in ['instnm', 'addr', 'city']:
            df_filtered[col] = df_filtered[col].str.title() # TitleCase
        df_filtered['year'] = int(year_num) # year identifier
        df_filtered['unitid'] = df_filtered['unitid'].astype(str).str.strip() # make id into string
        df_filtered['stabbr'] = df_filtered['stabbr'].map(state_mappings) # state abbreviation to state name
        for col in ['control', 'iclevel', 'sector', 'hbcu', 'tribal',
                    'deggrant', 'locale', 'c21basic']:
            df_filtered[col] = df_filtered[col].astype('string').str.strip()
        df_filtered = df_filtered.rename(columns=rename_dict)

        if int(year_num) < 1986:
            control_labels = {'0': 'Combined public and private', '1': 'Public',
                              '2': 'Private (profit status unspecified)'}
        else:
            control_labels = {'1': 'Public', '2': 'Private nonprofit',
                              '3': 'Private for-profit'}
        df_filtered['control'] = df_filtered['control_code'].map(control_labels)
        df_filtered['level'] = df_filtered['level_code'].map({
            '1': 'Four-year or above', '2': 'Two-year', '3': 'Less-than-two-year'
        })
        df_filtered['sector'] = df_filtered['sector_code'].map(SECTOR_LABELS)
        for code, name, start in (('hbcu_code', 'hbcu', 1992),
                                  ('tribal_code', 'tribal', 1993)):
            value = pd.Series(pd.NA, index=df_filtered.index, dtype='boolean')
            if int(year_num) >= start:
                value.loc[df_filtered[code] == '1'] = True
                value.loc[df_filtered[code] == '2'] = False
                if int(year_num) <= 1994:
                    # In these dictionaries a blank explicitly means "no";
                    # 1995-97 instead use missing/nonresponse conventions.
                    value.loc[df_filtered[code].isna()] = False
            df_filtered[name] = value
        df_filtered['degree_granting'] = df_filtered['degree_granting_code'].map(
            {'1': True, '2': False}).astype('boolean')
        scheme = ('legacy' if int(year_num) < 2005 else 'urban_centric')
        df_filtered['locale_scheme'] = scheme if int(year_num) >= 1995 else pd.NA
        master_df = pd.concat([master_df, df_filtered], ignore_index=True)
    
    return master_df


def clean_admissions(admissions_dir: str = 'admissionsdata',
                     year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''
    cleans yearly admissions data and returns complete admissions data
    
    :param admissions_dir: directory where raw admissions data is located
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    '''
    warnings.filterwarnings('ignore', category=FutureWarning)
    sorted_files = sorted(os.listdir(admissions_dir)) # unnecessary, but helps with error checking
    rename_dict = VARIABLE_RENAME['admissions']

    master_df = pd.DataFrame()
    
    for file in sorted_files:
        file_path = os.path.join(admissions_dir, file)
        year_num = re.split(r'_|\.', f'{file}')[1]
        
        if year_range:
            year_iter = get_year_iter(subject='admissions',
                                      year_range=year_range)
            if int(year_num) not in year_iter:
                continue

        df = pd.read_csv(file_path, dtype=str) # read in df
        df = df.rename(str.lower, axis='columns') # some df's have all uppercase, some have all lowercase
        df.columns = df.columns.str.strip() # some column names have right spaces
        
        cols_to_filter = [col for col in rename_dict.keys() if col in df.columns] # cols to filter per year
        df_filtered = df.reindex(columns=cols_to_filter)
        df_filtered = df_filtered.rename(columns=rename_dict) # rename cols

        for col in df_filtered.columns:
            if col == 'id':
                df_filtered[col] = df_filtered[col].astype(str).str.strip() # id str
            else:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

        if int(year_num) == 2001:
            df_filtered['men_enrolled'] = df_filtered['men_ft_enrolled'] + df_filtered['men_pt_enrolled']
            df_filtered['women_enrolled'] = df_filtered['women_ft_enrolled'] + df_filtered['women_pt_enrolled']
        if 'tot_applied' not in df_filtered.columns:
            df_filtered['tot_applied'] = df_filtered['men_applied'] + df_filtered['women_applied']
            df_filtered['tot_admitted'] = df_filtered['men_admitted'] + df_filtered['women_admitted']
            df_filtered['tot_enrolled'] = df_filtered['men_enrolled'] + df_filtered['women_enrolled']

        for i in ['men', 'women']:
            df_filtered[f'accept_rate_{i}'] = np.where(
            df_filtered[f'{i}_applied'] == 0,
            np.nan,
            (df_filtered[f'{i}_admitted'] / df_filtered[f'{i}_applied'] * 100)
            )
    
            df_filtered[f'yield_rate_{i}'] = np.where(
            df_filtered[f'{i}_admitted'] == 0,
            np.nan,
            (df_filtered[f'{i}_enrolled'] / df_filtered[f'{i}_admitted'] * 100)
            )
        
        df_filtered['year'] = int(year_num) # year identifier
        df_filtered['men_applied_share'] = df_filtered['men_applied'] / df_filtered['tot_applied'] * 100
        df_filtered['men_admitted_share'] = df_filtered['men_admitted'] / df_filtered['tot_admitted'] * 100

        master_df = pd.concat([master_df, df_filtered], ignore_index=True)
    
    # unneeded columns
    admissions_df = master_df.drop(columns=['women_applied', 'women_admitted', 'women_enrolled',
                                            'men_ft_enrolled', 'men_pt_enrolled', 'women_ft_enrolled', 'women_pt_enrolled'],
                                   errors='ignore')

    return admissions_df


def clean_enrollment(enrollment_dir: str = 'enrollmentdata', 
                     student_level: str = 'undergrad',
                     year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''
    cleans yearly enrollment data and returns complete student enrollment data

    :enrollment_dir: directory where raw enrollment data is located
    :student_level: level of enrollment; options include ['undergrad', 'grad']
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    '''
    warnings.filterwarnings('ignore', category=FutureWarning)
    sorted_files = sorted(os.listdir(enrollment_dir)) # unnecessary, but helps with error checking
    rename_dict = VARIABLE_RENAME['enrollment']

    grad_rules = [
        (lambda y: y in [1984,1985], 'line in [11,25,10,24]'),
        (lambda y: (y == 1986) or (y in range(1990,1999)), 'line in [14,28,9,10,23,24]'),
        (lambda y: y in [1987,1988,1989], 'line in [14,28]'),
        (lambda y: y == 1999, 'line in [32,52,16]'),
        (lambda y:  y in range(2000,2009), 'line in [11,25,9,23]'),
        (lambda y: y in range(2009,2025), 'line in [11,25]')
    ]
    
    df_list = []  

    for file in sorted_files:
        file_path = os.path.join(enrollment_dir, file)
        year_num = re.split(r'_|\.', f'{file}')[1]
        
        if year_range:
            year_iter = get_year_iter(subject='enrollment',
                                      year_range=year_range)
            if int(year_num) not in year_iter:
                continue

        df = pd.read_csv(file_path, dtype=str) # read in df
        df = df.rename(str.lower, axis='columns') # some df's have all uppercase, some have all lowercase

        if all(col in df.columns for col in ['efrace10', 'eftotlm']):
            cols_to_filter = [col for col in rename_dict.keys() if 
                              (col in df.columns) and ('efrace' not in col)] # annoying thing with duplicate cols in 
                                                                                # some years
        else:
            cols_to_filter = [col for col in rename_dict.keys() if col in df.columns]
            

        df_filtered = df.reindex(columns=cols_to_filter)
        df_filtered = df_filtered.rename(columns=rename_dict) # rename cols

        for col in df_filtered.columns:
            if col == 'id':
                df_filtered[col] = df_filtered[col].astype(str).str.strip() # id identifier
            else:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

        if student_level == 'undergrad':
            if int(year_num) < 1986:
                student_query = 'line == 1 or line == 15' # captures total full-time and total part-time undergrads, respectively
            else:
                student_query = 'line == 8 or line == 22' 
        elif student_level == 'grad':
            for cond,frmt in grad_rules:
                if cond(int(year_num)):
                    student_query = frmt # captures full-time and part-time graduate and first-professional students
                    break
            else:
                raise ValueError(f'No formatted rule for year {year_num}')
        else:
            raise ValueError("student_level must be 'undergrad' or 'grad' ")

        students = df_filtered.query(student_query) # filter data to total students
        
        if 'wtmen' not in students.columns:
            cols_to_sum = ['totmen', 'totwomen']
        else:
            cols_to_sum = ['totmen', 'totwomen', 'wtmen', 'wtwomen','bkmen', 'bkwomen','hspmen', 'hspwomen','asnmen', 'asnwomen']
        
        students_by_inst = students.groupby('id')[cols_to_sum].sum() # sum full-time and part-time students by school

        # Calculate male student share without using eval
        students_by_inst['totmen_share'] = students_by_inst['totmen'] / (students_by_inst['totmen'] + students_by_inst['totwomen']) * 100 # male student share

        # Resetting index here to be compatible with the previous version,
        # but I'm not sure why it's necessary.
        students_by_inst = students_by_inst.reset_index()

        students_by_inst['year'] = int(year_num) # get year marker for each set
        students_by_inst['studentlevel'] = student_level # get student level identifier

        if 'wtmen' in students_by_inst.columns:
            for attr in ['wt', 'bk', 'hsp', 'asn']:
                # Calculate race share breakdowns without using eval
                students_by_inst[f'tot{attr}_share'] = (students_by_inst[f'{attr}men'] + students_by_inst[f'{attr}women']) / (students_by_inst['totmen'] + students_by_inst['totwomen']) * 100

        df_list.append(students_by_inst)

    
    master_df = pd.concat(df_list, ignore_index=True)

    return master_df


def clean_twelve_month_enrollment(enrollment_dir: str = 'twelve_month_enrollmentdata',
                                  student_level: str = 'undergrad',
                                  year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''Return unduplicated EFFY headcounts for the selected source level.

    Through 2019 LSTUDY identifies level totals; since 2020 EFFYALEV has
    many nested undergraduate detail rows and only codes 1, 2, and 12
    represent the all-students, UG, and graduate totals respectively.
    Pre-2011 first-professional students are a separate category, not
    implicitly added to graduate headcounts.
    '''
    levels = {'undergrad', 'grad', 'first_professional', 'total', 'all'}
    if student_level not in levels:
        raise ValueError(f'student_level must be one of {sorted(levels)}')
    requested = set(get_year_iter('twelve_month_enrollment', year_range)) if year_range is not None else None
    if student_level == 'first_professional' and (requested is None or any(y > 2010 for y in requested)):
        raise ValueError('first_professional is separate only for 2002-2010; select those years')

    frames = []
    found = set()
    for file in sorted(os.listdir(enrollment_dir)):
        match = re.fullmatch(r'twelve_month_enrollment_(\d{4})\.csv', file, flags=re.IGNORECASE)
        if not match:
            continue
        year = int(match.group(1))
        if requested is not None and year not in requested:
            continue
        if not 2002 <= year <= 2025:
            continue
        early_race = year < 2008
        level_col = 'effyalev' if year >= 2020 else 'lstudy'
        level_codes = ({'total': '1', 'undergrad': '2', 'grad': '12'}
                       if year >= 2020 else
                       {'total': '999', 'undergrad': '1', 'first_professional': '2', 'grad': '3'})
        fields = [(name, pair[0 if early_race else 2], pair[1 if early_race else 3])
                  for name, pair in E12_FIELDS.items()]
        desired = {v for _, source, flag in fields for v in (source, flag) if v}
        desired.update({'unitid', level_col})
        df = pd.read_csv(os.path.join(enrollment_dir, file), dtype=str,
                         index_col=False, low_memory=False, encoding_errors='replace',
                         usecols=lambda c: c.strip().lower() in desired)
        df.columns = df.columns.str.lower().str.strip()
        required = {'unitid', level_col, *(source for name, source, _ in fields
                                           if name in ('total_students', 'men', 'women'))}
        if not required.issubset(df.columns):
            raise ValueError(f'{file} is missing E12 headcount fields: {sorted(required - set(df.columns))}')
        df = df.reindex(columns=sorted(desired))
        chosen = (set(level_codes.values()) if student_level == 'all'
                  else {level_codes[student_level]})
        df = df.loc[df[level_col].str.strip().isin(chosen)].copy()
        output = pd.DataFrame({'id': df['unitid'].str.strip(), 'year': year,
                               'period_start_year': year - 1,
                               'student_level': df[level_col].str.strip().map(
                                   {code: name for name, code in level_codes.items()}),
                               'source_level_code': df[level_col].str.strip(),
                               'level_code_system': level_col})
        for name, source, flag in fields:
            output[name] = (pd.to_numeric(df[source], errors='coerce')
                            if source else np.nan)
            output[name + '_status'] = (df[flag].astype('string').str.strip()
                                        if flag in df else pd.Series(pd.NA, index=df.index, dtype='string'))
        frames.append(output)
        found.add(year)

    if requested is not None and requested - found:
        raise FileNotFoundError(f'Missing downloaded 12-month enrollment years: {sorted(requested - found)}')
    if not frames:
        raise FileNotFoundError(f'No 12-month enrollment CSV files found in {enrollment_dir}')
    return pd.concat(frames, ignore_index=True)


def clean_retention(retention_dir: str = 'retentiondata',
                    year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''Return one row per institution and retention year from Fall Enrollment D.

    Rates are NCES's published percentages, not recomputed from counts. The
    preceding fall's entering cohort is ``cohort_year``. Cohort counts were not
    included until 2007, and study-abroad inclusions first appear in 2016;
    unavailable fields remain missing rather than being treated as zero.
    '''
    rename_dict = VARIABLE_RENAME['retention']
    status_dict = {'x' + raw: name + '_status' for raw, name in rename_dict.items()}
    requested = set(get_year_iter('retention', year_range)) if year_range is not None else None
    frames = []
    found = set()

    for file in sorted(os.listdir(retention_dir)):
        match = re.fullmatch(r'retention_(\d{4})\.csv', file, flags=re.IGNORECASE)
        if not match:
            continue
        year = int(match.group(1))
        if requested is not None and year not in requested:
            continue
        if not 2003 <= year <= 2024:
            continue

        df = pd.read_csv(os.path.join(retention_dir, file), dtype=str)
        df.columns = df.columns.str.lower().str.strip()
        required = {'unitid', 'ret_pcf', 'ret_pcp'}
        if not required.issubset(df.columns):
            raise ValueError(f'{file} is missing retention fields: {sorted(required - set(df.columns))}')

        df = df.reindex(columns=['unitid', *rename_dict, *status_dict])
        df = df.rename(columns={'unitid': 'id', **rename_dict, **status_dict})
        df['id'] = df['id'].str.strip()
        for name in rename_dict.values():
            df[name] = pd.to_numeric(df[name], errors='coerce')
        for name in status_dict.values():
            df[name] = df[name].astype('string').str.strip()
        df.insert(1, 'year', year)
        df.insert(2, 'cohort_year', year - 1)
        frames.append(df)
        found.add(year)

    if requested is not None and requested - found:
        raise FileNotFoundError(f'Missing downloaded retention years: {sorted(requested - found)}')
    if not frames:
        raise FileNotFoundError(f'No retention CSV files found in {retention_dir}')
    return pd.concat(frames, ignore_index=True)


def clean_tuition(tuition_dir: str = 'tuitiondata',
                  program_dir: str = 'tuition_programdata',
                  reporter: str = 'both',
                  year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''Harmonize published tuition/fees by institution, price year, and reporter.

    Before 2024 the academic and program files are separate; COST1_2024
    contains both. CHG*3 refers to the price year in the filename (not the
    earlier years also included in the source's rolling charge history).
    '''
    if reporter not in ('academic', 'program', 'both'):
        raise ValueError("reporter must be 'academic', 'program', or 'both'")
    requested = set(get_year_iter('tuition', year_range)) if year_range is not None else None
    all_fields = {raw: target for spec in TUITION_FIELDS.values()
                  for raw, (target, _) in spec.items()}
    flags = {flag: target + '_status' for spec in TUITION_FIELDS.values()
             for target, flag in spec.values()}
    output_cols = ['id', 'year', 'reporter', 'largest_program_cip',
                   *all_fields.values(), *flags.values()]
    frames = []

    for kind, directory, prefix in (
        ('academic', tuition_dir, 'tuition'),
        ('program', program_dir, 'tuition_program')
    ):
        if reporter not in (kind, 'both'):
            continue
        found = set()
        for file in sorted(os.listdir(directory)):
            match = re.fullmatch(rf'{prefix}_(\d{{4}})\.csv', file, flags=re.IGNORECASE)
            if not match:
                continue
            year = int(match.group(1))
            if requested is not None and year not in requested:
                continue
            if not 2000 <= year <= 2024:
                continue
            df = pd.read_csv(os.path.join(directory, file), dtype=str,
                             index_col=False, low_memory=False)
            df.columns = df.columns.str.lower().str.strip()
            required = {'unitid', 'chg1ay3' if kind == 'academic' else 'chg1py3'}
            if year == 2024:
                required.add('cipcode1')
            if not required.issubset(df.columns):
                raise ValueError(f'{file} is missing price fields: {sorted(required - set(df.columns))}')

            if year == 2024:
                # Cost I combines the old AY/PY tables; CIPCODE1 is -2 for
                # academic reporters and a field-of-study code for programs.
                is_academic = df['cipcode1'].str.strip() == '-2'
                df = df.loc[is_academic if kind == 'academic' else ~is_academic].copy()
            elif kind == 'program':
                # Some early PY extracts also contain academic reporters,
                # whose program CIP is the NCES not-applicable code -2.
                df = df.loc[df['cipcode1'].str.strip() != '-2'].copy()
            elif year == 2001:
                # IC2001_AY is a universe-wide extract, including program
                # reporters with entirely empty academic price fields.
                academic_values = ['tuition1', 'fee1', 'chg1ay3']
                df = df.loc[df.reindex(columns=academic_values).notna().any(axis=1)].copy()

            subset = df.reindex(columns=['unitid', 'cipcode1', *all_fields, *flags])
            subset = subset.rename(columns={'unitid': 'id', 'cipcode1': 'largest_program_cip',
                                            **all_fields, **flags})
            subset['id'] = subset['id'].str.strip()
            subset['largest_program_cip'] = (subset['largest_program_cip']
                                             .astype('string').str.strip()
                                             .replace({'-1': pd.NA, '-2': pd.NA}))
            for name in all_fields.values():
                subset[name] = pd.to_numeric(subset[name], errors='coerce')
            for name in flags.values():
                subset[name] = subset[name].astype('string').str.strip()
            subset.insert(1, 'year', year)
            subset.insert(2, 'reporter', kind)
            frames.append(subset.reindex(columns=output_cols))
            found.add(year)
        if requested is not None and requested - found:
            raise FileNotFoundError(f'Missing downloaded {kind} tuition years: {sorted(requested - found)}')

    if not frames:
        raise FileNotFoundError('No tuition CSV files found for the requested reporter(s)')
    return pd.concat(frames, ignore_index=True)


def clean_student_aid(aid_dir: str = 'student_aiddata',
                      net_price_dir: str = 'student_aid_net_pricedata',
                      reporter: str = 'both',
                      year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''Clean SFA grants and loans without conflating FTFT and all-UG groups.

    ``year`` is the END of the aid period (e.g. SFA2324 -> 2024), not the
    year the file was released. The early academic/program denominator names
    differ from the 2007-08+ common SCUGFFN/SCUGRAD fields.
    '''
    if reporter not in ('academic', 'program', 'both'):
        raise ValueError("reporter must be 'academic', 'program', or 'both'")
    requested = set(get_year_iter('student_aid', year_range)) if year_range is not None else None
    flags = {'x' + raw: name + '_status' for raw, name in AID_FIELDS.items()}
    frames = []
    found = set()

    for file in sorted(os.listdir(aid_dir)):
        match = re.fullmatch(r'student_aid_(\d{4})\.csv', file, flags=re.IGNORECASE)
        if not match:
            continue
        year = int(match.group(1))
        if requested is not None and year not in requested:
            continue
        if not 2002 <= year <= 2024:
            continue

        df = pd.read_csv(os.path.join(aid_dir, file), dtype=str,
                         index_col=False, low_memory=False)
        df.columns = df.columns.str.lower().str.strip()
        required = {'unitid', 'scfa1n', 'scfa2', 'scfy1n', 'scfy2', 'anyaidn'}
        if not required.issubset(df.columns):
            raise ValueError(f'{file} is missing aid fields: {sorted(required - set(df.columns))}')
        academic = df[['scfa1n', 'scfa2']].notna().any(axis=1)
        program = df[['scfy1n', 'scfy2']].notna().any(axis=1)
        if (academic == program).any():
            raise ValueError(f'{file} has ambiguous academic/program reporting rows')
        if reporter != 'both':
            chosen = academic if reporter == 'academic' else program
            df = df.loc[chosen].copy()
            academic = academic.loc[chosen]

        df = df.reindex(columns=['unitid', 'scugffn', 'xscugffn', 'scugrad', 'xscugrad',
                                 'scfa1n', 'xscfa1n', 'scfy1n', 'xscfy1n',
                                 'scfa2', 'xscfa2', 'scfy2', 'xscfy2',
                                 *AID_FIELDS, *flags])
        output = pd.DataFrame({'id': df['unitid'].str.strip(), 'year': year,
                               'aid_year_start': year - 1,
                               'reporter': np.where(academic, 'academic', 'program')})
        for common, fallback_academic, fallback_program, name in (
            ('scugffn', 'scfa1n', 'scfy1n', 'ftft_students'),
            ('scugrad', 'scfa2', 'scfy2', 'ug_students')
        ):
            newer = pd.to_numeric(df[common], errors='coerce')
            older = pd.to_numeric(df[fallback_academic].where(academic, df[fallback_program]),
                                  errors='coerce')
            output[name] = newer.where(newer.notna(), older)
            old_status = df['x' + fallback_academic].where(academic, df['x' + fallback_program])
            output[name + '_status'] = df['x' + common].where(newer.notna(), old_status).astype('string').str.strip()

        for raw, name in AID_FIELDS.items():
            output[name] = pd.to_numeric(df[raw], errors='coerce')
            output[name + '_status'] = df['x' + raw].astype('string').str.strip()
        if year == 2024:
            cost_path = os.path.join(net_price_dir, 'student_aid_net_price_2024.csv')
            cost = pd.read_csv(cost_path, dtype=str, index_col=False, low_memory=False)
            cost.columns = cost.columns.str.lower().str.strip()
            needed = {'unitid', 'npist2', 'xnpist2'}
            if not needed.issubset(cost.columns):
                raise ValueError(f'{cost_path} is missing Cost II net price fields')
            cost = cost.loc[:, ['unitid', 'npist2', 'xnpist2']]
            cost['unitid'] = cost['unitid'].str.strip()
            cost['npist2'] = pd.to_numeric(cost['npist2'], errors='coerce')
            cost['xnpist2'] = cost['xnpist2'].astype('string').str.strip()
            output = output.drop(columns=['ftft_net_price', 'ftft_net_price_status'])
            output = output.merge(cost.rename(columns={
                'unitid': 'id', 'npist2': 'ftft_net_price',
                'xnpist2': 'ftft_net_price_status'
            }), on='id', how='left', validate='one_to_one')
        frames.append(output)
        found.add(year)

    if requested is not None and requested - found:
        raise FileNotFoundError(f'Missing downloaded student aid years: {sorted(requested - found)}')
    if not frames:
        raise FileNotFoundError(f'No student aid CSV files found in {aid_dir}')
    ordered = ['id', 'year', 'aid_year_start', 'reporter', 'ftft_students', 'ug_students',
               *AID_FIELDS.values(), 'ftft_students_status', 'ug_students_status',
               *(name + '_status' for name in AID_FIELDS.values())]
    return pd.concat(frames, ignore_index=True).reindex(columns=ordered)


def clean_veterans_aid(aid_dir: str = 'veterans_aiddata',
                       year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''Preserve undergraduate and graduate GI Bill / DoD benefit measures.'''
    requested = set(get_year_iter('veterans_aid', year_range)) if year_range is not None else None
    flags = {'x' + raw: name + '_status' for raw, name in VETERANS_AID_FIELDS.items()}
    frames = []
    found = set()

    for file in sorted(os.listdir(aid_dir)):
        match = re.fullmatch(r'veterans_aid_(\d{4})\.csv', file, flags=re.IGNORECASE)
        if not match:
            continue
        year = int(match.group(1))
        if requested is not None and year not in requested:
            continue
        if not 2014 <= year <= 2024:
            continue
        df = pd.read_csv(os.path.join(aid_dir, file), dtype=str,
                         index_col=False, low_memory=False)
        df.columns = df.columns.str.lower().str.strip()
        required = {'unitid', 'ugpo9_n', 'gpo9_n', 'ugdod_n', 'gdod_n'}
        if not required.issubset(df.columns):
            raise ValueError(f'{file} is missing military aid fields: {sorted(required - set(df.columns))}')
        df = df.reindex(columns=['unitid', *VETERANS_AID_FIELDS, *flags])
        df = df.rename(columns={'unitid': 'id', **VETERANS_AID_FIELDS, **flags})
        df['id'] = df['id'].str.strip()
        for name in VETERANS_AID_FIELDS.values():
            df[name] = pd.to_numeric(df[name], errors='coerce')
        for name in flags.values():
            df[name] = df[name].astype('string').str.strip()
        df.insert(1, 'year', year)
        df.insert(2, 'aid_year_start', year - 1)
        frames.append(df)
        found.add(year)

    if requested is not None and requested - found:
        raise FileNotFoundError(f'Missing downloaded veterans aid years: {sorted(requested - found)}')
    if not frames:
        raise FileNotFoundError(f'No veterans aid CSV files found in {aid_dir}')
    return pd.concat(frames, ignore_index=True)


def clean_completion(completion_dir: str = 'completiondata', 
                      level: str = 'bach',
                      year_range: Optional[Union[Tuple[int,int], List[int], int]] = None,
                      major: str = 'both') -> pd.DataFrame:
    '''
    cleans yearly completion data and returns complete completions data

    :param completion_dir: directory where raw completion data is located
    :param level: level of degree, options include ['assc', 'bach', 'mast', 'doct']
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    :major: 'first', 'second', or 'both'. MAJORNUM is available from 2001;
      earlier files have no first/second-major identifier.
    '''
    if major not in ('first', 'second', 'both'):
        raise ValueError("major must be 'first', 'second', or 'both'")
    warnings.filterwarnings('ignore', category=FutureWarning)
    sorted_files = sorted(os.listdir(completion_dir)) # unnecessary, but helps with error checking
    rename_dict = VARIABLE_RENAME['completion']

    deglevel_rules = [
        (lambda l,y: l == 'assc', 'awlevel == 3'),
        (lambda l,y: l == 'bach', 'awlevel == 5'),
        (lambda l,y: l == 'mast', 'awlevel == 7'),
        (lambda l,y: (l == 'doct') and (y < 2010), 'awlevel == 9'),
        (lambda l,y: (l == 'doct') and (y >= 2010), 'awlevel >= 17 and awlevel <= 19')
    ]
    
    master_df = pd.DataFrame()

    for file in sorted_files:
        file_path = os.path.join(completion_dir, file)
        year_num = re.split(r'_|\.', f'{file}')[1]
        
        if year_range:
            year_iter = get_year_iter(subject='completion',
                                      year_range=year_range)
            if int(year_num) not in year_iter:
                continue
        
        df = pd.read_csv(file_path, dtype=str, index_col=False, low_memory=False,
                         usecols=lambda c: c.lower().strip() in rename_dict or c.lower().strip() == 'majornum')
        df.columns = df.columns.str.lower().str.strip()

        if int(year_num) < 2001:
            if major != 'both':
                raise ValueError(f'{file}: first/second major was not identified before 2001')
        else:
            if 'majornum' not in df.columns:
                raise ValueError(f'{file}: expected MAJORNUM for first/second majors')
            if major != 'both':
                df = df.loc[df['majornum'].str.strip() == ('1' if major == 'first' else '2')]
        
        if all(col in df.columns for col in ['crace10', 'ctotalm']):
            cols_to_filter = [col for col in rename_dict.keys() if 
                              (col in df.columns) and ('crace' not in col)] # annoying thing with duplicate cols in 
                                                                                # some years
        else:
            cols_to_filter = [col for col in rename_dict.keys() if col in df.columns]

        df_filtered = df.reindex(columns=cols_to_filter)
        df_filtered = df_filtered.rename(columns=rename_dict)
        df_filtered['id'] = df_filtered['id'].str.strip()
        df_filtered['cip'] = df_filtered['cip'].str.strip()
        for col in df_filtered:
            if col not in ['id', 'cip']:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
        
        for cond,frmt in deglevel_rules:
            if cond(level, int(year_num)):
                level_query = frmt
                break
        else:
            raise ValueError("level must be 'assc', 'bach', 'mast' or 'doct'") 
        
        completions = df_filtered.query(level_query)
        race_cols = [col for col in completions.columns if 'men' in col] # race columns to group
        completions = completions.groupby(['id', 'cip'])[race_cols].sum().reset_index()

        completions = completions.eval('totmen_share = totmen / (totmen + totwomen) * 100') # maleshare within each major
        if 'wtmen' in completions.columns:
            for attr in ['wt', 'bk', 'hsp', 'asn']:
                eval_str = f'tot{attr}_share = ({attr}men + {attr}women) / (totmen + totwomen) * 100' # race share breakdowns
                completions = completions.eval(eval_str)
        
        completions['deglevel'] = level # adds level identifier
        completions['major_type'] = (major if int(year_num) >= 2001 else 'unspecified')
        completions['year'] = int(year_num) # adds year identifier
        
        master_df = pd.concat([master_df, completions], ignore_index=True)

    return master_df


def clean_completers(completers_dir: str = 'completersdata',
                     award_dir: str = 'completers_by_awarddata',
                     degree_level: str = 'all',
                     year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''Distinct *people* across all awards (B) or within each award level (C).

    C's age and level data are not summed into B: one student can receive
    awards at multiple levels in the same reporting period.
    '''
    choices = {'all', 'award_levels', 'assc', 'bach', 'mast', 'doct'}
    if degree_level not in choices:
        raise ValueError(f'degree_level must be one of {sorted(choices)}')
    requested = set(get_year_iter('completers', year_range)) if year_range is not None else None
    part = 'B' if degree_level == 'all' else 'C'
    directory = completers_dir if part == 'B' else award_dir
    prefix = 'completers' if part == 'B' else 'completers_by_award'
    fields = set(COMPLETERS_FIELDS.values())
    flags = {'x' + field for field in fields}
    frames = []
    found = set()

    for file in sorted(os.listdir(directory)):
        match = re.fullmatch(rf'{prefix}_(\d{{4}})\.csv', file, flags=re.IGNORECASE)
        if not match:
            continue
        year = int(match.group(1))
        if requested is not None and year not in requested:
            continue
        if not 2012 <= year <= 2025:
            continue
        cols = fields | flags | {'unitid', 'awlevelc'}
        df = pd.read_csv(os.path.join(directory, file), dtype=str,
                         index_col=False, low_memory=False,
                         usecols=lambda c: c.lower().strip() in cols)
        df.columns = df.columns.str.lower().str.strip()
        required = {'unitid', 'cstotlt', 'cstotlm', 'cstotlw'}
        if part == 'C':
            required.add('awlevelc')
        if not required.issubset(df.columns):
            raise ValueError(f'{file} is missing completer fields: {sorted(required - set(df.columns))}')
        df = df.reindex(columns=sorted(cols))
        source_code = (df['awlevelc'].astype('string').str.strip() if part == 'C'
                       else pd.Series(pd.NA, index=df.index, dtype='string'))
        code = source_code.str.lstrip('0').replace('', pd.NA)
        if part == 'C' and degree_level != 'award_levels':
            wanted = {'assc': '3', 'bach': '5', 'mast': '7', 'doct': '9'}[degree_level]
            selected = code == wanted
            df = df.loc[selected].copy()
            source_code = source_code.loc[selected]
            code = code.loc[selected]
        award = code.map(COMPLETER_AWARD_LEVELS)
        if part == 'C' and year < 2020:
            award = award.mask(code.eq('1').fillna(False), 'certificate_under_1_year')
        output = pd.DataFrame({'id': df['unitid'].str.strip(), 'year': year,
                               'period_start_year': year - 1,
                               'source_table': part,
                               'award_level': award if part == 'C' else 'all_awards',
                               'award_level_code': code,
                               'source_award_code': source_code})
        for name, raw in COMPLETERS_FIELDS.items():
            output[name] = pd.to_numeric(df[raw], errors='coerce')
            output[name + '_status'] = df['x' + raw].astype('string').str.strip()
        frames.append(output)
        found.add(year)

    if requested is not None and requested - found:
        raise FileNotFoundError(f'Missing downloaded completer years: {sorted(requested - found)}')
    if not frames:
        raise FileNotFoundError(f'No completer CSV files found in {directory}')
    return pd.concat(frames, ignore_index=True)


def clean_cip_html(file_path: str) -> Dict[str,str]:
    '''
    returns dict of CIP subject code:label pairs for a given year's CIP dictionary html.
    
    :param file_path: string path to CIP data dictionary html
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    '''
    with open(file_path) as filehandle:
        soup = BeautifulSoup(filehandle, 'html.parser')
        rows = soup.find_all('tr', attrs={'bgcolor': ['White', 'Silver']})
        dat_rows = rows[1:]
        label_dict = {}
        for row in dat_rows:
            cells = row.find_all('td')
            if len(cells) > 1:
                label = cells[0].text.strip()
                val = cells[1].text.strip()
                if label == 'Totals':
                    break # end of relevant table
                else:
                    label_dict[val] = label
        return label_dict


def clean_cip(cip_codes_dir: str = 'cipdata',
              year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''
    cleans yearly CIP data and returns full dataframe

    :param cip_codes_dir: directory where raw CIP data is located
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    '''
    warnings.filterwarnings('ignore', category=FutureWarning)
    warnings.filterwarnings('ignore', category=UserWarning)
    sorted_files = sorted(os.listdir(cip_codes_dir))
    master_df = pd.DataFrame()

    for file in sorted_files:
        file_path = os.path.join(cip_codes_dir, file)
        year_num = re.split(r'_|\.', f'{file}')[1]
        
        if year_range:
            year_iter = get_year_iter(subject='cip',
                                      year_range=year_range)
            if int(year_num) not in year_iter:
                continue
        
        ext = re.split(r'_|\.', f'{file}')[2]
        if ext == 'html':
            html_dict = clean_cip_html(file_path=file_path)
            df = pd.DataFrame({'cip_description' : html_dict.values(),
                               'cip' : html_dict.keys()}, dtype=str)
        else:
            df = pd.read_excel(file_path, sheet_name='Frequencies', dtype=str)
            df = df.rename(columns=str.lower)
            df = df.query('varname == "CIPCODE" or varname == "Cipcode"').loc[:, ['codevalue', 'valuelabel']]
            df = df.rename(columns={'codevalue' : 'cip', 'valuelabel' : 'cip_description'})
        df['year'] = int(year_num) # year identifier
        
        master_df = pd.concat([master_df, df], ignore_index=True)
        master_df['cip'] = master_df['cip'].astype(str).str.strip() # strip spaces
        master_df['cip_description'] = master_df['cip_description'].str.title().replace(r'^(\d+)\s-\s', '', regex=True)

    return master_df


def clean_graduation(graduation_dir: str = 'graduationdata', 
                     deg_level: str = 'bach',
                     year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''
    cleans yearly graduation data and returns complete graduation data

    :graduation_dir: directory where raw completion data is located
    :deg_level: degree level; options include ['assc', 'bach']
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    '''
    warnings.filterwarnings('ignore', category=FutureWarning)
    sorted_files = sorted(os.listdir(graduation_dir)) # unnecessary, but helps with error checking
    rename_dict = VARIABLE_RENAME['graduation']
    master_df = pd.DataFrame()

    for file in sorted_files:
        file_path = os.path.join(graduation_dir, file)
        year_num = re.split(r'_|\.', f'{file}')[1]
        
        if year_range:
            year_iter = get_year_iter(subject='graduation',
                                      year_range=year_range)
            if int(year_num) not in year_iter:
                continue
        
        df = pd.read_csv(file_path, dtype=str) # read in df
        df = df.rename(str.lower, axis='columns') # some df's have all uppercase, some have all lowercase

        if all(col in df.columns for col in ['grrace10', 'grtotlm']):
            cols_to_filter = [col for col in rename_dict.keys() if 
                              (col in df.columns) and ('grrace' not in col)] # annoying thing with duplicate cols in 
                                                                                # some years
        else:
            cols_to_filter = [col for col in rename_dict.keys() if col in df.columns]
        df_filtered = df.reindex(columns=cols_to_filter)
        df_filtered = df_filtered.rename(columns=rename_dict)
        
        for col in df_filtered.columns:
            if col != 'id':
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce') # convert cols to float
        
        if deg_level == 'bach':
            deg_query = '(8 <= grtype <= 9) and (12 <= chrtstat <= 13) and section == 2'
            denom = 8
            num = 9
        elif deg_level == 'assc':
            deg_query = '(29 <= grtype <= 30) and (12 <= chrtstat <= 13) and section == 4'
            denom = 29
            num = 30
        else:
            raise ValueError("deg_level must be 'assc', 'bach'")

        grads = df_filtered.query(deg_query)
        pivoted_grads = grads.pivot(index='id', columns='grtype', values=['totmen', 'totwomen', # get cohort and grads
                                                                                        'wtmen', 'wtwomen',
                                                                                        'bkmen', 'bkwomen',
                                                                                        'hspmen', 'hspwomen',
                                                                                        'asnmen', 'asnwomen'])
        for i in ['tot', 'wt', 'bk', 'hsp', 'asn']:
            pivoted_grads[f'gradrate_{i}men'] = (pivoted_grads[f'{i}men'][num] /    
                                                     pivoted_grads[f'{i}men'][denom] * 100)
            
            pivoted_grads[f'gradrate_{i}women'] = (pivoted_grads[f'{i}women'][num] / 
                                                     pivoted_grads[f'{i}women'][denom] * 100) # grad rates
        pivoted_grads = pivoted_grads.reset_index()

        rnm_columns = pivoted_grads.columns.droplevel(1).tolist() # renaming columns
        for i in range(len(rnm_columns)):
            if rnm_columns[i] == rnm_columns[i - 1]:
                rnm_columns[i] = f'{rnm_columns[i]}_graduated'
        pivoted_grads.columns = rnm_columns
        
        pivoted_grads['year'] = int(year_num) # get year identifiers
        pivoted_grads['deglevel'] = deg_level

        master_df = pd.concat([master_df, pivoted_grads], ignore_index=True)
    
    return master_df
        

CLEANERS = {
    'characteristics' : clean_characteristics,
    'admissions' : clean_admissions,
    'enrollment' : clean_enrollment,
    'twelve_month_enrollment' : clean_twelve_month_enrollment,
    'retention' : clean_retention,
    'tuition' : clean_tuition,
    'student_aid' : clean_student_aid,
    'veterans_aid' : clean_veterans_aid,
    'completion' : clean_completion,
    'completers' : clean_completers,
    'cip' : clean_cip,
    'graduation' : clean_graduation
}
