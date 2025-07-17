import argparse

from genpeds.downloader import scrape_ipeds_data

# simple and doesn't handle many errors at the moment,
# but it'll do for now.

def parse_years(year_str: str ):
    '''
    parse year argument
    
    years take:
    1. range, ie. 2001-2023
    2. list, ie. [2022,2023,1990]
    3. single int, ie. 2022
    '''
    if len(year_str) == 1 and '-' not in year_str[0]:
        yrs_iter = int(year_str[0])
    elif len(year_str) == 1 and '-' in year_str[0]:
        split_yrs = year_str[0].split('-')
        start, end = split_yrs
        yrs_iter = (
            int(start), int(end)
        )
    elif len(year_str) > 1:
        yrs_iter = [int(yr) for yr in year_str]
    
    return yrs_iter


def main():
    parser = argparse.ArgumentParser('genpeds', description='NCES IPEDS subject-data scraper')
    parser.add_argument('subject', 
                        choices=['characteristics', 'admissions', 'enrollment', 
                                            'cip', 'completion', 'graduation'],
                        help=('IPEDS data subject to download. Options include:\n'
                        '[characteristics, admissions, enrollment, cip, completion, graduation]'))
    parser.add_argument('-y', '--years',
                        required=True, 
                        nargs='+',
                        help=('years of IPEDS subject data to download. Can take '
                              'range, ie. 2001-2023 or list, ie. 2022 2023 1990 or single year, ie. 2017'))
    
    args = parser.parse_args()
    cleaned_yrs = parse_years(args.years) 
    scrape_ipeds_data(
        subject=args.subject,
        year_range=cleaned_yrs
    )
    
if __name__ == '__main__':
    main()