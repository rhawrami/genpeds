'''Work with gendered NCES IPEDS data: from admissions to graduation'''

__version__ = '1.2.3'

from genpeds.core import Characteristics, Admissions, Enrollment, TwelveMonthEnrollment, Retention, Tuition, StudentAid, VeteransAid, Completion, Completers, Cip, Graduation
from genpeds.downloader import scrape_ipeds_data

__all__ = [
    'Characteristics',
    'Admissions',
    'Enrollment', 
    'TwelveMonthEnrollment',
    'Retention',
    'Tuition',
    'StudentAid',
    'VeteransAid',
    'Completion',
    'Completers',
    'Cip',
    'Graduation',
    'scrape_ipeds_data'
]
