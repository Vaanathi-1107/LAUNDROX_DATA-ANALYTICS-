import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import smtplib
import ssl
import hashlib
import secrets
import uuid
import json

from datetime import datetime
from email.message import EmailMessage
from dotenv import dotenv_values


# =====================================================
# 1. PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="LAUNDROX",
    page_icon="🧺",
    layout="wide"
)


# =====================================================
# 2. CONFIGURATION
# =====================================================

ENV = dotenv_values(".env")

SMTP_EMAIL = ENV.get("SMTP_EMAIL")
SMTP_APP_PASSWORD = ENV.get("SMTP_APP_PASSWORD")
SMTP_HOST = ENV.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(ENV.get("SMTP_PORT", 587))

ORDER_FILE = "laundrox_orders.csv"
CUSTOMER_FILE = "laundrox_customers.csv"
DATASET_FILE = "Laundry_Customer_Cleaned.csv"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

STATUSES = [
    "Received",
    "Washing",
    "Drying",
    "Ironing",
    "Ready",
    "Delivered"
]

CLOTH_OPTIONS = [
    "Shirt",
    "T-Shirt",
    "Pant",
    "Jeans",
    "Saree",
    "Chudithar",
    "Bedsheet",
    "Towel",
    "Jacket",
    "Other"
]

SERVICE_PRICES = {
    "Wash": 50,
    "Wash & Iron": 80,
    "Dry Cleaning": 150,
    "Ironing": 40
}

EMAIL_COLUMNS = {
    "Order Created": "Created_Email",
    "Received": "Received_Email",
    "Washing": "Washing_Email",
    "Drying": "Drying_Email",
    "Ironing": "Ironing_Email",
    "Ready": "Ready_Email",
    "Delivered": "Delivered_Email"
}

ORDER_COLUMNS = [
    "Order_ID",
    "Customer_Name",
    "Email",
    "Phone",
    "Clothes",
    "Total_Quantity",
    "Service",
    "Amount",
    "Status",
    "Created_Date",
    "Updated_Date",
    "Created_Email",
    "Received_Email",
    "Washing_Email",
    "Drying_Email",
    "Ironing_Email",
    "Ready_Email",
    "Delivered_Email"
]

CUSTOMER_COLUMNS = [
    "Name",
    "Email",
    "Phone",
    "Salt",
    "Password"
]


# =====================================================
# 3. BLUE THEME
# =====================================================

