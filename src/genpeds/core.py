import shutil
import json
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List, Union

import pandas as pd

from genpeds.downloader import scrape_ipeds_data
from genpeds.cleaners import CLEANERS


class IPDS(ABC):
    subject = None
    
    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        pkg_dir = Path(__file__).parent
        endpoint_path = pkg_dir / 'cfg.json'
        with open(endpoint_path, 'r') as cfgjf:
            cfg = json.load(cfgjf)

        self.year_range = year_range # year range by user
        self.description = cfg[self.subject]['description']
        self.available_years = cfg[self.subject]['years_available']
        self.variable_dict = cfg[self.subject]['variables']


    def get_description(self) -> str:
        '''returns description of the subject data.'''
        return self.description
    

    def get_available_years(self) -> Tuple[int,int]:
        '''returns available years for a subject's data.'''
        return tuple(self.available_years)
    

    def get_available_vars(self) -> Dict[str,str]:
        '''returns dict of available variables for a subject and their descriptions.'''
        return self.variable_dict
    

    def lookup_var(self, var: str) -> str:
        '''returns variable description.'''
        return self.variable_dict[var]


    def scrape(self, 
               see_progress: bool = False) -> None:
        '''
        downloads NCES IPEDS data to disk on specified years for a defined subject.
        
        :param see_progress::
            (bool) prints completion statement for extraction of each year's data. If False, no messages printed.
        '''
        scrape_ipeds_data(subject=self.subject, year_range=self.year_range, see_progress=see_progress)


    @abstractmethod
    def clean(self):
        '''clean the data'''
        pass


    @abstractmethod
    def run(self):
        '''scrape and clean'''
        pass


class Characteristics(IPDS):
    '''IPEDS Characteristics'''
    subject = 'characteristics'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''IPEDS Characteristics data.
        
        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.
        
          ex. year_range=(2002,2012)

        -----------------  
        <h3>Example Use:</h3>
        >>> import genpeds as ed
        >>> chars_2000 = ed.Characteristics(year_range=[2000,2005,2010]) # three years of data
        >>> chars_2000.get_available_years()
         (1984,2023) # available years for Characteristics data
        >>> chars_data = chars_2000.run() # returns Pandas dataframe

        
        ----------------
        <h3>IPEDS</h3>
        The Integrated Postsecondary Education Data System (IPEDS), ran by the National Center for Education Statistics (NCES), is a collection of surveys annually conducted. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys. IPEDS covers eight subjects: 
        1. institutional characteristics
        2. admissions
        3. enrollment
        4. degrees and certificates conferred
        5. student persistence and success
        6. institutional prices
        7. student financial aid
        8. institutional resources including human, resources, finance, and academic libraries

        As of this version, `genpeds` only provides objects for the first five subject areas, as these areas provide data by gender and variables of interest like graduation rates and enrollment.
        '''
        super().__init__(year_range)


    def clean(self, 
              char_dir: str = 'characteristicsdata', 
              rm_disk: bool = False) -> pd.DataFrame:
        '''
        cleans downloaded Characteristics data, returns Pandas Dataframe.
        
        :param char_dir::
          directory where raw Charactetistics data is located; defaults to default download dir name.
        :param rm_disk::
          removes downloaded Characteristics data from disk, after cleaning.
        '''
        df = CLEANERS[self.subject](char_dir,self.year_range)
        if rm_disk:
            shutil.rmtree(char_dir)
        return df
    

    def run(self, 
            see_progress: bool = False, 
            rm_disk: bool = False) -> pd.DataFrame:
        '''
        scrapes and cleans IPEDS Characteristics data; returns Pandas Dataframe.
        
        :param see_progress::
        (bool) When True, prints successful download confirmation for each year's data. If False, no messages printed.
        
        :param rm_disk::
        removes downloaded Characteristics data from disk after data is cleaned and returned.
        '''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk)
        return df


class Admissions(IPDS):
    '''IPEDS Admissions'''
    subject = 'admissions'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''IPEDS Admissions data.
        
        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.
          
          ex. year_range=(2002,2012)
          
        -----------------  
        <h3>Example Use:</h3>
        >>> import genpeds as ed
        >>> adm_2010s = ed.Admissions(year_range=(2010,2019)) # ten years of data
        >>> adm_2010s.get_available_years()
         (2001,2023) # available years for Admissions data
        >>> adm_data = adm_2010s.run() # returns Pandas dataframe

        ----------------
        <h3>IPEDS</h3>
        The Integrated Postsecondary Education Data System (IPEDS), ran by the National Center for Education Statistics (NCES), is a collection of surveys annually conducted. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys. IPEDS covers eight subjects: 
        1. institutional characteristics
        2. admissions
        3. enrollment
        4. degrees and certificates conferred
        5. student persistence and success
        6. institutional prices
        7. student financial aid
        8. institutional resources including human, resources, finance, and academic libraries

        As of this version, `genpeds` only provides objects for the first five subject areas, as these areas provide data by gender and variables of interest like graduation rates and enrollment.
        '''
        super().__init__(year_range)


    def clean(self, 
              admit_dir: str = 'admissionsdata', 
              rm_disk: bool = False) -> pd.DataFrame:
        '''
        cleans downloaded Admissions data, returns Pandas Dataframe.
        
        :param admit_dir::
          directory where raw Admissions data is located; defaults to default download dir name.
        :param rm_disk::
          removes downloaded Admissions data from disk, after cleaning.
        '''
        df = CLEANERS[self.subject](admissions_dir=admit_dir,
                                    year_range=self.year_range)
        if rm_disk:
            shutil.rmtree(admit_dir) # removes data from disk
        return df
    
    
    def run(self, see_progress=False, merge_with_char=False, rm_disk=False) -> pd.DataFrame:
        '''scrapes and cleans Admissions data; returns Pandas Dataframe.
        
        :param see_progress::
        (bool) When True, prints successful download confirmation for each year's data. If False, no messages printed.

        :param merge_with_char::
        (bool) When True, scrapes Admissions data and merges with Characteristics data (includes variables like school name and address). 
        
        :param rm_disk::
        removes downloaded Admissions (and Characteristics if applicable) data from disk after data is cleaned and returned.
        '''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(see_progress=see_progress, rm_disk=rm_disk)
            df = df.merge(char_df, on=['id', 'year'])
        return df
    

