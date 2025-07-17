# genpeds
A Python package for working with NCES IPEDS data, particularly for studying trends by gender.

The Integrated Postsecondary Education Data System ([IPEDS](https://nces.ed.gov/ipeds/about-ipeds)), run by the National Center for Education Statistics ([NCES](https://nces.ed.gov/)), is a collection of surveys annually conducted on a range of subjects, from finances and admissions to enrollment and graduation. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys.

Per [IPEDS](https://nces.ed.gov/ipeds/about-ipeds):
> "IPEDS provides basic data needed to describe — and analyze trends in — postsecondary education in the United States, in terms of the numbers of students enrolled, staff employed, dollars expended, and degrees earned. Congress, federal agencies, state governments, education providers, professional associations, private businesses, media, students and parents, and others rely on IPEDS data for this basic information on postsecondary institutions." 

`genpeds`, or the **[gen]dered [p]ostsecondary [education] [d]ata [s]atrap**, provides a Python API for requesting, and cleaning IPEDS data for a host of subjects, particularly for studying college trends by gender.

## Usage

### Install
```bash
pip install genpeds
```

### API

#### Downloading IPEDS Data
To just request IPEDS data, you can use the `scrape_ipeds_data()` standalone function:

```python
from genpeds import scrape_ipeds_data

# ex. download Characteristics data for years 2013-2023:
scrape_ipeds_data(subject='characteristics', 
                  year_range=(2013,2023),
                  see_progress=True)
# if see_progress==True, download confirmation statements will be printed

# for year_range param, you can pass (inclusive) tuple range, list of years, or single year
# ex. download enrollment data for 1980/1990 and 2015/2016:
scrape_ipeds_data(subject='enrollment', 
                  year_range=[1980,1990,2015,2016],
                  see_progress=True)
# download completion data for 1990
scrape_ipeds_data(subject='completion', 
                  year_range=1990,
                  see_progress=True)
```

#### Subject Classes
If you'd also like to clean data in order to study trends, you can use the various subject classes; you can also just download data with these classes, so it's recommended to primarily use these classes.

```python
from genpeds import Enrollment

enroll_20s = Enrollment(year_range=(2020,2023)) # enrollment data for the 20s

enroll_20s.get_description() # returns description of subject, enrollment in this case

enroll_20s.get_available_vars() # returns dict of var names and descriptions
```

The key methods we'll be using 99% of the time are:

- `.scrape()`, which downloads subject data
- `.clean()`, which cleans subject data
- `.run()`, which downloads and cleans subject data (along with some further options)

```python
from genpeds import Graduation

grad_aughts = Graduation(year_range=(2000,2009)) 

grad_aughts.scrape(see_progress=False) # downloads grad data for 2000-2009

grad_df = grad_aughts.clean(degree_level='bach',
                            rm_disk=True)
# .clean() returns a Pandas DataFrame 
# degree_level specifies the level of graduation data
# rm_disk determines if previously downloaded data should be removed from disk after data is cleaned and returned in a DataFrame

grad_df = grad_aughts.run(degree_level='assc',
                          see_progress=False,
                          merge_with_char=True,
                          rm_disk=False)
# .run() downloads subject data, then cleans it
# returns Pandas DataFrame
# merge_with_char, if True, downloads Characteristics data (e.g., school names, addresses) and merges with subject data

# to look up variable descriptions, you can either use:
# .get_available_vars() -> dict
# .lookup_var() -> str
grad_aughts.lookup_var('gradrate_wtmen')
# returns: 'Graduation rate for non-Hispanic White men (within 150 percent of normal time taken to graduate).'
```

### Subjects
IPEDS [covers](https://nces.ed.gov/ipeds/about-ipeds) eight main subjects:
1. Institutional Characteristics
2. Admissions
3. Enrollment
4. Degrees and Certificates Conferred
5. Student Persistence and Success
6. Institutional Prices
7. Student Financial Aid
8. institutional Resources including Human, resources, Finance, and Academic Libraries

`genpeds` currently ***supports the first five*** subjects:

- **Characteristics** (e.g., school name, address, longitude/latitude, etc.) (available 1984-2023)
```python
from genpeds import scrape_ipeds_data, Characteristics

scrape_ipeds_data(subject='characteristics',
                  year_range=(1984,2023))

chardat = Characteristics(year_range=(1984,2023))

char_df = chardat.run(rm_disk=False)
```
- **Admissions** (e.g., SAT/ACT scores, admit rates by gender, etc.) (available 2001-2023)
```python
from genpeds import scrape_ipeds_data, Admissions

scrape_ipeds_data(subject='admissions',
                  year_range=(2001,2023))

admdat = Admissions(year_range=(2001,2023))

adm_df = admdat.run(merge_with_char=True,
                    rm_disk=True)
```
- **Enrollment** (e.g., enrollment by race/gender/level, etc.) (available 1984-2023)
```python
from genpeds import scrape_ipeds_data, Enrollment

scrape_ipeds_data(subject='enrollment',
                  year_range=(1984,2023))

enrolldat = Enrollment(year_range=(1984,2023))

enroll_df = enrolldat.run(merge_with_char=False,
                          student_level='undergrad')
```
- **Completion** (e.g., degree completion by race/gender/subject/level, etc.) (available 1984-2023)
```python
from genpeds import scrape_ipeds_data, Completion

scrape_ipeds_data(subject='completion',
                  year_range=(1984,2023))

completedat = Completion(year_range=(1984,2023))

complete_df = completedat.run(degree_level='doct',
                              get_cip_codes=True,
                              merge_with_char=True,
                              rm_disk=False)
```
- **Graduation** (e.g., graduation rate by race/gender/level, etc.) (available 2000-2023)
```python
from genpeds import scrape_ipeds_data, Graduation

scrape_ipeds_data(subject='graduation',
                  year_range=(2000,2023))

graddat = Graduation(year_range=(2000,2023))

grad_df = graddat.run(degree_level='bach',
                      merge_with_char=True)
```

In the future, the remaining subjects will likely be added to `genpeds`. But just with the already provided subjects, you can study school-level trends for their male and female students, from admissions to completion.

## Development Installation

To set up a development environment for contributing to `genpeds`:

### 1. Create a conda (or other virtual) environment
```bash
conda create -n genpeds python -y
conda activate genpeds
```

### 2. Install dependencies
```bash
pip install -r requirements-dev.txt
```

### 3. Install genpeds in development mode
```bash
pip install -e .
```

This will install `genpeds` in editable mode, allowing you to make changes to the source code and see them immediately without reinstalling the package.

### 4. Run tests
```bash
pytest tests/
```

This will run all tests in the `tests/` directory to verify that the installation and package functionality are working correctly.

