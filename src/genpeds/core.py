import shutil
import json
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List, Union

import pandas as pd

from genpeds.downloader import scrape_ipeds_data, get_year_iter
from genpeds.cleaners import CLEANERS, _validate_om_selection


def _remove_download_dir(directory: str) -> None:
    '''Refuse to recursively remove the working directory or its ancestors.'''
    path = Path(directory)
    resolved = path.resolve()
    cwd = Path.cwd().resolve()
    if (path.is_symlink() or resolved == cwd or resolved in cwd.parents
            or resolved == Path.home().resolve()):
        raise ValueError(f'Unsafe download directory for rm_disk: {directory}')
    shutil.rmtree(path)


def _merge_characteristics(df: pd.DataFrame, char_df: pd.DataFrame) -> pd.DataFrame:
    '''Avoid multiplying rows when a historical UNITID is not unique.'''
    duplicates = char_df.duplicated(['id', 'year'], keep=False)
    if duplicates.any():
        years = sorted(char_df.loc[duplicates, 'year'].unique().tolist())
        raise ValueError(f'Characteristics has non-unique UNITIDs in years {years}; '
                         'cannot safely merge by id and year (1986 uses placeholder IDs)')
    return df.merge(char_df, on=['id', 'year'], validate='many_to_one')


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
         (1984,2025) # available years for Characteristics data
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
            _remove_download_dir(char_dir)
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
         (2001,2024) # available years for Admissions data
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
            _remove_download_dir(admit_dir) # removes data from disk
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
            df = _merge_characteristics(df, char_df)
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
         (1984,2024) # available years for Enrollment data
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
            _remove_download_dir(enroll_dir)
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
            df = _merge_characteristics(df, char_df)
        return df


