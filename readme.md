# Student Registration Audit System

## Table of Contents

1. [Overview](#overview)
2. [Dependencies](#dependencies)
3. [Configuration Files](#configuration-files)
4. [Main Logic](#main-Logic)
5. [License](#license)

## Overview

This Python script is designed to audit and plan student registrations by analyzing course completion and projecting future coursework requirements based on a set of predefined rules and configurations.

The script reads student data from an Excel file and course configurations from YAML files. It then processes each student's academic record to determine their completed, failed, and remaining courses. Based on this information, the script generates a course plan and projections for each student.

## Dependencies

The script requires the following Python libraries:

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
```

- **Description**: Specifies the pattern for catalog filenames. The pattern `_20??.yaml` matches catalog files for the years 2000 to 2099.

#### Input and Output Data Files

```yaml
Input_Data_File: "Students.xlsx"
Output_Data_File: "StudentsAudit.xlsx"
```

- **Input_Data_File**: The Excel file containing student data.
- **Output_Data_File**: The Excel file where the audited student data will be saved.

#### Concentrations

```yaml
Concentrations: 
  { "Security and Network Tech":      "SECNET",
    "Web and Mobile App Development": "WAM",
    "Business Intelligence":          "BI",
    "Enterprise Systems":             "ES",
    "Mgmt. of Information Systems":   "MIS" }
```

- **Description**: Maps full concentration names to their corresponding abbreviations used in the system.
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
File_Format: 
  {
    "Students.xlsx": {
      skiprows: 0,
      columns: {
        "STUD_ID" : "ID",
        "STU_NAME" : "Name",
        "CTLG_TERM" : "Catalog",
        "MAJOR" : "Major",
        "CONCENTRATION" : "Concentration",
        "SKILL" : "Skill",
        "CGPA" : "cGPA",
        "EARNED_HRS" : "ECH",
        "ASTD" : "Standing",
        "WF_W_SPRING_2024" : "Failed_Courses",
        "REG_HRS_202421" : "Registered_CH",
        "COUNT_CRSE_202421" : "Registered_Count",
        "REG_CRSE_202421" : "Registered",
        "REG_CRSE_202323" : "Registered_Summer",
        "COUNT_CRSE_202323" : "Registered_Summer_Count",
        "REG_HRS_202323" : "Registered_Summer_CH",
        "CurrentCourses" : "Current_Courses",
        "CompletedCourses" : "Completed_Courses",
        "IncompleteCourses" : "Remaining_Courses"
      }
    }
  }
```

- **File Format Configuration**: Specifies how to read the input data file.
  - **skiprows**: Number of rows to skip at the beginning of the file.
  - **columns**: Maps columns in the Excel file to the desired column names used in the program.
    - **STUD_ID**: Mapped to `ID`
    - **STU_NAME**: Mapped to `Name`
    - **CTLG_TERM**: Mapped to `Catalog`
    - **MAJOR**: Mapped to `Major`
    - **CONCENTRATION**: Mapped to `Concentration`
    - **SKILL**: Mapped to `Skill`
    - **CGPA**: Mapped to `cGPA`
    - **EARNED_HRS**: Mapped to `ECH`
    - **ASTD**: Mapped to `Standing`
    - **WF_W_SPRING_2024**: Mapped to `Failed_Courses`
    - **REG_HRS_202421**: Mapped to `Registered_CH`
    - **COUNT_CRSE_202421**: Mapped to `Registered_Count`
    - **REG_CRSE_202421**: Mapped to `Registered`
    - **REG_CRSE_202323**: Mapped to `Registered_Summer`
    - **COUNT_CRSE_202323**: Mapped to `Registered_Summer_Count`
    - **REG_HRS_202323**: Mapped to `Registered_Summer_CH`
    - **CurrentCourses**: Mapped to `Current_Courses`
    - **CompletedCourses**: Mapped to `Completed_Courses`
    - **IncompleteCourses**: Mapped to `Remaining_Courses`

### Catalog Files

Catalog files contain course plans and requirements for different academic years and concentrations.

#### One_CH_Courses

This section lists the courses that are worth one credit hour each.

```yaml
One_CH_Courses: 
  [Course1, Course2, Course3]
```

#### CoRequisites

This section defines the co-requisite courses. A co-requisite is a course that must be taken simultaneously with another course.

```yaml
CoRequisites: 
  { Course1: Course2, 
    Course3: Course4}
```

#### Concentration Plans

This section details the academic plans for various concentrations. Each concentration includes a series of semesters (`S1`, `S2`, etc.), each containing courses divided into two parts by priority (`1` and `2`, with `1` being higher priority).

```yaml
Concentration: 
  S1: {1: [Course1, Course2],   2: [Course3, GroupA]},
  S2: {1: [Course4],            2: [Elective, Course5]},
  ...
```

#### Groups

This section defines various groups of courses that students can choose from as part of their academic plan.

```yaml
Groups: 
  { GroupA: [Course1, Course1, ...],
    Elective: [Course3, Course4, ...]}
```

## Main Logic

The script is designed to be executed as a standalone program. The main steps are:

1. Read the configuration file `_config.yaml`.
2. Load catalog files & student data.
3. Determine the catalog year and concentration.
4. Audit students' registrations against catalogs; for each student record:
    - Identify failed and completed courses. Remove completed courses from plan.
    - Project the next 10 courses the student should take.
    - Identify three key courses (by priority) from the projection.
    - Calculate the student's registered credit hours.
    - Generate a list of additional courses needed to meet the minimum credit hour requirement.
    - Include co-requisite courses if necessary.
    - Save a summary of the student's academic plan.

### Example Usage

To run the script, use the following command:

```sh
python Audit.py
```

### Output

The script generates an Excel file with the following columns for each student:
- `Plan`: The updated catalog plan after removing completed courses.
- `Uncounted`: List of completed courses not counted in the plan.
- `Projection`: Projected courses for the next 10 enrollments.
- `add`: List of additional courses needed to meet credit hour requirements.
- `add_CH`: Total additional credit hours needed.

## License

License:    GPLv3

Copyright:  Sinan Salman, 2024