import os
from datetime import datetime
import streamlit as st
from sqlalchemy import text

# Streamlit UI Configuration Window
st.set_page_config(page_title="Institute & Graphics Management", layout="wide")

# ==================== CLOUD DATABASE SETUP ====================
# Connects to Supabase using the hidden connection URL string inside your Secrets vault
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"Failed to connect to cloud database. Please verify your Streamlit Secrets string. Error: {e}")

def create_tables():
    """Initializes permanent cloud tables if they do not exist in your Supabase database."""
    try:
        with conn.session as session:
            # PostgreSQL Courses Table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS courses (
                    course_id SERIAL PRIMARY KEY,
                    course_name VARCHAR(255) NOT NULL UNIQUE,
                    duration_months INT NOT NULL,
                    fee NUMERIC NOT NULL,
                    subjects TEXT
                );
            """))
            # PostgreSQL Students Table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(255)
                );
            """))
            # PostgreSQL Enrollments Table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id SERIAL PRIMARY KEY,
                    student_id INT REFERENCES students(student_id) ON DELETE CASCADE,
                    course_id INT REFERENCES courses(course_id) ON DELETE CASCADE,
                    enrollment_date DATE NOT NULL,
                    status VARCHAR(50) DEFAULT 'Active'
                );
            """))
            # PostgreSQL Graphics Orders Table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS graphics_orders (
                    order_id SERIAL PRIMARY KEY,
                    client_name VARCHAR(255) NOT NULL,
                    client_phone VARCHAR(50) NOT NULL,
                    work_description TEXT NOT NULL,
                    total_amount NUMERIC NOT NULL,
                    paid_amount NUMERIC NOT NULL,
                    order_date DATE NOT NULL,
                    status VARCHAR(50) DEFAULT 'Pending'
                );
            """))
            # PostgreSQL Attendance Table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id SERIAL PRIMARY KEY,
                    student_id INT REFERENCES students(student_id) ON DELETE CASCADE,
                    date DATE NOT NULL,
                    status VARCHAR(50) NOT NULL
                );
            """))
            session.commit()
    except Exception as e:
        st.error(f"Schema Initialization Error: {e}")

def execute_query(query_str, params={}):
    """Safely executes write operations (INSERT, UPDATE, DELETE) on the cloud server."""
    try:
        with conn.session as session:
            session.execute(text(query_str), params)
            session.commit()
        return True
    except Exception as e:
        st.error(f"Cloud DB Write Error: {e}")
        return False

def fetch_query(query_str, params={}):
    """Safely reads records from your permanent cloud storage tables."""
    try:
        with conn.session as session:
            result = session.execute(text(query_str), params)
            return result.fetchall()
    except Exception as e:
        st.error(f"Cloud DB Read Error: {e}")
        return []

# Run Database Schema Checks
create_tables()

st.title("🎓 Institute & Graphics Management System (Cloud Cloud)")

# Sidebar Navigation Control Setup
menu = ["Course Administration", "Student Management", "Commercial Graphics Work"]
choice = st.sidebar.selectbox("Navigate Modules", menu)

# ==================== MODULE 1: COURSE ADMINISTRATION ====================
if choice == "Course Administration":
    st.header("📚 Course Administration")
    tab1, tab2, tab3 = st.tabs(["Add New Course", "View Existing Courses", "Update Course Subjects"])
    
    with tab1:
        with st.form("add_course_form"):
            name = st.text_input("Course Name")
            subjects = st.text_input("Course Subjects (Separate with commas)")
            duration = st.number_input("Duration (Months)", min_value=1, step=1)
            fee = st.number_input("Total Fee (PKR)", min_value=0.0, step=100.0)
            submitted = st.form_submit_button("Add Course")
            if submitted and name:
                q = "INSERT INTO courses (course_name, duration_months, fee, subjects) VALUES (:name, :duration, :fee, :subjects);"
                if execute_query(q, {"name": name, "duration": duration, "fee": fee, "subjects": subjects}):
                    st.success(f"Course '{name}' permanently saved to cloud!")
                    st.rerun()

    with tab2:
        courses = fetch_query("SELECT * FROM courses ORDER BY course_id ASC;")
        if courses:
            st.table([{"ID": c[0], "Course Name": c[1], "Subjects": c[4] if c[4] else "N/A", "Duration (Months)": c[2], "Fee (PKR)": float(c[3])} for c in courses])
        else:
            st.info("No cloud courses available.")

    with tab3:
        st.subheader("📝 Add/Update Subjects for Existing Courses")
        existing_courses = fetch_query("SELECT course_id, course_name FROM courses;")
        if not existing_courses:
            st.info("No courses available to update.")
        else:
            with st.form("update_subjects_form"):
                course_mapping = {c[1]: c[0] for c in existing_courses}
                selected_course_name = st.selectbox("Select Course to Update", list(course_mapping.keys()))
                new_subjects = st.text_input("Type Subjects (e.g., Photoshop, Illustrator)")
                submit_update = st.form_submit_button("Update Subjects")
                if submit_update and new_subjects:
                    target_id = course_mapping[selected_course_name]
                    q = "UPDATE courses SET subjects = :subjects WHERE course_id = :id;"
                    if execute_query(q, {"subjects": new_subjects, "id": target_id}):
                        st.success(f"Updated subjects for '{selected_course_name}'!")
                        st.rerun()

# ==================== MODULE 2: STUDENT MANAGEMENT ====================
elif choice == "Student Management":
    st.header("👥 Student Management")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Register Student", "Enroll Student", "Enrollment Roster", "Take Attendance", "Attendance Log"])
    
    with tab1:
        with st.form("register_student_form"):
            s_name = st.text_input("Student Full Name")
            s_phone = st.text_input("Contact Phone Number")
            s_email = st.text_input("Email Address (Optional)")
            submitted = st.form_submit_button("Register Student")
            if submitted and s_name and s_phone:
                q = "INSERT INTO students (name, phone, email) VALUES (:name, :phone, :email);"
                if execute_query(q, {"name": s_name, "phone": s_phone, "email": s_email}):
                    st.success(f"Student '{s_name}' registered successfully!")
                    st.rerun()

    with tab2:
        courses = fetch_query("SELECT course_id, course_name FROM courses;")
        students = fetch_query("SELECT student_id, name FROM students;")
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
                    today_str = datetime.today().date()
                    q = "INSERT INTO enrollments (student_id, course_id, enrollment_date) VALUES (:s_id, :c_id, :date);"
                    if execute_query(q, {"s_id": student_options[selected_student], "c_id": course_options[selected_course], "date": today_str}):
                        st.success(f"Enrolled successfully!")
                        st.rerun()

    with tab3:
        q = """
            SELECT e.enrollment_id, s.name, c.course_name, e.enrollment_date, e.status
            FROM enrollments e
            JOIN students s ON e.student_id = s.student_id
            JOIN courses c ON e.course_id = c.course_id;
        """
        records = fetch_query(q)
        if records:
            st.table([{"ID": r[0], "Student Name": r[1], "Course Enrolled": r[2], "Date": str(r[3]), "Status": r[4]} for r in records])
        else:
            st.info("No active cloud enrollments found.")

    with tab4:
        st.subheader("📝 Daily Attendance Sheet")
        today_date = datetime.today().date()
        st.info(f"Marking attendance for today: **{today_date}**")
        all_students = fetch_query("SELECT student_id, name FROM students;")
        if not all_students:
            st.info("No students registered yet.")
        else:
            with st.form("attendance_form"):
                attendance_data = {}
                for s in all_students:
                    is_present = st.checkbox(f"{s[1]} (ID: {s[0]})", value=True)
                    attendance_data[s[0]] = "Present" if is_present else "Absent"
                submit_attendance = st.form_submit_button("Save Attendance")
                if submit_attendance:
                    success = True
                    for student_id, status in attendance_data.items():
                        execute_query("DELETE FROM attendance WHERE student_id = :s_id AND date = :date;", {"s_id": student_id, "date": today_date})
                        q = "INSERT INTO attendance (student_id, date, status) VALUES (:s_id, :date, :status);"
                        if not execute_query(q, {"s_id": student_id, "date": today_date, "status": status}):
                            success = False
                    if success:
                        st.success("Attendance updated successfully on cloud!")
                        st.rerun()

    with tab5:
        st.subheader("📊 Historical Attendance Records")
        q = """
            SELECT a.date, s.name, a.status 
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            ORDER BY a.date DESC, s.name ASC;
        """
        logs = fetch_query(q)
        if logs:
            st.table([{"Date": str(l[0]), "Student Name": l[1], "Attendance Status": l[2]} for l in logs])
        else:
            st.info("No attendance records found.")

# ==================== MODULE 3: COMMERCIAL GRAPHICS WORK ====================
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
                today_str = datetime.today().date()
                status = "Completed" if paid >= total else "Pending"
                q = """
                    INSERT INTO graphics_orders (client_name, client_phone, work_description, total_amount, paid_amount, order_date, status)
                    VALUES (:client, :phone, :desc, :total, :paid, :date, :status);
                """
                if execute_query(q, {"client": client, "phone": phone, "desc": desc, "total": total, "paid": paid, "date": today_str, "status": status}):
                    st.success(f"Graphics order for '{client}' logged permanently!")
                    st.rerun()

    with tab2:
        orders = fetch_query("SELECT * FROM graphics_orders ORDER BY order_id DESC;")
        if orders:
            st.table([{"ID": o[0], "Client": o[1], "Description": o[3], "Total": float(o[4]), "Paid": float(o[5]), "Balance": float(o[4]-o[5]), "Status": o[7]} for o in orders])
        else:
            st.info("No graphics orders recorded yet.")
