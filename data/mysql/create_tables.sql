CREATE TABLE IF NOT EXISTS Account (
    acc varchar(12) NOT NULL PRIMARY KEY,
    passwd varchar(12) NOT NULL,
    CreateDate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS Student (
    Sno varchar(9) NOT NULL PRIMARY KEY,
    Snm varchar(10) NOT NULL,
    Sex varchar(1) NOT NULL,
    Sde varchar(6) NOT NULL,
    Pwd char(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS Course (
    Cno char(4) NOT NULL PRIMARY KEY,
    Cnm varchar(10) NOT NULL,
    Ctm integer NOT NULL,
    Cpt integer NOT NULL,
    Tec varchar(20) NOT NULL,
    Pla varchar(18) NOT NULL,
    Share char(1) NOT NULL,
    capacity integer NOT NULL DEFAULT 30
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS Enrollment (
    Cno char(4) NOT NULL,
    Sno varchar(9) NOT NULL,
    Grd integer NOT NULL,
    UNIQUE KEY uq_enrollment_course_student (Cno, Sno),
    CONSTRAINT fk_enrollment_course FOREIGN KEY (Cno) REFERENCES Course(Cno),
    CONSTRAINT fk_enrollment_student FOREIGN KEY (Sno) REFERENCES Student(Sno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS EnrollmentLog (
    enrollment_id varchar(20) NOT NULL PRIMARY KEY,
    student_id varchar(9) NOT NULL,
    course_id char(4) NOT NULL,
    source_college_id varchar(8) NOT NULL,
    target_college_id varchar(8) NOT NULL,
    score integer NOT NULL,
    origin varchar(16) NOT NULL,
    status varchar(16) NOT NULL,
    created_at datetime NOT NULL,
    updated_at datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS OutboundRequestLog (
    enrollment_id varchar(20) NOT NULL PRIMARY KEY,
    home_college_id varchar(8) NOT NULL,
    target_college_id varchar(8) NOT NULL,
    student_id varchar(9) NOT NULL,
    course_id varchar(8) NOT NULL,
    score integer NOT NULL,
    status varchar(20) NOT NULL,
    request_time varchar(19) NOT NULL,
    updated_at varchar(19) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
