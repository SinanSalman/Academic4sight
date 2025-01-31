#! /usr/bin/env python


"""
Copyright:  Sinan Salman, 2024
License:    GPLv3

Version History:
19.05.2024	1.0     initial release
"""


import pandas as pd
import yaml
import glob
import copy
import time


def read_yaml(filename):
    print(f'reading {filename}...')
    with open(filename, 'r') as yamlfile:
        return yaml.load(yamlfile, Loader=yaml.FullLoader)


tik = time.time()
config_filename = '_config.yaml'
catalogs = {}
config = read_yaml(config_filename)
verbose = config['Verbose']
catalog_filenames = config['catalog_filenames']
Input_Data_File = config['Input_Data_File']
Output_Data_File = config['Output_Data_File']
for filename in glob.glob(catalog_filenames):
    catalogs[filename[1:5]] = read_yaml(filename)
    

def load_data(filename):
    global config
    format = config['File_Format'][filename]
    df = pd.read_excel(filename, sheet_name=0, skiprows=format['skiprows'])
    # df = pd.read_csv(filename, index_col=False, header=0, engine='python',
    #                     skiprows=format['skiprows'], sep=format['sep'],
    #                     encoding='utf_8', encoding_errors='replace', on_bad_lines='warn')
    drop_list = [k for k in df.columns if k not in format['columns'].keys()]
    df.drop(drop_list, axis=1, inplace =True)
    df.rename(columns=format['columns'], inplace=True)
    for x in ['Skill','Failed_Courses','Registered','Registered_Summer','Current_Courses','Completed_Courses','Remaining_Courses']:
        df[x] = df[x].fillna('')
    return df


def drop_course(crs, cat):
    for semester, plan in cat.items():
        for order, courses in plan.items():
            if crs in courses:
                cat[semester][order].remove(crs)
                return True
    return False
    

def audit_student_registration(rec, catalog_year, concentration):
    global config, catalogs, verbose

    # setup variables
    rec = rec.to_dict()
    if rec["Failed_Courses"]:
        Failed_Courses = [x.strip()[:6] for x in rec["Failed_Courses"].split(',')]
    else:
        Failed_Courses = []
    if rec["Completed_Courses"]:
        Completed_Courses = [x.strip() for x in rec["Completed_Courses"].split(',')]
    else:
        Completed_Courses = []
    cat = copy.deepcopy(catalogs[catalog_year][concentration])
    grp = copy.deepcopy(catalogs[catalog_year]['Groups'])
    one_CH_Courses = copy.deepcopy(catalogs[catalog_year]['One_CH_Courses'])
    CoRequisites = copy.deepcopy(catalogs[catalog_year]["CoRequisites"])

    # remove courses from the catalog plan
    taken = []
    for course in Completed_Courses.copy():
        if drop_course(course, cat):
            Completed_Courses.remove(course)
            taken.append(course)
        else:
            if verbose: print(f'{course} not found in plan')
    if verbose: print(f'taken: {taken}')

    # remove group/elective courses from the catalog plan
    for course in Completed_Courses.copy():
        course_found_in_groups = False
        for g, l in grp.items():
            if course in l and course not in taken:
                if drop_course(g, cat):
                    Completed_Courses.remove(course)
                    taken.append(course)
                    if verbose: print(f'{course} --> {g}')
                    course_found_in_groups = True
        if not course_found_in_groups:
            if verbose: print(f'{course} Not found in groups; uncounted')

    # prep preojection for the next 10 courses
    proj_10 = []
    for course in Failed_Courses:  # start w/ failed courses
        if len(proj_10) < 10:
            proj_10.append(course)
    for plan in cat.values():  # add remaining courses from plan
        for courses in plan.values():
            for crs in courses:
                if crs not in proj_10 and len(proj_10) < 10:
                    proj_10.append(crs)

    # prep a list of 3 key courses to take from the projection
    key___3 = []
    for plan in cat.values():
        for crs in plan[1]:
            if len(key___3) < 3:
                key___3.append(crs)

    # calculate registered CH
    CH_registered = 0
    for c in rec["Registered"]:
        if c in one_CH_Courses:
            CH_registered += 1
        else:
            CH_registered += 3

    # prep list of needed courses
    add = []
    add_CH = 0
    minCH = 14 if rec['cGPA']>2 else 11  # need to make this parametrized
    for course in key___3:
        if CH_registered+add_CH < minCH:
            if course not in rec["Registered_Summer"]:
                add.append(course)
                add_CH += 1 if course in one_CH_Courses else 3
    for course in proj_10:
        if CH_registered+add_CH < minCH:
            if course not in rec["Registered_Summer"]:
                add.append(course)
                add_CH += 1 if course in one_CH_Courses else 3

    # include co-requisites
    for course in add:
        if course in CoRequisites.keys():
            coreq = CoRequisites[course]
            if coreq not in add:
                add.append(coreq)
                add_CH += 1 if coreq in one_CH_Courses else 3
                if verbose: print(f'added co=requisite: {coreq}')

    # cleanup cat:
    cat_copy = copy.deepcopy(cat)
    for semester, plan in cat_copy.items():
        plan = plan[1] + plan [2]
        if not plan:
            del cat[semester]
        else:
            cat[semester] = plan

    return {'Catalog': str(cat).replace("'","").replace("{","").replace("}",""),
            'Uncounted': ', '.join(Completed_Courses),
            'Projection': ', '.join(proj_10),
            'add': ', '.join(add),
            'add_CH': str(add_CH)}


