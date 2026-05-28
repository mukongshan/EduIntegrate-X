CREATE TABLE Account (
    "账户名" varchar2(12) PRIMARY KEY,
    "密码" varchar2(12) NOT NULL,
    "级别" number(2) NOT NULL,
    "客体" varchar2(9)
);

CREATE TABLE Student (
    "学号" varchar2(9) PRIMARY KEY,
    "姓名" varchar2(10) NOT NULL,
    "性别" varchar2(2) NOT NULL,
    "专业" varchar2(16) NOT NULL,
    "密码" varchar2(6) NOT NULL
);

CREATE TABLE Course (
    "编号" varchar2(5) PRIMARY KEY,
    "名称" varchar2(16) NOT NULL,
    "课时" varchar2(2) NOT NULL,
    "学分" varchar2(1) NOT NULL,
    "老师" varchar2(10) NOT NULL,
    "地点" varchar2(20) NOT NULL,
    "共享" char(1) NOT NULL
);

CREATE TABLE Enrollment (
    "课程编号" varchar2(5) NOT NULL,
    "学号" varchar2(9) NOT NULL,
    "得分" varchar2(3) NOT NULL,
    CONSTRAINT pk_b_enrollment PRIMARY KEY ("课程编号", "学号")
);

CREATE TABLE EnrollmentLog (
    enrollment_id varchar2(24) PRIMARY KEY,
    student_id varchar2(9) NOT NULL,
    course_id varchar2(5) NOT NULL,
    source_college_id varchar2(8) NOT NULL,
    target_college_id varchar2(8) NOT NULL,
    score number(3) NOT NULL,
    origin varchar2(16) NOT NULL,
    status varchar2(16) NOT NULL,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL
);

CREATE TABLE OutboundRequestLog (
    enrollment_id varchar2(24) PRIMARY KEY,
    home_college_id varchar2(8) NOT NULL,
    target_college_id varchar2(8) NOT NULL,
    student_id varchar2(9) NOT NULL,
    course_id varchar2(5) NOT NULL,
    score number(3) NOT NULL,
    status varchar2(20) NOT NULL,
    request_time varchar2(19) NOT NULL,
    updated_at varchar2(19)
);
