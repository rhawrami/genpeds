# genpeds
A Python package for downloading and harmonizing NCES IPEDS institution-level data.

The Integrated Postsecondary Education Data System ([IPEDS](https://nces.ed.gov/ipeds/about-ipeds)), run by the National Center for Education Statistics ([NCES](https://nces.ed.gov/)), is a collection of surveys annually conducted on a range of subjects, from finances and admissions to enrollment and graduation. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys.

Per [IPEDS](https://nces.ed.gov/ipeds/about-ipeds):
> "IPEDS provides basic data needed to describe — and analyze trends in — postsecondary education in the United States, in terms of the numbers of students enrolled, staff employed, dollars expended, and degrees earned. Congress, federal agencies, state governments, education providers, professional associations, private businesses, media, students and parents, and others rely on IPEDS data for this basic information on postsecondary institutions." 

`genpeds`, or the **[gen]dered [p]ostsecondary [education] [d]ata [s]atrap**, provides a Python API for downloading and cleaning IPEDS data across subjects, including measures without a gender breakdown.

## Recent Updates
Support for 2024 data has been added.
Tuition, StudentAid, and VeteransAid now provide institutional price and aid data.

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
# ex. download enrollment data for 1984/1990 and 2015/2016:
scrape_ipeds_data(subject='enrollment', 
                  year_range=[1984,1990,2015,2016],
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
8. Institutional Resources including Human Resources, Finance, and Academic Libraries

`genpeds` supports selected data from the first seven subject areas. Finance, Human Resources, and Academic Libraries remain to be added:

- **Characteristics** (e.g., school name, address, longitude/latitude, etc.) (available 1984-2024)
```python
from genpeds import scrape_ipeds_data, Characteristics

scrape_ipeds_data(subject='characteristics',
                  year_range=(1984,2023))

chardat = Characteristics(year_range=(1984,2023))

char_df = chardat.run(rm_disk=False)
```
- **Admissions** (e.g., SAT/ACT scores, admit rates by gender, etc.) (available 2001-2024)
```python
from genpeds import scrape_ipeds_data, Admissions

scrape_ipeds_data(subject='admissions',
                  year_range=(2001,2023))

admdat = Admissions(year_range=(2001,2023))

adm_df = admdat.run(merge_with_char=True,
                    rm_disk=True)
```
- **Enrollment** (e.g., enrollment by race/gender/level, etc.) (available 1984-2024)
```python
from genpeds import scrape_ipeds_data, Enrollment

scrape_ipeds_data(subject='enrollment',
                  year_range=(1984,2023))

enrolldat = Enrollment(year_range=(1984,2023))

enroll_df = enrolldat.run(merge_with_char=False,
                          student_level='undergrad')
```
- **Retention** (first-year undergraduate retention for full-time and part-time entering students; available 2003–2024)
```python
from genpeds import Retention

retention = Retention(year_range=[2003, 2016, 2024])
retention.get_available_years()  # (2003, 2024)
retention.lookup_var('ft_retention_rate')

# Downloads to retentiondata/ and returns one row per institution and fall year.
retention_df = retention.run(merge_with_char=True, rm_disk=False)

# Alternatively, clean previously downloaded files without downloading again:
retention_df = retention.clean(retention_dir='retentiondata')
```

`year` is the fall in which retention is measured, and `cohort_year` is the preceding fall. `ft_retention_rate` and `pt_retention_rate` are NCES-published percentages, available from 2003. Cohort counts, exclusions, adjusted denominators, and numbers retained start in 2007; study-abroad inclusions start in 2016. Unavailable fields are missing, not zero. Each measure also has a `_status` field carrying its NCES reporting/imputation flag. The input cohorts are first-time, degree/certificate-seeking undergraduates; this series is not disaggregated by gender. `rm_disk=True` removes the downloaded directory after cleaning (and Characteristics downloads if merged).

The year-specific [Fall Enrollment D files and dictionaries](https://nces.ed.gov/ipeds/datacenter/Default.aspx?gotoReportId=7&fromIpeds=true) explain these boundaries:

| Reporting years | Retention fields present |
| --- | --- |
| 2003–2006 | Published full-time/part-time rates and their status flags only; no prior-fall cohort counts. |
| 2007–2015 | Adds entering cohorts, exclusions, adjusted cohorts, and numbers retained. |
| 2016–2024 | Adds study-abroad inclusions to the adjusted cohort calculation. |

The cleaner trims raw header whitespace (including a trailing space on an early `RET_PCP` column) and keeps the published rates rather than recomputing rounded percentages from counts. Status flags distinguish reported (`R`), not-applicable (`A`), blank (`B`), implied-zero (`Z`), and other corrected or imputed values; consult the dictionary for a given year before interpreting its flags. `year` refers to the retention measurement fall, **not** the fall when the students entered.
- **Tuition** (published undergraduate tuition and required fees, 2000–2024)
```python
from genpeds import Tuition

prices = Tuition(year_range=[2000, 2010, 2024])
price_df = prices.run(reporter='both', merge_with_char=True, rm_disk=False)

# Or download/clean one reporting calendar at a time:
academic_df = prices.run(reporter='academic')
program_df = prices.run(reporter='program')
```

`reporter` is `'academic'`, `'program'`, or `'both'` (default). The result has one row per institution, price year, and reporting calendar. `year=2024` refers to published **2024–25** prices, not to an annual total of earlier price snapshots in the ZIP. Academic-year reporters have in-district/in-state/out-of-state tuition, required fees, and published tuition-plus-fees columns. Program-year reporters have published tuition-plus-fees for their largest program, its CIP code, and a separate `largest_program_tuition_fees_no_ftft` measure (available from 2006) for institutions without full-time first-time undergraduates. These measures are not interchangeable with net price after financial aid. Each numeric price has a `_status` flag; missing fields remain missing. Data come from `IC*_AY/PY` through 2023 and `COST1_2024` in 2024. Downloads are cached in `tuitiondata/` and `tuition_programdata/` according to `reporter`; `rm_disk=True` removes the selected cache directories after cleaning.

The 2001 IC price extracts unusually include non-reporters in both files: the cleaner removes academic rows without academic price values and program rows whose largest-program CIP is the NCES not-applicable code `-2`. In 2024, the Cost I file combines both groups; the cleaner uses that same program-code marker to separate them. A blank price and a price of zero are different, and the published tuition-plus-fees value is kept as reported rather than calculated by adding the separately defined tuition and fee fields.
- **StudentAid** (SFA grants, loans and net price; aid years ending 2002–2024)
```python
from genpeds import StudentAid

aid = StudentAid(year_range=[2002, 2009, 2024])
aid_df = aid.run(reporter='both', merge_with_char=True, rm_disk=False)

# Filter the SFA academic-year or program-year cohort if needed:
program_aid = aid.run(reporter='program')
```

`year=2024` denotes the **2023–24 aid period**, not the 2024–25 aid period. `reporter` is `'academic'`, `'program'`, or `'both'` (default). `ftft_*` columns measure aid for full-time first-time degree/certificate-seeking undergraduates; `ug_*` columns describe **all** undergraduates. The two groups have different denominators (`ftft_students`, `ug_students`) and must not be pooled. Federal/state/institutional grant and student-loan counts and averages for FTFT students are available throughout 2002–2024; combined/Pell/federal-loan breakdowns begin in 2008, and all-undergraduate grant/Pell/federal-loan measures and dollar totals generally begin in 2009. Amounts are nominal dollars, and `*_avg` fields are averages among recipients, not all enrolled students. NCES changed some reporting wording from *received* to *awarded* over time; the original reporting/imputation codes are preserved in matching `_status` fields. Missing earlier fields remain missing rather than zero.

The cleaner uses `SCFA1N`/`SCFA2` for early academic-year reporters and `SCFY1N`/`SCFY2` for early full-year program reporters, then uses the common `SCUGFFN`/`SCUGRAD` financial-aid-cohort fields when present. The NCES-published `ftft_any_aid_pct` is retained as reported rather than recalculated from the cohort counts. `ftft_student_loan_*` includes nonfederal student loans where reported; `ftft_federal_loan_*` is the distinct federal subset. Grant categories can overlap at the recipient level and should not be summed as unique people.

`ftft_net_price` is the NCES average cost of attendance **after** qualifying grants for in-state/in-district FTFT grant recipients (not published tuition or an individual student's price). It begins in aid year 2008–09: through 2022–23 it comes from SFA, and for 2023–24 from `COST2_2024`. Calling `StudentAid(2024).scrape()` therefore caches two sources in `student_aiddata/` and `student_aid_net_pricedata/`; `run(rm_disk=True)` removes both after cleaning. These data are institution aggregates and have no student-level or gender split.

- **VeteransAid** (separate SFA veteran and military-benefit files; aid years ending 2014–2024)
```python
from genpeds import VeteransAid

benefits_df = VeteransAid((2014, 2024)).run(merge_with_char=True)
# E.g. grad_post911_count, ug_post911_total, grad_dod_avg
```

This separate class keeps institutions with **graduate-only** GI Bill or DoD Tuition Assistance recipients that are absent from the main SFA file. It provides recipient counts, total dollars, averages and `_status` flags by undergraduate/graduate level and benefit program. Award amounts represent benefits known to the institution, not every benefit a student may have received. Data are cached in `veterans_aiddata/`. For both aid classes, merging Characteristics uses the aid period's ending year as `year`; institutional characteristics are a snapshot from that year rather than the same aid-period measure.
- **Completion** (e.g., degree completion by race/gender/subject/level, etc.) (available 1984-2024)
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
- **Graduation** (e.g., graduation rate by race/gender/level, etc.) (available 2000-2024)
```python
from genpeds import scrape_ipeds_data, Graduation

scrape_ipeds_data(subject='graduation',
                  year_range=(2000,2023))

graddat = Graduation(year_range=(2000,2023))

grad_df = graddat.run(degree_level='bach',
                      merge_with_char=True)
```

These classes support institution-level trends across admissions, enrollment, persistence, completions, prices, and aid. Further IPEDS subjects and additional fields within existing subjects can be added over time.

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
