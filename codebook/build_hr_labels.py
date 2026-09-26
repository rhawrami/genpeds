"""Build year-specific HR category labels from NCES dictionary ZIPs.

Requires the research copies in scratch/hr_api (see its download_files.py).
Produces the packaged src/genpeds/hr_labels.json and a searchable CSV in
codebook/. `--check` verifies both without writing. Raw codes are retained by
the API even when a label is absent in a particular year's dictionary.
"""

import csv
import io
import json
from pathlib import Path
import re
import sys
import warnings
import zipfile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / 'scratch/hr_api'
DESTINATION = ROOT / 'src/genpeds/hr_labels.json'
CSV = ROOT / 'codebook/hr_codes.csv'
FAMILIES = {
    'staff': ('S{year}_OC', ('staffcat', 'ftpt', 'occupcat')),
    'employees': ('EAP{year}', ('eapcat', 'occupcat', 'facstat')),
    'instructional_staff': ('S{year}_IS', ('siscat', 'facstat', 'arank')),
    'faculty_ranks': ('S{year}_SIS', ('facstat',)),
    'new_hires': ('S{year}_NH', ('snhcat', 'occupcat', 'facstat')),
    'instructional_salaries': ('SAL{year}_IS', ('arank',)),
    'noninstructional_salaries': ('SAL{year}_NIS', ()),
}


def build():
    labels = {}
    records = []
    for dataset, (pattern, fields) in FAMILIES.items():
        labels[dataset] = {}
        for year in range(2012, 2025):
            stem = pattern.format(year=year)
            source = SAMPLES / f'{stem}_Dict.zip'
            if not source.is_file():
                raise FileNotFoundError(f'Missing year dictionary: {source}')
            root = ('https://nces.ed.gov/ipeds/complete-data-files/' if year > 2022
                    else 'https://nces.ed.gov/ipeds/datacenter/data/')
            url = root + stem + '_Dict.zip'
            with zipfile.ZipFile(source) as archive:
                member = next(name for name in archive.namelist()
                              if name.lower().endswith(('.xlsx', '.xls')))
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', message='Cannot parse header or footer',
                                            category=UserWarning)
                    excel = pd.ExcelFile(io.BytesIO(archive.read(member)))
                    if fields:
                        sheet = next(name for name in excel.sheet_names
                                     if name.lower() == 'frequencies')
                        frequencies = pd.read_excel(excel, sheet_name=sheet, dtype=str)
                        frequencies.columns = frequencies.columns.str.lower().str.strip()
                    else:
                        frequencies = pd.DataFrame()
                    columns = pd.read_excel(excel, sheet_name=next(name for name in excel.sheet_names
                                                                    if name.lower() == 'varlist'), dtype=str)
                    columns.columns = columns.columns.str.lower().str.strip()
            mapping = {}
            for field in fields:
                rows = frequencies.loc[frequencies['varname'].astype(str).str.lower().eq(field)]
                codes = {}
                for _, item in rows.iterrows():
                    code = str(item['codevalue']).strip()
                    label = str(item['valuelabel']).strip()
                    if code.lower() == 'nan' or label.lower() == 'nan':
                        continue
                    if code in codes and codes[code] != label:
                        raise ValueError(f'Conflicting {stem} {field} {code} labels')
                    codes[code] = label
                if not codes:
                    raise ValueError(f'Missing category labels: {stem} {field}')
                mapping[field] = codes
            if dataset == 'noninstructional_salaries':
                groups = {}
                for _, item in columns.iterrows():
                    match = re.fullmatch(r'SANIN(\d\d)', str(item['varname']).strip(), re.I)
                    if match:
                        label = re.sub(r'\s*-\s*number\s*$', '',
                                       str(item['vartitle']).strip(), flags=re.I)
                        groups[match.group(1)] = label
                if set(groups) != {f'{i:02d}' for i in range(1, 15)}:
                    raise ValueError(f'Incomplete noninstructional groups in {stem}')
                mapping['occupation'] = groups
            labels[dataset][str(year)] = mapping
            records.extend((year, dataset, field, code, label, url)
                           for field, codes in mapping.items()
                           for code, label in sorted(codes.items()))
    json_text = json.dumps(labels, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('year', 'dataset', 'source_field', 'source_code', 'source_label',
                     'nces_dictionary_url'))
    writer.writerows(records)
    return json_text, output.getvalue()


def main():
    snapshots = dict(zip((DESTINATION, CSV), build()))
    for path, contents in snapshots.items():
        if '--check' in sys.argv:
            if not path.is_file() or path.read_text(encoding='utf-8') != contents:
                raise SystemExit(f'{path} is stale; run python codebook/build_hr_labels.py')
        else:
            path.write_text(contents, encoding='utf-8')
        print(path.relative_to(ROOT), 'checked' if '--check' in sys.argv else 'written')


if __name__ == '__main__':
    main()
