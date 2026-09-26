'''Work with gendered NCES IPEDS data: from admissions to graduation'''

__version__ = '1.2.3'

from genpeds.core import Characteristics, Admissions, Enrollment, Retention, Tuition, StudentAid, VeteransAid, Completion, Cip, Graduation
from genpeds.downloader import scrape_ipeds_data

__all__ = [
    'Characteristics',
    'Admissions',
    'Enrollment', 
    'Retention',
    'Tuition',
    'StudentAid',
    'VeteransAid',
    'Completion',
    'Cip',
    'Graduation',
    'scrape_ipeds_data'
]
