from utils import get_data_from_cams
from config import CURR_TERM


import argparse
import logging
import os


data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw"))

logging.basicConfig(level=logging.DEBUG, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

logger.addHandler(logging.FileHandler('get_data.log', 'w'))


def cte(rest_of_query):
    s = f"""
    with terms as (
        SELECT TermCalendarID
            , Term as TermCode
            , TextTerm as Term
            , ROW_NUMBER() over (order by Term) as TermIndex
        FROM TermCalendar
        where TextTerm not like '%Flx%'
            and TextTerm not like '%Qtr%'
            and TextTerm not like '%wk%'
            and TextTerm not like 'Summer%' -- comment it if summer needed
            and TermCalendarID <> 0
            and year(TermStartDate) BETWEEN 2017 and year(GETDATE())
    ),

    sids as (
        -- * get all students who enrolled in the terms above
        select distinct StudentID
            , g.DisplayText as Ethnicity
            , sd.Gender
            , sd.IsHispanic
        from SRAcademic sra
        join Student s on sra.StudentUID = s.StudentUID
        join StudentDemographics sd on s.StudentUID = sd.StudentUID
        join Glossary g on sd.EthnicOriginID = g.UniqueId
        where sra.TermCalendarID in (select TermCalendarID from terms)
    )

    {rest_of_query}
    """
    return s


def get_target():
    logger.info("Getting target data...")
    s = """
    select distinct StudentID
        , tc.Term as TermCode
        , case when sum(case when Grade = 'W' then 1 else 0 end) > 0 then 1 else 0 end as [Target]
    from SRAcademic sra
    join TermCalendar tc on sra.TermCalendarID = tc.TermCalendarID
    join Student s on sra.StudentUID = s.StudentUID
    where sra.TermCalendarID in (select TermCalendarID from terms)
    group by StudentID, Term
    """
    df = get_data_from_cams(cte(s))
    df.to_csv(os.path.join(data_dir, "targets.csv"), index=False)
    return df


def get_demographics():
    logger.info("Getting demographics data...")
    s = """
    select *
    from sids
    """
    df = get_data_from_cams(cte(s))
    df.to_csv(os.path.join(data_dir, "students.csv"), index=False)
    return df


def get_terms():
    logger.info("Getting terms data...")

    s = f"""
    select distinct left(Section, 1) as WeekType
        , DATEDIFF(week, sro.StartDate, GETDATE()) + 1 as WeekNumber
    from SROffer sro
    join TermCalendar tc on tc.TermCalendarID = sro.TermCalendarID
    where tc.TextTerm = '{CURR_TERM}'
        and sro.EndDate >= GETDATE()
    """
    df = get_data_from_cams(s)
    df.to_csv(os.path.join(data_dir, "terms.csv"), index=False)
    return df


def get_course_history():
    logger.info("Getting course history data...")
    """
    Returns course histroty of students who enrolled in the last 5 years.
    """

    s = """
    SELECT TextTerm as Term
        , tc.Term as TermCode
        , s.StudentID
        , sro.Department, sro.CourseID, sro.Section, sro.Credits
        , Grade
        , year(sro.StartDate) - year(s.BirthDate) as Age
        , case when fp.DisplayText like '%Full%' then 1 else 0 end as IsFullTime
    FROM SRAcademic sra
    join SROffer sro on sra.SROfferID = sro.SROfferID
    join TermCalendar tc on tc.TermCalendarID = sra.TermCalendarID
    join Student s on s.StudentUID = sra.StudentUID
    join StudentStatus ss on sra.StudentUID = ss.StudentUID and sra.TermCalendarID = ss.TermCalendarID
    join Glossary fp on fp.UniqueId = ss.FTPTStatusID
    where sro.StartDate is not null 
        and sro.Section is not NULL 
        and len(Term) = 4
        and sro.StartDate <= GETDATE()         -- only include the courses have started
        and s.StudentID in (select StudentID from sids)-- student list from above
    """
    df = get_data_from_cams(cte(s))
    df.to_csv(os.path.join(data_dir, "course_history.csv"), index=False)
    return df


def get_major_history():
    logger.info("Getting major history data...")
    """
    Returns student major history for the last 10 years.
    """
    s = """
    select distinct s.StudentID
        , Term as TermCode
        , MajorMinorName as Major
        , LAG(MajorMinorName, 1, MajorMinorName) over (PARTITION by StudentID ORDER BY Term) as LastMajor
    from StudentStatus ss 
    join Student s on s.StudentUID = ss.StudentUID
    join TermCalendar tc on ss.TermCalendarID = tc.TermCalendarID
    join StudentProgram sp on ss.StudentStatusID = sp.StudentStatusID
    join MajorMinor mm on sp.MajorProgramID = mm.MajorMinorID
    where SUBSTRING(Term, 2, 2) between (year(GETDATE()) - 10) % 100 and YEAR(GETDATE()) % 100
        and len(Term) = 4
        and TextTerm not like '%wk%'
        and MajorMinorName <> ''
        and StudentID in  (select StudentID from sids)
    """
    df = get_data_from_cams(cte(s))
    df.to_csv(os.path.join(data_dir, "major_history.csv"), index=False)
    return df


def get_attendance_history():
    logger.info("Getting attendance history")
    """
    Returns student attendance history for the past 5 years.
    """

    s = f"""
        select distinct StudentID
            , TermCode
            , WeekNumber
            , (1.0 * sum(IsAbsent) over (partition by StudentID, TermCode order by WeekNumber)) / (1.0 * count(*) over (partition by StudentID, TermCode order by WeekNumber)) as PercentageOfAbsence
    from (
        select s.StudentID
            , Term as TermCode
            , case when sa.Comment like '%abs%' then 1 else 0 end as IsAbsent
            , sa.Comment
            , DATEDIFF(week, sro.StartDate, sa.SADate) + 1 as WeekNumber
            , sro.StartDate
            , sro.EndDate
            , sa.SADate
        from StudentAttendance sa
        join SROffer sro on sa.SROfferID = sro.SROfferID
        join Student s on sa.StudentUID = s.StudentUID
        join TermCalendar tc on tc.TermCalendarID = sa.TermCalendarID
        where sa.SADate >= sro.StartDate and sa.SADate <= sro.EndDate
            and len(Term) = 4
            and TextTerm not like '%wk%'
            and StudentId in (select StudentID from sids)
    ) d 
    """
    df = get_data_from_cams(cte(s))
    df.to_csv(os.path.join(data_dir, "attendance_history.csv"), index=False)
    return df


def get_last_term_gpa():
    logger.info("Getting last term GPA...")
    """
    Returns last term gpa and cum gpa.
    """

    s = """
    select s.StudentID, Term as TermCode
        , LAG(TermGPA, 1, 0) over (partition by StudentID order by Term) as TermGPALast
        , LAG(CumGPA, 1, 0) over (partition by StudentID order by Term) as CumGPALast
    from CAMS_StudentCumulativeGPA_View g
    join Student s on g.StudentUID = s.StudentUID
    join TermCalendar tc on g.TermCalendarID = tc.TermCalendarID
    where StudentID in (select StudentID from sids)
        and len(Term) = 4
        and TextTerm not like '%wk%'
    order by s.StudentID, tc.Term
    """
    df = get_data_from_cams(cte(s))
    df.to_csv(os.path.join(data_dir, "gpa_history.csv"), index=False)
    return df


# TODO: add canvas data mannually later
def get_canvas_data():
    pass


def main():
    get_target()
    get_demographics()
    get_attendance_history()
    get_major_history()
    get_course_history()
    get_last_term_gpa()


if __name__ == "__main__":
    main()
