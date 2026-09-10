from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import User
from database import get_db_connection, init_db, insert_sample_data
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('login.html')
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT id, teacher_id as user_id, name, email, password, 'teacher' as role 
            FROM teachers WHERE teacher_id = %s
            UNION
            SELECT id, student_id as user_id, name, email, password, 'student' as role 
            FROM students WHERE student_id = %s
            UNION
            SELECT id, admin_id as user_id, name, email, password, 'admin' as role 
            FROM admins WHERE admin_id = %s
            """
            cursor.execute(query, (user_id, user_id, user_id))
            user_data = cursor.fetchone()
            if user_data and bcrypt.check_password_hash(user_data['password'], password):
                user = User(user_data['id'], user_data['user_id'], user_data['name'], user_data['email'], user_data['role'])
                login_user(user)
                if user.role == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
                elif user.role == 'student':
                    return redirect(url_for('student_dashboard'))
                else:
                    return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid credentials', 'error')
        except Exception as e:
            flash(f'An error occurred during login: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    return render_template('admin-dashboard.html')

@app.route('/admin/manage-teachers')
@login_required
def manage_teachers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teachers ORDER BY name")
    teachers = cursor.fetchall()
    for teacher in teachers:
        cursor.execute("""
            SELECT semester FROM teacher_semesters
            WHERE teacher_id = %s
            ORDER BY semester
        """, (teacher['id'],))
        teacher['semesters'] = [s['semester'] for s in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('manage-teachers.html', teachers=teachers)

@app.route('/admin/add-teacher', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        name = request.form['name']
        email = request.form['email']
        department = request.form['department']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        semesters = request.form.getlist('semesters')
        if not semesters:
            flash('Please select at least one semester', 'error')
            return redirect(url_for('add_teacher'))
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('add_teacher'))
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("""
                INSERT INTO teachers (teacher_id, name, email, department, password)
                VALUES (%s, %s, %s, %s, %s)
            """, (teacher_id, name, email, department, hashed_password))
            new_teacher_id = cursor.lastrowid
            for semester in semesters:
                cursor.execute("""
                    INSERT INTO teacher_semesters (teacher_id, semester)
                    VALUES (%s, %s)
                """, (new_teacher_id, semester))
            conn.commit()
            flash('Teacher added successfully!', 'success')
            return redirect(url_for('manage_teachers'))
        except Exception as e:
            conn.rollback()
            flash(f'Error adding teacher: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    return render_template('add-teacher.html')

@app.route('/admin/edit-teacher/<teacher_id>', methods=['GET', 'POST'])
@login_required
def edit_teacher(teacher_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            department = request.form.get('department')
            password = request.form.get('password')
            if password:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                cursor.execute("""
                    UPDATE teachers SET name = %s, email = %s, department = %s, password = %s
                    WHERE teacher_id = %s
                """, (name, email, department, hashed_password, teacher_id))
            else:
                cursor.execute("""
                    UPDATE teachers SET name = %s, email = %s, department = %s
                    WHERE teacher_id = %s
                """, (name, email, department, teacher_id))
            conn.commit()
            flash('Teacher updated successfully', 'success')
            return redirect(url_for('manage_teachers'))
        cursor.execute("SELECT * FROM teachers WHERE teacher_id = %s", (teacher_id,))
        teacher = cursor.fetchone()
        if not teacher:
            flash('Teacher not found', 'error')
            return redirect(url_for('manage_teachers'))
        return render_template('edit-teacher.html', teacher=teacher)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_teachers'))

@app.route('/admin/delete-teacher/<teacher_id>', methods=['POST'])
@login_required
def delete_teacher(teacher_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM teachers WHERE teacher_id = %s", (teacher_id,))
        result = cursor.fetchone()
        if not result:
            flash('Teacher not found', 'error')
            return redirect(url_for('manage_teachers'))
        internal_id = result[0]
        cursor.execute("SELECT id FROM courses WHERE teacher_id = %s", (internal_id,))
        course_ids = [row[0] for row in cursor.fetchall()]
        if course_ids:
            format_strings = ','.join(['%s'] * len(course_ids))
            cursor.execute(f"DELETE FROM attendance WHERE course_id IN ({format_strings})", tuple(course_ids))
            cursor.execute(f"DELETE FROM marks WHERE course_id IN ({format_strings})", tuple(course_ids))
            cursor.execute(f"DELETE FROM courses WHERE id IN ({format_strings})", tuple(course_ids))
        cursor.execute("DELETE FROM attendance WHERE marked_by = %s", (internal_id,))
        cursor.execute("DELETE FROM teachers WHERE id = %s", (internal_id,))
        conn.commit()
        flash('Teacher deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting teacher: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_teachers'))

@app.route('/admin/manage-courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            course_name = request.form.get('course_name')
            course_code = request.form.get('course_code')
            teacher_id = request.form.get('teacher_id')
            department = request.form.get('department')
            semester = request.form.get('semester')
            cursor.execute("""
                INSERT INTO courses (course_name, course_code, teacher_id, department, semester)
                VALUES (%s, %s, %s, %s, %s)
            """, (course_name, course_code, teacher_id, department, semester))
            conn.commit()
            flash('Course added successfully!', 'success')
            return redirect(url_for('manage_courses'))
        cursor.execute("""
            SELECT c.*, t.name as teacher_name 
            FROM courses c
            JOIN teachers t ON c.teacher_id = t.id
            ORDER BY c.department, c.semester, c.course_name
        """)
        courses = cursor.fetchall()
        cursor.execute("SELECT id, name, teacher_id FROM teachers ORDER BY name")
        teachers = cursor.fetchall()
        cursor.execute("SELECT DISTINCT department FROM teachers ORDER BY department")
        departments = [row['department'] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT semester FROM teacher_semesters ORDER BY semester")
        semesters = [row['semester'] for row in cursor.fetchall()]
        return render_template('manage-courses.html', 
                               courses=courses, 
                               teachers=teachers, 
                               departments=departments, 
                               semesters=semesters)
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit-course/<course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            course_name = request.form.get('course_name')
            course_code = request.form.get('course_code')
            teacher_id = request.form.get('teacher_id')
            department = request.form.get('department')
            semester = request.form.get('semester')
            cursor.execute("""
                UPDATE courses 
                SET course_name = %s, course_code = %s, teacher_id = %s, department = %s, semester = %s
                WHERE id = %s
            """, (course_name, course_code, teacher_id, department, semester, course_id))
            conn.commit()
            flash('Course updated successfully', 'success')
            return redirect(url_for('manage_courses'))
        cursor.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
        course = cursor.fetchone()
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('manage_courses'))
        cursor.execute("SELECT id, name FROM teachers ORDER BY name")
        teachers = cursor.fetchall()
        cursor.execute("SELECT DISTINCT department FROM teachers ORDER BY department")
        departments = [row['department'] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT semester FROM teacher_semesters ORDER BY semester")
        semesters = [row['semester'] for row in cursor.fetchall()]
        return render_template('edit-course.html', 
                               course=course, 
                               teachers=teachers, 
                               departments=departments, 
                               semesters=semesters)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_courses'))

@app.route('/admin/delete-course/<course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        conn.start_transaction()
        cursor.execute("DELETE FROM attendance WHERE course_id = %s", (course_id,))
        cursor.execute("DELETE FROM marks WHERE course_id = %s", (course_id,))
        cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))
        conn.commit()
        flash('Course deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting course: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_courses'))

@app.route('/admin/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        email = request.form.get('email')
        department = request.form.get('department')
        semester = request.form.get('semester')
        section = request.form.get('section')
        password = request.form.get('password')
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM students WHERE student_id = %s OR email = %s", (student_id, email))
            if cursor.fetchone():
                flash('Student ID or email already exists', 'error')
                return redirect(url_for('add_student'))
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("""
                INSERT INTO students (student_id, name, email, department, semester, section, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (student_id, name, email, department, semester, section, hashed_password))
            conn.commit()
            flash('Student added successfully', 'success')
            return redirect(url_for('manage_students'))
        except Exception as e:
            flash(f'Error adding student: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT department FROM teachers")
    departments = [row['department'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('add-student.html', departments=departments)

@app.route('/admin/manage-students')
@login_required
def manage_students():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students ORDER BY name")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('manage-students.html', students=students)

@app.route('/admin/edit-student/<student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            department = request.form.get('department')
            semester = request.form.get('semester')
            section = request.form.get('section')
            password = request.form.get('password')
            if password:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                cursor.execute("""
                    UPDATE students SET name = %s, email = %s, department = %s, 
                    semester = %s, section = %s, password = %s
                    WHERE student_id = %s
                """, (name, email, department, semester, section, hashed_password, student_id))
            else:
                cursor.execute("""
                    UPDATE students SET name = %s, email = %s, department = %s, 
                    semester = %s, section = %s
                    WHERE student_id = %s
                """, (name, email, department, semester, section, student_id))
            conn.commit()
            flash('Student updated successfully', 'success')
            return redirect(url_for('manage_students'))
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            flash('Student not found', 'error')
            return redirect(url_for('manage_students'))
        cursor.execute("SELECT DISTINCT department FROM teachers")
        departments = [row['department'] for row in cursor.fetchall()]
        return render_template('edit-student.html', student=student, departments=departments)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_students'))

@app.route('/admin/delete-student/<student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM students WHERE student_id = %s", (student_id,))
        result = cursor.fetchone()
        if not result:
            flash('Student not found', 'error')
            return redirect(url_for('manage_students'))
        internal_id = result[0]
        cursor.execute("DELETE FROM attendance WHERE student_id = %s", (internal_id,))
        cursor.execute("DELETE FROM students WHERE id = %s", (internal_id,))
        conn.commit()
        flash('Student deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_students'))

@app.route('/teacher-dashboard')
@login_required
def teacher_dashboard():
    if not hasattr(current_user, 'role') or current_user.role != 'teacher':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM courses 
            WHERE teacher_id = (
                SELECT id FROM teachers 
                WHERE teacher_id = %s
            )
        """, (current_user.user_id,))
        courses = cursor.fetchall()
        return render_template('teacher-dashboard.html', courses=courses)
    except Exception as e:
        flash(f'Error retrieving data: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('login'))

@app.route('/take-attendance/<course_id>', methods=['GET', 'POST'])
@login_required
def take_attendance(course_id):
    if not hasattr(current_user, 'role') or current_user.role != 'teacher':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*, t.id as teacher_id 
            FROM courses c
            JOIN teachers t ON c.teacher_id = t.id
            WHERE c.id = %s AND t.teacher_id = %s
        """, (course_id, current_user.user_id))
        course = cursor.fetchone()
        if not course:
            flash('Course not found or unauthorized', 'error')
            return redirect(url_for('teacher_dashboard'))
        if request.method == 'POST':
            date = request.form.get('date')
            attendance_data = request.form.getlist('attendance[]')
            student_ids = request.form.getlist('student_id[]')
            remarks = request.form.getlist('remarks[]')
            cursor.execute("""
                DELETE FROM attendance 
                WHERE course_id = %s AND date = %s
            """, (course_id, date))
            for student_id, status, remark in zip(student_ids, attendance_data, remarks):
                cursor.execute("""
                    INSERT INTO attendance 
                    (student_id, course_id, date, status, marked_by, remarks)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (student_id, course_id, date, status, course['teacher_id'], remark))
            conn.commit()
            flash('Attendance recorded successfully', 'success')
            return redirect(url_for('view_attendance', course_id=course_id))
        cursor.execute("""
            SELECT s.* 
            FROM students s
            WHERE s.department = %s AND s.semester = %s
            ORDER BY s.name
        """, (course['department'], course['semester']))
        students = cursor.fetchall()
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT student_id, status, remarks
            FROM attendance
            WHERE course_id = %s AND date = %s
        """, (course_id, today))
        present_students = []
        attendance_remarks = {}
        for row in cursor.fetchall():
            if row['status'] == 'present':
                present_students.append(row['student_id'])
            attendance_remarks[row['student_id']] = row['remarks']
        return render_template('take-attendance.html', 
                               course=course, 
                               students=students, 
                               today=today,
                               present_students=present_students,
                               attendance_remarks=attendance_remarks)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/view-attendance/<course_id>')
@login_required
def view_attendance(course_id):
    if not hasattr(current_user, 'role') or current_user.role != 'teacher':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*, t.id as teacher_id 
            FROM courses c
            JOIN teachers t ON c.teacher_id = t.id
            WHERE c.id = %s AND t.teacher_id = %s
        """, (course_id, current_user.user_id))
        course = cursor.fetchone()
        if not course:
            flash('Course not found or unauthorized', 'error')
            return redirect(url_for('teacher_dashboard'))
        cursor.execute("""
            SELECT 
                s.name as student_name,
                s.student_id,
                a.date,
                a.status,
                a.remarks
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.course_id = %s
            ORDER BY a.date DESC, s.name
        """, (course_id,))
        attendance_records = cursor.fetchall()
        return render_template('view-attendance.html', course=course, attendance_records=attendance_records)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/add-marks/<course_id>', methods=['GET', 'POST'])
@login_required
def add_marks(course_id):
    if not hasattr(current_user, 'role') or current_user.role != 'teacher':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*, t.id as teacher_id 
            FROM courses c
            JOIN teachers t ON c.teacher_id = t.id
            WHERE c.id = %s AND t.teacher_id = %s
        """, (course_id, current_user.user_id))
        course = cursor.fetchone()
        if not course:
            flash('Course not found or unauthorized', 'error')
            return redirect(url_for('teacher_dashboard'))
        if request.method == 'POST':
            student_ids = request.form.getlist('student_id[]')
            iat1_marks = request.form.getlist('iat1_marks[]')
            iat2_marks = request.form.getlist('iat2_marks[]')
            assignment1_marks = request.form.getlist('assignment1_marks[]')
            assignment2_marks = request.form.getlist('assignment2_marks[]')
            for idx, student_id in enumerate(student_ids):
                cursor.execute("""
                    INSERT INTO marks 
                    (student_id, course_id, iat1_marks, iat2_marks, assignment1_marks, assignment2_marks)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    iat1_marks = VALUES(iat1_marks),
                    iat2_marks = VALUES(iat2_marks),
                    assignment1_marks = VALUES(assignment1_marks),
                    assignment2_marks = VALUES(assignment2_marks)
                """, (
                    student_id, 
                    course_id, 
                    float(iat1_marks[idx]) if iat1_marks[idx] else 0, 
                    float(iat2_marks[idx]) if iat2_marks[idx] else 0,
                    float(assignment1_marks[idx]) if assignment1_marks[idx] else 0,
                    float(assignment2_marks[idx]) if assignment2_marks[idx] else 0
                ))
            conn.commit()
            flash('Marks updated successfully', 'success')
            return redirect(url_for('view_marks', course_id=course_id))
        cursor.execute("""
            SELECT s.*, m.iat1_marks, m.iat2_marks, m.assignment1_marks, m.assignment2_marks 
            FROM students s
            LEFT JOIN marks m ON s.id = m.student_id AND m.course_id = %s
            WHERE s.department = %s AND s.semester = %s
            ORDER BY s.name
        """, (course_id, course['department'], course['semester']))
        students = cursor.fetchall()
        return render_template('add-marks.html', course=course, students=students)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/view-marks/<course_id>')
@login_required
def view_marks(course_id):
    if not hasattr(current_user, 'role') or current_user.role != 'teacher':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*, t.id as teacher_id 
            FROM courses c
            JOIN teachers t ON c.teacher_id = t.id
            WHERE c.id = %s AND t.teacher_id = %s
        """, (course_id, current_user.user_id))
        course = cursor.fetchone()
        if not course:
            flash('Course not found or unauthorized', 'error')
            return redirect(url_for('teacher_dashboard'))
        cursor.execute("""
            SELECT 
                s.name as student_name,
                s.student_id,
                m.iat1_marks,
                m.iat2_marks,
                m.assignment1_marks,
                m.assignment2_marks,
                (m.iat1_marks/4 + m.iat2_marks/4 + m.assignment1_marks + m.assignment2_marks) as total_marks
            FROM students s
            LEFT JOIN marks m ON s.id = m.student_id AND m.course_id = %s
            WHERE s.department = %s AND s.semester = %s
            ORDER BY s.name
        """, (course_id, course['department'], course['semester']))
        marks_records = cursor.fetchall()
        return render_template('view-marks.html', course=course, marks_records=marks_records)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))
    finally:
        cursor.close()
        conn.close()        

@app.route('/student-dashboard')
@login_required
def student_dashboard():
    if not hasattr(current_user, 'role') or current_user.role != 'student':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM students WHERE id = %s
        """, (current_user.id,))
        student_details = cursor.fetchone()
        overall_present = 0
        overall_absent = 0
        overall_late = 0
        overall_excused = 0
        attendance_summary = []
        marks_data = []
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) AS overall_present,
                SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) AS overall_absent,
                SUM(CASE WHEN status = 'late' THEN 1 ELSE 0 END) AS overall_late,
                SUM(CASE WHEN status = 'excused' THEN 1 ELSE 0 END) AS overall_excused
            FROM attendance
            WHERE student_id = %s
        """, (current_user.id,))
        attendance_result = cursor.fetchone()
        if attendance_result:
            overall_present = attendance_result['overall_present'] or 0
            overall_absent = attendance_result['overall_absent'] or 0
            overall_late = attendance_result['overall_late'] or 0
            overall_excused = attendance_result['overall_excused'] or 0
        cursor.execute("""
            SELECT 
                c.course_name,
                SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS present_count,
                SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absent_count,
                SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS late_count,
                COUNT(*) AS total_classes
            FROM attendance a
            JOIN courses c ON a.course_id = c.id
            WHERE a.student_id = %s
            GROUP BY c.course_name
        """, (current_user.id,))
        attendance_summary = cursor.fetchall()
        cursor.execute("""
            SELECT 
                c.course_name,
                m.iat1_marks,
                m.iat2_marks,
                m.assignment1_marks,
                m.assignment2_marks,
                (m.iat1_marks/4 + m.iat2_marks/4 + m.assignment1_marks + m.assignment2_marks) as total_marks
            FROM marks m
            JOIN courses c ON m.course_id = c.id
            WHERE m.student_id = %s
        """, (current_user.id,))
        marks_data = cursor.fetchall()
        return render_template('student-dashboard.java', 
                               current_user=current_user,
                               student_details=student_details,
                               overall_present=overall_present,
                               overall_absent=overall_absent,
                               overall_late=overall_late,
                               overall_excused=overall_excused,
                               attendance_summary=attendance_summary,
                               marks_data=marks_data)
    except Exception as e:
        flash(f'Error retrieving data: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

if __name__== '__main__':
    init_db()
    insert_sample_data()
    app.run(debug=True)