
DROP TABLE IF EXISTS fact_risk_assessment;
DROP TABLE IF EXISTS fact_gpa_history;
DROP TABLE IF EXISTS fact_exam_scores;
DROP TABLE IF EXISTS fact_assignment_scores;
DROP TABLE IF EXISTS fact_lms_activity;
DROP TABLE IF EXISTS fact_attendance;
DROP TABLE IF EXISTS fact_enrollment;
DROP TABLE IF EXISTS dim_course;
DROP TABLE IF EXISTS dim_program;
DROP TABLE IF EXISTS dim_student;
DROP TABLE IF EXISTS dim_department;
DROP TABLE IF EXISTS dim_term;

PRAGMA foreign_keys = ON;

CREATE TABLE dim_department (
    department_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_code TEXT NOT NULL UNIQUE,
    department_name TEXT NOT NULL,
    faculty_name TEXT,
    campus TEXT
);

CREATE TABLE dim_program (
    program_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_code TEXT NOT NULL UNIQUE,
    program_name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    degree_level TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES dim_department(department_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE dim_course (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0),
    is_core INTEGER NOT NULL DEFAULT 0 CHECK (is_core IN (0, 1)),
    course_level INTEGER,
    FOREIGN KEY (department_id) REFERENCES dim_department(department_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE dim_student (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    gender TEXT,
    age INTEGER CHECK (age IS NULL OR age BETWEEN 0 AND 120),
    date_of_birth TEXT,
    nationality TEXT,
    residency_status TEXT,
    first_generation INTEGER NOT NULL DEFAULT 0 CHECK (first_generation IN (0, 1)),
    scholarship_flag INTEGER NOT NULL DEFAULT 0 CHECK (scholarship_flag IN (0, 1)),
    admission_year INTEGER,
    academic_status TEXT NOT NULL DEFAULT 'Good Standing'
);

CREATE TABLE dim_term (
    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    academic_year TEXT NOT NULL,
    term_name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    UNIQUE (academic_year, term_name),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE TABLE dim_advisor (
    advisor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisor_code TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE,
    department_id INTEGER,
    active_flag INTEGER NOT NULL DEFAULT 1 CHECK (active_flag IN (0, 1)),
    FOREIGN KEY (department_id) REFERENCES dim_department(department_id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE fact_enrollment (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    program_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    section_id TEXT NOT NULL,
    enrollment_date TEXT,
    course_status TEXT NOT NULL DEFAULT 'Enrolled',
    FOREIGN KEY (student_id) REFERENCES dim_student(student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (program_id) REFERENCES dim_program(program_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (course_id) REFERENCES dim_course(course_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (term_id) REFERENCES dim_term(term_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (student_id, course_id, term_id, section_id)
);

CREATE TABLE fact_grade (
    grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    assessment_type TEXT NOT NULL,
    score REAL,
    max_score REAL NOT NULL DEFAULT 100 CHECK (max_score > 0),
    grade_date TEXT,
    letter_grade TEXT,
    FOREIGN KEY (enrollment_id) REFERENCES fact_enrollment(enrollment_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (score IS NULL OR (score >= 0 AND score <= max_score)),
    UNIQUE (enrollment_id, assessment_type)
);

CREATE TABLE fact_attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL UNIQUE,
    lectures_attended INTEGER NOT NULL DEFAULT 0 CHECK (lectures_attended >= 0),
    total_lectures INTEGER NOT NULL CHECK (total_lectures > 0),
    absences INTEGER NOT NULL DEFAULT 0 CHECK (absences >= 0),
    attendance_pct REAL NOT NULL CHECK (attendance_pct BETWEEN 0 AND 100),
    FOREIGN KEY (enrollment_id) REFERENCES fact_enrollment(enrollment_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (lectures_attended <= total_lectures),
    CHECK (absences <= total_lectures)
);

CREATE TABLE fact_lms_activity (
    lms_activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL UNIQUE,
    logins INTEGER NOT NULL DEFAULT 0 CHECK (logins >= 0),
    discussion_posts INTEGER NOT NULL DEFAULT 0 CHECK (discussion_posts >= 0),
    videos_watched INTEGER NOT NULL DEFAULT 0 CHECK (videos_watched >= 0),
    time_spent_minutes INTEGER NOT NULL DEFAULT 0 CHECK (time_spent_minutes >= 0),
    activity_score REAL CHECK (activity_score IS NULL OR activity_score >= 0),
    FOREIGN KEY (enrollment_id) REFERENCES fact_enrollment(enrollment_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE fact_assignment_scores (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    assignment_name TEXT NOT NULL,
    week_number INTEGER,
    score REAL,
    max_score REAL NOT NULL DEFAULT 100 CHECK (max_score > 0),
    submission_delay_days INTEGER NOT NULL DEFAULT 0 CHECK (submission_delay_days >= 0),
    FOREIGN KEY (enrollment_id) REFERENCES fact_enrollment(enrollment_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (score IS NULL OR (score >= 0 AND score <= max_score)),
    UNIQUE (enrollment_id, assignment_name)
);

CREATE TABLE fact_exam_scores (
    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    exam_type TEXT NOT NULL,
    score REAL,
    max_score REAL NOT NULL DEFAULT 100 CHECK (max_score > 0),
    exam_date TEXT,
    FOREIGN KEY (enrollment_id) REFERENCES fact_enrollment(enrollment_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (score IS NULL OR (score >= 0 AND score <= max_score)),
    UNIQUE (enrollment_id, exam_type)
);

CREATE TABLE fact_gpa_history (
    gpa_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    semester_gpa REAL CHECK (semester_gpa IS NULL OR semester_gpa BETWEEN 0 AND 4),
    cumulative_gpa REAL CHECK (cumulative_gpa IS NULL OR cumulative_gpa BETWEEN 0 AND 4),
    academic_standing TEXT,
    FOREIGN KEY (student_id) REFERENCES dim_student(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES dim_term(term_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (student_id, term_id)
);

CREATE TABLE fact_risk_assessment (
    risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    assessment_timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT NOT NULL DEFAULT 'rules-v1',
    risk_score REAL NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_label TEXT NOT NULL CHECK (risk_label IN ('Low', 'Medium', 'Moderate', 'High')),
    risk_reasons TEXT,
    FOREIGN KEY (student_id) REFERENCES dim_student(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES dim_term(term_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (student_id, term_id, model_version, assessment_timestamp)
);

CREATE TABLE student_advisor (
    student_advisor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    advisor_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    assignment_type TEXT NOT NULL DEFAULT 'Primary',
    FOREIGN KEY (student_id) REFERENCES dim_student(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (advisor_id) REFERENCES dim_advisor(advisor_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (end_date IS NULL OR end_date >= start_date),
    UNIQUE (student_id, advisor_id, start_date)
);

CREATE TABLE fact_intervention (
    intervention_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    advisor_id INTEGER,
    risk_id INTEGER,
    intervention_type TEXT NOT NULL,
    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT,
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK (status IN ('Open', 'In Progress', 'Closed', 'Declined')),
    outcome TEXT,
    notes TEXT,
    FOREIGN KEY (student_id) REFERENCES dim_student(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES dim_term(term_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (advisor_id) REFERENCES dim_advisor(advisor_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY (risk_id) REFERENCES fact_risk_assessment(risk_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CHECK (closed_at IS NULL OR closed_at >= opened_at)
);

CREATE INDEX idx_dim_student_status ON dim_student (academic_status);
CREATE INDEX idx_fact_enrollment_student ON fact_enrollment (student_id);
CREATE INDEX idx_fact_enrollment_course ON fact_enrollment (course_id);
CREATE INDEX idx_fact_enrollment_term ON fact_enrollment (term_id);
CREATE INDEX idx_fact_risk_student_term ON fact_risk_assessment (student_id, term_id);