st.markdown("""
<style>

.stApp {
    background-color: #f3f6fb;
}

[data-testid="stSidebar"] {
    background-color: #10263d;
}

[data-testid="stSidebar"] * {
    color: white !important;
}

.main .block-container {
    max-width: 1450px;
    padding-top: 2rem;
}

.hero-banner {
    background: linear-gradient(110deg, #10263d, #176d9b);
    color: white;
    padding: 40px;
    border-radius: 18px;
    margin-bottom: 25px;
}

.hero-banner h1 {
    color: white;
    font-size: 38px;
    font-weight: 800;
}

.hero-banner p {
    color: white;
    font-size: 17px;
}

.metric-card {
    background: white;
    border: 1px solid #dce5ef;
    border-radius: 14px;
    padding: 20px;
    min-height: 110px;
}

.metric-label {
    color: #64758b;
    font-size: 15px;
}

.metric-number {
    color: #10263d;
    font-size: 28px;
    font-weight: 800;
}

.service-card {
    background: white;
    border: 1px solid #dce5ef;
    border-radius: 14px;
    padding: 20px;
    min-height: 130px;
}

.service-card h3 {
    color: #263b55;
}

.service-card p {
    color: #176d9b;
    font-size: 24px;
    font-weight: bold;
}

.stButton > button {
    background-color: #176d9b;
    color: white;
    border-radius: 8px;
    border: none;
    font-weight: 600;
}

.stButton > button:hover {
    background-color: #10263d;
    color: white;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# 4. SESSION STATE
# =====================================================

defaults = {
    "customer_logged_in": False,
    "customer_email": "",
    "customer_name": "",
    "customer_phone": "",
    "admin_logged_in": False,
    "main_navigation": "Home",
    "cloth_rows": 1
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =====================================================
# 5. NAVIGATION
# =====================================================

def go_to_page(page):
    st.session_state["pending_page"] = page
    st.rerun()


def customer_logout():
    st.session_state.customer_logged_in = False
    st.session_state.customer_email = ""
    st.session_state.customer_name = ""
    st.session_state.customer_phone = ""
    st.session_state.cloth_rows = 1

    go_to_page("Home")


def admin_logout():
    st.session_state.admin_logged_in = False
    go_to_page("Home")


# =====================================================
# 6. PASSWORD HASHING
# =====================================================

def hash_password(password, salt):

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()


# =====================================================
# 7. CUSTOMER CSV
# =====================================================

def load_customers():

    try:
        df = pd.read_csv(CUSTOMER_FILE)

        for col in CUSTOMER_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        return df[CUSTOMER_COLUMNS]

    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=CUSTOMER_COLUMNS)


def save_customers(df):
    df.to_csv(CUSTOMER_FILE, index=False)


# =====================================================
# 8. ORDER CSV
# =====================================================

def load_orders():

    try:
        df = pd.read_csv(ORDER_FILE)

        for col in ORDER_COLUMNS:
            if col not in df.columns:

                if col.endswith("_Email"):
                    df[col] = "No"
                else:
                    df[col] = ""

        return df[ORDER_COLUMNS]

    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=ORDER_COLUMNS)


def save_orders(df):
    df = df.reindex(columns=ORDER_COLUMNS)
    df.to_csv(ORDER_FILE, index=False)


# =====================================================
# 9. EMAIL NOTIFICATION
# =====================================================

def send_email(to_email, subject, body):

    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        return False

    try:

        message = EmailMessage()
        message["From"] = SMTP_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        context = ssl.create_default_context()

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20
        ) as server:

            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

            server.login(
                SMTP_EMAIL,
                SMTP_APP_PASSWORD
            )

            server.send_message(message)

        return True

    except Exception as error:
        print("Email Error:", error)
        return False


def send_stage_notification(order_id, stage):

    df = load_orders()

    matches = df[
        df["Order_ID"].astype(str) == str(order_id)
    ]

    if matches.empty:
        return False

    index = matches.index[0]

    email_column = EMAIL_COLUMNS.get(stage)

    if not email_column:
        return False

    if str(df.at[index, email_column]) == "Yes":
        return True

    customer_email = str(df.at[index, "Email"])
    customer_name = str(df.at[index, "Customer_Name"])

    subject = f"LAUNDROX Order Update - {order_id}"

    body = f"""
Dear {customer_name},

Your laundry order has been updated.

Order ID: {order_id}

Current Status: {stage}

Thank you for choosing LAUNDROX.

Smart Laundry Management System
"""

    success = send_email(
        customer_email,
        subject,
        body
    )

    if success:
        df.at[index, email_column] = "Yes"
        save_orders(df)

    return success


# =====================================================
# 10. HOME PAGE
# =====================================================

def home_page():

    df = load_orders()

    total_orders = len(df)

    pending = (
        len(df[df["Status"] != "Delivered"])
        if not df.empty else 0
    )

    completed = (
        len(df[df["Status"] == "Delivered"])
        if not df.empty else 0
    )

    revenue = (
        pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).fillna(0).sum()
        if not df.empty else 0
    )

    st.markdown("""
    <div class="hero-banner">
        <h1>Welcome to LAUNDROX 🧺</h1>
        <p>Your Smart Laundry Management System</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.customer_logged_in:

        st.subheader("Get Started")

        c1, c2 = st.columns(2)

        with c1:
            st.button(
                "Register New Customer",
                use_container_width=True,
                on_click=go_to_page,
                args=("Register",)
            )

        with c2:
            st.button(
                "Customer Login",
                use_container_width=True,
                on_click=go_to_page,
                args=("Customer Login",)
            )

    else:

        st.success(
            f"Welcome back, {st.session_state.customer_name}!"
        )

    st.subheader("Order Overview")

    c1, c2, c3, c4 = st.columns(4)

    metrics = [
        (c1, "Total Orders", total_orders),
        (c2, "Pending Orders", pending),
        (c3, "Completed Orders", completed),
        (c4, "Total Revenue", f"₹{revenue:,.2f}")
    ]

    for col, label, value in metrics:

        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-number">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    st.subheader("Our Services")

    cols = st.columns(4)

    for col, (service, price) in zip(
        cols,
        SERVICE_PRICES.items()
    ):

        with col:
            st.markdown(f"""
            <div class="service-card">
                <h3>{service}</h3>
                <p>₹{price}/piece</p>
            </div>
            """, unsafe_allow_html=True)

    st.subheader("Recent Orders")

    if not df.empty:

        st.dataframe(
            df.tail(10).iloc[::-1][[
                "Order_ID",
                "Customer_Name",
                "Total_Quantity",
                "Service",
                "Amount",
                "Status"
            ]],
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No orders available yet.")
        # =====================================================
# 11. REGISTER
# =====================================================

def register_page():

    st.markdown("""
    <div class="hero-banner">
        <h1>Customer Registration</h1>
        <p>Create your LAUNDROX account</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("register_form"):

        name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        phone = st.text_input("Phone Number")

        password = st.text_input(
            "Password",
            type="password"
        )

        confirm = st.text_input(
            "Confirm Password",
            type="password"
        )

        submitted = st.form_submit_button("Create Account")

    if submitted:

        if not all([
            name.strip(),
            email.strip(),
            phone.strip(),
            password,
            confirm
        ]):

            st.error("Please fill all fields.")

        elif "@" not in email or "." not in email:

            st.error("Enter a valid email address.")

        elif password != confirm:

            st.error("Passwords do not match.")

        elif len(password) < 6:

            st.error("Password must contain at least 6 characters.")

        else:

            customers = load_customers()
            email = email.strip().lower()

            existing = customers[
                customers["Email"].astype(str).str.lower() == email
            ]

            if not existing.empty:

                st.error("Email already registered.")

            else:

                salt = secrets.token_hex(16)

                encrypted = hash_password(
                    password,
                    salt
                )

                new_customer = pd.DataFrame([{
                    "Name": name.strip(),
                    "Email": email,
                    "Phone": phone.strip(),
                    "Salt": salt,
                    "Password": encrypted
                }])

                customers = pd.concat(
                    [customers, new_customer],
                    ignore_index=True
                )

                save_customers(customers)

                st.success("Registration successful!")
                st.info("Now login with your registered account.")

    st.divider()

    st.write("Already registered?")

    st.button(
        "Login Here",
        on_click=go_to_page,
        args=("Customer Login",)
    )


# =====================================================
# 12. CUSTOMER LOGIN
# =====================================================

def customer_login_page():

    st.markdown("""
    <div class="hero-banner">
        <h1>Customer Login</h1>
        <p>Welcome back to LAUNDROX</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("customer_login_form"):

        email = st.text_input("Email Address")

        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = st.form_submit_button("Login")

    if submitted:

        customers = load_customers()
        email = email.strip().lower()

        matched = customers[
            customers["Email"].astype(str).str.lower() == email
        ]

        if matched.empty:

            st.error("Account not found. Please register first.")

        else:

            customer = matched.iloc[0]

            entered_password = hash_password(
                password,
                str(customer["Salt"])
            )

            if entered_password == str(customer["Password"]):

                st.session_state.customer_logged_in = True
                st.session_state.customer_email = customer["Email"]
                st.session_state.customer_name = customer["Name"]
                st.session_state.customer_phone = customer["Phone"]

                st.success("Customer login successful!")

                go_to_page("Customer Dashboard")

            else:

                st.error("Incorrect password.")

    st.divider()

    st.write("New customer?")

    st.button(
        "Register Here",
        on_click=go_to_page,
        args=("Register",)
    )


# =====================================================
# 13. CUSTOMER DASHBOARD
# =====================================================

def customer_dashboard():

    st.markdown(f"""
    <div class="hero-banner">
        <h1>Welcome {st.session_state.customer_name}</h1>
        <p>Your Customer Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_orders()

    my_orders = df[
        df["Email"].astype(str).str.lower()
        == st.session_state.customer_email.lower()
    ]

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Orders", len(my_orders))

    c2.metric(
        "Active Orders",
        len(my_orders[my_orders["Status"] != "Delivered"])
    )

    c3.metric(
        "Delivered Orders",
        len(my_orders[my_orders["Status"] == "Delivered"])
    )

    st.subheader("My Orders")

    if my_orders.empty:

        st.info("You have not created any orders yet.")

    else:

        st.dataframe(
            my_orders[[
                "Order_ID",
                "Total_Quantity",
                "Service",
                "Amount",
                "Status",
                "Created_Date"
            ]],
            use_container_width=True,
            hide_index=True
        )


# =====================================================
# 14. NEW ORDER
# =====================================================

def new_order_page():

    st.markdown("""
    <div class="hero-banner">
        <h1>Create New Order</h1>
        <p>Add your laundry items</p>
    </div>
    """, unsafe_allow_html=True)

    st.write("Customer:", st.session_state.customer_name)
    st.write("Email:", st.session_state.customer_email)

    cloth_details = []
    total_quantity = 0

    for i in range(st.session_state.cloth_rows):

        st.subheader(f"Cloth {i + 1}")

        c1, c2 = st.columns(2)

        with c1:

            cloth = st.selectbox(
                "Clothing Type",
                CLOTH_OPTIONS,
                key=f"cloth_{i}"
            )

        with c2:

            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=100,
                value=1,
                key=f"quantity_{i}"
            )

        cloth_details.append({
            "cloth": cloth,
            "quantity": int(quantity)
        })

        total_quantity += int(quantity)

    c1, c2 = st.columns(2)

    with c1:

        st.button(
            "➕ Add Another Cloth",
            on_click=lambda: st.session_state.update(
                cloth_rows=st.session_state.cloth_rows + 1
            )
        )

    with c2:

        if st.button("➖ Remove Last Cloth"):

            if st.session_state.cloth_rows > 1:

                last = st.session_state.cloth_rows - 1

                st.session_state.cloth_rows -= 1

                st.session_state.pop(f"cloth_{last}", None)
                st.session_state.pop(f"quantity_{last}", None)

                st.rerun()

    st.divider()

    service = st.selectbox(
        "Select Laundry Service",
        list(SERVICE_PRICES.keys())
    )

    amount = total_quantity * SERVICE_PRICES[service]

    st.metric("Total Quantity", total_quantity)
    st.metric("Total Amount", f"₹{amount}")

    if st.button("Create Laundry Order", type="primary"):

        df = load_orders()

        order_id = "LX" + uuid.uuid4().hex[:8].upper()

        current_time = datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )

        new_order = {
            "Order_ID": order_id,
            "Customer_Name": st.session_state.customer_name,
            "Email": st.session_state.customer_email,
            "Phone": st.session_state.customer_phone,
            "Clothes": json.dumps(cloth_details),
            "Total_Quantity": total_quantity,
            "Service": service,
            "Amount": amount,
            "Status": "Received",
            "Created_Date": current_time,
            "Updated_Date": current_time,
            "Created_Email": "No",
            "Received_Email": "No",
            "Washing_Email": "No",
            "Drying_Email": "No",
            "Ironing_Email": "No",
            "Ready_Email": "No",
            "Delivered_Email": "No"
        }

        df = pd.concat(
            [df, pd.DataFrame([new_order])],
            ignore_index=True
        )

        save_orders(df)

        st.success("Order created successfully!")

        st.write("Order ID:", order_id)
        st.write("Total Quantity:", total_quantity)
        st.write("Service:", service)
        st.write("Amount:", f"₹{amount}")

        email_sent = send_stage_notification(
            order_id,
            "Order Created"
        )

        if email_sent:
            st.success("Confirmation email sent!")
        else:
            st.warning(
                "Order saved. Email could not be sent. "
                "Please check SMTP settings."
            )

        st.session_state.cloth_rows = 1


# =====================================================
# 15. TRACK ORDER
# =====================================================

def track_order_page():

    st.markdown("""
    <div class="hero-banner">
        <h1>Track My Order</h1>
        <p>Check your laundry status</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_orders()

    my_orders = df[
        df["Email"].astype(str).str.lower()
        == st.session_state.customer_email.lower()
    ]

    if my_orders.empty:

        st.info("No orders found.")
        return

    selected = st.selectbox(
        "Select Order ID",
        my_orders["Order_ID"].astype(str).tolist()
    )

    order = my_orders[
        my_orders["Order_ID"].astype(str) == selected
    ].iloc[0]

    st.subheader(f"Order ID: {selected}")

    st.success(f"Current Status: {order['Status']}")

    st.write("Quantity:", order["Total_Quantity"])
    st.write("Service:", order["Service"])
    st.write("Amount:", f"₹{order['Amount']}")
    st.write("Created:", order["Created_Date"])

    st.subheader("Order Progress")

    current = str(order["Status"])

    for stage in STATUSES:

        if (
            current in STATUSES
            and STATUSES.index(stage) <= STATUSES.index(current)
        ):
            st.success(f"✓ {stage}")
        else:
            st.write(f"○ {stage}")
            # =====================================================
# 16. ADMIN LOGIN
# =====================================================

def admin_login_page():

    st.markdown("""
    <div class="hero-banner">
        <h1>Admin Login</h1>
        <p>LAUNDROX Management Portal</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("admin_login_form"):

        username = st.text_input("Admin Username")

        password = st.text_input(
            "Admin Password",
            type="password"
        )

        submitted = st.form_submit_button("Admin Login")

    if submitted:

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            st.session_state.admin_logged_in = True

            st.success("Admin login successful!")

            st.rerun()

        else:

            st.error("Invalid admin credentials.")


# =====================================================
# 17. ADMIN DASHBOARD
# =====================================================

def admin_dashboard_page():

    if not st.session_state.admin_logged_in:

        admin_login_page()
        return

    st.markdown("""
    <div class="hero-banner">
        <h1>Admin Dashboard</h1>
        <p>Manage all laundry orders</p>
    </div>
    """, unsafe_allow_html=True)

    st.button(
        "Admin Logout",
        on_click=admin_logout
    )

    df = load_orders()

    if df.empty:

        st.info("No orders available.")
        return

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Orders", len(df))

    c2.metric(
        "Pending Orders",
        len(df[df["Status"] != "Delivered"])
    )

    c3.metric(
        "Delivered Orders",
        len(df[df["Status"] == "Delivered"])
    )

    revenue = pd.to_numeric(
        df["Amount"],
        errors="coerce"
    ).fillna(0).sum()

    c4.metric("Revenue", f"₹{revenue:,.2f}")

    st.subheader("All Orders")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Update Order Status")

    order_ids = df["Order_ID"].astype(str).tolist()

    selected = st.selectbox(
        "Select Order",
        order_ids
    )

    index = df[
        df["Order_ID"].astype(str) == selected
    ].index[0]

    current = str(df.at[index, "Status"])

    new_status = st.selectbox(
        "New Status",
        STATUSES,
        index=STATUSES.index(current) if current in STATUSES else 0
    )

    if st.button("Update Status"):

        if current == new_status:

            st.info("Status is already selected.")

        else:

            df.at[index, "Status"] = new_status

            df.at[index, "Updated_Date"] = datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            )

            save_orders(df)

            email_sent = send_stage_notification(
                selected,
                new_status
            )

            if email_sent:
                st.success("Status updated and email sent!")
            else:
                st.warning(
                    "Status updated, but notification email failed."
                )

            st.rerun()

    st.divider()

    st.subheader("Delete Order")

    delete_id = st.selectbox(
        "Select Order to Delete",
        order_ids,
        key="delete_order"
    )

    if st.button("Delete Order"):

        df = df[
            df["Order_ID"].astype(str) != delete_id
        ]

        save_orders(df)

        st.success("Order deleted!")
        st.rerun()

    st.download_button(
        "Download Orders CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="laundrox_orders.csv",
        mime="text/csv"
    )
    # =====================================================
# 18. DATASET DASHBOARD
# =====================================================

def dataset_dashboard_page():

    st.markdown("""
    <div class="hero-banner">
        <h1>📊 Dataset Analysis Dashboard</h1>
        <p>Advanced Laundry Customer Dataset Visualization</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        df = pd.read_csv(DATASET_FILE)

    except FileNotFoundError:
        st.error("Laundry_Customer_Cleaned.csv not found!")
        return

    analysis_df = df.copy()

    for col in analysis_df.columns:

        converted = pd.to_numeric(
            analysis_df[col],
            errors="coerce"
        )

        if converted.notna().sum() >= max(1, int(len(df) * 0.8)):
            analysis_df[col] = converted

    # DATASET OVERVIEW

    st.subheader("Dataset Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Records", f"{len(df):,}")
    c2.metric("Total Columns", len(df.columns))
    c3.metric("Missing Values", int(df.isnull().sum().sum()))
    c4.metric("Duplicate Records", int(df.duplicated().sum()))

    st.divider()

    # DATASET PREVIEW

    st.subheader("📋 Dataset Preview")

    st.dataframe(
        df.head(20),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # COLUMN INFORMATION

    st.subheader("📌 Column Information")

    info = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": analysis_df.dtypes.astype(str).values,
        "Non-Null Values": df.notnull().sum().values,
        "Missing Values": df.isnull().sum().values,
        "Unique Values": df.nunique().values
    })

    st.dataframe(
        info,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # MISSING VALUE ANALYSIS

    st.subheader("Missing Value Analysis")

    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)

    if not missing.empty:

        fig, ax = plt.subplots(figsize=(12, 5))

        missing.plot(
            kind="bar",
            ax=ax,
            color="#176D9B"
        )

        ax.set_title("Missing Values by Column")
        ax.set_xlabel("Columns")
        ax.set_ylabel("Missing Records")
        ax.tick_params(axis="x", rotation=35)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    else:
        st.success("No missing values found in the dataset!")

    st.divider()

    # NUMERIC COLUMN HISTOGRAM

    st.subheader("📊 Numeric Column Histogram")

    numeric_columns = analysis_df.select_dtypes(
        include=np.number
    ).columns.tolist()

    if numeric_columns:

        selected_numeric = st.selectbox(
            "Select numeric column",
            numeric_columns,
            key="dataset_numeric_column"
        )

        values = analysis_df[selected_numeric].dropna()

        if not values.empty:

            fig, ax = plt.subplots(figsize=(13, 5))

            ax.hist(
                values,
                bins=20,
                color="#176D86",
                edgecolor="white"
            )

            ax.set_title(
                f"Distribution of {selected_numeric}",
                fontsize=16
            )

            ax.set_xlabel(selected_numeric)
            ax.set_ylabel("Number of Records")
            ax.grid(axis="y", alpha=0.25)

            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            st.caption(
                f"Minimum: {values.min():,.2f} | "
                f"Maximum: {values.max():,.2f} | "
                f"Average: {values.mean():,.2f}"
            )

    else:
        st.info("No numeric columns available.")

    st.divider()

    # CATEGORY DISTRIBUTION

    st.subheader("📊 Category Distribution")

    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    if categorical_columns:

        selected_category = st.selectbox(
            "Select category",
            categorical_columns,
            key="dataset_category_column"
        )

        category_counts = (
            df[selected_category]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .head(10)
            .sort_values()
        )

        fig, ax = plt.subplots(figsize=(13, 6))

        category_counts.plot(
            kind="barh",
            ax=ax,
            color="#11796F"
        )

        ax.set_title(
            f"Top 10 Categories - {selected_category}",
            fontsize=16
        )

        ax.set_xlabel("Count")
        ax.set_ylabel(selected_category)
        ax.grid(axis="x", alpha=0.25)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    else:
        st.info("No categorical columns available.")

    st.divider()

    # CORRELATION ANALYSIS

    st.subheader("📈 Correlation Analysis")

    if len(numeric_columns) >= 2:

        correlation = analysis_df[numeric_columns].corr()

        fig, ax = plt.subplots(figsize=(11, 7))

        image = ax.imshow(
            correlation,
            cmap="Blues",
            aspect="auto",
            vmin=-1,
            vmax=1
        )

        ax.set_xticks(range(len(correlation.columns)))
        ax.set_yticks(range(len(correlation.columns)))

        ax.set_xticklabels(
            correlation.columns,
            rotation=45,
            ha="right"
        )

        ax.set_yticklabels(correlation.columns)

        ax.set_title("Numeric Feature Correlation")

        fig.colorbar(image, ax=ax, label="Correlation")

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    else:
        st.info("At least two numeric columns are required.")

    st.divider()

    # STATISTICAL SUMMARY

    st.subheader("📋 Statistical Summary")

    if numeric_columns:

        st.dataframe(
            analysis_df[numeric_columns].describe(),
            use_container_width=True
        )

    # DOWNLOAD

    st.download_button(
        "⬇ Download Dataset CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="Laundry_Customer_Analysis.csv",
        mime="text/csv"
    )


# =====================================================
# 19. ORDER ANALYTICS
# =====================================================

def analytics_page():

    st.markdown("""
    <div class="hero-banner">
        <h1>📊 Created Orders Analytics</h1>
        <p>Visual reports based on orders created in LAUNDROX.</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_orders()

    if df.empty:
        st.info("No orders available for analytics.")
        return

    df["Amount"] = pd.to_numeric(
        df["Amount"],
        errors="coerce"
    ).fillna(0)

    df["Total_Quantity"] = pd.to_numeric(
        df["Total_Quantity"],
        errors="coerce"
    ).fillna(0)

    # FILTERS

    col1, col2 = st.columns(2)

    services = sorted(
        df["Service"].dropna().astype(str).unique().tolist()
    )

    statuses = sorted(
        df["Status"].dropna().astype(str).unique().tolist()
    )

    with col1:
        selected_services = st.multiselect(
            "Filter by service",
            services,
            default=services
        )

    with col2:
        selected_statuses = st.multiselect(
            "Filter by status",
            statuses,
            default=statuses
        )

    filtered = df[
        df["Service"].astype(str).isin(selected_services)
        & df["Status"].astype(str).isin(selected_statuses)
    ].copy()

    st.divider()

    if filtered.empty:
        st.warning("No orders match the selected filters.")
        return

    # SUMMARY METRICS

    total_orders = len(filtered)
    total_revenue = filtered["Amount"].sum()

    average_order = (
        total_revenue / total_orders
        if total_orders else 0
    )

    total_quantity = filtered["Total_Quantity"].sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Orders", total_orders)

    c2.metric(
        "Total Revenue",
        f"₹{total_revenue:,.2f}"
    )

    c3.metric(
        "Average Order Value",
        f"₹{average_order:,.2f}"
    )

    c4.metric(
        "Total Quantity",
        f"{int(total_quantity)} pieces"
    )

    st.divider()

    # ORDERS BY SERVICE

    st.subheader("Orders by Service")

    service_counts = filtered["Service"].value_counts()

    fig, ax = plt.subplots(figsize=(12, 5))

    service_counts.plot(
        kind="bar",
        ax=ax,
        color="#176D86"
    )

    ax.set_xlabel("Service")
    ax.set_ylabel("Number of Orders")
    ax.set_title("Orders by Service")

    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.divider()

    # STATUS + REVENUE

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Order Status Distribution")

        status_counts = filtered["Status"].value_counts()

        fig2, ax2 = plt.subplots(figsize=(7, 5))

        ax2.pie(
            status_counts,
            labels=status_counts.index,
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"width": 0.55}
        )

        ax2.set_title("Order Status Distribution")

        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

    with col2:

        st.subheader("Revenue by Service")

        revenue_service = (
            filtered.groupby("Service")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )

        fig3, ax3 = plt.subplots(figsize=(7, 5))

        revenue_service.plot(
            kind="bar",
            ax=ax3,
            color="#11796F"
        )

        ax3.set_ylabel("Revenue (₹)")
        ax3.set_xlabel("Service")
        ax3.set_title("Revenue by Service")

        ax3.tick_params(axis="x", rotation=25)
        ax3.grid(axis="y", alpha=0.25)

        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

    st.divider()

    # DAILY ORDERS TREND

    st.subheader("Daily Orders Trend")

    if "Created_Date" in filtered.columns:

        filtered["Parsed_Date"] = pd.to_datetime(
            filtered["Created_Date"],
            errors="coerce",
            dayfirst=True
        )

        daily_orders = (
            filtered.dropna(subset=["Parsed_Date"])
            .groupby(filtered["Parsed_Date"].dt.date)
            .size()
        )

        if not daily_orders.empty:

            fig4, ax4 = plt.subplots(figsize=(12, 5))

            ax4.plot(
                daily_orders.index.astype(str),
                daily_orders.values,
                marker="o",
                linewidth=2,
                color="#176D9B"
            )

            ax4.set_title("Daily Orders Trend")
            ax4.set_xlabel("Date")
            ax4.set_ylabel("Number of Orders")

            ax4.tick_params(axis="x", rotation=35)
            ax4.grid(alpha=0.25)

            plt.tight_layout()
            st.pyplot(fig4)
            plt.close(fig4)

        else:
            st.info("Date information is not available.")

    st.divider()

    # QUANTITY DISTRIBUTION

    st.subheader("Order Quantity Distribution")

    fig5, ax5 = plt.subplots(figsize=(12, 5))

    ax5.hist(
        filtered["Total_Quantity"],
        bins=10,
        color="#176D86",
        edgecolor="white"
    )

    ax5.set_xlabel("Quantity")
    ax5.set_ylabel("Number of Orders")
    ax5.set_title("Quantity Distribution")

    ax5.grid(axis="y", alpha=0.25)

    plt.tight_layout()
    st.pyplot(fig5)
    plt.close(fig5)

    st.divider()

    # ORDER TABLE

    st.subheader("Created Orders Details")

    st.dataframe(
        filtered[[
            "Order_ID",
            "Customer_Name",
            "Total_Quantity",
            "Service",
            "Amount",
            "Status",
            "Created_Date"
        ]],
        use_container_width=True,
        hide_index=True
    )

    # DOWNLOAD

    st.download_button(
        "⬇ Download Orders Analytics",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="LAUNDROX_Orders_Analytics.csv",
        mime="text/csv"
    )


# =====================================================
# 20. SIDEBAR
# =====================================================

st.sidebar.markdown("""
<h1 style="text-align:center;">🧺 LAUNDROX</h1>
<p style="text-align:center;">Smart Laundry Management</p>
""", unsafe_allow_html=True)

st.sidebar.divider()

if st.session_state.customer_logged_in:

    st.sidebar.success(
        "Customer: " + st.session_state.customer_name
    )

if st.session_state.admin_logged_in:

    st.sidebar.success("Admin Logged In")

navigation = [
    "Home",
    "Register",
    "Customer Login",
    "Customer Dashboard",
    "New Order",
    "Track Order",
    "Dataset Dashboard",
    "Order Analytics",
    "Admin Dashboard"
]

if "pending_page" in st.session_state:
    st.session_state["main_navigation"] = st.session_state.pop("pending_page")

page = st.sidebar.radio(
    "Navigation",
    navigation,
    key="main_navigation"
)

st.sidebar.divider()

if st.session_state.customer_logged_in:

    st.sidebar.button(
        "Customer Logout",
        use_container_width=True,
        on_click=customer_logout
    )

if st.session_state.admin_logged_in:

    st.sidebar.button(
        "Admin Logout",
        use_container_width=True,
        on_click=admin_logout
    )

st.sidebar.caption("LAUNDROX © 2026")


# =====================================================
# 21. PAGE ROUTING
# =====================================================

if page == "Home":

    home_page()


elif page == "Register":

    if not st.session_state.customer_logged_in:
        register_page()
    else:
        st.info("Customer is already logged in.")


elif page == "Customer Login":

    if not st.session_state.customer_logged_in:
        customer_login_page()
    else:
        st.success("Customer already logged in.")
        customer_dashboard()


elif page == "Customer Dashboard":

    if st.session_state.customer_logged_in:
        customer_dashboard()
    else:
        st.warning("Please login as Customer first.")


elif page == "New Order":

    if st.session_state.customer_logged_in:
        new_order_page()
    else:
        st.warning("Please login as Customer first.")


elif page == "Track Order":

    if st.session_state.customer_logged_in:
        track_order_page()
    else:
        st.warning("Please login as Customer first.")


elif page == "Dataset Dashboard":

    dataset_dashboard_page()


elif page == "Order Analytics":

    analytics_page()


elif page == "Admin Dashboard":

    admin_dashboard_page()