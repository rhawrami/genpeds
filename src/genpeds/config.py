'''
MAIN DATASETS AS OF FIRST RELEASE
- INCLUDES [CHARACTERISTICS, ADMISSIONS, ENROLLMENT, COMPLETION, GRADUATION]
- DICTIONARY INCLUDES DESCRIPTION AND ENDPOINT FORMATTING RULES
'''

DATASETS = {

    'characteristics' : {
        'description' : '''Institutional characteristics for each school in a given year, including information like a school's name and address; available for years 1984-2023.''',
        'years_available' : (1984,2023),
        'dir' : 'characteristicsdata',
        'file_prefix' : 'characteristics',
        'file_template' : 'https://nces.ed.gov/ipeds/datacenter/data/{}.zip', 
        'format_rules' : [
            (lambda y : y <= 1985, 'IC{year}'),
            (lambda y : (1985 < y <= 1989) or (1991 < y <= 1994), 'IC{year}_A'),
            (lambda y : y == 1990,  'IC90HD'), 
            (lambda y : y == 1991,  'IC1991_hdr'),
            (lambda y : 1994 < y < 1997, 'ic{lag0}{lead1}_A'), 
            (lambda y : y == 1997, 'ic9798_HDR'), 
            (lambda y : y == 1998, 'IC98hdac'),
            (lambda y : y == 1999, 'IC99_HD'),
            (lambda y : y == 2000 or y == 2001, 'FA{year}HD'),
            (lambda y : y >= 2002, 'HD{year}')
        ]
        
    },

    'admissions' : {
        'description' : '''Admissions data for each school in a given year (measured in the Fall), including information like ACT/SAT scores and acceptance rates by gender; available for years 2001-2023.''',
        'years_available' : (2001,2023),
        'dir' : 'admissionsdata',
        'file_prefix' : 'admissions',
        'file_template' : 'https://nces.ed.gov/ipeds/datacenter/data/{}.zip',
        'format_rules' : [
            (lambda y: 2001 <= y <= 2013, 'IC{year}'),
            (lambda y: 2014 <= y <= 2023, 'ADM{year}'), 
        ]
    },

    'enrollment' : {
        'description' : '''Enrollment data for each school in a given year (measured in the Fall), including information like the male enrollment share and enrollment by gender and race; available at the undergraduate or graduate level; available for years 1984-2023.''',
        'years_available' : (1984,2023),
        'dir' : 'enrollmentdata',
        'file_prefix' : 'enrollment',
        'file_template' : 'https://nces.ed.gov/ipeds/datacenter/data/{}.zip',
        'format_rules' : [
            (lambda y: y <= 1985, 'EF{year}'),
            (lambda y: (1985 < y < 1990) or (1991 < y < 1994), 'EF{year}_A'),
            (lambda y: y == 1990, 'EF90_A'),
            (lambda y: y == 1991, 'ef1991_A'),
            (lambda y: y == 1994,  'EF{year}_ANR'),
            (lambda y: 1994 < y < 2000, 'EF{lag0}_ANR'),
            (lambda y: y >= 2000, 'EF{year}A')
        ]
    },

    'completion' : {
        'description' : '''Completion data for each school in a given year by detailed subject field, including information like the male completion share within a subject (e.g., Economics); available at the Associate, Bachelor's, Master's or Doctoral level; available for years 1984-2023.''',
        'years_available' : (1984,2023),
        'dir' : 'completiondata',
        'file_prefix' : 'completion',
        'file_template' : 'https://nces.ed.gov/ipeds/datacenter/data/{}.zip',
        'format_rules' : [
            (lambda y: y < 1990 or (1991 < y < 1995), 'C{year}_CIP'),
            (lambda y: y == 1990, 'C8990CIP'),
            (lambda y: y == 1991, 'c1991_cip'),
            (lambda y: 1995 <= y < 2000, 'C{lag1}{lag0}_A'),
            (lambda y: y >= 2000, 'C{year}_A')
        ]
    },

    'graduation' : {
        'description' : '''Graduation data for each school in a given year, including information like the graduation rate by gender and race; available at the Associate or Bachelor's level; available for years 2000-2023.''',
        'years_available' : (2000,2023),
        'dir' : 'graduationdata',
        'file_prefix' : 'graduation',
        'file_template' : 'https://nces.ed.gov/ipeds/datacenter/data/{}.zip',
        'format_rules' : [
            (lambda y: y in range(2000,2024), 'GR{year}')
        ]
    },

    'cip' : {
        'description' : '''Provides subject field codes for subjects in a given year; should be used with Completion data; available for years 1984-2023.''',
        'years_available' : (1984,2023),
        'dir' : 'cipdata',
        'file_prefix' : 'cip',
        'file_template' : 'https://nces.ed.gov/ipeds/datacenter/data/{}_Dict.zip',
        'format_rules' : [
            (lambda y: (y < 1990) or (1991 < y < 1995), 'C{year}_CIP'),
            (lambda y: y == 1990, 'C8990CIP'),
            (lambda y: y == 1991, 'c1991_cip'),
            (lambda y: 1995 <= y < 2000, 'C{lag1}{lag0}_A'),
            (lambda y: y >= 2000, 'C{year}_A')
        ]
    }

}


