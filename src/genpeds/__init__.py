'''Work with gendered NCES IPEDS data: from admissions to graduation'''

__version__ = '1.2.3'

from genpeds.core import Characteristics, Admissions, Enrollment, DistanceEnrollment, TwelveMonthEnrollment, InstructionalActivity, Retention, Tuition, StudentAid, VeteransAid, Finance, AcademicLibraries, HumanResources, Completion, Completers, Cip, Graduation, Graduation200, OutcomeMeasures
from genpeds.downloader import scrape_ipeds_data

__all__ = [
    'Characteristics',
    'Admissions',
    'Enrollment', 
    'DistanceEnrollment',
    'TwelveMonthEnrollment',
    'InstructionalActivity',
    'Retention',
    'Tuition',
    'StudentAid',
    'VeteransAid',
    'Finance',
    'AcademicLibraries',
    'HumanResources',
    'Completion',
    'Completers',
    'Cip',
    'Graduation',
    'Graduation200',
    'OutcomeMeasures',
    'scrape_ipeds_data'
]
