# genpeds
A Python package for downloading and harmonizing NCES IPEDS institution-level data.

The Integrated Postsecondary Education Data System ([IPEDS](https://nces.ed.gov/ipeds/about-ipeds)), run by the National Center for Education Statistics ([NCES](https://nces.ed.gov/)), is a collection of surveys annually conducted on a range of subjects, from finances and admissions to enrollment and graduation. All postsecondary institutions that participate in federal student aid financial aid programs are required to participate in these surveys.

Per [IPEDS](https://nces.ed.gov/ipeds/about-ipeds):
> "IPEDS provides basic data needed to describe — and analyze trends in — postsecondary education in the United States, in terms of the numbers of students enrolled, staff employed, dollars expended, and degrees earned. Congress, federal agencies, state governments, education providers, professional associations, private businesses, media, students and parents, and others rely on IPEDS data for this basic information on postsecondary institutions." 

`genpeds`, or the **[gen]dered [p]ostsecondary [education] [d]ata [s]atrap**, provides a Python API for downloading and cleaning IPEDS data across subjects, including measures without a gender breakdown.

For the complete output-variable inventory, source mappings, and year-specific interpretation rules, see the stand-alone [API codebook and harmonization guide](codebook/README.md).

## Recent Updates
Characteristics, 12-month enrollment, Completion and Completers include the released 2025 files; most other classes currently end in 2024.
Tuition, StudentAid, and VeteransAid now provide institutional price and aid data.
Admissions now retains applicant/admit/enrollment breakdowns and year-specific admissions policies; OutcomeMeasures adds 4/6/8-year student-success outcomes.
InstructionalActivity now complements 12-month enrollment headcounts with hours and FTE through 2025.
HumanResources now covers modern staffing, faculty, new-hire and salary tables through 2024.
Finance now covers public GASB and nonprofit/for-profit FASB fiscal-year statements, 2004–2024.
AcademicLibraries now covers the complete 2014–2024 annual AL collection, including collections, circulation, library FTE and spending.

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

Downloads use HTTPS with explicit timeouts, reject unexpected HTTP responses, and write only a validated data member from an NCES ZIP to the subject cache. A failed download raises an error instead of being silently skipped. `rm_disk=True` is opt-in and removes the selected download directory after cleaning; keep unrelated files out of those cache directories.

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

`genpeds` supports selected data from the first seven subject areas and Human Resources, Finance and Academic Libraries within institutional resources:

- **Characteristics** (directory, geography and institutional classification; available 1984–2025)
```python
from genpeds import scrape_ipeds_data, Characteristics

scrape_ipeds_data(subject='characteristics',
                  year_range=(1984,2023))

chardat = Characteristics(year_range=(1984,2023))

char_df = chardat.run(rm_disk=False)
# Or: Characteristics(2025).run()[['id', 'name', 'control', 'sector', 'locale_code']]
```

The output includes `control` (public/private, with profit status when known), program `level`, `sector`, nullable `hbcu`, `tribal` and `degree_granting` indicators, `locale_code`/`locale_scheme`, and `carnegie_2021_basic_code`. The matching `*_code` columns retain the NCES source codes, including special missing/not-applicable values. **Historical meanings differ:** `CONTROL=2` in 1984–85 means private without a profit-status distinction, whereas from 1986 it means private nonprofit; `ICLEVEL=7` in 1984–85 means unclassified rather than a less-than-two-year program. HBCU and tribal fields start in 1992 and 1993, degree-granting status in 2000, and the 2021 Carnegie Basic code in 2021. The `LOCALE` code system switches from legacy urbanization codes to urban-centric codes in 2005; compare codes only within the same `locale_scheme`. Early nonresponse is kept missing rather than interpreted as a negative answer.

The 1986 header extract contains multiple distinct institutions using the same placeholder UNITID `247719`; their identifiers are **not suitable as a unique merge key**. Other years were checked against downloaded headers for duplicate institution-year IDs. A `merge_with_char=True` request involving 1986 now raises an error rather than multiplying the affected subject rows; `Characteristics(1986).run()` still returns the original header records.
- **Admissions** (e.g., SAT/ACT scores, admit rates by gender, etc.) (available 2001-2024)
```python
from genpeds import scrape_ipeds_data, Admissions

scrape_ipeds_data(subject='admissions',
                  year_range=(2001,2023))

admdat = Admissions(year_range=(2001,2023))

adm_df = admdat.run(merge_with_char=True,
                    rm_disk=True)
```

`Admissions` now keeps women applicants/admittees/enrollees, full-time and part-time enrollment counts, and the source's published totals; in 2001 the absent totals and sex-specific enrolled counts are derived from the available men/women FT/PT fields. It also returns SAT/ACT **submitter counts** (`num_submit_sat`, `num_submit_act`) next to the existing submission percentages. `accept_rate_total` and `yield_rate_total` use the published totals where present; zero denominators give missing rates.

`consider_*_code` exposes raw `ADMCON` admission-policy codes, with year-aware `consider_*` labels for GPA, rank, record, preparation, recommendations, testing, and other available criteria. **The codes change meaning**: older `2` means recommended, a `5` consideration category appears from 2016, and 2022+ `5`/`3` on `consider_test_scores` mean test optional/test blind. Other-test consideration starts in 2005; work experience, essay and legacy status start in 2022. Test-score medians and reported another-gender/unknown-gender admissions counts also start in 2022; these supplements are not simply added to men/women counts. SAT/ACT percentages describe first-time degree/certificate-seeking *score submitters*, not a share of everyone admitted. See [codebook/changes.csv](codebook/changes.csv) for the documented boundaries.
- **Enrollment** (e.g., enrollment by race/gender/level, etc.) (available 1984-2024)
```python
from genpeds import scrape_ipeds_data, Enrollment

scrape_ipeds_data(subject='enrollment',
                  year_range=(1984,2023))

enrolldat = Enrollment(year_range=(1984,2023))

enroll_df = enrolldat.run(merge_with_char=False,
                          student_level='undergrad')
```
- **DistanceEnrollment** (fall students taking exclusively, some, or no distance education courses; 2012–2024)
```python
from genpeds import DistanceEnrollment

distance = DistanceEnrollment((2012, 2024))
undergrad_distance = distance.run(student_level='undergrad', merge_with_char=True)
graduate_distance = distance.run(student_level='grad')
```

An IPEDS distance education course delivers its **instructional content exclusively at a distance**; an on-campus orientation, exam or academic support visit does not by itself disqualify it. `exclusive_distance`, `some_distance`, and `no_distance` count fall students in those mutually exclusive categories, not numbers of courses. `exclusive_same_state`, `exclusive_other_us_state`, `exclusive_us_state_unknown`, `exclusive_outside_us`, and `exclusive_location_unknown` describe **exclusively** distance students only. The three `*_share` fields divide each category by `total_students` and are missing for a zero/missing denominator. Each reported count has a matching NCES `_status` flag.

`student_level` is `'undergrad'` (default), `'grad'`, `'total'`, `'degree_seeking'` (undergrad), `'non_degree'` (undergrad), or `'all'`. The `total` row overlaps the other levels; degree-seeking and non-degree rows subdivide undergraduates. This separate class uses the `EF*_A_DIST` files and caches downloads in `distance_enrollmentdata/`; its row categories must not be added wholesale to `Enrollment` or `TwelveMonthEnrollment`.
- **TwelveMonthEnrollment** (unduplicated July–June enrollment headcounts; periods ending 2002–2025)
```python
from genpeds import TwelveMonthEnrollment

annual = TwelveMonthEnrollment(year_range=[2002, 2019, 2025])
undergrad_df = annual.run(student_level='undergrad', merge_with_char=True)
grad_df = annual.run(student_level='grad')

# 'total' returns institution-wide headcounts; 'all' returns one row per
# available level, including the overlapping institution-wide total.
all_levels_df = annual.run(student_level='all')
```

`year=2025` means **July 2024 through June 2025**; this unduplicated count is not the fall enrollment snapshot. `student_level` accepts `'undergrad'` (default), `'grad'`, `'total'`, `'all'`, or `'first_professional'` for years 2002–2010 only. NCES reported first-professional students **separately** from graduate students through 2010 and combined them into graduate reporting thereafter; do not infer a consistent historical graduate series without accounting for that break. In `'all'`, the `total` row overlaps the other levels and must not be summed with them. Through 2019 the cleaner selects `LSTUDY` rows; from 2020 it selects `EFFYALEV` codes 1, 2, and 12, excluding nested undergraduate detail rows. `source_level_code` and `level_code_system` record which coding scheme was used.

The output includes reported total, men/women and race/ethnicity headcounts with matching `_status` flags. The older combined Asian/Pacific Islander category (`asian_pacific`) is available in 2002–2007; `asian` and `pacific_islander` are distinct from 2008. Race definitions should be compared with each year's NCES dictionary. `TwelveMonthEnrollment(2025).run(merge_with_char=True)` joins the 2025 Characteristics snapshot by UNITID and year; its survey snapshot and the enrollment reporting period refer to different time windows. Downloads are cached in `twelve_month_enrollmentdata/` unless `rm_disk=True`.
- **InstructionalActivity** (12-month instructional hours and full-time-equivalent enrollment; periods ending 2002–2025)
```python
from genpeds import InstructionalActivity, TwelveMonthEnrollment

activity = InstructionalActivity(2025).run(merge_with_char=True)
undergrads = TwelveMonthEnrollment(2025).run(student_level='undergrad')
comparison = activity.merge(undergrads[['id', 'year', 'total_students']],
                            on=['id', 'year'])
```

`year=2025` covers July 2024–June 2025, as in `TwelveMonthEnrollment`, but **instructional credit/clock hours and FTE are not unique student headcounts**. EFIA has one row per institution/year: `ug_credit_hours`, `ug_contact_clock_hours`, and `grad_credit_hours` are available from 2002. The source calls `CNACTUA` *contact hours* through 2018 and *clock hours* from 2019; `hour_term` and the raw `activity_type_code` (1 contact/clock, 2 credit, 3 both, -2 not applicable) preserve that distinction. Do not add credit hours to contact/clock hours.

`ug_estimated_fte`/`grad_estimated_fte` and `ug_reported_fte`/`grad_reported_fte` appear from 2004; `professional_practice_reported_fte` starts in 2012. Early unavailable measures stay missing. **Reported FTE is not necessarily an independent institution calculation**: NCES documents a fallback to estimated FTE when an institution does not supply its own figure. We keep the reported and estimated columns and their individual `_status` flags rather than combining them. This class uses `EFIA*` files and caches downloads in `instructional_activitydata/`; `merge_with_char` and `rm_disk` follow the other subject classes.
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
- **Finance** (institutional fiscal years ending 2004–2024)
```python
from genpeds import Finance

finance = Finance([2004, 2014, 2020, 2024])
public = finance.run(form='f1a', merge_with_char=True)  # GASB public
nonprofit = finance.run(form='f2')  # FASB nonprofits and some publics
forprofit = finance.run(form='f3')  # FASB for-profits
# Or: all_forms = Finance(2024).run(form='all')
finance.get_form_vars('f3')  # applicable fields; some begin only in 2014/2020
```

`year=2024` is **fiscal 2024** (`F2324_F1A/F2/F3`), not the 2024–25 price year. `form='all'` (default) downloads three separate source families and retains a `form`/`accounting_basis` on each row; don't pool form totals as interchangeable accounting measures. `accounting_regime` marks prealigned 2004–09, aligned 2010+, and the F3 redesign from **fiscal 2014** (the 2014–15 collection). `net_tuition_fees` is after discounts, **not** published tuition or a student's net price. GASB `revenues_and_additions` and FASB `revenues_and_investment_return` stay in different columns; `net_position`, `net_assets`, and `equity` likewise remain separate. F3 `total_expenses` (financial statement) and `functional_expenses` (functional table, since 2014) are **distinct** and can differ; the former is not applicable for many F3 reporters. F3 `instruction_expenses` starts in 2014, while `pell_discounts` begins in 2020 for all forms. Earlier fields remain missing, not zero. Each amount has its own NCES `_status` flag. The **2024 Spring Finance release was provisional** when checked; see [Finance harmonization](codebook/harmonization.md#finance) for scope, accounting changes and source dictionaries.

`scrape_ipeds_data('finance', 2024)` downloads **F1A only**; use `Finance(2024).scrape(form='all')` for all three. Cached CSVs live in `financedata/`, `finance_f2data/`, and `finance_f3data/` respectively. `Finance.clean(form='f2', finance_dir='my_cache')` reads a single form offline; `run(..., rm_disk=True)` removes the selected source caches. A Characteristics merge uses the **fiscal-ending year** as its join key, not an identical survey period.

To check the full Finance download → clean → Characteristics merge against NCES, run `GENPEDS_LIVE_TESTS=1 pytest tests/test_finance_live.py -q`. This downloads the FY2023 F1A/F2/F3 files and HD2023 into an isolated temporary directory. The test is skipped in the ordinary suite so routine runs remain fast and work without network access.

- **AcademicLibraries** (annual library resources, fiscal years 2014–2024)
```python
from genpeds import AcademicLibraries

al = AcademicLibraries([2014, 2019, 2024])
library_df = al.run(merge_with_char=True)
library_df[['id', 'year', 'physical_books', 'electronic_books',
            'total_expenditures', 'staff_fte']]
# Clean a previously downloaded year without contacting NCES:
local_df = AcademicLibraries(2024).clean()
```

`year=2024` means **fiscal 2024** (`AL2024`, collected in 2024–25), not 2024–25 tuition. The annual AL series **ended after 2024–25**; older biennial Academic Libraries Survey (ALS) files are a separate collection, not more years of the same source. The output retains each NCES amount and its `*_status` flag, plus categorical codes/labels for the collection, services, staffing and spending screeners. `expenditure_threshold_code` starts in **2019** (`1` at least $100,000, `2` below); earlier missing screener values are **unknown**. Detailed library expenses (`total_expenditures`, `salaries_wages` etc.) are not reported by many below-threshold libraries: missing is not zero. `expenditures_excluding_fringe` is the separate NCES-calculated `LSWMSOM`, not `total_expenditures` and has no X flag. Collection and circulation totals begin in **2015**, individual serial counts in **2016**, and the `physical_collections` / `electronic_collections` definition adds serials in **2019**; `collection_total_definition` records the break. Library staff **FTE** begins in **2020** and is not an HR employee headcount. The 2024 AL release was provisional when checked. Downloads are cached in `academic_librariesdata/`; `rm_disk` and `merge_with_char` work as in the other classes. See the [AL harmonization guide](codebook/harmonization.md#academic-libraries) for source eligibility and meanings.

An opt-in live integration check (`GENPEDS_LIVE_TESTS=1 pytest tests/test_academic_libraries_live.py -q`) downloads final FY2023 AL and HD files and checks the cleaned join; the ordinary suite skips it.

- **HumanResources** (modern IPEDS staffing and salary files, 2012–2024)
```python
from genpeds import HumanResources

hr = HumanResources(2024)
staff = hr.run(dataset='staff', category_codes=['1100'],
               merge_with_char=True)  # grand-total staff row per school
professor_pay = hr.run(dataset='instructional_salaries',
                       category_codes=['1'])  # professors only
professor_pay[['id', 'rank_label', 'equated_9_month_salary_men',
               'equated_9_month_salary_women']]

hr.get_dataset_vars('instructional_salaries')  # variables for this file family
```

`dataset` selects **one** source family and row grain:

| `dataset` | Source | Contents |
| --- | --- | --- |
| `'staff'` (default) | `S*_OC` | Occupational/FT/PT counts by sex and race/ethnicity. |
| `'employees'` | `EAP*` | Employee counts by occupation/faculty status, FT/PT and medical-school status. |
| `'instructional_staff'` | `S*_IS` | Full-time instructional faculty by tenure/faculty status, rank, sex and race/ethnicity. |
| `'faculty_ranks'` | `S*_SIS` | Faculty-status/rank totals; **no sex breakdown** in this table. |
| `'new_hires'` | `S*_NH` | Full-time hires by occupation, faculty status, sex and race/ethnicity. |
| `'instructional_salaries'` | `SAL*_IS` | Instructional counts and salary outlays by rank/sex, contract months and available average salaries. |
| `'noninstructional_salaries'` | `SAL*_NIS` | Full-time noninstructional counts and annual salary outlays by occupation; **no sex breakdown**. |

The full HR cleaner preserves year-specific `*_code` **and** NCES dictionary labels for categories; [`codebook/hr_codes.csv`](codebook/hr_codes.csv) lists their definitions. `category_codes` filters the dataset's primary code (`STAFFCAT`, `EAPCAT`, `SISCAT`, `FACSTAT`, `SNHCAT`, `ARANK`, or `01`–`14` for noninstructional occupations). **Totals and detail categories overlap**, so don't sum every row for a school. `get_available_vars()` is the union across datasets; `get_dataset_vars(dataset)` describes columns actually returned by one selection. Count and salary fields retain NCES `_status` flags. All datasets support `see_progress`, `merge_with_char`, and `rm_disk`.

`year=2024` describes **fall 2024 staffing**, but salary fields cover **academic year 2024–25**. The source's nine-month-equivalent average (`equated_9_month_salary_*`) starts in **2016** and is **missing in 2012–15**, when the salary collection used different months-worked information. New-hire counts cover **July–October through 2017** versus **the preceding November–October from 2018**; `hire_window_months` and `hire_period_start_year` expose the boundary. `HumanResources` starts at the modern **2012 occupational redesign**: earlier IPEDS salary/staff files exist, but their categories and pay conventions are not silently joined into this series. These are institutional counts, annual salary outlays and rank/contract averages—**not individual salaries or medians**. See the [harmonization guide](codebook/harmonization.md#human-resources) for the reporting populations and comparability notes.
- **Completion** (awards by CIP field, level and first/second major, 1984–2025)
```python
from genpeds import scrape_ipeds_data, Completion

scrape_ipeds_data(subject='completion',
                  year_range=(1984,2023))

completedat = Completion(year_range=(1984,2025))

complete_df = completedat.run(degree_level='doct',
                               get_cip_codes=True,
                               merge_with_char=True,
                               rm_disk=False)

# Filter first or second majors for years 2001 onward:
first_majors = Completion((2020, 2025)).run(
    degree_level='bach', major='first')
second_majors = Completion(2025).run(
    degree_level='bach', major='second')
```

`major` accepts `'first'`, `'second'`, or `'both'` (default). The `MAJORNUM` code distinguishes first and second majors **from 2001 onward**. Before that, the C-A files do not identify major order: the default preserves those awards with `major_type='unspecified'`, and asking for first or second majors raises a `ValueError`. For later years `major_type` records the chosen category, or `'both'` when first- and second-major awards are summed within a CIP. A second major is another reported field of study, **not another distinct graduate**. `year=2025` is the July 2024–June 2025 award period; CIP descriptions are joined by code and reporting year.

- **Completers** (distinct people earning degrees or certificates, 2012–2025)
```python
from genpeds import Completers

# C-B: one row per institution/year, unduplicated across all awards:
people_df = Completers((2012, 2025)).run(merge_with_char=True)

# C-C: distinct completers within a specific award level, with age bands:
bachelors_df = Completers(2025).run(degree_level='bach')
levels_df = Completers(2025).run(degree_level='award_levels')
```

`degree_level='all'` (default) downloads C-B and counts each student **once across all awards**. `'assc'`, `'bach'`, `'mast'`, and `'doct'` select the corresponding C-C award level; `'award_levels'` returns **all** available C-C award levels, including certificates and postgraduate certificates, one row per institution/year/award level. C-C counts are unduplicated *within a level*, but a student may earn awards at multiple levels: **do not sum C-C rows to reproduce C-B**. C-C has age bands (`age_under_18`, `age_18_to_24`, `age_25_to_39`, `age_40_plus`, `age_unknown`); B has no age breakdown, so these fields are missing there. Both have overall and race/sex counts with `_status` flags. `award_level_code` normalizes leading zeros in source C codes, while `source_award_code` retains them. Short-certificate categories changed in 2020 (codes 11 and 12 replace the earlier code 1); the readable `award_level` reflects the year's dictionary. Neither B nor C has CIP/major-order detail; use `Completion` for awards by field. Downloads use `completersdata/` for B or `completers_by_awarddata/` for C, and `rm_disk=True` removes the selected cache.
- **Graduation** (e.g., graduation rate by race/gender/level, etc.) (available 2000-2024)
```python
from genpeds import scrape_ipeds_data, Graduation

scrape_ipeds_data(subject='graduation',
                  year_range=(2000,2023))

graddat = Graduation(year_range=(2000,2023))

grad_df = graddat.run(degree_level='bach',
                      merge_with_char=True)
```

`Graduation()` now defaults to its configured 2000–2024 years. The rates above use **150%** of normal completion time for the selected bachelor or associate cohort.

- **Graduation200** (100%, 150%, and 200%-of-normal-time outcomes; reporting years 2008–2024)
```python
from genpeds import Graduation200

rates = Graduation200([2008, 2009, 2024])
df = rates.run(cohort_type='both', merge_with_char=True)
bachelor_df = rates.run(cohort_type='bachelor')
```

`cohort_type` is `'bachelor'`, `'less_than_four_year'`, or `'both'` (default). The latter includes **degree and certificate** seekers at less-than-four-year institutions; it is not an associate-only group. For `year=2024`, `cohort_year` is 2016 for bachelor's entrants and 2020 for less-than-four-year entrants. `adjusted_cohort_150` and `adjusted_cohort_200` may differ because additional exclusions are allowed; `completed_150_to_200` is an incremental count, whereas `completed_200` is cumulative. `rate_100`, `rate_150`, and `rate_200` are NCES's published percentages, not rates recalculated or clamped by the package. `still_enrolled` starts in 2011, and `collection_phase='supplemental'` identifies the initial 2008 wave. Counts and rates have `_status` flags. GR200 follows older entering cohorts than `Graduation` for the same reporting year, so it remains a separate class. Downloads are cached in `graduation200data/`.

- **OutcomeMeasures** (awards at 4/6/8 years and enrollment outcomes at 8 years; 2015–2024)
```python
from genpeds import OutcomeMeasures

outcomes = OutcomeMeasures((2017, 2024))
pell_transfers = outcomes.run(cohort_type='non_first_time_full_time',
                             pell_group='pell', merge_with_char=True)
initial = OutcomeMeasures((2015, 2016)).run(
    cohort_type='first_time_full_time')
```

`cohort_type` accepts `'all'` (default), `'total'` (2017+), or the first-/non-first-time × full-/part-time groups. `pell_group` is `'total'` (default), `'pell'`, `'non_pell'`, or `'all'`; Pell breakdowns exist only from **2017**. `'all'` includes overlapping overall and Pell subcohorts: **never sum them as independent people**. `year=2024` follows July 2016–June 2017 entering students to August 2024. `awards_4/6/8` and `awards_*_pct` retain NCES's counts and published rates for awards at the reporting institution; `certificate_*`, `associate_*`, and `bachelor_*` distinguish highest award at each checkpoint from 2017. Eight-year `still_enrolled_here_8`, `subsequently_enrolled_elsewhere_8`, `enrollment_unknown_8`, and `no_award_8` describe further outcomes, **not earnings or awards earned elsewhere**. The 2015–16 `schema_version='initial'` has separate six- and eight-year adjusted cohorts and no four-year/Pell/award-level breakdown; 2015 also has an `inconsistency_flag`. Counts and percentages preserve NCES `_status` flags. Source ZIPs are cached in `outcome_measuresdata/`. See the [harmonization guide](codebook/harmonization.md#outcome-measures) for cross-year interpretation.

These classes support institution-level trends across admissions, enrollment, persistence, completions, prices, aid, staffing, finance, and academic libraries. Further IPEDS subjects and additional fields within existing subjects can be added over time.

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
# Opt in to live NCES download/clean/merge checks as well:
GENPEDS_LIVE_TESTS=1 pytest tests/
```

The default suite is offline and uses isolated temporary caches. The opt-in checks fetch a small number of real NCES files and also use temporary directories; test order and pre-existing download folders do not affect either mode.
