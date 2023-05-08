import argparse
import sys

import pandas as pd
import numpy as np
import logging


logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler('preprocess.log', 'w'))

def is_dev_course(section):
    return 1 if str(section).startswith("0") else 0


def is_nt_course(section):
    return 1 if 'NT' in str(section) else 0


def is_w_grade(grade):
    return 1 if grade == 'W' else 0


def go(args):
    # process course data
    logger.info(">>>>>> Processing course data <<<<<<")
    crs = pd.read_csv("../../data/raw/course_history.csv")
    crs["Course"] = crs["Department"] + crs["CourseID"]
    crs["IsDev"] = [is_dev_course(sec) for sec in crs.Section]
    crs["IsInternet"] = [is_nt_course(sec) for sec in crs.Section]
    crs["IsW"] = [is_w_grade(grade) for grade in crs.Grade]
    
    
    # sort terms and select terms after 2017 only for fall and spring
    term_codes = sorted([tc for tc in crs.TermCode.unique() if tc[0] == 'B' and int(tc[1:3]) >= 17 and tc[-1] in 'QC'])

    # calculate the number of credits attempted by each student in each term
    logger.info("Calculating the number of credits attempted by each student in each term")
    crs_calc_by_term = {}
    for tc in term_codes:
        logger.info(f"Calculating attepmpted credits for {tc}")
        curr = crs[crs.TermCode == tc].copy()
        curr_agg = curr.groupby('StudentID').agg(
            Attempted = ('Credits', np.sum),
            Full = ('IsFullTime', np.max),
            Age = ('Age', np.max),
            Dev = ('IsDev', np.sum),
            Internet = ('IsInternet', np.sum),
        ).reset_index()

        logger.info(f"Calculating drop rate for previous terms for {tc}")
        prev = crs.loc[crs.TermCode < tc, ["StudentID", "Course", "IsW"]]
        prev_drop_rate = prev.groupby("StudentID").agg(
            PercentageOfHistDrop = ("IsW", np.mean)
        ).reset_index()

        logger.info(f"Calculating if any repeated courses for {tc}")
        prev["Repeated"] = "Y"
        # count reapeat times for repeated courses on student level
        curr_repeated = pd.merge(curr[["StudentID", "Course"]], prev[["StudentID", "Course", "Repeated"]], how="left", on=["StudentID", "Course"])
        curr_repeated_agg = curr_repeated.groupby("StudentID").agg(
            PercentageOfRepeats = ("Repeated", lambda x: x.eq("Y").mean())
        ).reset_index()
        
        temp_df = curr_agg.merge(curr_repeated_agg, on="StudentID")
        temp_df = temp_df.merge(prev_drop_rate, on="StudentID")
        temp_df["TermCode"] = tc
        crs_calc_by_term[tc] = temp_df
    
    # aggregate the data by student
    course_agg = pd.concat([v for _, v in crs_calc_by_term.items()])
    logger.info(f"Course data shape: {course_agg.shape}")
    
    logger.info(">>>>>> Processing major data <<<<<<")
    majors = pd.read_csv("../../data/raw/major_history.csv")
    
    majors_calc_by_term = {}
    for tc in term_codes:
        logger.info(f"Calculating major change for {tc}")
        curr = majors[majors.TermCode == tc].copy()
        if not len(curr):
            continue

        # calculate if major changed from last term
        curr["MajorChangedFromLast"] = (curr.Major != curr.LastMajor).astype(int)

        # calculate the number of different majors for the past terms
        prev = majors[majors.TermCode < tc]
        major_counts = pd.concat([curr, prev]).groupby("StudentID")["Major"].size().reset_index().rename(columns={"Major": "NumberOfMajors"})
        major_counts["TermCode"] = tc
        
        # calculate the number of unique majors for the past terms
        unique_major_counts = pd.concat([curr, prev]).groupby("StudentID")["Major"].nunique().reset_index().rename(columns={"Major": "NumberOfUniqueMajors"})
        unique_major_counts["TermCode"] = tc

        # merge the data
        temp_df = curr[["StudentID", "TermCode", "MajorChangedFromLast"]].merge(major_counts, on=["StudentID", "TermCode"])
        temp_df = temp_df.merge(unique_major_counts, on=["StudentID", "TermCode"])

        # TODO: add if student graduated from any previous majors        
        majors_calc_by_term[tc] = temp_df


    major_agg = pd.concat([v for _, v in majors_calc_by_term.items()])
    logger.info(f"Major data shape: {major_agg.shape}")
    
    logger.info(">>>>>> Getting GPA data <<<<<<")
    gpa = pd.read_csv("../../data/raw/gpa_history.csv")
    
    logger.info(">>>>>> Processing attendance data <<<<<<")
    attendance = pd.read_csv("../../data/raw/attendance_history.csv")
    attendance = attendance.loc[attendance.WeekNumber == args.week_number, ["StudentID", "TermCode", "PercentageOfAbsence"]]
    
    logger.info(">>>>>> Processing demographic data <<<<<<")
    demo = pd.read_csv("../../data/raw/students.csv")
    demo.fillna("unknown", inplace=True)
    
    logger.info(">>>>>> Processing target data <<<<<<")
    targets = pd.read_csv("../../data/raw/targets.csv")
    
    logger.info(">>>>>> Merging data <<<<<<")
    
    cleaned = course_agg.merge(major_agg, on=["StudentID", "TermCode"])
    cleaned = cleaned.merge(gpa, on=["StudentID", "TermCode"])
    cleaned = cleaned.merge(attendance, on=["StudentID", "TermCode"])
    
    # TODO: verfity age >= 14
    # TODO: check missing values for each column
    cleaned = cleaned.merge(demo, on="StudentID")
    cleaned = cleaned.merge(targets, on="StudentID")
    
    cleaned.to_csv(f"../../data/processed/cleaned-{args.week_number}.csv", index=False)
    
    return cleaned



if __name__ == "__main__":
    #TODO: add week number to the parameters
    #TODO: add input data path to the parameters
    #TODO: add output data path to the parameters
    parser = argparse.ArgumentParser(description='Preprocess data')
    
    
    parser.add_argument('-w', 
                        '--week_number', 
                        type=int, 
                        default=1,
                        required=True,
                        )
    
    args = parser.parse_args()

    go(args)