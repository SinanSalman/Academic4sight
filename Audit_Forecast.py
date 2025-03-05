#! /usr/bin/env python

"""Copyright:  Sinan Salman, 2024-2025
License:    GPLv3

Version History:
05.03.2025  3.1     bug fix; add co-req if not taken with course when registered; check in student's catalog before adding a pre-req to key courses
02.03.2025  3.0     new feature; added stochastic forecasting
21.02.2025  2.12    fixed bug; add pre-req only if it is in the student catalog, if not, it is not required to be taken
21.02.2025  2.11    improved logic; some courses (e.g., GroupA or Elective) can repeat, others not
18.02.2025  2.1     bug fix; new students' MinCH=15; failed courses enrolled now should not appear in projection
15.02.2025  2.0     new feature: forecasting using "add_courses"
14.02.2025  1.61    bug fix; do not add a failed course to Projected_Courses & Must_take_Courses if it is already registered
31.01.2025  1.51    updated readme.md and created github
16.12.2024	1.5     bug fix; set() are not ordered while lists are. Replaced sets with ordered lists and introduced a function to remove duplicates from lists.
12.12.2024	1.4     bug fix; if the course was listed in current courses and completed courses, it was checked twice, with the second check resulting in an uncounted course.
11.12.2024	1.3     new feature; added a "common_catalog" yaml default file and a rule for adding comments; Verbose configuration affects screen, not log file
06.12.2024	1.2     improved logic; fixed rules bugs; checks for co-reqs in projection; added log_file
29.05.2024	1.1     improved logic, format, and added rules
20.05.2024	1.0     initial release"""

import pandas as pd
import yaml
import glob
import copy
import time
from collections import Counter
from tqdm import tqdm
# added below to ignore "PerformanceWarning: DataFrame is highly fragmented.  This is usually the result of calling `frame.insert` many times, which has poor performance.  Consider joining all columns at once using pd.concat(axis=1) instead. To get a de-fragmented frame, use `newframe = frame.copy()`"
from warnings import simplefilter
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)

Required_Columns = ['ID','Catalog','Concentration','Campus','cGPA',
                    'CompletedCourses','CurrentCourses','FailedCourses',
                    'Registered','Registered_Summer', 'Skill']
Forecast_Columns = ['ID', 'Status', 'Standing', 'Campus', 'Catalog', 'College',
                    'Degree', 'Major', 'Concentration', 'Program', 'Current Credits',
                    'Earned Hours', 'GPA Hours', 'cGPA', 'Skill']
log_text = ''

def print_log(log_entry, verbose_to_screen = False):
    global log_text
    log_text += log_entry + '\n'
    if verbose_to_screen:
        print(log_entry)


def read_yaml(filename):
    print_log(f'reading {filename}...', verbose_to_screen = True)
    with open(filename, 'r') as yamlfile:
        return yaml.load(yamlfile, Loader=yaml.FullLoader)


def no_duplicates_ordered_list(list_with_duplicates):
    return list(dict.fromkeys(list_with_duplicates).keys())


def clean_course_code(course):
    return course.replace('-','').strip()[:6]


tik = time.time()
config_filename = '_config.yaml'
config = read_yaml(config_filename)
verbose = config['Verbose']
# use catalog_defaults as a base and update with each catalog file
catalog_defaults = read_yaml(config['catalog_defaults'])
catalogs = {}
for filename in glob.glob(config['catalog_filenames']):
    tmp = copy.deepcopy(catalog_defaults)
    for k,v in read_yaml(filename).items():
        if k not in tmp.keys():
            tmp[k] = v
        else:
            if type(tmp[k]) != type(v):
                raise ValueError(f'Error - Incompatible value types in catalog YAML files: ({catalog_defaults}){tmp[k]} :: ({filename}){v}')
            elif isinstance(v, list):
                for v1 in v:
                    if v1 not in tmp[k]:
                        tmp[k].append(v1)
            elif isinstance(v, dict):
                for k1,v1 in v.items():
                    tmp[k][k1] = v1
    catalogs[filename[1:5]] = tmp


