#! /usr/bin/env python

"""Copyright:  Sinan Salman, 2024
License:    GPLv3

Version History:
29.05.2024	1.1     improved logic, format, and added rules
20.05.2024	1.0     initial release"""

import pandas as pd
import yaml
import glob
import copy
import time
from collections import Counter


def read_yaml(filename):
    print(f'reading {filename}...')
    with open(filename, 'r') as yamlfile:
        return yaml.load(yamlfile, Loader=yaml.FullLoader)


tik = time.time()
config_filename = '_config.yaml'
config = read_yaml(config_filename)
verbose = config['Verbose']
catalogs = {}
for filename in glob.glob(config['catalog_filenames']):
    catalogs[filename[1:5]] = read_yaml(filename)
    

def load_data(filename):
    global config
    format = config['File_Format'][filename]
    df = pd.read_excel(filename, sheet_name=0, skiprows=format['skiprows'])
    missing_columns_error = []
    missing_columns_warning = []
    for k,v in format['columns'].items():
        if k not in df.columns:
            if v in ['ID','Catalog','Concentration','Completed_Courses']:
                missing_columns_error.append(k)
            else:
                missing_columns_warning.append(k)
                df[k] = ''
    if missing_columns_error:
        print(f'Error: the following columns {missing_columns_error} are missing in the input data file: {filename}')
        quit()
    if missing_columns_warning:
        print(f'Warning: the following columns {missing_columns_warning} are missing in the input data file: {filename}, continuing with no entries for these columns.')

    df.rename(columns=format['columns'], inplace=True)
    for c in df.columns:
        if c in ['Skill','Failed_Courses','Registered',
                 'Registered_Summer','Current_Courses',
                 'Completed_Courses']:
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


def apply_rule(rules, rec,  CH_earned,  Projected_Courses,  Must_take_Courses):
    applied_rules = []
    for label, rule in rules.items():
        applicable = True
        for k,v in rule.items():
            if k in ['Drop','If_Not_Drop']:
                continue
            if k == 'Campus':
                if rec['Campus'] in v:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'RegCount':
                if v[0] <= len(Projected_Courses) <= v[1]:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'ECHiP':
                if v[0] <= CH_earned <= v[1]:
                    applicable &= True
                else:
                    applicable &= False
            if k == 'Allow':
                if v in Projected_Courses:
                    applicable &= True
                else:
                    applicable &= False

        Dropped_Courses = set()
        if ('Drop' in rule.keys() and applicable) or ('If_Not_Drop' in rule.keys() and not applicable):
            for course in v:
                if course in Projected_Courses:
                    Projected_Courses.remove(course)
                    Dropped_Courses.add(course)
                if course in Must_take_Courses:
                    Must_take_Courses.remove(course)
                    Dropped_Courses.add(course)

        if Dropped_Courses:
            applied_rules.append(f'{label}(drop:{"+".join(Dropped_Courses)})')

    return '\n'.join(applied_rules)