'''
VARIABLES AND VARIABLE DESCRIPTIONS INCLUDED IN EACH SUBJECT DATASET
'''
VARIABLE_DICT = {

    'characteristics' : {
       'id' : 'Institutional unique identifier ID; though UNITIDs can vary over time due to instutions splitting, this variable is generally consistent for an institution over time.', 
       'year' : 'Survey year.',
       'name' : 'Name of institution location.', 
       'address' : 'Address of institution location.', 
       'city' : 'City of institution location.', 
       'state' : 'State of institution location.', 
       'zipcode' : 'Zipcode of institution location.', 
       'webaddress' : 'Admissions website URL of institution location.',
       'longitude' : 'Longitude coordinate of institution location.', 
       'latitude' : 'Latitude coordinate of institution location.', 
    },

    'admissions' : {
       'id' : 'Institutional unique identifier ID; though UNITIDs can vary over time due to instutions splitting, this variable is generally consistent for an institution over time.', 
       'year' : 'Survey year.',
       'tot_applied' : 'Total number of first-time, degree/certificate-seeking applicants in a given year.',
       'tot_admitted' : 'Total number of first-time, degree/certificate-seeking applicants who were admitted in a given year.', 
       'tot_enrolled' : 'Total number of admitteees who ultimately enrolled (includes part-time and full-time enrollemnt).', 
       'men_applied' : 'Number of first-time, degree/certificate-seeking men who applied to an institution in a given year.', 
       'men_admitted' : 'Number of first-time, degree/certificate-seeking men who were admitted to an institution in a given year.', 
       'men_enrolled' : 'Number of admitted men who ultimately enrolled (includes part-time and full-time enrollemnt).', 
       'accept_rate_men' : 'Acceptance rate of male applicants.', 
       'accept_rate_women' : 'Acceptance rate of female applicants.', 
       'yield_rate_men': 'Yield rate (share of admitted students who ultimately enrolled) of male admittees.',
       'yield_rate_women' : 'Yield rate (share of admitted students who ultimately enrolled) of female admittees.',
       'men_applied_share' : 'Male share of total number of first-time, degree/certificate-seeking applicants in a given year.',
       'men_admitted_share' : 'Male share of total number of first-time, degree/certificate-seeking admittees in a given year.', 
       'share_submit_sat' : 'Share of admitted students who submitted an SAT score.',
       'share_submit_act' : 'Share of admitted students who submitted an ACT score.', 
       'sat_rw_25' : 'SAT reading/writing score (25th percentile).',
       'sat_rw_50' : 'SAT reading/writing score (50th percentile).', 
       'sat_rw_75' : 'SAT reading/writing score (75th percentile).', 
       'sat_math_25' : 'SAT mathematics score (25th percentile).',
       'sat_math_50' : 'SAT mathematics score (50th percentile).',
       'sat_math_75' : 'SAT mathematics score (75th percentile).', 
       'act_comp_25' : 'ACT composite score (25th percentile).', 
       'act_comp_50' : 'ACT composite score (50th percentile).',
       'act_comp_75' : 'ACT composite score (75th percentile).', 
       'act_eng_25' : 'ACT English score (25th percentile).', 
       'act_eng_50' : 'ACT English score (50th percentile).', 
       'act_eng_75' : 'ACT English score (75th percentile).',
       'act_math_25' : 'ACT mathematics score (25th percentile).', 
       'act_math_50' : 'ACT mathematics score (50th percentile).', 
       'act_math_75' : 'ACT mathematics score (75th percentile).'
    },

    'enrollment' : {
       'id' : 'Institutional unique identifier ID; though UNITIDs can vary over time due to instutions splitting, this variable is generally consistent for an institution over time.', 
       'year' : 'Survey year.',
       'studentlevel' : "Level of student enrollment; either 'undergrad' (Undergraduate) or 'grad' (Graduate).",
       'totmen' : 'Total number of men enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'totwomen' : 'Total number of women enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'wtmen' : 'Total number of non-Hispanic White men enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'wtwomen' : 'Total number of non-Hispanic White women enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'bkmen' : 'Total number of non-Hispanic Black men enrolled in the Fall; this includes both part-time and full-time enrollment.',
       'bkwomen' : 'Total number of non-Hispanic Black women enrolled in the Fall; this includes both part-time and full-time enrollment.',
       'hspmen' : 'Total number of Hispanic men (of any race) enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'hspwomen' : 'Total number of Hispanic women (of any race) enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'asnmen' : 'Total number of non-Hispanic Asian men enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'asnwomen' : 'Total number of non-Hispanic Asian women enrolled in the Fall; this includes both part-time and full-time enrollment.', 
       'totmen_share' : "Male share of total enrollment; 'total' here is defined as the sum of male and female enrollment; this includes both part-time and full-time enrollment.",  
       'totwt_share' : "Non-Hispanic White share of total enrollment; 'total' here is defined as the sum of male and female enrollment; this includes both part-time and full-time enrollment.",   
       'totbk_share' : "Non-Hispanic Black share of total enrollment; 'total' here is defined as the sum of male and female enrollment; this includes both part-time and full-time enrollment.", 
       'tothsp_share' : "Hispanic share of total enrollment; 'total' here is defined as the sum of male and female enrollment; this includes both part-time and full-time enrollment.",
       'totasn_share' : "Non-Hispanic Asian share of total enrollment; 'total' here is defined as the sum of male and female enrollment; this includes both part-time and full-time enrollment."
    },

    'completion' : {
        'id' : 'Institutional unique identifier ID; though UNITIDs can vary over time due to instutions splitting, this variable is generally consistent for an institution over time.', 
        'year' : 'Survey year. Note that the cohort being tracked is the cohort that started either six years back (for bachelor) or three years back (for associate).',
        'cip' : 'CIP (Classification of Instructional Programs) code for a subject in a given year.', 
        'totmen' : 'Total number of male completers within a CIP subject.', 
        'totwomen' : 'Total number of female completers within a CIP subject.', 
        'wtmen' : 'Total number of non-Hispanic White men completers within a CIP subject.; this includes both part-time and full-time enrollment.', 
        'wtwomen' : 'Total number of non-Hispanic White women completers within a CIP subject.; this includes both part-time and full-time enrollment.', 
        'bkmen' : 'Total number of non-Hispanic Black men completers within a CIP subject.; this includes both part-time and full-time enrollment.',
        'bkwomen' : 'Total number of non-Hispanic Black women completers within a CIP subject.; this includes both part-time and full-time enrollment.',
        'hspmen' : 'Total number of Hispanic men (of any race) completers within a CIP subject.; this includes both part-time and full-time enrollment.', 
        'hspwomen' : 'Total number of Hispanic women (of any race) completers within a CIP subject.; this includes both part-time and full-time enrollment.', 
        'asnmen' : 'Total number of non-Hispanic Asian men completers within a CIP subject.; this includes both part-time and full-time enrollment.', 
        'asnwomen' : 'Total number of non-Hispanic Asian women completers within a CIP subject.; this includes both part-time and full-time enrollment.', 
        'totwt_share' : "Non-Hispanic White share of total (male and female) completers within a CIP subject.",   
        'totbk_share' : "Non-Hispanic Black share of total (male and female) completers within a CIP subject.", 
        'tothsp_share' : "Hispanic share of total (male and female) completers within a CIP subject.",
        'totasn_share' : "Non-Hispanic Asian share of total (male and female) completers within a CIP subject.",
        'totmen_share' : 'Male share of total (male and female) completers within a CIP subject.', 
        'deglevel' : "Degree level of completers; options include 'assc' (Associate's), 'bach' (Bachelor's), 'mast' (Master's), and 'doct' (Doctoral)."
    },

    'cip' : {
        'year' : 'Survey year. Note that the cohort being tracked is the cohort that started either six years back (for bachelor) or three years back (for associate).',
        'cip' : 'CIP (Classification of Instructional Programs) identifier code.',
        'cip_description' : 'CIP subject label (e.g., Geology).'

    },

    'graduation' : {
       'id' : 'Institutional unique identifier ID; though UNITIDs can vary over time due to instutions splitting, this variable is generally consistent for an institution over time.', 
       'year' : 'Survey year. Note that the cohort being tracked is the cohort that started either six years back (for bachelor) or three years back (for associate).',
       'deglevel' : "Level of student degree; either 'bach' (Bachelor's) or 'assc' (Associates).",
       'totmen' : 'Total number of men within an adjusted cohort.', 
       'totmen_graduated' : "Total number of men within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'totwomen' : 'Total number of women within an adjusted cohort.', 
       'totwomen_graduated' : "Total number of women within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.",
       'wtmen' : 'Total number of non-Hispanic White men within an adjusted cohort.', 
       'wtmen_graduated' : "Total number of non-Hispanic White men within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'wtwomen' : 'Total number of non-Hispanic White women within an adjusted cohort.', 
       'wtwomen_graduated' : "Total number of  non-Hispanic White women within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'bkmen' : 'Total number of non-Hispanic Black men within an adjusted cohort.',
       'bkmen_graduated' : "Total number of non-Hispanic Black men within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'bkwomen' : 'Total number of non-Hispanic Black women within an adjusted cohort.', 
       'bkwomen_graduated' : "Total number of non-Hispanic Black women within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'hspmen' : 'Total number of Hispanic men within an adjusted cohort.',
       'hspmen_graduated' : "Total number of Hispanic men within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'hspwomen' : 'Total number of Hispanic women within an adjusted cohort.', 
       'hspwomen_graduated' : "Total number of Hispanic women within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'asnmen' : 'Total number of non-Hispanic Asian men within an adjusted cohort.',
       'asnmen_graduated' : "Total number of non-Hispanic Asian men within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.", 
       'asnwomen' : 'Total number of non-Hispanic Asian women within an adjusted cohort.', 
       'asnwomen_graduated' : "Total number of non-Hispanic Asian women within an adjusted cohort that graduated within 150 percent of the normal time considered to graduate; for bachelor's degrees, this is six years, and for associate's degrees, this is three years.",  
       'gradrate_totmen' : 'Graduation rate for men (within 150 percent of normal time taken to graduate).',
       'gradrate_totwomen' : 'Graduation rate for women (within 150 percent of normal time taken to graduate).', 
       'gradrate_wtmen' : 'Graduation rate for non-Hispanic White men (within 150 percent of normal time taken to graduate).', 
       'gradrate_wtwomen' : 'Graduation rate for non-Hispanic White women (within 150 percent of normal time taken to graduate).',
       'gradrate_bkmen' : 'Graduation rate for non-Hispanic Black men (within 150 percent of normal time taken to graduate).', 
       'gradrate_bkwomen' : 'Graduation rate for non-Hispanic Black women (within 150 percent of normal time taken to graduate).', 
       'gradrate_hspmen' : 'Graduation rate for Hispanic men (within 150 percent of normal time taken to graduate).',
       'gradrate_hspwomen' : 'Graduation rate for Hispanic women (within 150 percent of normal time taken to graduate).', 
       'gradrate_asnmen' : 'Graduation rate for  non-Hispanic Asianmen (within 150 percent of normal time taken to graduate).', 
       'gradrate_asnwomen' : 'Graduation rate for non-Hispanic Asian women (within 150 percent of normal time taken to graduate).' 
    }
    
}

