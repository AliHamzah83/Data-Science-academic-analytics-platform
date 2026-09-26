from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(os.environ.get("ACADEMIC_ANALYTICS_RAW_DIR", ROOT / "data" / "raw"))
RAW_DIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)

DEPARTMENTS = [
    ("CS", "Computer Science", "School of Engineering", "Main Campus"),
    ("MATH", "Mathematics", "School of Science", "Main Campus"),
    ("BIO", "Biology", "School of Life Sciences", "North Campus"),
    ("BUS", "Business", "School of Management", "Downtown Campus"),
    ("PSY", "Psychology", "School of Social Sciences", "Main Campus"),
    ("ENG", "English", "School of Humanities", "North Campus"),
    ("ECE", "Electrical & Computer Engineering", "School of Engineering", "Main Campus"),
]

PROGRAMS = {
    "CS": [
        ("BSCS", "BSc Computer Science", "Undergraduate"),
        ("MSCS", "MSc Computer Science", "Graduate"),
    ],
    "MATH": [
        ("BSM", "BSc Mathematics", "Undergraduate"),
        ("MSM", "MSc Mathematics", "Graduate"),
    ],
    "BIO": [
        ("BSB", "BSc Biology", "Undergraduate"),
        ("MSB", "MSc Biology", "Graduate"),
    ],
    "BUS": [
        ("BBA", "BBA Business Administration", "Undergraduate"),
        ("MBA", "MBA", "Graduate"),
    ],
    "PSY": [
        ("BSP", "BSc Psychology", "Undergraduate"),
        ("MSP", "MSc Psychology", "Graduate"),
    ],
    "ENG": [
        ("BAE", "BA English", "Undergraduate"),
        ("MAE", "MA English", "Graduate"),
    ],
    "ECE": [
        ("BSEE", "BSc Electrical Engineering", "Undergraduate"),
        ("MSEE", "MSc Electrical Engineering", "Graduate"),
    ],
}

COURSES = {
    "CS": [
        ("CS101", "Intro to Programming", 3, True, 1),
        ("CS201", "Data Structures", 3, True, 2),
        ("CS220", "Database Systems", 3, True, 2),
        ("CS301", "Algorithms", 3, True, 3),
        ("CS410", "AI Fundamentals", 3, False, 4),
    ],
    "MATH": [
        ("MTH101", "Calculus I", 4, True, 1),
        ("MTH201", "Linear Algebra", 4, True, 2),
        ("MTH220", "Probability", 4, True, 2),
        ("MTH301", "Statistics", 4, True, 3),
        ("MTH410", "Optimization", 4, False, 4),
    ],
    "BIO": [
        ("BIO101", "Cell Biology", 3, True, 1),
        ("BIO201", "Genetics", 3, True, 2),
        ("BIO220", "Ecology", 3, True, 2),
        ("BIO301", "Molecular Biology", 3, True, 3),
        ("BIO410", "Biotech Lab", 3, False, 4),
    ],
    "BUS": [
        ("BUS101", "Intro to Business", 3, True, 1),
        ("BUS201", "Marketing", 3, True, 2),
        ("BUS220", "Finance", 3, True, 2),
        ("BUS301", "Operations", 3, True, 3),
        ("BUS410", "Strategy", 3, False, 4),
    ],
    "PSY": [
        ("PSY101", "Intro to Psychology", 3, True, 1),
        ("PSY201", "Cognitive Psychology", 3, True, 2),
        ("PSY220", "Research Methods", 3, True, 2),
        ("PSY301", "Abnormal Psychology", 3, True, 3),
        ("PSY410", "Clinical Practice", 3, False, 4),
    ],
    "ENG": [
        ("ENG101", "Composition", 3, True, 1),
        ("ENG201", "Critical Reading", 3, True, 2),
        ("ENG220", "Literature Studies", 3, True, 2),
        ("ENG301", "Academic Writing", 3, True, 3),
        ("ENG410", "Modern Literature", 3, False, 4),
    ],
    "ECE": [
        ("ECE101", "Circuits", 4, True, 1),
        ("ECE201", "Signals", 4, True, 2),
        ("ECE220", "Embedded Systems", 4, True, 2),
        ("ECE301", "Control Systems", 4, True, 3),
        ("ECE410", "Smart Systems", 4, False, 4),
    ],
}

