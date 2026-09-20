import streamlit as st
import psycopg2
from datetime import datetime
import os

# Page Configuration (Must be at the very top)
st.set_page_config(page_title="Institute & Graphics Portal", layout="wide")

# ==================== DATABASE HELPER FUNCTIONS ====================
def get_db_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

def check_credentials(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role FROM users WHERE username = %s AND password = %s;", 
            (username, password)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        st.error(f"Database Auth Error: {e}")
        return None

def fetch_query(query, params=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return []

def execute_query(query, params=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert named dict params (:key) to psycopg2 %s format if passed
        if isinstance(params, dict):
            for key, val in params.items():
                query = query.replace(f":{key}", "%s")
            cursor.execute(query, list(params.values()))
        else:
            cursor.execute(query, params or ())
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Execution Error: {e}")
        return False

# ==================== SESSION STATE INITIALIZATION ====================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None

# ==================== 1. LOGIN & ACCOUNT MANAGEMENT INTERFACE ====================
if not st.session_state["authenticated"]:
    st.title("🔐 Institute Portal Gateway")
    
    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 Login", "👤 Create Account", "🔄 Reset Password"])
    
    # --- TAB 1: LOGIN ---
    with auth_tab1:
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                role = check_credentials(user, pwd)
                if role:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = role
                    st.session_state["username"] = user
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")

    # --- TAB 2: CREATE ACCOUNT ---
    with auth_tab2:
        with st.form("create_account_form"):
            st.subheader("Create New Portal Account")
            new_user = st.text_input("Choose Username")
            new_pass = st.text_input("Choose Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            user_role = st.selectbox("Account Role", ["admin", "staff", "student"])
            submit_create = st.form_submit_button("Register Account")
            
            if submit_create:
                if not new_user or not new_pass:
                    st.error("Please fill out all fields.")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                else:
                    # Check if username already exists
                    existing = fetch_query("SELECT username FROM users WHERE username = %s;", (new_user,))
                    if existing:
                        st.error("Username already taken. Please choose another.")
                    else:
                        q = "INSERT INTO users (username, password, role) VALUES (:user, :pass, :role);"
                        if execute_query(q, {"user": new_user, "pass": new_pass, "role": user_role}):
                            st.success(f"Account for '{new_user}' created! You can now log in.")

    # --- TAB 3: RESET PASSWORD ---
    with auth_tab3:
        with st.form("reset_password_form"):
            st.subheader("Reset User Password")
            reset_user = st.text_input("Your Username")
            old_pass = st.text_input("Current Password", type="password")
            updated_pass = st.text_input("New Password", type="password")
            confirm_updated_pass = st.text_input("Confirm New Password", type="password")
            submit_reset = st.form_submit_button("Update Password")
            
            if submit_reset:
                if not reset_user or not old_pass or not updated_pass:
                    st.error("Please fill out all fields.")
                elif updated_pass != confirm_updated_pass:
                    st.error("New passwords do not match.")
                else:
                    valid_role = check_credentials(reset_user, old_pass)
                    if not valid_role:
                        st.error("Invalid username or current password.")
                    else:
                        q = "UPDATE users SET password = :pass WHERE username = :user;"
                        if execute_query(q, {"pass": updated_pass, "user": reset_user}):
                            st.success(f"Password updated for '{reset_user}'! You can now log in with your new password.")

# ==================== 2. MAIN APPLICATION INTERFACE ====================
else:
    # Sidebar Navigation & User Info
    st.sidebar.title("📌 Navigation")
    st.sidebar.write(f"Logged in as: **{st.session_state['role'].upper()}** ({st.session_state['username']})")
    
    choice = st.sidebar.radio(
        "Select Module:",
        ["Course Administration", "Student Management", "Commercial Graphics Work"]
    )
    
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["role"] = None
        st.session_state["username"] = None
        st.rerun()

    # -------------------- MODULE 1: COURSE ADMINISTRATION --------------------
    if choice == "Course Administration":
        st.header("🎓 Course Administration")
        
        tab1, tab2, tab3 = st.tabs(["View All Courses", "Add New Course", "Update Subjects"])
        
        # TAB 1: View existing courses
        with tab1:
            st.subheader("📚 Existing Courses List")
            courses = fetch_query("SELECT course_id, course_name, subjects, duration_months, total_fee FROM courses ORDER BY course_id ASC;")
            if courses:
                st.table([
                    {
                        "ID": c[0], 
                        "Course Name": c[1], 
                        "Subjects": c[2] if c[2] else "N/A", 
                        "Duration (Months)": c[3], 
                        "Total Fee (PKR)": float(c[4]) if c[4] else 0.0
                    } 
                    for c in courses
                ])
            else:
                st.info("No courses found in database.")

        # TAB 2: Add a new course
        with tab2:
            st.subheader("➕ Create New Course")
            with st.form("add_course_form"):
                c_name = st.text_input("Course Name")
                c_subjects = st.text_input("Course Subjects (e.g. Graphic Design, Video Editing)")
                c_duration = st.number_input("Duration (Months)", min_value=1, value=1)
                c_fee = st.number_input("Total Fee (PKR)", min_value=0.0, step=500.0)
                submit_course = st.form_submit_button("Add Course")
                
                if submit_course and c_name:
                    q = "INSERT INTO courses (course_name, subjects, duration_months, total_fee) VALUES (:name, :subjects, :duration, :fee);"
                    if execute_query(q, {"name": c_name, "subjects": c_subjects, "duration": c_duration, "fee": c_fee}):
                        st.success(f"Course '{c_name}' created successfully!")
                        st.rerun()

        # TAB 3: Update subjects for existing courses
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

    # -------------------- MODULE 2: STUDENT MANAGEMENT --------------------
    elif choice == "Student Management":
        st.header("👥 Student Management")
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Register Student", "Enroll Student", "Enrollment Roster", "Take Attendance", "Attendance Log"
        ])
        
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
                            st.success("Enrolled successfully!")
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

    # -------------------- MODULE 3: COMMERCIAL GRAPHICS WORK --------------------
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
