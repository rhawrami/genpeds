# genpeds API codebook

This is the **version-controlled, stand-alone** reference for the output of `genpeds`; these files live outside the installable Python package. It describes what the **current cleaners return**, not every variable NCES publishes. Updated with the 1984–2025 configured file series; the latest published year differs by subject.

| File | Purpose |
| --- | --- |
| [harmonization.md](harmonization.md) | How years, row grains, transformations, joins, and important definition breaks work. Start here. |
| [variables.csv](variables.csv) | One row per publicly described API column: subject, description, supported/field years, units, grain, raw fields, and calculation or mapping. |
| [source_files.csv](source_files.csv) | Per-subject/year endpoint from `src/genpeds/cfg.json` with constructed data and dictionary ZIP URLs. Includes internal download variants. |
| [changes.csv](changes.csv) | Dated decisions and dictionary evidence for schema/definition transitions. |
| [codes.csv](codes.csv) | Important categorical codes and their **year-dependent** API interpretations. |
| [hr_codes.csv](hr_codes.csv) | Year-specific HR category/rank/occupation labels from NCES dictionaries (including occupation recodes). |
| [build.py](build.py) | Regenerates the two config-derived CSVs; `--check` verifies they match the current source. |
| [build_hr_labels.py](build_hr_labels.py) | Recreates packaged `src/genpeds/hr_labels.json` and `hr_codes.csv` from the downloaded dictionaries under ignored `scratch/hr_api/`; supports `--check`. |

Search `variables.csv` by `api_class` + `variable`, e.g. `Completion` + `major_type`. The `subject_years` column gives the **API's overall supported interval**; it is **not proof that every field exists or every institution reports it throughout that interval**. Read `field_availability` and the matching sections of `harmonization.md`/`changes.csv`. `_status` fields hold source NCES reporting/imputation codes; see [missingness and flags](harmonization.md#missing-data-and-source-flags).

`source_files.csv` reflects **configured filenames and the download URL rule**, not generally an independently re-fetched URL manifest. Its 63 Finance data ZIPs were HEAD-checked on 2026-09-26; Finance dictionaries were inspected for selected years rather than all 63. Use its `dictionary_zip_url` to check a claim against the official dictionary for a particular year (HTML in some older years, Excel in later years). NCES can revise releases; a raw `_rv.csv` in a data ZIP may supersede an earlier CSV. Configured file-year is not necessarily an aid, fiscal, cohort, or academic year; the [period key](harmonization.md#year-and-join-semantics) gives the differences.

Evidence in `changes.csv` can also link to older NCES tables **outside the currently configured API**, for example `SAL2011_A` as the pre-2012 HR comparison. Those research references are not downloadable subjects listed in `source_files.csv`.

To regenerate the two inventories in a development environment with package dependencies installed:

```bash
python codebook/build.py
python codebook/build.py --check
```

`changes.csv`, `codes.csv`, and the guide are curated; review these manually when expanding a subject. The ordinary generated variable/source inventories need no `scratch/` files; **regenerating the HR category labels** requires its 2012–24 year dictionaries under ignored `scratch/hr_api/`. The packaged label JSON and `hr_codes.csv` are committed snapshots and can be used without those ZIPs. Primary evidence is linked in `changes.csv`, `hr_codes.csv`, and `source_files.csv`.
