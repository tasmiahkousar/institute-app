import os
import sqlite3
from datetime import datetime
import streamlit as st

class DatabaseManager:
    def __init__(self, db_name="institute_management.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL UNIQUE,
                duration_months INTEGER NOT NULL,
                fee REAL NOT NULL
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                course_id INTEGER,
                enrollment_date TEXT NOT NULL,
                status TEXT DEFAULT 'Active',
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS graphics_orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                work_description TEXT NOT NULL,
                total_amount REAL NOT NULL,
                paid_amount REAL NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending'
            );
        """)
        self.conn.commit()

    def execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Database Error: {e}")
            return False

    def fetch_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            st.error(f"Database Error: {e}")
            return []

# Initialize Database
db = DatabaseManager()

# Streamlit UI Setup
st.set_page_config(page_title="Institute & Graphics Management", layout="wide")
st.title("🎓 Institute & Graphics Management System")

# Sidebar navigation
menu = ["Course Administration", "Student Management", "Commercial Graphics Work"]
choice = st.sidebar.selectbox("Navigate Modules", menu)

# ==================== COURSE MANAGEMENT ====================
if choice == "Course Administration":
    st.header("📚 Course Administration")
    
    tab1, tab2 = st.tabs(["Add New Course", "View Existing Courses"])
    
    with tab1:
        with st.form("add_course_form"):
            name = st.text_input("Course Name")
            duration = st.number_input("Duration (Months)", min_value=1, step=1)
            fee = st.number_input("Total Fee (PKR)", min_value=0.0, step=100.0)
            submitted = st.form_submit_button("Add Course")
            if submitted and name:
                query = "INSERT INTO courses (course_name, duration_months, fee) VALUES (?, ?, ?);"
                if db.execute_query(query, (name, duration, fee)):
                    st.success(f"Course '{name}' added successfully!")

    with tab2:
        courses = db.fetch_query("SELECT * FROM courses;")
        if courses:
            st.table([{"ID": c[0], "Course Name": c[1], "Duration (Months)": c[2], "Fee (PKR)": c[3]} for c in courses])
        else:
            st.info("No courses available.")

# ==================== STUDENT MANAGEMENT ====================
elif choice == "Student Management":
    st.header("👥 Student Management")
    
    tab1, tab2, tab3 = st.tabs(["Register Student", "Enroll Student", "Enrollment Roster"])
    
    with tab1:
        with st.form("register_student_form"):
            s_name = st.text_input("Student Full Name")
            s_phone = st.text_input("Contact Phone Number")
            s_email = st.text_input("Email Address (Optional)")
            submitted = st.form_submit_button("Register Student")
            if submitted and s_name and s_phone:
                query = "INSERT INTO students (name, phone, email) VALUES (?, ?, ?);"
                if db.execute_query(query, (s_name, s_phone, s_email)):
                    st.success(f"Student '{s_name}' registered successfully!")

    with tab2:
        courses = db.fetch_query("SELECT course_id, course_name FROM courses;")
        students = db.fetch_query("SELECT student_id, name FROM students;")
        
        if not courses or not students:
            st.warning("Ensure you have registered at least one student and one course first.")
        else:
            with st.form("enroll_form"):
                course_options = {c[1]: c[0] for c in courses}
                student_options = {s[1]: s[0] for s in students}
                
                selected_course = st.selectbox("Select Course", list(course_options.keys()))
                selected_student = st.selectbox("Select Student", list(student_options.keys()))
                submitted = st.form_submit_button("Enroll Student")
                
                if submitted:
                    today_str = datetime.today().strftime('%Y-%m-%d')
                    query = "INSERT INTO enrollments (student_id, course_id, enrollment_date) VALUES (?, ?, ?);"
                    if db.execute_query(query, (student_options[selected_student], course_options[selected_course], today_str)):
                        st.success(f"Enrolled successfully!")

    with tab3:
        query = """
            SELECT e.enrollment_id, s.name, c.course_name, e.enrollment_date, e.status
            FROM enrollments e
            JOIN students s ON e.student_id = s.student_id
            JOIN courses c ON e.course_id = c.course_id;
        """
        records = db.fetch_query(query)
        if records:
            st.table([{"ID": r[0], "Student Name": r[1], "Course Enrolled": r[2], "Date": r[3], "Status": r[4]} for r in records])
        else:
            st.info("No active enrollments found.")

# ==================== GRAPHICS ORDER MANAGEMENT ====================
elif choice == "Commercial Graphics Work":
    st.header("🎨 Graphics Work Order Module")
    
    tab1, tab2 = st.tabs(["Record New Order", "View Receivables Ledger"])
    
    with tab1:
        with st.form("graphics_form"):
            client = st.text_input("Client Name")
            phone = st.text_input("Client Phone")
            desc = st.text_area("Work Description")
            total = st.number_input("Total Invoice Amount (PKR)", min_value=0.0)
            paid = st.number_input("Amount Paid Today (PKR)", min_value=0.0)
            submitted = st.form_submit_button("Log Order")
            
            if submitted and client and phone and desc:
                today_str = datetime.today().strftime('%Y-%m-%d')
                status = "Completed" if paid >= total else "Pending"
                query = """
                    INSERT INTO graphics_orders (client_name, client_phone, work_description, total_amount, paid_amount, order_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """
                if db.execute_query(query, (client, phone, desc, total, paid, today_str, status)):
                    st.success(f"Graphics order for '{client}' logged!")

    with tab2:
        orders = db.fetch_query("SELECT * FROM graphics_orders;")
        if orders:
            st.table([{"ID": o[0], "Client": o[1], "Description": o[3], "Total": o[4], "Paid": o[5], "Balance": o[4]-o[5], "Status": o[7]} for o in orders])
        else:
            st.info("No graphics orders recorded yet.")