# def apply_rules(df):
#     n = 1
#     for rule in rules:
#         tag = [f'Rule-{n:02d}']
#         mask = [True] * len(df) 
#         for k,v in rule.items():
#             if not v:
#                 continue
#             if k in ['cGPA','ECH']:
#                 mask = mask & ((df[k]>=v[0]) & (df[k]<=v[1]))
#             if k in ['Catalog','Concentration','Standing']:
#                 mask = mask & (df[k].include == v)
# still writing code here
#         if k == 'Tag':
#             if 
#             mask = mask & ((df[k]>=v[0]) & (df[k]<=v[1]))
#         if k == 'Audit':
#             if rule['Audit'] == True:
#                 Print('need to audit')
#             if k == 'xxxx':
#                 mask = mask & df[k].str.contains(v,case=Case,regex=True)
#         affected_rows = sum(mask)
#         if affected_rows == 0:
#             print(f'Warning rule with Zero affected rows: {rule}')
#         else:
#             df.loc[mask,'Cat'] = Label
#         n += 1
#     df.loc[(df['Cat']==''),'Cat'] = Default
#     return df

if __name__ == "__main__":
    n = 0
    df = load_data(Input_Data_File)
    df['Plan'] = ''
    df['Uncounted'] = ''
    df['Projection'] = ''
    df['add'] = ''
    df['add_CH'] = ''
    for index, row in df.iterrows():
        n += 1
        if verbose: print(f'{"-"*80}\nProcessing student ID: {row["ID"]}')
        # get catalog year and concentration
        concentration = row['Concentration']
        if concentration in config['Concentrations'].keys():
            concentration = config['Concentrations'][concentration]  # replace concentraiton with acronym
        catalog_year = str(row['Catalog'])[:4]
        if catalog_year in config['Equal_Catalog_Years'].keys():
            if verbose: print(f'Catalog {catalog_year} is eqivelant to {config["Equal_Catalog_Years"][catalog_year]}; the latter is used')
            catalog_year = config['Equal_Catalog_Years'][catalog_year]
        # check if catalog data is available first
        if catalog_year not in catalogs.keys():
            print(f'{row["ID"]} with unrecognized catalog year: {catalog_year}')
            continue
        if concentration not in catalogs[catalog_year].keys():
            print(f'{row["ID"]} with unrecognized concentration: {concentration}')
            continue
        # Audit
        R = audit_student_registration(row, catalog_year, concentration)
        df.loc[index,['Plan','Uncounted','Projection','add','add_CH']] = R.values()
    df.to_excel(Output_Data_File)
    tok = time.time()
    print(f'\nProcessed {n} students in {round(tok-tik)} seconds')