class DistanceEnrollment(IPDS):
    '''Fall students enrolled in distance education courses.'''
    subject = 'distance_enrollment'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''EF-A distance tables, fall years 2012-2024.'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def clean(self,
              student_level: str = 'undergrad',
              distance_dir: str = 'distance_enrollmentdata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean cached EF-A distance records for a selected row category.'''
        df = CLEANERS[self.subject](distance_dir=distance_dir,
                                    student_level=student_level,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(distance_dir)
        return df

    def run(self,
            student_level: str = 'undergrad',
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean fall distance data; optionally join IC.'''
        self.scrape(see_progress=see_progress)
        df = self.clean(student_level=student_level, rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class TwelveMonthEnrollment(IPDS):
    '''Unduplicated 12-month IPEDS enrollment headcounts.'''
    subject = 'twelve_month_enrollment'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''Reporting periods ending 2002-2025; inclusive range, list, or year.'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def clean(self,
              student_level: str = 'undergrad',
              enroll_dir: str = 'twelve_month_enrollmentdata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean EFFY headcounts for undergrad, grad, total, or all levels.'''
        df = CLEANERS[self.subject](enrollment_dir=enroll_dir,
                                    student_level=student_level,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(enroll_dir)
        return df

    def run(self,
            student_level: str = 'undergrad',
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean EFFY files; optionally join Characteristics.'''
        self.scrape(see_progress=see_progress)
        df = self.clean(student_level=student_level, rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class Retention(IPDS):
    '''First-year undergraduate retention from the Fall Enrollment D files.'''
    subject = 'retention'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''IPEDS first-year undergraduate retention, available for 2003-2024.

        ``year_range`` accepts an inclusive tuple, a list of years, or one year.
        The reported year is the fall in which retention is measured; the
        entering cohort is from the preceding fall.
        '''
        get_year_iter(self.subject, year_range)  # check availability before downloading
        super().__init__(year_range)

    def clean(self,
              retention_dir: str = 'retentiondata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean downloaded retention files, optionally removing their directory.'''
        df = CLEANERS[self.subject](retention_dir=retention_dir,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(retention_dir)
        return df

    def run(self,
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean retention data; optionally join characteristics.'''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class Tuition(IPDS):
    '''Published undergraduate tuition and fees, by reporting calendar.'''
    subject = 'tuition'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''Price years 2000-2024; accepts an inclusive tuple, list, or year.'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def scrape(self, reporter: str = 'both', see_progress: bool = False) -> None:
        '''Download academic-year and/or program-year price files.'''
        if reporter not in ('academic', 'program', 'both'):
            raise ValueError("reporter must be 'academic', 'program', or 'both'")
        if reporter in ('academic', 'both'):
            scrape_ipeds_data('tuition', self.year_range, see_progress=see_progress)
        if reporter in ('program', 'both'):
            scrape_ipeds_data('tuition_program', self.year_range, see_progress=see_progress)

    def clean(self,
              reporter: str = 'both',
              tuition_dir: str = 'tuitiondata',
              program_dir: str = 'tuition_programdata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean locally cached price files, optionally removing those used.'''
        df = CLEANERS[self.subject](tuition_dir=tuition_dir,
                                    program_dir=program_dir,
                                    reporter=reporter,
                                    year_range=self.year_range)
        if rm_disk:
            if reporter in ('academic', 'both'):
                _remove_download_dir(tuition_dir)
            if reporter in ('program', 'both'):
                _remove_download_dir(program_dir)
        return df

    def run(self,
            reporter: str = 'both',
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean price data, optionally merging Characteristics.'''
        self.scrape(reporter=reporter, see_progress=see_progress)
        df = self.clean(reporter=reporter, rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class StudentAid(IPDS):
    '''Institution-level grants and loans from Student Financial Aid files.'''
    subject = 'student_aid'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''SFA aid years ending 2002-2024, as a range, list, or single year.'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def scrape(self, see_progress: bool = False) -> None:
        '''Download SFA, and Cost II net price for aid year 2023-24.'''
        super().scrape(see_progress=see_progress)
        if 2024 in get_year_iter(self.subject, self.year_range):
            scrape_ipeds_data('student_aid_net_price', 2024,
                              see_progress=see_progress)

    def clean(self,
              reporter: str = 'both',
              aid_dir: str = 'student_aiddata',
              net_price_dir: str = 'student_aid_net_pricedata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean cached SFA files; reporter is academic, program, or both.'''
        df = CLEANERS[self.subject](aid_dir=aid_dir,
                                    net_price_dir=net_price_dir,
                                    reporter=reporter,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(aid_dir)
            if 2024 in get_year_iter(self.subject, self.year_range) and Path(net_price_dir).is_dir():
                _remove_download_dir(net_price_dir)
        return df

    def run(self,
            reporter: str = 'both',
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean aid years; optionally join Characteristics.'''
        if reporter not in ('academic', 'program', 'both'):
            raise ValueError("reporter must be 'academic', 'program', or 'both'")
        self.scrape(see_progress=see_progress)
        df = self.clean(reporter=reporter, rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class VeteransAid(IPDS):
    '''Post-9/11 GI Bill and Department of Defense tuition assistance.'''
    subject = 'veterans_aid'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''Aid years ending 2014-2024, as an inclusive tuple, list, or year.'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def clean(self,
              aid_dir: str = 'veterans_aiddata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean separately reported military benefits for UG and grad students.'''
        df = CLEANERS[self.subject](aid_dir=aid_dir, year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(aid_dir)
        return df

    def run(self,
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean military-benefit data, with optional IC merge.'''
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class Cip(IPDS):
    '''CIP Codes'''
    subject = 'cip'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = (1984,2025)):
        '''
        IPEDS CIP Codes data.

        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.

        CIP, or Classification of Instructional Programs, are key-value pairs for subject study fields. CIP's vary by year, and are relevant to identify subject field in completion data. Available for years 1984-2025. CIP data should be used in conjunction with Completion data.
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
            _remove_download_dir(cip_dir)
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
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = (1984,2025)):
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
         (1984,2025) # available years for Completion data
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
              rm_disk: bool = False,
              major: str = 'both') -> pd.DataFrame:
        '''
        cleans downloaded Completion data, returns Pandas Dataframe.
        
        :param degree_level::
         level of student degree completion; options include ['assc', 'bach', 'mast', 'doct'].
        :param major:: 'first', 'second', or 'both' for years 2001+; before 2001 the data do not identify first/second majors.
        :param complete_dir::
          directory where raw Completion data is located; defaults to default download dir name.
        :param rm_disk::
          removes downloaded Completion data from disk, after cleaning.
        '''
        df = CLEANERS[self.subject](completion_dir=complete_dir, 
                                    level=degree_level,
                                    major=major,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(complete_dir)
        return df
    

    def run(self, 
            degree_level: str = 'bach', 
            see_progress: bool = False, 
            merge_with_char: bool = False, 
            get_cip_codes: bool = True, 
            rm_disk: bool = False,
            major: str = 'both') -> pd.DataFrame:
        '''scrapes and cleans IPEDS Completion data; returns Pandas Dataframe.
        
        :param degree_level::
         level of student degree completion; options include ['assc', 'bach', 'mast', 'doct'].
        :param major:: 'first', 'second', or 'both'. Before 2001 MAJORNUM is absent, so only 'both' is supported and marked unspecified.

        :param see_progress::
        (bool) When True, prints successful download confirmation for each year's data. If False, no messages printed.

        :param merge_with_char::
        (bool) When True, scrapes Completion data and merges with Characteristics data (includes variables like school name and address). 
        
        :param get_cip_codes::
        (bool) When True, scrapes CIP (e.g., field of study) codes/labels and merges with Completion data.

        :param rm_disk::
        removes downloaded Completion (and Characteristics if applicable) data from disk after data is cleaned and returned.
        '''
        if major not in ('first', 'second', 'both'):
            raise ValueError("major must be 'first', 'second', or 'both'")
        if major != 'both' and any(y < 2001 for y in get_year_iter(self.subject, self.year_range)):
            raise ValueError('First/second major is not identified before 2001; select years 2001 or later')
        self.scrape(see_progress=see_progress)
        df = self.clean(rm_disk=rm_disk, degree_level=degree_level, major=major)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        if get_cip_codes:
            cip_df = Cip(year_range=self.year_range).run(see_progress=see_progress, rm_disk=rm_disk)
            df = df.merge(cip_df, on=['cip', 'year'])
        return df


class Completers(IPDS):
    '''Distinct people completing awards (not counts of awards or majors).'''
    subject = 'completers'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''Completions B/C files, award years ending 2012-2025.'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def scrape(self,
               degree_level: str = 'all',
               see_progress: bool = False) -> None:
        '''Download B for unique recipients across all awards, or C by level.'''
        if degree_level not in ('all', 'award_levels', 'assc', 'bach', 'mast', 'doct'):
            raise ValueError("degree_level must be 'all', 'award_levels', 'assc', 'bach', 'mast', or 'doct'")
        subject = 'completers' if degree_level == 'all' else 'completers_by_award'
        scrape_ipeds_data(subject, self.year_range, see_progress=see_progress)

    def clean(self,
              degree_level: str = 'all',
              completers_dir: str = 'completersdata',
              award_dir: str = 'completers_by_awarddata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean cached B or C files; optionally remove the selected cache.'''
        df = CLEANERS[self.subject](completers_dir=completers_dir,
                                    award_dir=award_dir,
                                    degree_level=degree_level,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(completers_dir if degree_level == 'all' else award_dir)
        return df

    def run(self,
            degree_level: str = 'all',
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean distinct-completer data, optionally joining IC.'''
        self.scrape(degree_level=degree_level, see_progress=see_progress)
        df = self.clean(degree_level=degree_level, rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class Graduation(IPDS):
    '''IPEDS Graduation'''
    subject = 'graduation'

    def __init__(self, 
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = (2000,2024)):
        '''
        IPEDS Graduation data.
        
        :param year_range::
          tuple of inclusive year integers (indicates a range), iterable of year integers (indicates group of individual years), or single year to pull data from.
        
         ex. year_range=(2002,2012)
        
        -----------------  
        <h3>Example Use:</h3>
        >>> import genpeds as ed
        >>> grad_aughts = ed.Graduation(year_range=(2000,2009)) # ten years of data
        >>> grad_aughts.get_available_years()
         (2000,2024) # available years for Graduation data
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
            _remove_download_dir(grad_dir)
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
            df = _merge_characteristics(df, char_df)
        return df


class Graduation200(IPDS):
    '''GR200 cohort outcomes through 200% of normal completion time.'''
    subject = 'graduation200'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''GR200 status/reporting years 2008-2024; 2008 is a supplemental wave.'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def clean(self,
              cohort_type: str = 'both',
              graduation_dir: str = 'graduation200data',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean selected bachelor's/less-than-four-year source cohorts.'''
        df = CLEANERS[self.subject](graduation_dir=graduation_dir,
                                    cohort_type=cohort_type,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(graduation_dir)
        return df

    def run(self,
            cohort_type: str = 'both',
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean GR200; optionally join Characteristics.'''
        if cohort_type not in ('both', 'bachelor', 'less_than_four_year'):
            raise ValueError("cohort_type must be 'both', 'bachelor', or 'less_than_four_year'")
        self.scrape(see_progress=see_progress)
        df = self.clean(cohort_type=cohort_type, rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df


class OutcomeMeasures(IPDS):
    '''Four-/six-/eight-year awards and subsequent enrollment for UG entrants.'''
    subject = 'outcome_measures'

    def __init__(self,
                 year_range: Optional[Union[Tuple[int,int], List[int], int]] = None):
        '''OM reporting/status years 2015-2024 (2017+ expanded Pell cohorts).'''
        get_year_iter(self.subject, year_range)
        super().__init__(year_range)

    def clean(self,
              cohort_type: str = 'all',
              pell_group: str = 'total',
              outcomes_dir: str = 'outcome_measuresdata',
              rm_disk: bool = False) -> pd.DataFrame:
        '''Clean OM source rows without aggregating overlapping cohorts.'''
        df = CLEANERS[self.subject](outcomes_dir=outcomes_dir,
                                    cohort_type=cohort_type,
                                    pell_group=pell_group,
                                    year_range=self.year_range)
        if rm_disk:
            _remove_download_dir(outcomes_dir)
        return df

    def run(self,
            cohort_type: str = 'all',
            pell_group: str = 'total',
            see_progress: bool = False,
            merge_with_char: bool = False,
            rm_disk: bool = False) -> pd.DataFrame:
        '''Download and clean OM, optionally attaching Characteristics.'''
        _validate_om_selection(cohort_type, pell_group, self.year_range)
        self.scrape(see_progress=see_progress)
        df = self.clean(cohort_type=cohort_type, pell_group=pell_group,
                        rm_disk=rm_disk)
        if merge_with_char:
            char_df = Characteristics(year_range=self.year_range).run(
                see_progress=see_progress, rm_disk=rm_disk)
            df = _merge_characteristics(df, char_df)
        return df