TERMS = [
    (1, "2023-2024", "Fall", "2023-09-01", "2023-12-20"),
    (2, "2023-2024", "Spring", "2024-01-15", "2024-05-15"),
    (3, "2024-2025", "Fall", "2024-09-01", "2024-12-20"),
    (4, "2024-2025", "Spring", "2025-01-15", "2025-05-15"),
]


def grade_from_score(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


# 1. Departments
department_rows = []
for i, (code, name, faculty, campus) in enumerate(DEPARTMENTS, start=1):
    department_rows.append(
        {"department_id": i, "department_code": code, "department_name": name, "faculty_name": faculty, "campus": campus}
    )
df_departments = pd.DataFrame(department_rows)
df_departments.to_csv(RAW_DIR / "dim_department.csv", index=False)

# 2. Programs
program_rows = []
program_id = 1
for dept_code, dept_name, _, _ in DEPARTMENTS:
    for program_code, program_name, degree_level in PROGRAMS[dept_code]:
        program_rows.append(
            {
                "program_id": program_id,
                "program_code": program_code,
                "program_name": program_name,
                "department_id": next(d["department_id"] for d in department_rows if d["department_code"] == dept_code),
                "degree_level": degree_level,
            }
        )
        program_id += 1
df_programs = pd.DataFrame(program_rows)
df_programs.to_csv(RAW_DIR / "dim_program.csv", index=False)

# 3. Students
student_rows = []
for i in range(1, 1501):
    dept_code = rng.choice([d[0] for d in DEPARTMENTS])
    program_info = rng.choice(PROGRAMS[dept_code])
    gender = rng.choice(["Female", "Male", "Non-binary"], p=[0.52, 0.46, 0.02])
    age = int(np.clip(rng.normal(20.5, 2.2), 17, 35))
    residency = rng.choice(["Domestic", "International"], p=[0.75, 0.25])
    first_generation = bool(rng.binomial(1, 0.38))
    scholarship = bool(rng.binomial(1, 0.28))
    current_year = int(rng.integers(1, 5))
    academic_status = rng.choice(["Good Standing", "Academic Warning", "Probation"], p=[0.82, 0.13, 0.05])
    student_rows.append(
        {
            "student_id": i,
            "student_code": f"S{1000 + i}",
            "first_name": f"Student{i}",
            "last_name": f"Last{i}",
            "gender": gender,
            "age": age,
            "nationality": rng.choice(["Local", "American", "British", "Indian", "Nigerian", "Egyptian", "Brazilian", "German"]),
            "residency_status": residency,
            "first_generation": first_generation,
            "scholarship_flag": scholarship,
            "admission_year": 2021 + int(rng.integers(0, 4)),
            "current_year": current_year,
            "academic_status": academic_status,
        }
    )
df_students = pd.DataFrame(student_rows)
df_students.to_csv(RAW_DIR / "dim_student.csv", index=False)

# 4. Courses
df_courses_rows = []
course_id = 1
for dept_code, _, _, _ in DEPARTMENTS:
    for course_code, course_name, credits, is_core, course_level in COURSES[dept_code]:
        df_courses_rows.append(
            {
                "course_id": course_id,
                "course_code": course_code,
                "course_name": course_name,
                "department_id": next(d["department_id"] for d in department_rows if d["department_code"] == dept_code),
                "credits": credits,
                "is_core": is_core,
                "course_level": course_level,
            }
        )
        course_id += 1
df_courses = pd.DataFrame(df_courses_rows)
df_courses.to_csv(RAW_DIR / "dim_course.csv", index=False)

# 5. Terms
def parse_date(date_str: str):
    return pd.to_datetime(date_str)

term_rows = []
for term_id, academic_year, term_name, start_date, end_date in TERMS:
    term_rows.append(
        {
            "term_id": term_id,
            "academic_year": academic_year,
            "term_name": term_name,
            "start_date": parse_date(start_date),
            "end_date": parse_date(end_date),
        }
    )
df_terms = pd.DataFrame(term_rows)
df_terms.to_csv(RAW_DIR / "dim_term.csv", index=False)

# 6. Enrollments, Attendance, LMS, Assignments, Exams, GPA, Risk
enrollments = []
attendance_rows = []
lms_rows = []
assignment_rows = []
exam_rows = []
gpa_rows = []
risk_rows = []

for student_id in range(1, 1501):
    for term_id in [1, 2, 3, 4]:
        dept_code = rng.choice([d[0] for d in DEPARTMENTS])
        program_id = int(rng.choice(df_programs[df_programs["department_id"] == next(d["department_id"] for d in department_rows if d["department_code"] == dept_code)]["program_id"].tolist()))

        selected_courses = rng.choice(df_courses[df_courses["department_id"] == next(d["department_id"] for d in department_rows if d["department_code"] == dept_code)]["course_id"].tolist(), size=4, replace=False)
        term_activity_scores: list[float] = []

        for course_id in selected_courses:
            course = df_courses[df_courses["course_id"] == course_id].iloc[0]
            base_risk = 0.12 if student_id % 9 == 0 else 0.0
            engagement = 0.55 + 0.25 * rng.random() + (0.10 if not student_rows[student_id - 1]["first_generation"] else 0.0)
            attendance_rate = np.clip(0.82 + rng.normal(0, 0.12) - base_risk + 0.08 * (course["is_core"]), 0.35, 0.99)
            assignment_avg = np.clip(0.74 + rng.normal(0, 0.15) + 0.06 * (1 if course["is_core"] else 0), 0.25, 0.98)
            midterm_score = np.clip(0.66 + rng.normal(0, 0.18) + 0.04 * engagement, 0.20, 0.98)
            final_score = np.clip(0.68 + rng.normal(0, 0.20) + 0.04 * engagement, 0.15, 0.99)
            weighted = 0.30 * assignment_avg + 0.25 * midterm_score + 0.45 * final_score
            course_grade = np.clip(weighted * 100, 0, 100)
            letter = grade_from_score(course_grade)
            course_status = "Pass" if course_grade >= 50 else "Fail"
            if rng.random() < 0.03:
                course_status = "Withdrawn"

            enrollments.append(
                {
                    "student_id": student_id,
                    "program_id": program_id,
                    "course_id": int(course_id),
                    "term_id": term_id,
                    "section_id": f"SEC-{term_id}-{course['course_code']}",
                    "attendance_rate": round(float(attendance_rate), 4),
                    "assignment_avg": round(float(assignment_avg * 100), 2),
                    "midterm_score": round(float(midterm_score * 100), 2),
                    "final_score": round(float(final_score * 100), 2),
                    "course_grade": round(float(course_grade), 2),
                    "letter_grade": letter,
                    "course_status": course_status,
                }
            )

            lectures_attended = int(round(attendance_rate * (12 + rng.integers(0, 6))))
            total_lectures = lectures_attended + max(2, int(rng.integers(1, 6)))
            attendance_rows.append(
                {
                    "student_id": student_id,
                    "course_id": int(course_id),
                    "term_id": term_id,
                    "lectures_attended": lectures_attended,
                    "total_lectures": total_lectures,
                    "attendance_pct": round(100 * lectures_attended / total_lectures, 2),
                    "absences": total_lectures - lectures_attended,
                }
            )

            lms_logins = int(rng.integers(4, 25))
            discussion_posts = int(rng.integers(0, 12))
            videos_watched = int(rng.integers(2, 20))
            time_spent = int(rng.integers(25, 210))
            activity_score = round(float(np.clip(0.35 * lms_logins / 25 + 0.25 * discussion_posts / 10 + 0.25 * videos_watched / 20 + 0.15 * time_spent / 180, 0, 1) * 100), 2)
            term_activity_scores.append(activity_score)
            lms_rows.append(
                {
                    "student_id": student_id,
                    "course_id": int(course_id),
                    "term_id": term_id,
                    "logins": lms_logins,
                    "discussion_posts": discussion_posts,
                    "videos_watched": videos_watched,
                    "time_spent_minutes": time_spent,
                    "activity_score": activity_score,
                }
            )

            assignment_count = 3 + int(rng.integers(0, 3))
            for j in range(assignment_count):
                score = np.clip(assignment_avg * 100 + rng.normal(0, 12), 15, 100)
                max_score = 100
                late_days = max(0, int(rng.integers(0, 4))) if rng.random() < 0.35 else 0
                assignment_rows.append(
                    {
                        "student_id": student_id,
                        "course_id": int(course_id),
                        "term_id": term_id,
                        "assignment_name": f"Assignment {j + 1}",
                        "week_number": j + 1,
                        "score": round(float(score), 2),
                        "max_score": max_score,
                        "submission_delay_days": late_days,
                    }
                )

            exam_types = ["Midterm", "Final"]
            for exam_type in exam_types:
                exam_score = (midterm_score if exam_type == "Midterm" else final_score) * 100
                exam_rows.append(
                    {
                        "student_id": student_id,
                        "course_id": int(course_id),
                        "term_id": term_id,
                        "exam_type": exam_type,
                        "score": round(float(exam_score), 2),
                        "max_score": 100,
                        "exam_date": pd.to_datetime("2024-01-15") if exam_type == "Midterm" else pd.to_datetime("2024-05-01"),
                    }
                )

        # semester GPA over term
        semester_gpa = round(float(np.clip(2.6 + rng.normal(0, 0.9) + (0.1 if student_id % 7 == 0 else 0), 1.0, 4.0)), 2)
        cumulative_gpa = round(float(np.clip(semester_gpa + rng.normal(0, 0.4), 1.5, 4.0)), 2)
        if semester_gpa < 2.0:
            standing = "Probation"
        elif semester_gpa < 2.5:
            standing = "Warning"
        else:
            standing = "Good Standing"
        gpa_rows.append(
            {
                "student_id": student_id,
                "term_id": term_id,
                "semester_gpa": semester_gpa,
                "cumulative_gpa": cumulative_gpa,
                "academic_standing": standing,
            }
        )

        average_activity_score = float(np.mean(term_activity_scores)) if term_activity_scores else 50.0
        risk_score = 15 + (100 - attendance_rate * 100) * 0.25 + (100 - average_activity_score) * 0.2 + max(0, (2.5 - semester_gpa) * 20)
        risk_score = float(np.clip(risk_score, 0, 100))
        if risk_score >= 70:
            risk_label = "High"
        elif risk_score >= 45:
            risk_label = "Moderate"
        else:
            risk_label = "Low"
        intervention_flag = risk_label in ["High", "Moderate"]
        reasons = "Low attendance; weak LMS engagement; GPA below target" if risk_label == "High" else "Moderate engagement and grade pressure" if risk_label == "Moderate" else "Stable academic engagement"
        risk_rows.append(
            {
                "student_id": student_id,
                "term_id": term_id,
                "risk_score": round(risk_score, 2),
                "risk_label": risk_label,
                "intervention_flag": intervention_flag,
                "risk_reasons": reasons,
            }
        )

# Save all CSVs
pd.DataFrame(enrollments).to_csv(RAW_DIR / "fact_enrollment.csv", index=False)
pd.DataFrame(attendance_rows).to_csv(RAW_DIR / "fact_attendance.csv", index=False)
pd.DataFrame(lms_rows).to_csv(RAW_DIR / "fact_lms_activity.csv", index=False)
pd.DataFrame(assignment_rows).to_csv(RAW_DIR / "fact_assignment_scores.csv", index=False)
pd.DataFrame(exam_rows).to_csv(RAW_DIR / "fact_exam_scores.csv", index=False)
pd.DataFrame(gpa_rows).to_csv(RAW_DIR / "fact_gpa_history.csv", index=False)
pd.DataFrame(risk_rows).to_csv(RAW_DIR / "fact_risk_assessment.csv", index=False)

print(f"Generated synthetic data files in: {RAW_DIR}")
print(f"Departments: {len(df_departments)}")
print(f"Programs: {len(df_programs)}")
print(f"Students: {len(df_students)}")
print(f"Courses: {len(df_courses)}")
print(f"Enrollments: {len(enrollments)}")
print(f"Risk records: {len(risk_rows)}")
