# academic4sight - a system for student enrolment auditing and forecasting

## Table of Contents

1. [Overview](#overview)
2. [Dependencies](#dependencies)
3. [Configuration Files](#configuration-files)
4. [Main Logic](#main-Logic)
5. [Forecasting Student Enrolment Demand](#forecasting-student-enrolment-demand)
6. [Usage](#usage)
7. [License](#license)

## Overview

Academic4Sight is a robust academic audit and course forecasting engine built in Python. It processes student academic records to assess their current progress, apply catalog rules, and predict future semester enrollments using deterministic and stochastic models.

**Key Features**
- Audit Engine: Validates student progress against prerequisites, co-requisites, and catalog requirements.
- Forecasting:
  - Deterministic: Rule-based, fixed predictions.
  - Stochastic: Simulates student registration behavior using probabilistic models.
- Course Substitutions: Automatically handles group electives, substitutions, and catalog transitions.
- Excel Integration: Inputs and outputs are managed via .xlsx files.
- configurable system: course configurations from YAML files. 

## Dependencies

The program requires the following Python libraries:

- `pandas`
- `yaml`
- `glob`
- `copy`
- `time`
- `collections`
- `tqdm`

These can be installed using pip:

```sh
pip install pandas openpyxl tqdm pyyaml
```

## Configuration Files

### `academic4sight_config.yaml`

This YAML file contains various configurations, including file formats, verbosity settings, concentration mappings, and equivalent catalog years.

#### Verbose

```yaml
Verbose: False
```

- **Description**: Controls the verbosity of the output. When set to `False`, the program will run with minimal output. Set to `True` for more detailed logs.

#### Catalog Filenames

```yaml
catalog_filenames: "catalogs/20??.yaml"
catalog_defaults:  "catalogs/_common_catalog.yaml"
```

- **Description**: Specifies the pattern for catalog filenames. The pattern `20??.yaml` matches catalog files for the years 2000 to 2099. ***catalog_defaults*** is the base catalog information that is extended by the `20xx.yaml` files.


#### Input and Output Data Files

```yaml
Input_Data_File: "Students.xlsx"
Audit_Output_File: "StudentsAudit.xlsx"
Forecast_d_Output_File_sum: "StudentsForecast_d_summary.xlsx"
Forecast_d_Output_File_det: "StudentsForecast_d_details.xlsx"
Forecast_s_Output_File_sum: "StudentsForecast_s_summary.xlsx"
Forecast_s_Output_File_det: "StudentsForecast_s_details.xlsx"
```

**Descriptions**:
- **Input_Data_File**: The Excel file containing student data.
- **Audit_Output_File**: The Excel file where the audited student data will be saved.
- **Forecast_d_Output_File_sum**: forecast summary - Deterministic
- **Forecast_d_Output_File_det**: detailed forecast - Deterministic
- **Forecast_s_Output_File_sum**: forecast summary - Stochastic
- **Forecast_s_Output_File_det**: detailed forecast - Stochastic

#### Projection Parameters
```yaml
Number_Projection_Courses: 10
Number_Key_Courses:        3
MaxLabs:                   2
MinimalEnrollmentMode:     True
GuessSubstitutions:        True
CH_ranges:                [ { gpa: [0.0, 1.9999], minCH: 11, maxCH: 13 }
                            { gpa: [2.0, 4.0000], minCH: 14, maxCH: 16 } ]
Allowed_Duplicate_Courses: [ GroupA, GroupD, GroupG, P_Elective, ZU_Elective ]
```

**Descriptions**:
- **Number_Projection_Courses**: The number of forecasted courses when suggesting enrolment options.
- **Number_Key_Courses**: The number of key courses to prioritize when suggesting enrolment options.
- **MaxLabs: Max number of Labs per semester
- **MinimalEnrollmentMode**: Seek Minimal Enrollment with in the allowed range
- **GuessSubstitutions**: Substitutions are guessed if allowed and plausible based on earned CH differences
- **CH_ranges**: allowable registration Credit Hours ranges by GPA brackets
- **Allowed_Duplicate_Courses**: 'Group' courses that can repeat in the catalog

#### Stochastic forecasting parameters
```yaml
Perform_Stochastic_forecasting:       False
First_choice_ratio:                   0.75  
Excluded_from_stochastic_forecasting: [ CIT490, CIT499 ]
```

**Descriptions**:
- **Perform_Stochastic_forecasting**: to enable the logic or not
- **First_choice_ratio**: the ratio of students who will register in their first choice courses (vs. second choice courses)
- **Excluded_from_stochastic_forecasting**: courses that should stick with deterministic forecasting

#### Concentrations

```yaml
Concentrations: 
  { "Security and Network Tech":      "SECNET",
    "Web and Mobile App Development": "WAM",
    "Business Intelligence":          "BI",
    "Enterprise Systems":             "ES",
    "Mgmt. of Information Systems":   "MIS" }
```

- **Description**: Maps full concentration names (found in the input data) to their corresponding abbreviations used in the system and catalog files.
  - **Security and Network Tech**: SECNET
  - **Web and Mobile App Development**: WAM
  - **Business Intelligence**: BI
  - **Enterprise Systems**: ES
  - **Mgmt. of Information Systems**: MIS

#### Equal Catalog Years

```yaml
Equal_Catalog_Years: 
  { "2017": "2019",
    "2018": "2019",
    "2022": "2021",
    "2023": "2021" }
```

- **Description**: Maps catalog years to their equivalent years. This ensures that courses and requirements for certain years are treated as equivalent to those of another year.
  - **2017 and 2018** are equivalent to **2019**
  - **2022 and 2023** are equivalent to **2021**

### File Format

```yaml
File_Format: {
  "Student Records Information - Faculty Access Portal.xlsx": {
    skiprows: 2,
    columns: {
      "Student ID" : "ID",
      "Admitted Term (Major)" : "Catalog",
      "NextCourses" : "Registered",
      "CGPA" : "cGPA"
    }
  }
}
```

- **File Format Configuration**: Specifies how to read the input data file.
  - **skiprows**: Number of rows to skip at the beginning of the file.
  - **columns**: Maps column names in the Excel file to the standard column names used in the program.

### `Catalog Files`

Catalog files contain course plans and requirements for different academic years and concentrations.

#### Course_CHs

This section lists the courses and their credit hour worth, and a default value for all unlisted courses.

```yaml
Course_CHs: {
  0: [],
  1: [  INS211, SWE321, CIT461, INS469, INS477, INS475, INS363, INS368, INS464, INS426,
        NET257, SEC336, NET352, SEC433 ],
  2: [],
  4: [],
  default: 3 
}
```

#### CoRequisites & PreRequisites

This section defines the pre-requisite and co-requisite courses. A pre-requisite is a course that must be completed before taking another course. A co-requisite is a course that must be taken simultaneously with another course.

```yaml
CoRequisites: 
  { Course1: Course2, 
    Course3: Course4}
```

```yaml
PreRequisites: 
  { Course1: Course2, 
    Course3: Course4}
```

A dictionary entry (```{a: Course1, b: Course2}```) indicates an ***OR*** relationship. A list entry (```[Course1, Course2]```) indicates an ***AND*** relationship. For Example:

```yaml
PreRequisites: {
  Course1: {a: Course2, b:Course3},  # Course2 OR Course3
  Course1: [Course2, Course3],        # Course2 AND Course3
}
```

#### Key/important courses
A list of key/important courses to be prioritized over other projection courses by concentration; 'ALL' counts for all concentrations. Pre-requisite courses will be considered automatically. The list is in decreasing priority (order counts).

```yaml
Key_Courses: {
    ALL: [],
    SECNET: [],
    WAM: [],
    BI: [Course],
    MIS: [],
    ES: []
}
```

#### Concentration Plans

This section details the academic plans for various concentrations. Each concentration includes a list of ordered courses by decreasing priority (order counts).

```yaml
Concentration:
  [ Course1, Course2,   #S1
    Course3, GroupA,    #S2
    Course4,            #S3
    Elective, Course5]  #S4
```

#### Groups

This section defines various groups of courses that students can choose from as part of their academic plan. This can also be used for susbtitution courses.

```yaml
Groups: 
  { GroupA: [Course1, Course1, ...],
    Elective: [Course3, Course4, ...]}
```

#### Rules
This section defines rules that can be applied to the student's course plan based on various conditions such as status, skill, campus, and more.

```yaml
Rules:
  "Label": {
    CONDITION1: [Value1, Value2, ...],
    CONDITION2: [Value1, Value2, ...],

    ACTION: [Course1, Course2, ...],
    # OR
    Note: "Some note about this rule"
  }
```

***CONDITION***: `Status`, `Skill`, `Campus`, `ProjectionCount`, `ECHiP`, `MatchAll`, `MatchAny`, `MissingAny`, `Replace`, `Substitute_Uncounted`, and `NotInPlanCount`

***ACTIONS***: `Drop`, `If_Not_Drop`, and `Note`

## Main Logic

The program is designed to be executed as a standalone program. The main steps are:

1. Read the configuration file `academic4sight_config.yaml`.
2. Load catalog files (`_catalog_defaults.yaml` and `202x.yaml`) & student data.
3. Determine the catalog year and concentration.
4. Audit students' registrations against catalogs; for each student record:
    - Identify failed and completed courses. Remove completed courses from plan.
    - Project the next XX courses the student should take.
    - Identify three key courses (by priority) from the projection.
    - Calculate the student's registered credit hours.
    - Generate a list of additional courses needed to meet the minimum credit hour requirement.
    - Include co-requisite courses if necessary.
    - Save a summary of the student's academic plan.
5. Tally students' recommended courses (from add_courses) into a pivot table

## Forecasting Student Enrolment Demand
Recommended courses to complete each student's enrollment to the minimum Credit Hours are tallied and summarized into a pivot table. The resulting summary table is saved into an Excel output file dictated by the following parameters:
- Forecast_d_Output_File_sum
- Forecast_d_Output_File_det
- Forecast_s_Output_File_sum
- Forecast_s_Output_File_det

## Usage

### Syntax

To run the script, use the following command:

```sh
python academic4sight.py
```

### Output

The program generates an Excel file with the following columns for each student and text log file:

- `Audit_UsedCatalog`: catalog used for the audit.
- `Audit_taken`: Courses taken by the student.
- `Audit_satisfy_groups`: Courses that satisfy group requirements.
- `Audit_uncounted`: Completed courses not counted in the plan.
- `Audit_Guessed_substitutions`: Substitutions guessed based on earned CH differences.
- `Audit_Remaining_in_plan`: Remaining courses in the plan.
- `Audit_unsatisfied_PreReq`: Courses with unsatisfied prerequisites.
- `Audit_Projected_Courses`: Projected courses for the next 10 enrolment courses.
- `Audit_Must_take_Courses`: Key courses that the student must take.
- `Audit_Courses_to_add`: Additional courses needed to meet credit hour requirements.
- `Audit_Courses_to_add_CH`: Total additional credit hours needed.
- `Audit_CH_earned`: Total credit hours earned by the student.
- `Audit_CH_registered`: Total credit hours registered by the student.
- `Audit_Exception_Mgs`: Reported exception messages.
- `Audit_Applied_Rules`: Rules applied to the student's course plan.
- `Audit_Courses_to_add_extend`: Additional courses added by the stochastic forecasting algorithm.
- `Audit_Courses_to_add_CH_extend`: Total additional credit hours added by the stochastic forecasting algorithm.

## License

License:    GPLv3

Copyright:  Sinan Salman, 2024-2025