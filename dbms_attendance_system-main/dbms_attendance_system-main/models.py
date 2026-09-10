from flask_login import UserMixin
from database import get_db_connection

class User(UserMixin):
    def __init__(self, id, user_id, name, email, role):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role

    def get_id(self):
        # Flask-Login needs this to be a string
        return str(self.user_id)

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT id, teacher_id as user_id, name, email, 'teacher' as role 
            FROM teachers WHERE teacher_id = %s
            UNION
            SELECT id, student_id as user_id, name, email, 'student' as role 
            FROM students WHERE student_id = %s
            UNION
            SELECT id, admin_id as user_id, name, email, 'admin' as role 
            FROM admins WHERE admin_id = %s
            """
            cursor.execute(query, (user_id, user_id, user_id))
            
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    user_data['id'],
                    user_data['user_id'],
                    user_data['name'],
                    user_data['email'],
                    user_data['role']
                )
            return None
        except Exception as e:
            print(f"Error in get_by_id: {e}")
            return None
        finally:
            cursor.close()
            conn.close()