class Enrollment(IPDS):
    '''IPEDS Enrollment'''
    subject = 'enrollment'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''
        IPEDS Enrollment data.
        
        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.
        
         ex. year_range=(2002,2012)

        -----------------  
        <h3>Example Use:</h3>
        >>> import genpeds as ed
        >>> enroll_2022 = ed.Enrollment(year_range=2022) # one year of data
        >>> enroll_2022.get_available_years()
         (1984,2023) # available years for Enrollment data
        >>> enroll_data = enroll_2022.run() # returns Pandas dataframe

        ----------------
        <h3>IPEDS</h3>
        The Integrated Postsecondary Education Data System (IPEDS), ran by the National Center for Education Statistics (NCES), is a collection of surveys annually conducted. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys. IPEDS covers eight subjects: 
        1. institutional characteristics
        2. admissions
        3. enrollment
        4. degrees and certificates conferred
        5. student persistence and success
        6. institutional prices
        7. student financial aid
        8. institutional resources including human, resources, finance, and academic libraries

        As of this version, `genpeds` only provides objects for the first five subject areas, as these areas provide data by gender and variables of interest like graduation rates and enrollment.
        '''
        super().__init__(year_range)


    def clean(self, 
              student_level: str = 'undergrad', 
              enroll_dir: str = 'enrollmentdata', 
              rm_disk = False) -> pd.DataFrame:
        '''
        cleans downloaded Fall Enrollment data, returns Pandas Dataframe.
        
        :param student_level::
         level of student enrollment; options include ['undergrad', 'grad'].
        :param enroll_dir::
          directory where raw Enrollment data is located; defaults to default download dir name.
        :param rm_disk::
          removes downloaded Enrollment data from disk, after cleaning.
        '''
        df = CLEANERS[self.subject](enrollment_dir=enroll_dir, 
                                    student_level=student_level,
                                    year_range=self.year_range)
        if rm_disk:
            shutil.rmtree(enroll_dir)
        return df
    

    def run(self, 
            student_level: str = 'undergrad', 
            see_progress: bool = False, 
            merge_with_char: bool = False, 
            rm_disk: bool = False) -> pd.DataFrame:
        '''
        scrapes and cleans IPEDS Fall Enrollment data; returns Pandas Dataframe.
        
        :param student_level::
         level of student enrollment; options include ['undergrad', 'grad'].

        :param see_progress::
        (bool) When True, prints successful download confirmation for each year's data. If False, no messages printed.

        :param merge_with_char::
        (bool) When True, scrapes Enrollment data and merges with Characteristics data (includes variables like school name and address). 
        
        :param rm_disk::
        removes downloaded Enrollment (and Characteristics if applicable) data from disk after data is cleaned and returned. 
        '''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk, student_level=student_level)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(see_progress=see_progress, rm_disk=rm_disk)
            df = df.merge(char_df, on=['id', 'year'])
        return df


class Cip(IPDS):
    '''CIP Codes'''
    subject = 'cip'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = (1984,2023)):
        '''
        IPEDS CIP Codes data.

        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.

        CIP, or Classification of Instructional Programs, are key-value pairs for subject study fields. CIP's vary by year, and are relevant to identify subject field in completion data. Available for years 1984-2023. CIP data should be used in conjunction with Completion data.
        '''
        super().__init__(year_range)


    def clean(self, 
              cip_dir: str = 'cipdata', 
              rm_disk: bool = False) -> pd.DataFrame:
        '''
        cleans downloaded CIP data, returns Pandas Dataframe.
        
        :param cip_dir::
          directory where raw CIP data is located; defaults to default download dir name.
        :param rm_disk::
          removes downloaded CIP data from disk, after cleaning.
        '''
        df = CLEANERS[self.subject](cip_codes_dir=cip_dir,
                                    year_range=self.year_range)
        if rm_disk:
            shutil.rmtree(cip_dir)
        return df
    

    def run(self, 
            see_progress: bool = False, 
            rm_disk: bool = False) -> pd.DataFrame:
        '''
        scrapes and cleans IPEDS CIP data; returns Pandas DataFrame.

        :param see_progress::
        (bool) When True, prints successful download confirmation for each year's data. If False, no messages printed.
        
        :param rm_disk::
        removes downloaded Enrollment (and Characteristics if applicable) data from disk after data is cleaned and returned.
        '''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk)
        return df


class Completion(IPDS):
    '''IPEDS Completion'''
    subject = 'completion'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = (1984,2023)):
        '''
        IPEDS Completion data.
        
        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.
        
         ex. year_range=(2002,2012)
        
        -----------------  
        <h3>Example Use:</h3>
        >>> import genpeds as ed
        >>> complete_2022 = ed.Completion(year_range=2022) # one year of data
        >>> complete_2022.get_available_years()
         (1984,2023) # available years for Enrollment data
        >>> complete_data = complete_2022.run() # returns Pandas dataframe

        ----------------
        <h3>IPEDS</h3>
        The Integrated Postsecondary Education Data System (IPEDS), ran by the National Center for Education Statistics (NCES), is a collection of surveys annually conducted. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys. IPEDS covers eight subjects: 
        1. institutional characteristics
        2. admissions
        3. enrollment
        4. degrees and certificates conferred
        5. student persistence and success
        6. institutional prices
        7. student financial aid
        8. institutional resources including human, resources, finance, and academic libraries

        As of this version, `genpeds` only provides objects for the first five subject areas, as these areas provide data by gender and variables of interest like graduation rates and enrollment.
        '''
        super().__init__(year_range)


    def clean(self, 
              degree_level: str = 'bach', 
              complete_dir: str = 'completiondata', 
              rm_disk: bool = False) -> pd.DataFrame:
        '''
        cleans downloaded Completion data, returns Pandas Dataframe.
        
        :param degree_level::
         level of student degree completion; options include ['assc', 'bach', 'mast', 'doct'].
        :param complete_dir::
          directory where raw Completion data is located; defaults to default download dir name.
        :param rm_disk::
          removes downloaded Completion data from disk, after cleaning.
        '''
        df = CLEANERS[self.subject](completion_dir=complete_dir, 
                                    level=degree_level,
                                    year_range=self.year_range)
        if rm_disk:
            shutil.rmtree(complete_dir)
        return df
    

    def run(self, 
            degree_level: str = 'bach', 
            see_progress: bool = False, 
            merge_with_char: bool = False, 
            get_cip_codes: bool = True, 
            rm_disk: bool = False) -> pd.DataFrame:
        '''scrapes and cleans IPEDS Completion data; returns Pandas Dataframe.
        
        :param degree_level::
         level of student degree completion; options include ['assc', 'bach', 'mast', 'doct'].

        :param see_progress::
        (bool) When True, prints successful download confirmation for each year's data. If False, no messages printed.

        :param merge_with_char::
        (bool) When True, scrapes Completion data and merges with Characteristics data (includes variables like school name and address). 
        
        :param get_cip_codes::
        (bool) When True, scrapes CIP (e.g., field of study) codes/labels and merges with Completion data.

        :param rm_disk::
        removes downloaded Completion (and Characteristics if applicable) data from disk after data is cleaned and returned.
        '''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk, degree_level=degree_level)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(see_progress=see_progress, rm_disk=rm_disk)
            df = df.merge(char_df, on=['id', 'year'])
        if get_cip_codes:
            cip_df = Cip(year_range=self.year_range).run(see_progress=see_progress, rm_disk=rm_disk)
            df = df.merge(cip_df, on=['cip', 'year'])
        return df


class Graduation(IPDS):
    '''IPEDS Graduation'''
    subject = 'graduation'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = (1984,2023)):
        '''
        IPEDS Graduation data.
        
        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.
        
         ex. year_range=(2002,2012)
        
        -----------------  
        <h3>Example Use:</h3>
        >>> import genpeds as ed
        >>> grad_aughts = ed.Completion(year_range=(2000,2009)) # ten years of data
        >>> grad_aughts.get_available_years()
         (2000,2023) # available years for Enrollment data
        >>> grad_data = grad_aughts.run() # returns Pandas dataframe

        ----------------
        <h3>IPEDS</h3>
        The Integrated Postsecondary Education Data System (IPEDS), ran by the National Center for Education Statistics (NCES), is a collection of surveys annually conducted. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys. IPEDS covers eight subjects: 
        1. institutional characteristics
        2. admissions
        3. enrollment
        4. degrees and certificates conferred
        5. student persistence and success
        6. institutional prices
        7. student financial aid
        8. institutional resources including human, resources, finance, and academic libraries

        As of this version, `genpeds` only provides objects for the first five subject areas, as these areas provide data by gender and variables of interest like graduation rates and enrollment.
        '''
        super().__init__(year_range)


    def clean(self, 
              degree_level: str = 'bach', 
              grad_dir: str = 'graduationdata', 
              rm_disk: bool = False) -> pd.DataFrame:
        '''
        cleans downloaded undergraduate Graduation data, returns Pandas Dataframe.
        
        :param degree_level::
         level of graduate; options include ['assc', 'bach'].
        :param grad_dir::
          directory where raw Graduation data is located; defaults to default download dir name.
        :param rm_disk::
          removes downloaded Graduation data from disk, after cleaning.
        '''
        df = CLEANERS[self.subject](graduation_dir=grad_dir, 
                                    deg_level=degree_level,
                                    year_range=self.year_range)
        if rm_disk:
            shutil.rmtree(grad_dir)
        return df
    

    def run(self, 
            degree_level: str = 'bach', 
            see_progress: bool = False, 
            merge_with_char: bool = False, 
            rm_disk: bool = False) -> pd.DataFrame:
        '''
        scrapes and cleans IPEDS Graduation data; returns Pandas Dataframe.
        
        :param degree_level::
         level of graduate; options include ['assc', 'bach'].

        :param see_progress::
        (bool) When True, prints successful download confirmation for each year's data. If False, no messages printed.
        
        :param merge_with_char::
        (bool) When True, scrapes Graduation data and merges with Characteristics data (includes variables like school name and address). 
        
        :param rm_disk::
          removes downloaded Graduation (and Characteristics if applicable) data from disk, after cleaning.
        '''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk, degree_level=degree_level)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(see_progress=see_progress, rm_disk=rm_disk)
            df = df.merge(char_df, on=['id', 'year'])
        return df
