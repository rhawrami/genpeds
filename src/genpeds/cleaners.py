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
          'longitud' : 'longitude', 'latitude' : 'latitude'
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

    dtypes = {
        'unitid' : str, 'instnm' : str, 'addr' : str, 'city' : str, 
        'stabbr' : str, 'zip' : str, 'webaddr' : str, 'longitud' : str, 'latitude' : str
    }
    for file in sorted_files:
        file_path = os.path.join(characteristics_dir, file)
        year_num = re.split(r'_|\.', f'{file}')[1]
        
        if year_range:
            year_iter = get_year_iter(subject='characteristics',
                                      year_range=year_range)
            if int(year_num) not in year_iter:
                continue

        df = pd.read_csv(file_path, dtype=dtypes, encoding_errors='replace', low_memory=False)
        df = df.rename(str.lower, axis='columns')
        
        if int(year_num) > 1998:
            if int(year_num) > 2008:
                filt_col = ['unitid', 'instnm', 'addr', 'city', 'stabbr', 'zip', 'webaddr', 'longitud', 'latitude']
            else:
                filt_col = ['unitid', 'instnm', 'addr', 'city', 'stabbr', 'zip', 'webaddr'] # long/lat NA for before 2008
        else:
            filt_col = ['unitid', 'instnm', 'addr', 'city', 'stabbr', 'zip'] # for years < 1999
        df_filtered = df.loc[:, filt_col]
        
        for col in ['instnm', 'addr', 'city']:
            df_filtered[col] = df_filtered[col].str.title() # TitleCase
        df_filtered['year'] = int(year_num) # year identifier
        df_filtered['unitid'] = df_filtered['unitid'].astype(str).str.strip() # make id into string
        df_filtered['stabbr'] = df_filtered['stabbr'].map(state_mappings) # state abbreviation to state name
        master_df = pd.concat([master_df, df_filtered], ignore_index=True)
    
    master_df = master_df.rename(columns=rename_dict) # rename vars
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
        (lambda y: y in range(2009,2024), 'line in [11,25]')
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


def clean_completion(completion_dir: str = 'completiondata', 
                     level: str = 'bach',
                     year_range: Optional[Union[Tuple[int,int], List[int], int]] = None) -> pd.DataFrame:
    '''
    cleans yearly completion data and returns complete completions data

    :param completion_dir: directory where raw completion data is located
    :param level: level of degree, options include ['assc', 'bach', 'mast', 'doct']
    :year_range: range of years to clean data from. This is in case that you have more data than you want to actually clean and return
    '''
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
        
        df = pd.read_csv(file_path, dtype=str) # read in df
        df = df.rename(str.lower, axis='columns') # some df's have all uppercase, some have all lowercase
        
        if all(col in df.columns for col in ['crace10', 'ctotalm']):
            cols_to_filter = [col for col in rename_dict.keys() if 
                              (col in df.columns) and ('crace' not in col)] # annoying thing with duplicate cols in 
                                                                                # some years
        else:
            cols_to_filter = [col for col in rename_dict.keys() if col in df.columns]

        df_filtered = df.reindex(columns=cols_to_filter)
        df_filtered = df_filtered.rename(columns=rename_dict)
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
        completions['year'] = int(year_num) # adds year identifier
        completions['cip'] = completions['cip'].astype(str).str.strip()
        
        master_df = pd.concat([master_df, completions], ignore_index=True)

    return master_df


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
            raise  ValueError("deg_level must be 'assc', 'bach', 'mast' or 'doct'")

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
    'completion' : clean_completion,
    'cip' : clean_cip,
    'graduation' : clean_graduation
}