def load_data(filename):
    global config
    format = config['File_Format'][filename]
    df = pd.read_excel(filename, sheet_name=0, skiprows=format['skiprows'])
    missing_columns_error = []
    missing_columns_warning = []
    for k,v in format['columns'].items():
        if k not in df.columns:
            if v in Required_Columns:
                missing_columns_error.append(k)
            else:
                missing_columns_warning.append(k)
                df[k] = ''
    if missing_columns_warning:
        print_log(f'Warning: the following columns {missing_columns_warning} are missing in the input data file: {filename}, continuing with no entries for these columns.', verbose_to_screen = True)
    if missing_columns_error:
        print_log(f'Error: the following columns {missing_columns_error} are missing in the input data file: {filename}', verbose_to_screen = True)
        quit()
    df.rename(columns=format['columns'], inplace=True)
    for k in Required_Columns:
        if k not in df.columns:
            missing_columns_error.append(k)
    if missing_columns_error:
        print_log(f'Error: the following columns {missing_columns_error} are missing in the input data file: {filename}', verbose_to_screen = True)
        quit()
    for c in df.columns:
        if c in ['FailedCourses','Registered','Registered_Summer','CurrentCourses','CompletedCourses']:
            df[c] = df[c].fillna('')
    return df


def drop_course(course, Catalog):
    if course in Catalog:
        Catalog.remove(course)
        return True
    else:
        return False


def get_course_CHs(course, Course_CHs):
    for k,v in Course_CHs.items():
        if k != 'default':
            if course in v:
                return k
    return getattr(Course_CHs, 'default', 3)


def apply_rule(rules, rec,  CH_earned,  Projected_Courses,  Must_take_Courses, not_in_plan):
    applied_rules = []
    for label, rule in rules.items():
        applicable = True
        for k,v in rule.items():
            if k in ['Drop','If_Not_Drop','Note']:
                continue
            if k == 'Status':
                if rec['Status'] in v:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'Skill':
                if rec['Skill'] in v:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'Campus':
                if rec['Campus'] in v:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'ProjectionCount':
                if v[0] <= len(Projected_Courses) <= v[1]:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'ECHiP':
                if v[0] <= CH_earned <= v[1]:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'MatchAll':
                if all(x in Projected_Courses for x in v):
                    applicable &= True
                else:
                    applicable &= False
            if k == 'MatchAny':
                if any(x in Projected_Courses for x in v):
                    applicable &= True
                else:
                    applicable &= False
            if k == 'MissingAny':
                if any(x not in Projected_Courses for x in v):
                    applicable &= True
                else:
                    applicable &= False
            if k == 'MissingAll':
                if all(x not in Projected_Courses for x in v):
                    applicable &= True
                else:
                    applicable &= False
            if k == 'NotInPlanCount':
                if v[0] <= len(not_in_plan) <= v[1]:
                    applicable &= True
                else:
                    applicable &= False
        Dropped_Courses = set()
        v = []
        if ('Drop' in rule.keys() and applicable):
            v = rule['Drop']
        if ('If_Not_Drop' in rule.keys() and not applicable):
            v = rule['If_Not_Drop']            
        for course in v:
            if course in Projected_Courses:
                Projected_Courses.remove(course)
                Dropped_Courses.add(course)
            if course in Must_take_Courses:
                Must_take_Courses.remove(course)
                Dropped_Courses.add(course)
        if Dropped_Courses:
            applied_rules.append(f'{label}(drop:{"+".join(Dropped_Courses)})')
        if ('Note' in rule.keys() and applicable):
            applied_rules.append(f'Note: {rule["Note"]}')
    return '\n\t'.join(applied_rules)


