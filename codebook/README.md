# genpeds API codebook

This is the **version-controlled, stand-alone** reference for the output of `genpeds`; these files live outside the installable Python package. It describes what the **current cleaners return**, not every variable NCES publishes. Updated with the 1984–2025 configured file series; the latest published year differs by subject.

| File | Purpose |
| --- | --- |
| [harmonization.md](harmonization.md) | How years, row grains, transformations, joins, and important definition breaks work. Start here. |
| [variables.csv](variables.csv) | One row per publicly described API column: subject, description, supported/field years, units, grain, raw fields, and calculation or mapping. |
| [source_files.csv](source_files.csv) | Per-subject/year endpoint from `src/genpeds/cfg.json` with constructed data and dictionary ZIP URLs. Includes internal download variants. |
| [changes.csv](changes.csv) | Dated decisions and dictionary evidence for schema/definition transitions. |
| [codes.csv](codes.csv) | Important categorical codes and their **year-dependent** API interpretations. |
| [build.py](build.py) | Regenerates the two config-derived CSVs; `--check` verifies they match the current source. |

Search `variables.csv` by `api_class` + `variable`, e.g. `Completion` + `major_type`. The `subject_years` column gives the **API's overall supported interval**; it is **not proof that every field exists or every institution reports it throughout that interval**. Read `field_availability` and the matching sections of `harmonization.md`/`changes.csv`. `_status` fields hold source NCES reporting/imputation codes; see [missingness and flags](harmonization.md#missing-data-and-source-flags).

`source_files.csv` reflects **configured filenames and the download URL rule**, not an independently re-fetched or validated URL manifest. Use its `dictionary_zip_url` to check a claim against the official dictionary for a particular year (HTML in some older years, Excel in later years). NCES can revise releases; a raw `_rv.csv` in a data ZIP may supersede an earlier CSV. Configured file-year is not necessarily an aid, fiscal, cohort, or academic year; the [period key](harmonization.md#year-and-join-semantics) gives the differences.

To regenerate the two inventories in a development environment with package dependencies installed:

```bash
python codebook/build.py
python codebook/build.py --check
```

`changes.csv`, `codes.csv`, and the guide are curated; review these manually when expanding a subject. The raw data and dictionaries inspected during the research remain under the ignored `scratch/` directory on the research workstation and are **not** needed to read or regenerate this codebook. The primary evidence is linked in `changes.csv` and `source_files.csv`.
