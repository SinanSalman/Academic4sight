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

This system is designed to audit and plan student registrations by analyzing course completion and projecting future coursework requirements based on a set of predefined rules and configurations.

The system reads student data from an Excel file and course configurations from YAML files. It then processes each student's academic record to determine their completed, failed, and remaining courses. Based on this information, the program generates a course plan and projections for each student.

The system also generates forecasts for students demands per course, allowing accurate planning of resources.

## Dependencies

The program requires the following Python libraries:

- `pandas`
- `yaml`
- `glob`
- `copy`
- `time`

These can be installed using pip:

```sh
pip install pandas pyyaml
```

## Configuration Files

### `_config.yaml`

This YAML file contains various configurations, including file formats, verbosity settings, concentration mappings, and equivalent catalog years.

#### Verbose

```yaml
Verbose: False
```

- **Description**: Controls the verbosity of the output. When set to `False`, the program will run with minimal output. Set to `True` for more detailed logs.

#### Catalog Filenames

```yaml
catalog_filenames: "_20??.yaml"
catalog_defaults: "_common_catalog.yaml"
```

- **Description**: Specifies the pattern for catalog filenames. The pattern `_20??.yaml` matches catalog files for the years 2000 to 2099. ***catalog_defaults*** is the base catalog information that is extended by the `_20xx.yaml` files.


#### Input and Output Data Files

```yaml
Input_Data_File: "Students.xlsx"
Audit_Output_File: "StudentsAudit.xlsx"
Forecast_Output_File: "StudentsForecast.xlsx"
```

- **Input_Data_File**: The Excel file containing student data.
- **Audit_Output_File**: The Excel file where the audited student data will be saved.
- **Forecast_Output_File**: The Excel file where the forecast summary will be saved.

#### Projection Parameters
```yaml
Number_Projection_Courses: 10
Number_Key_Courses:        3
```

- **Description**: The number of forecasted courses and the number of key courses to prioritize when suggesting enrolment options.

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
A list of key/important courses to be prioritized over other projection courses. Pre-requisite courses will be added automatically to this list. The list is in decreasing priority (order counts).

```yaml
Key_Courses: [ Course ]
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

***CONDITION***: `Status`, `Skill`, `Campus`, `ProjectionCount`, `ECHiP`, `MatchAll`, `MatchAny`, `MissingAny`, and `NotInPlanCount`

***ACTIONS***: `Drop`, `If_Not_Drop`, and `Note`

## Main Logic

The program is designed to be executed as a standalone program. The main steps are:

1. Read the configuration file `_config.yaml`.
2. Load catalog files (`_catalog_defaults.yaml` and `_202x.yaml`) & student data.
3. Determine the catalog year and concentration.
4. Audit students' registrations against catalogs; for each student record:
    - Identify failed and completed courses. Remove completed courses from plan.
    - Project the next 10 courses the student should take.
    - Identify three key courses (by priority) from the projection.
    - Calculate the student's registered credit hours.
    - Generate a list of additional courses needed to meet the minimum credit hour requirement.
    - Include co-requisite courses if necessary.
    - Save a summary of the student's academic plan.
5. Tally students' recommended courses (from add_courses) into a pivot table

## Forecasting Student Enrolment Demand
Recommended courses to complete each student's enrollment to the minimum Credit Hours are tallied and summarized into a pivot table. The resulting summary table is saved into an Excel output file dictated by the `Forecast_Output_File` parameter.

## Usage

### Syntax

To run the script, use the following command:

```sh
python Audit_Forecast.py
```

### Output

The program generates an Excel file with the following columns for each student and text log file:
- `Audit_taken`: Courses taken by the student.
- `Audit_satisfy_groups`: Courses that satisfy group requirements.
- `Audit_uncounted`: Completed courses not counted in the plan.
- `Audit_Remaining_in_plan`: Remaining courses in the plan.
- `Audit_unsatisfied_PreReq`: Courses with unsatisfied prerequisites.
- `Audit_Projected_Courses`: Projected courses for the next 10 enrolment courses.
- `Audit_Must_take_Courses`: Key courses that the student must take.
- `Audit_Courses_to_add`: Additional courses needed to meet credit hour requirements.
- `Courses_to_add_CH`: Total additional credit hours needed.
- `Audit_CH_earned`: Total credit hours earned by the student.
- `CH_registered`: Total credit hours registered by the student.
- `Audit_Applied_Rules`: Rules applied to the student's course plan.

## License

License:    GPLv3

Copyright:  Sinan Salman, 2024-2025