def audit_student_registration(record, catalog_year, concentration):
    global catalogs

    # setup variables
    rec = record.to_dict()
    if rec["FailedCourses"]:
        FailedCourses = [clean_course_code(x) for x in rec["FailedCourses"].split(',')]
    else:
        FailedCourses = []
    if rec["CompletedCourses"]:
        CompletedCourses = [clean_course_code(x) for x in rec["CompletedCourses"].split(',')]
    else:
        CompletedCourses = []
    if rec["CurrentCourses"]:
        CurrentCourses = [clean_course_code(x) for x in rec["CurrentCourses"].split(',')]
    else:
        CurrentCourses = []
    if rec["Registered"]:
        Registered = [clean_course_code(x) for x in rec["Registered"].split(',')]
    else:
        Registered = []
    if rec["Registered_Summer"]:
        Registered_Summer = [clean_course_code(x) for x in rec["Registered_Summer"].split(',')]
    else:
        Registered_Summer = []
    cat = copy.deepcopy(catalogs[catalog_year][concentration])
    grp = copy.deepcopy(catalogs[catalog_year]['Groups'])
    Course_CHs = copy.deepcopy(catalogs[catalog_year]['Course_CHs'])
    CoRequisites = copy.deepcopy(catalogs[catalog_year]["CoRequisites"])
    PreRequisites = copy.deepcopy(catalogs[catalog_year]["PreRequisites"])

    #  Collapse all Pre-Reqs into a flat list to add to Key_Courses
    Key_Courses = catalogs[catalog_year]['Key_Courses'].copy()
    for course, PreReq in PreRequisites.items():
        if course in cat: # only add pre-req if the course is in the student's catalog
            if isinstance(PreReq, str): # one course
                if PreReq not in Key_Courses:
                    Key_Courses.append(PreReq)
            elif isinstance(PreReq, dict): # any of the courses in a dict 
                for c in PreReq.values():
                    if c not in Key_Courses:
                        Key_Courses.append(c)
            elif isinstance(PreReq, list): # all of the courses in a list
                for c in PreReq:
                    if c not in Key_Courses:
                        Key_Courses.append(c)
            else:
                print_log(f'Error: preReq "{PreReq}" is not recognized as valid format for PreRequisites', verbose_to_screen = True)
                quit()

    # remove completed & currently taking courses from the catalog plan & check for group/elective courses
    taken = []
    satisfy_groups = []
    not_in_plan = []
    for course in no_duplicates_ordered_list(CompletedCourses+CurrentCourses):
        if drop_course(course, cat):
            taken.append(course)
        else:
            course_found_in_groups = False
            for g, l in grp.items():
                if course in l:
                    if drop_course(g, cat):
                        taken.append(course)
                        satisfy_groups.append(f'{course}({g})')
                        course_found_in_groups = True
                        break
            if not course_found_in_groups:
                not_in_plan.append(course)

    print_log(f'                  Catalog: {catalog_year}', verbose_to_screen = verbose)
    print_log(f'                     cGPA: {rec['cGPA']}', verbose_to_screen = verbose)
    print_log(f'            Concentration: {concentration}', verbose_to_screen = verbose)
    print_log(f'            Taken courses: {", ".join(taken)}', verbose_to_screen = verbose)
    print_log(f'         Satisfied groups: {", ".join(satisfy_groups)}', verbose_to_screen = verbose)
    print_log(f'           Failed courses: {", ".join(FailedCourses)}', verbose_to_screen = verbose)
    print_log(f'    Uncounted (NotInPlan): {", ".join(not_in_plan)}', verbose_to_screen = verbose)

    # remove courses from plan when they have unsatisfied pre-requisites
    courses_w_unsatisfied_prereqs = []
    courses_w_unsatisfied_prereqs_and_why = []
    for course in cat.copy():
        metPreReq = False
        if course in PreRequisites.keys():
            PreReq = PreRequisites[course]
            if isinstance(PreReq, str): # one course
                if PreReq in taken:
                    metPreReq = True
            elif isinstance(PreReq, dict): # any of the courses in a dict 
                if any(c in taken for c in PreReq.values()):
                    metPreReq = True
            elif isinstance(PreReq, list): # all of the courses in a list
                if all(c in taken for c in PreReq):
                    metPreReq = True
            if not metPreReq:
                if not drop_course(course, cat):
                    raise ValueError(f'could not drop course:{course} from plan: {cat}')
                courses_w_unsatisfied_prereqs.append(course)
                courses_w_unsatisfied_prereqs_and_why.append(f'{course}({PreReq})')

    # calculate registered & earned CH
    CH_registered = 0
    CH_earned = 0
    for c in Registered + Registered_Summer:
        CH_registered += get_course_CHs(c, Course_CHs)
    for c in taken:
        CH_earned += get_course_CHs(c, Course_CHs)

    print_log(f'          Current Courses: {", ".join(CurrentCourses)}', verbose_to_screen = verbose)
    print_log(f'Registered Summer Courses: {", ".join(Registered_Summer)}', verbose_to_screen = verbose)
    print_log(f'       Registered Courses: {", ".join(Registered)}', verbose_to_screen = verbose)
    print_log(f'           Registered CHs: {CH_registered}', verbose_to_screen = verbose)
    print_log(f'               Earned CHs: {CH_earned}', verbose_to_screen = verbose)

    # prep Projected & Must_take_Courses
    Projected_Courses = []
    Must_take_Courses = []
    total_registration = no_duplicates_ordered_list(Registered + Registered_Summer + CurrentCourses)
    for course in FailedCourses:  # start w/ failed courses
        if course not in total_registration:  # if already registered for, skip
            if course not in Projected_Courses:
                Projected_Courses.append(course)
            if course not in Must_take_Courses:
                Must_take_Courses.append(course)
    for course in total_registration:  # add not taken co-requisites of currently registered courses
        if course in CoRequisites.keys():
            coreq = CoRequisites[course]
            if not isinstance(coreq, str):
                raise ValueError(f'Error - unidentified format for co-req: {course}:{coreq}')
            if coreq in cat and coreq not in Must_take_Courses:
                Must_take_Courses.append(coreq)
    for course in cat:  # add remaining courses from plan
        if course not in Projected_Courses or course in config['Allowed_Duplicate_Courses']:
            Projected_Courses.append(course)
        if course in Key_Courses and course not in Must_take_Courses:
            Must_take_Courses.append(course)

    # remove co-requisites(lab) from projection when the co-requisites(course is not taken or in projection)
    for course, coreq in CoRequisites.items():
        if course not in taken and course not in Projected_Courses:
            if coreq in Projected_Courses:
                Projected_Courses.remove(coreq)
        if course not in taken and course not in Must_take_Courses:
            if coreq in Must_take_Courses:
                Must_take_Courses.remove(coreq)

    # apply rules
    rules_msg = apply_rule(catalogs[catalog_year]['Rules'], 
                           rec, 
                           CH_earned, 
                           Projected_Courses, 
                           Must_take_Courses,
                           not_in_plan)


    Projected_Courses_extended = Projected_Courses.copy()
    Must_take_Courses_extended = Must_take_Courses.copy()
    Projected_Courses = list(Projected_Courses)[:config['Number_Projection_Courses']]
    Must_take_Courses = list(Must_take_Courses)[:config['Number_Key_Courses']]

    print_log(f'\nApplied rules:\n\t{rules_msg}\n', verbose_to_screen = verbose)
    print_log(f' Remaining in plan: {", ".join(cat+courses_w_unsatisfied_prereqs)}', verbose_to_screen = verbose)
    print_log(f'unsatisfied PreReq: {", ".join(courses_w_unsatisfied_prereqs_and_why)}\n', verbose_to_screen = verbose)
    print_log(f' Projected courses: {", ".join(Projected_Courses)}', verbose_to_screen = verbose)
    print_log(f' Must take courses: {", ".join(Must_take_Courses)}', verbose_to_screen = verbose)

    # prep list of courses to add
    add_courses = []
    add_co_requisites = []
    add_CH = 0
    if rec['cGPA'] > 2:  # need to make this and the minCH parametrized
        minCH = 14
    else:
        if rec['cGPA'] == 0 and rec['Earned Hours'] == 0 and len(FailedCourses) == 0:
            minCH = 14
        else:
            minCH = 11

    for course in Must_take_Courses + Projected_Courses:
        if CH_registered + add_CH < minCH:
            if course not in total_registration:
                if course not in add_courses or course in config['Allowed_Duplicate_Courses']:
                    add_courses.append(course)
                    add_CH += get_course_CHs(course, Course_CHs)

                    # include co-requisites
                    if course in CoRequisites.keys():
                        coreq = CoRequisites[course]
                        if not isinstance(coreq, str):
                            raise ValueError(f'Error - unidentified format for co-req: {course}:{coreq}')
                        if coreq not in total_registration and coreq not in taken:
                            if coreq in cat:
                                add_courses.append(coreq)
                                add_co_requisites.append(coreq)
                                add_CH += get_course_CHs(coreq, Course_CHs)

    print_log(f'       add_courses: {", ".join(add_courses)}', verbose_to_screen = verbose)
    # print_log(f'     added co-reqs: {", ".join(add_co_requisites)}', verbose_to_screen = verbose)  # also included in add_courses
    print_log(f'            add_CH: {add_CH}', verbose_to_screen = verbose)

    # Stochastic forecasting 
    add_courses_extended = []
    add_co_requisites_extended = []
    add_CH_extended = 0
    if config['Perform_Stochastic_forecasting']:
        # find remaining additional courses in the original Must_take_Courses_extended + Projected_Courses_extended lists
        for c in add_courses + config['Excluded_from_stochastic_forecasting']:
            if c in Projected_Courses_extended:
                Projected_Courses_extended.remove(c)
            if c in Must_take_Courses_extended:
                Must_take_Courses_extended.remove(c)

        for course in Must_take_Courses_extended + Projected_Courses_extended:
            tmp_course_ch = get_course_CHs(course, Course_CHs)
            if add_CH_extended + tmp_course_ch <= add_CH:  # add as many courses as needed to reach the same CH as the deterministic forecast
                if course not in total_registration:
                    if course not in add_courses_extended or course in config['Allowed_Duplicate_Courses']:
                        add_courses_extended.append(course)
                        add_CH_extended += tmp_course_ch

                        # include co-requisites
                        if course in CoRequisites.keys():
                            coreq = CoRequisites[course]
                            tmp_course_ch = get_course_CHs(coreq, Course_CHs)
                            if not isinstance(coreq, str):
                                raise ValueError(f'Error - unidentified format for co-req: {course}:{coreq}')
                            if coreq not in add_courses_extended and coreq not in taken:
                                if coreq in cat:
                                    add_courses_extended.append(coreq)
                                    add_co_requisites_extended.append(coreq)
                                    add_CH_extended += tmp_course_ch

        print_log(f'~~~~~~~~~~~~~~~~~~', verbose_to_screen = verbose)
        print_log(f'Identifying additional courses for stochastic forecasting', verbose_to_screen = verbose)
        print_log(f'add_courses_extend: {", ".join(add_courses_extended)}', verbose_to_screen = verbose)
        # print_log(f' added co-reqs_ext: {", ".join(add_co_requisites_extended)}', verbose_to_screen = verbose)  # also included in add_courses_extended
        print_log(f'     add_CH_extend: {add_CH_extended}', verbose_to_screen = verbose)

    return {
        'taken': ', '.join(taken),
        'satisfy_groups': ', '.join(satisfy_groups),
        'Uncounted': ', '.join(not_in_plan),
        'Remaining_in_plan': ', '.join(cat+courses_w_unsatisfied_prereqs),
        'unsatisfied_PreReq': ', '.join(courses_w_unsatisfied_prereqs_and_why),
        'Projected_Courses': ', '.join(Projected_Courses),
        'Must_take_Courses': ', '.join(Must_take_Courses),
        'Courses_to_add': ', '.join(add_courses),
        'Courses_to_add_CH': str(add_CH),
        'CH_earned': str(CH_earned),
        'CH_registered': str(CH_registered),
        'Applied_Rules': rules_msg,
        'Courses_to_add_extend': ', '.join(add_courses_extended),
        'Courses_to_add_CH_extend': str(add_CH_extended),
        }, \
        add_courses, add_courses_extended