VARIABLE_RENAME = {
    'characteristics' : {
        'unitid' : 'id', 'instnm' : 'name',
          'addr' : 'address', 'city' : 'city', 'stabbr' : 'state', 'zip' : 'zipcode', 
          'webaddr' : 'webaddress', 
          'longitud' : 'longitude', 'latitude' : 'latitude'
    },

    'admissions' : {
        'unitid' : 'id', 
        'applcnm' : 'men_applied', 'applcnw' : 'women_applied', 
        'admssnm' : 'men_admitted', 'admssnw' : 'women_admitted',
        'satpct' : 'share_submit_sat', 'actpct' : 'share_submit_act',                                      
        'satvr25' : 'sat_rw_25', 'satvr75' : 'sat_rw_75', 
        'satmt25' : 'sat_math_25', 'satmt75' : 'sat_math_75', 
        'actcm25' : 'act_comp_25', 'actcm75' : 'act_comp_75',
        'acten25' : 'act_eng_25', 'acten75' : 'act_eng_75', 
        'actmt25' : 'act_math_25', 'actmt75' : 'act_math_75',
        'enrlftm' : 'men_ft_enrolled', 'enrlftw' : 'women_ft_enrolled',
        'enrlptm' : 'men_pt_enrolled', 'enrlptw' : 'women_pt_enrolled',
        'enrlm' : 'men_enrolled', 'enrlw' : 'women_enrolled',
        'applcn' : 'tot_applied', 'admssn' : 'tot_admitted', 'enrlt' : 'tot_enrolled',
        'acten50' : 'act_eng_50', 'actmt50' : 'act_math_50', 'actcm50' : 'act_comp_50',
        'satvr50' : 'sat_rw_50', 'satmt50' : 'sat_math_50'
    },

    'enrollment' : {
        'unitid' : 'id', 'line' : 'line', 'efrace15' : 'totmen', 'efrace16' : 'totwomen',
        'eftotlm' : 'totmen', 'eftotlw' : 'totwomen', 'efwhitm' : 'wtmen', 'efwhitw' : 'wtwomen',
        'efbkaam' : 'bkmen', 'efbkaaw' : 'bkwomen', 'efhispm' : 'hspmen', 'efhispw' : 'hspwomen', 
        'efasiam' : 'asnmen', 'efasiaw' : 'asnwomen', 'eftotlw' : 'totwomen',
        'efrace11' : 'wtmen', 'efrace12' : 'wtwomen', 'efrace03' : 'bkmen', 'efrace04' : 'bkwomen', 
        'efrace09' : 'hspmen', 'efrace10' : 'hspwomen', 'efrace07' : 'asnmen', 'efrace08' : 'asnwomen'
    },

    'completion' : {
        'unitid' : 'id', 'cipcode' : 'cip', 'awlevel' : 'awlevel',
        'crace15' : 'totmen', 'crace16' : 'totwomen',
        'ctotalm' : 'totmen', 'ctotalw' : 'totwomen', 
        'cwhitm' : 'wtmen', 'cwhitw' : 'wtwomen', 'cbkaam' : 'bkmen', 'cbkaaw' : 'bkwomen', 
        'chispm' : 'hspmen', 'chispw' : 'hspwomen', 'casiam' : 'asnmen', 'casiaw' : 'asnwomen',
        'crace11' : 'wtmen', 'crace12' : 'wtwomen', 'crace03' : 'bkmen', 'crace04' : 'bkwomen', 
        'crace09' : 'hspmen', 'crace10' : 'hspwomen', 'crace07' : 'asnmen', 'crace08' : 'asnwomen'
    },

    'cip' : {
        # nothing needed for now.
    },

    'graduation' : {
        'grtotlm' : 'totmen', 'grtotlw' : 'totwomen', 
        'grwhitm' : 'wtmen', 'grwhitw' : 'wtwomen',
        'grbkaam' : 'bkmen', 'grbkaaw' : 'bkwomen', 
        'grhispm' : 'hspmen', 'grhispw' : 'hspwomen', 
        'grasiam' : 'asnmen', 'grasiaw' : 'asnwomen', 
        'grrace15' : 'totmen', 'grrace16' : 'totwomen',
        'grrace11' : 'wtmen', 'grrace12' : 'wtwomen', 
        'grrace03' : 'bkmen', 'grrace04' : 'bkwomen', 
        'grrace09' : 'hspmen', 'grrace10' : 'hspwomen', 
        'grrace07' : 'asnmen', 'grrace08' : 'asnwomen',
        'chrtstat' : 'chrtstat', 'section' : 'section', 
        'cohort' : 'cohort', 'unitid' : 'id', 'grtype' : 'grtype'
    }
}