def audit_student_registration(record, catalog_year, concentration):
    global config, catalogs, verbose

    # setup variables
    rec = record.to_dict()
    if rec["Failed_Courses"]:
        Failed_Courses = [x.strip()[:6] for x in rec["Failed_Courses"].split(',')]
    else:
        Failed_Courses = []
    if rec["Completed_Courses"]:
        Completed_Courses = [x.strip()[:6] for x in rec["Completed_Courses"].split(',')]
    else:
        Completed_Courses = []
    if rec["Registered"]:
        Registered = [x.strip()[:6] for x in rec["Registered"].split(',')]
    else:
        Registered = []
    if rec["Registered_Summer"]:
        Registered_Summer = [x.strip()[:6] for x in rec["Registered_Summer"].split(',')]
    else:
        Registered_Summer = []
    cat = copy.deepcopy(catalogs[catalog_year][concentration])
    grp = copy.deepcopy(catalogs[catalog_year]['Groups'])
    Course_CHs = copy.deepcopy(catalogs[catalog_year]['Course_CHs'])
    CoRequisites = copy.deepcopy(catalogs[catalog_year]["CoRequisites"])
    PreRequisites = copy.deepcopy(catalogs[catalog_year]["PreRequisites"])

    # if verbose: 
    #     for k,v in rec.items():
    #         print(f'{k:20s}:{v}')
    #     print('\n')

    #  Collapse all Pre-Reqs into a flat list
    Key_Courses = catalogs[catalog_year]['Key_Courses'].copy()
    for PreReq in PreRequisites.values():
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
            print (f'Error: preReq "{PreReq}" is not recognized as valid format for PreRequisites')
            quit()

    # remove completed courses from the catalog plan & check for group/elective courses
    taken = []
    satisfy_groups = []
    not_in_plan = []
    for course in Completed_Courses:
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

    if verbose: 
        print(f'Taken courses:  {", ".join(taken)}')
        print(f'Satisfy groups: {", ".join(satisfy_groups)}')
        print(f'Uncounted:      {", ".join(not_in_plan)}')

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
                for c in PreReq.values():
                    if c in taken:
                        metPreReq = True
            elif isinstance(PreReq, list): # all of the courses in a list
                metPreReq = True
                for c in PreReq:
                    if c not in taken:
                        metPreReq = False
            if not metPreReq:
                if not drop_course(course, cat):
                    raise ValueError(f'could not drop course:{course} from plan: {cat}')
                courses_w_unsatisfied_prereqs.append(course)
                courses_w_unsatisfied_prereqs_and_why.append(f'{course}({PreReq})')

    # calculate registered & earned CH
    CH_registered = 0
    CH_earned = 0
    for c in Registered:
        CH_registered += get_course_CHs(c, Course_CHs)
    for c in taken:
        CH_earned += get_course_CHs(c, Course_CHs)

    if verbose: 
        print(f'Registered Summer Cources: {rec["Registered_Summer"]}')
        print(f'       Registered Cources: {rec["Registered"]}')
        print(f'           Registered CHs: {CH_registered}')
        print(f'               Earned CHs: {CH_earned}')

    # prep Projected & Must_take_Courses
    Projected_Courses = []
    Must_take_Courses = []
    for course in Failed_Courses:  # start w/ failed courses
        if course not in Projected_Courses:
            Projected_Courses.append(course)
        if course not in Must_take_Courses:
            Must_take_Courses.append(course)
    for course in cat:  # add remaining courses from plan
        if course not in Projected_Courses:
            Projected_Courses.append(course)
        if course in Key_Courses and course not in Must_take_Courses:
            Must_take_Courses.append(course)

    # apply rules
    rules_msg = apply_rule(catalogs[catalog_year]['Rules'], 
                           rec, 
                           CH_earned, 
                           Projected_Courses, 
                           Must_take_Courses)

    Projected_Courses = list(Projected_Courses)[:config['Number_Projection_Courses']]
    Must_take_Courses = list(Must_take_Courses)[:config['Number_Key_Courses']]

    if verbose: 
        print(f'Applied rules:\n{rules_msg}\n')
        print(f'     Plan courses: {", ".join(cat+courses_w_unsatisfied_prereqs)}')
        print(f'unsatisfied PreReq: {", ".join(courses_w_unsatisfied_prereqs_and_why)}\n')
        print(f'Projected courses: {", ".join(Projected_Courses)}')
        print(f'Must take courses: {", ".join(Must_take_Courses)}')

    # prep list of courses to add
    add_courses = []
    add_CH = 0
    minCH = 14 if rec['cGPA']>2 else 11  # need to make this parametrized
    total_registration = set(Registered + Registered_Summer)
    for course in Must_take_Courses + Projected_Courses:
        if CH_registered+add_CH < minCH:
            if course not in total_registration and course not in add_courses:
                add_courses.append(course)
                add_CH += get_course_CHs(course, Course_CHs)

    # include co-requisites
    added_co_requisites = []
    total_registration = total_registration.union(add_courses)
    for course in total_registration:
        if course in CoRequisites.keys():
            coreq = CoRequisites[course]
            if coreq not in total_registration and coreq not in add_courses:
                add_courses.append(coreq)
                added_co_requisites.append(coreq)
                add_CH += get_course_CHs(coreq, Course_CHs)

    if verbose: 
        print(f'added co-reqs: {", ".join(added_co_requisites)}')
        print(f'  add_courses: {", ".join(add_courses)}')
        print(f'       add_CH: {add_CH}')

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
        'Applied_Rules': rules_msg}

if __name__ == "__main__":
    n = 0
    df = load_data(config['Registration_Data'])
    df_CompletedCourses = load_data(config['Completed_Courses_Data'])
    df = pd.merge(df, df_CompletedCourses[['ID','CurrentCourses','Completed_Courses']], on="ID")
    output_columns = ['Audit_taken', 'Audit_satisfy_groups', 'Audit_uncounted', 
                      'Audit_Remaining_in_plan','Audit_unsatisfied_PreReq',
                      'Audit_Projected_Courses', 'Audit_Must_take_Courses', 
                      'Audit_Courses_to_add', 'Courses_to_add_CH', 
                      'Audit_CH_earned', 'CH_registered',
                      'Audit_Applied_Rules']
    for c in output_columns:
        df[c] = ''
    warnings = []
    for index, row in df.iterrows():

        # if row["ID"] not in [202106299,]:
        #     continue

        n += 1
        if verbose: 
            print(f'{"-"*80}\nProcessing student ID: {row["ID"]}')
        # get catalog year and concentration
        concentration = row['Concentration']
        if concentration in config['Concentrations'].keys():
            concentration = config['Concentrations'][concentration]  # replace concentraiton with acronym
        catalog_year = str(row['Catalog'])[:4]
        if catalog_year in config['Equal_Catalog_Years'].keys():
            if verbose: 
                print(f'Info: Catalog {catalog_year} is eqivelant to {config["Equal_Catalog_Years"][catalog_year]}; the latter is used')
            catalog_year = config['Equal_Catalog_Years'][catalog_year]
        # check if catalog data is available first
        msg = ''
        if catalog_year not in catalogs.keys():
            warnings.append(f'Students with unrecognized catalog year: {catalog_year}')
            df.loc[index,['Audit_taken']] = f'Warning: unrecognized catalog year: {catalog_year}'
            continue
        if concentration not in catalogs[catalog_year].keys():
            warnings.append(f'Students with unrecognized concentration: {concentration}')
            df.loc[index,['Audit_taken']] = f'Warning: unrecognized concentration: {concentration}'
            continue
        # Audit
        R = audit_student_registration(row, catalog_year, concentration)
        df.loc[index,output_columns] = R.values()
    df.to_excel(config['Output_File'])
    warnings = Counter(warnings)
    if warnings:
        print(f'The folowing warnings were present:')
        for w in warnings:
            print(f'\t{warnings[w]:4d} {w}')
    tok = time.time()
    print(f'\nProcessed {n} students in {round(tok-tik)} seconds\n')