if __name__ == "__main__":
    n = 0
    df = load_data(config['Input_File'])
    df_forecast_d = pd.DataFrame({k: pd.Series(dtype=df[k].dtype) for k in Forecast_Columns})
    df_forecast_s = pd.DataFrame({k: pd.Series(dtype=df[k].dtype) for k in Forecast_Columns})

    # get additional end_of_semester data for columns not in FAP: FailedCourses, Registered_Summer
    # if config['Registration_Data']:
    #     df_Registration_Data = load_data(config['Registration_Data'])
    #     df = pd.merge(df, df_Registration_Data[['FailedCourses', 'Registered_Summer']], on="ID")

    no_concentration_mask = df['Concentration'].isnull()
    no_concentration_count = no_concentration_mask.sum()
    if no_concentration_count > 0:
        print_log(f'Info: found {no_concentration_count} records students with "Null" Concentrations, using Major instead.', verbose_to_screen = True)
        df.loc[no_concentration_mask,'Concentration'] = df.loc[no_concentration_mask,'Major']

    output_columns = ['Audit_taken', 'Audit_satisfy_groups', 'Audit_uncounted', 
                      'Audit_Remaining_in_plan','Audit_unsatisfied_PreReq',
                      'Audit_Projected_Courses', 'Audit_Must_take_Courses', 
                      'Audit_Courses_to_add', 'Courses_to_add_CH', 
                      'Audit_CH_earned', 'CH_registered',
                      'Audit_Applied_Rules',
                      'Courses_to_add_extend', 'Courses_to_add_CH_extend']
    for c in output_columns:
        df[c] = ''
    warnings = []

    print_log(f'Auditing students...', verbose_to_screen = True)
    course_list = []
    course_list_extend = []

    for index, row in tqdm(df.iterrows(), total=len(df)):
        n += 1
        print_log(f'{"-"*80}\n*** Processing student ID: {row["ID"]}', verbose_to_screen = verbose)

        # get catalog year and concentration
        concentration = row['Concentration']
        if concentration in config['Concentrations'].keys():
            concentration = config['Concentrations'][concentration]  # replace concentration with acronym
        catalog_year = str(row['Catalog'])[:4]
        if catalog_year in config['Equal_Catalog_Years'].keys():
            print_log(f'Info: Catalog {catalog_year} is equivalent to {config["Equal_Catalog_Years"][catalog_year]}; {config["Equal_Catalog_Years"][catalog_year]} is used', verbose_to_screen = verbose)
            catalog_year = config['Equal_Catalog_Years'][catalog_year]

        # check if catalog data is available first
        msg = ''
        if catalog_year not in catalogs.keys():
            warnings.append(f'Students with unrecognized catalog year: {catalog_year}. Excluded from analysis.')
            df.loc[index,['Audit_taken']] = f'Warning: unrecognized catalog year: {catalog_year}. Excluded from analysis.'
            continue
        if concentration not in catalogs[catalog_year].keys():
            warnings.append(f'Students with unrecognized concentration: {concentration}. Excluded from analysis.')
            df.loc[index,['Audit_taken']] = f'Warning: unrecognized concentration: {concentration}. Excluded from analysis.'
            continue

        # Audit
        R, add_courses, add_courses_extended = audit_student_registration(row, catalog_year, concentration)
        df.loc[index,output_columns] = R.values()

        # Forecast: Deterministic
        df_forecast_d.loc[index,Forecast_Columns] = df.loc[index,Forecast_Columns]
        for c in add_courses:
            if c not in course_list:
                course_list.append(c)
                df_forecast_d.loc[index,c] = 1
            elif pd.isnull(df_forecast_d.loc[index,c]):
                df_forecast_d.loc[index,c] = 1
            else:
                df_forecast_d.loc[index,c] += 1

        # Forecast: Stochastic
        if config['Perform_Stochastic_forecasting']:
            r1 = config['First_choice_ratio']
            r2 = 1 - r1
            n1 = len(add_courses)
            n2 = len(add_courses_extended)
            if n2 == 0:
                r1 = 1
                r2 = 0
            else:
                r2 *= n1 / n2  # prorate to ensure the number of student registrations remain the same
            df_forecast_s.loc[index,Forecast_Columns] = df.loc[index,Forecast_Columns]
            for c in add_courses:
                if c not in course_list_extend:
                    course_list_extend.append(c)
                    df_forecast_s.loc[index,c] = 0.0
                elif pd.isnull(df_forecast_s.loc[index,c]):
                    df_forecast_s.loc[index,c] = 0.0
                df_forecast_s.loc[index,c] += r1
            for c in add_courses_extended:
                if c not in course_list_extend:
                    course_list_extend.append(c)
                    df_forecast_s.loc[index,c] = 0.0
                elif pd.isnull(df_forecast_s.loc[index,c]):
                    df_forecast_s.loc[index,c] = 0.0
                df_forecast_s.loc[index,c] += r2

    # save auditing file
    print_log(f'Saving audit file: {config['Audit_Output_File']}', verbose_to_screen = True)
    df.to_excel(config['Audit_Output_File'])

    # save forecast files: Deterministic
    course_list = sorted(list(course_list))
    grouped_forecast_d = df_forecast_d.groupby(by='Campus')[course_list].sum().transpose()
    print_log(f'Saving deterministic forecast files: {config['Forecast_d_Output_File_sum']} + {config['Forecast_d_Output_File_det']}', verbose_to_screen = True)
    grouped_forecast_d.to_excel(config['Forecast_d_Output_File_sum'])
    df_forecast_d.to_excel(config['Forecast_d_Output_File_det'])

    # save forecast files: Stochastic
    if config['Perform_Stochastic_forecasting']:
        course_list_extend = sorted(list(course_list_extend))
        grouped_forecast_s = df_forecast_s.groupby(by='Campus')[course_list_extend].sum().transpose().round(1)
        print_log(f'Saving stochastic forecast files: {config['Forecast_s_Output_File_sum']} + {config['Forecast_s_Output_File_det']}', verbose_to_screen = True)
        grouped_forecast_s.to_excel(config['Forecast_s_Output_File_sum'])
        df_forecast_s.to_excel(config['Forecast_s_Output_File_det'])
    
    # show warnings
    warnings = Counter(warnings)
    if warnings:
        print_log(f'The following warnings were present:', verbose_to_screen = True)
        for w in warnings:
            print_log(f'\t{warnings[w]:4d} {w}', verbose_to_screen = True)

    # calculate run time
    tok = time.time()
    print_log(f'\nProcessed {n} students in {round(tok-tik)} seconds\n', verbose_to_screen = True)

    # save log file
    log_file_name = config['Audit_Output_File'][0:-5]+'.txt'
    print_log(f'Saving log file: {log_file_name}\n', verbose_to_screen = True)
    with open(log_file_name,'w') as log_file:
        log_file.write(log_text)