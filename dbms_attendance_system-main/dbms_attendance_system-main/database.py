import mysql.connector
from mysql.connector import Error
from config import Config
from flask_bcrypt import Bcrypt
from datetime import date, timedelta
import random

def get_db_connection():
    try:
        print("Attempting to connect with these settings:")
        print(f"Host: {Config.MYSQL_HOST}")
        print(f"User: {Config.MYSQL_USER}")
        print(f"Database: {Config.MYSQL_DB}")
        
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        print("Database connection successful!")
        return connection
    except Error as e:
        print(f"Failed to connect to database. Error: {e}")
        print(f"Error Code: {e.errno if hasattr(e, 'errno') else 'N/A'}")
        print(f"SQL State: {e.sqlstate if hasattr(e, 'sqlstate') else 'N/A'}")
        return None    

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables with better structure - removing admin table
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        teacher_id VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        department VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        department VARCHAR(50),
        semester INT,
        section VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_code VARCHAR(20) UNIQUE NOT NULL,
        course_name VARCHAR(100) NOT NULL,
        department VARCHAR(50),
        semester INT,
        teacher_id INT,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT,
        course_id INT,
        Iat1_marks FLOAT DEFAULT 0,
        Iat2_marks FLOAT DEFAULT 0,
        Assignment1_marks FLOAT DEFAULT 0,
        Assignment2_marks FLOAT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (course_id) REFERENCES courses(id),
        UNIQUE KEY unique_student_course (student_id, course_id)
    )
    """)               
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT,
        course_id INT,
        date DATE NOT NULL,
        status ENUM('present', 'absent', 'late') NOT NULL,
        marked_by INT,
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        FOREIGN KEY (marked_by) REFERENCES teachers(id) ON DELETE SET NULL,
        UNIQUE KEY unique_attendance (student_id, course_id, date)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teacher_semesters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT,
    semester INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    UNIQUE KEY unique_teacher_semester (teacher_id, semester)
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

def insert_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    bcrypt = Bcrypt()

    # Check if data already exists
    
    try:
        # Removed admin user insertion

        # Insert teachers - one teacher per department to handle all semesters
        initial_teachers = [
            ('T001', 'John Smith', 'john.smith@example.com', bcrypt.generate_password_hash('teacher123').decode('utf-8'), 'Computer Science'),
            ('T002', 'Sarah Wilson', 'sarah.wilson@example.com', bcrypt.generate_password_hash('teacher456').decode('utf-8'), 'Mathematics'),
            ('T003', 'Michael Brown', 'michael.brown@example.com', bcrypt.generate_password_hash('teacher789').decode('utf-8'), 'Physics'),
            ('T004', 'Emily Parker', 'emily.parker@example.com', bcrypt.generate_password_hash('teacher_emp123').decode('utf-8'), 'English'),
            ('T005', 'Robert Chen', 'robert.chen@example.com', bcrypt.generate_password_hash('teacher_rob123').decode('utf-8'), 'Chemistry'),
            ('T006', 'Maria Garcia', 'maria.garcia@example.com', bcrypt.generate_password_hash('teacher_mar123').decode('utf-8'), 'Biology'),
            ('T007', 'James Wilson', 'james.wilson@example.com', bcrypt.generate_password_hash('teacher_jam123').decode('utf-8'), 'History')
        ]
        
        cursor.executemany("""
            INSERT IGNORE INTO teachers 
            (teacher_id, name, email, password, department)
            VALUES (%s, %s, %s, %s, %s)
        """, initial_teachers)

        # Get teacher IDs for course assignment (based only on department)
        cursor.execute("SELECT id, department FROM teachers")
        teachers = cursor.fetchall()
        teacher_dept_map = {dept: tid for tid, dept in teachers}

        # Insert all courses with a variety of semesters
        all_courses = [
            # Computer Science courses for multiple semesters
            ('CS101', 'Introduction to Programming', 'Computer Science', 1, teacher_dept_map['Computer Science']),
            ('CS201', 'Data Structures', 'Computer Science', 2, teacher_dept_map['Computer Science']),
            ('CS301', 'Advanced Programming', 'Computer Science', 3, teacher_dept_map['Computer Science']),
            ('CS302', 'Database Systems', 'Computer Science', 3, teacher_dept_map['Computer Science']),
            ('CS401', 'Software Engineering', 'Computer Science', 4, teacher_dept_map['Computer Science']),
            ('CS501', 'Machine Learning', 'Computer Science', 5, teacher_dept_map['Computer Science']),
            ('CS601', 'Distributed Systems', 'Computer Science', 6, teacher_dept_map['Computer Science']),
            ('CS701', 'Advanced Algorithms', 'Computer Science', 7, teacher_dept_map['Computer Science']),
            ('CS801', 'Research Methods', 'Computer Science', 8, teacher_dept_map['Computer Science']),
            
            # Mathematics courses for multiple semesters
            ('MATH101', 'Calculus I', 'Mathematics', 1, teacher_dept_map['Mathematics']),
            ('MATH201', 'Linear Algebra', 'Mathematics', 2, teacher_dept_map['Mathematics']),
            ('MATH301', 'Differential Equations', 'Mathematics', 3, teacher_dept_map['Mathematics']),
            ('MATH401', 'Abstract Algebra', 'Mathematics', 4, teacher_dept_map['Mathematics']),
            ('MATH501', 'Real Analysis', 'Mathematics', 5, teacher_dept_map['Mathematics']),
            ('MATH601', 'Complex Analysis', 'Mathematics', 6, teacher_dept_map['Mathematics']),
            ('MATH701', 'Numerical Methods', 'Mathematics', 7, teacher_dept_map['Mathematics']),
            ('MATH801', 'Mathematical Modeling', 'Mathematics', 8, teacher_dept_map['Mathematics']),
            
            # Physics courses for multiple semesters
            ('PHY101', 'Mechanics', 'Physics', 1, teacher_dept_map['Physics']),
            ('PHY201', 'Electricity and Magnetism', 'Physics', 2, teacher_dept_map['Physics']),
            ('PHY301', 'Thermodynamics', 'Physics', 3, teacher_dept_map['Physics']),
            ('PHY401', 'Quantum Mechanics', 'Physics', 4, teacher_dept_map['Physics']),
            ('PHY501', 'Nuclear Physics', 'Physics', 5, teacher_dept_map['Physics']),
            ('PHY601', 'Optics', 'Physics', 6, teacher_dept_map['Physics']),
            ('PHY701', 'Astrophysics', 'Physics', 7, teacher_dept_map['Physics']),
            ('PHY801', 'Particle Physics', 'Physics', 8, teacher_dept_map['Physics']),
            
            # English courses for multiple semesters
            ('ENG101', 'English Composition', 'English', 1, teacher_dept_map['English']),
            ('ENG201', 'Advanced English', 'English', 2, teacher_dept_map['English']),
            ('ENG301', 'Literature Survey', 'English', 3, teacher_dept_map['English']),
            ('ENG401', 'Creative Writing', 'English', 4, teacher_dept_map['English']),
            ('ENG501', 'Drama Studies', 'English', 5, teacher_dept_map['English']),
            ('ENG601', 'Poetry Analysis', 'English', 6, teacher_dept_map['English']),
            ('ENG701', 'Literary Theory', 'English', 7, teacher_dept_map['English']),
            ('ENG801', 'Modern Literature', 'English', 8, teacher_dept_map['English']),
            
            # Chemistry courses for multiple semesters
            ('CHEM101', 'Basic Chemistry', 'Chemistry', 1, teacher_dept_map['Chemistry']),
            ('CHEM201', 'Organic Chemistry', 'Chemistry', 2, teacher_dept_map['Chemistry']),
            ('CHEM301', 'Inorganic Chemistry', 'Chemistry', 3, teacher_dept_map['Chemistry']),
            ('CHEM401', 'Physical Chemistry', 'Chemistry', 4, teacher_dept_map['Chemistry']),
            ('CHEM501', 'Biochemistry', 'Chemistry', 5, teacher_dept_map['Chemistry']),
            ('CHEM601', 'Analytical Chemistry', 'Chemistry', 6, teacher_dept_map['Chemistry']),
            ('CHEM701', 'Environmental Chemistry', 'Chemistry', 7, teacher_dept_map['Chemistry']),
            ('CHEM801', 'Polymer Chemistry', 'Chemistry', 8, teacher_dept_map['Chemistry']),
            
            # Biology courses for multiple semesters
            ('BIO101', 'Introduction to Biology', 'Biology', 1, teacher_dept_map['Biology']),
            ('BIO201', 'Cell Biology', 'Biology', 2, teacher_dept_map['Biology']),
            ('BIO301', 'Genetics', 'Biology', 3, teacher_dept_map['Biology']),
            ('BIO401', 'Ecology', 'Biology', 4, teacher_dept_map['Biology']),
            ('BIO501', 'Microbiology', 'Biology', 5, teacher_dept_map['Biology']),
            ('BIO601', 'Physiology', 'Biology', 6, teacher_dept_map['Biology']),
            ('BIO701', 'Evolutionary Biology', 'Biology', 7, teacher_dept_map['Biology']),
            ('BIO801', 'Conservation Biology', 'Biology', 8, teacher_dept_map['Biology']),
            
            # History courses for multiple semesters
            ('HIST101', 'World History', 'History', 1, teacher_dept_map['History']),
            ('HIST201', 'Modern History', 'History', 2, teacher_dept_map['History']),
            ('HIST301', 'Ancient Civilizations', 'History', 3, teacher_dept_map['History']),
            ('HIST401', 'Medieval History', 'History', 4, teacher_dept_map['History']),
            ('HIST501', 'Renaissance History', 'History', 5, teacher_dept_map['History']),
            ('HIST601', 'Colonial History', 'History', 6, teacher_dept_map['History']),
            ('HIST701', 'Contemporary History', 'History', 7, teacher_dept_map['History']),
            ('HIST801', 'Historiography', 'History', 8, teacher_dept_map['History'])
        ]
        
        cursor.executemany("""
            INSERT IGNORE INTO courses 
            (course_code, course_name, department, semester, teacher_id)
            VALUES (%s, %s, %s, %s, %s)
        """, all_courses)

        # Only add the 4 specific students (no random generation)
        initial_students = [
            ('S001', 'Alice Johnson', 'alice.j@example.com', 'Computer Science', 3, 'A', bcrypt.generate_password_hash('student123').decode('utf-8')),
            ('S002', 'Bob Williams', 'bob.w@example.com', 'Computer Science', 3, 'A', bcrypt.generate_password_hash('student456').decode('utf-8')),
            ('S003', 'Carol Davis', 'carol.d@example.com', 'Mathematics', 2, 'B', bcrypt.generate_password_hash('student789').decode('utf-8')),
            ('S004', 'David Miller', 'david.m@example.com', 'Physics', 4, 'A', bcrypt.generate_password_hash('student101').decode('utf-8'))
        ]
        
        cursor.executemany("""
            INSERT IGNORE INTO students 
            (student_id, name, email, department, semester, section, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, initial_students)

        # Create attendance records only for the 4 specific students
        cursor.execute("SELECT id, department, semester FROM students")
        students = cursor.fetchall()
        
        cursor.execute("SELECT id, department, semester FROM courses")
        courses = cursor.fetchall()

        attendance_records = []
        today = date.today()
        
        for student_id, student_dept, student_sem in students:
            for course_id, course_dept, course_sem in courses:
                if student_dept == course_dept and student_sem == course_sem:
                    # Use the teacher for this department for marking attendance
                    teacher_id = teacher_dept_map[student_dept]
                    for i in range(5):
                        record_date = today - timedelta(days=i)
                        status = 'present' if i % 3 != 0 else 'absent'
                        attendance_records.append((
                            student_id,
                            course_id,
                            record_date,
                            status,
                            teacher_id,
                            'Regular class'
                        ))

        # Insert attendance records
        cursor.executemany("""
            INSERT IGNORE INTO attendance 
            (student_id, course_id, date, status, marked_by, remarks)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, attendance_records)
        conn.commit()

        # Create marks only for the 4 specific students
        marks_records = []
        
        for student_id, student_dept, student_sem in students:
            for course_id, course_dept, course_sem in courses:
                if student_dept == course_dept and student_sem == course_sem:
                    # Generate specific marks instead of random
                    iat1 = 25.0  # marks out of 30
                    iat2 = 27.0  # marks out of 30
                    assignment1 = 12.0  # marks out of 20
                    assignment2 = 13.0  # marks out of 20
                    
                    marks_records.append((
                        student_id,
                        course_id,
                        iat1,
                        iat2,
                        assignment1,
                        assignment2
                    ))

        # Insert marks records
        cursor.executemany("""
            INSERT IGNORE INTO marks 
            (student_id, course_id, iat1_marks, iat2_marks, assignment1_marks, assignment2_marks)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, marks_records)
        conn.commit()

        print("Sample data inserted successfully!")

    except Exception as e:
        print(f"Error inserting sample data: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()
    insert_sample_data()