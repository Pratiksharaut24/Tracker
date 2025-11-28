import streamlit as st
import pandas as pd
import pyodbc
from datetime import date

# -------------------------------------------------------
# SQL CONNECTION
# -------------------------------------------------------
def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=PRATIKSHARAUT\\SQLEXPRESS;"
        "DATABASE=version1;"
        "Trusted_Connection=yes;"
    )

# -------------------------------------------------------
# FETCH INVENTORY (UPDATED FOR NEW COLUMNS)
# -------------------------------------------------------
def fetch_inventory():
    try:
        conn = get_connection()
        query = """
        SELECT 
            Description,
            Ratings,
            CatNo,
            Make,
            MaterialName,
            TotalQuantity,
            Discount,
            ListPrice,
            Total
        FROM Inventory
        """
        df = pd.read_sql(query, conn)
        conn.close()

        df["TotalQuantity"] = pd.to_numeric(df["TotalQuantity"], errors="coerce").fillna(0).astype(int)
        df["ListPrice"] = pd.to_numeric(df["ListPrice"], errors="coerce").fillna(0).astype(float)
        df["Discount"] = pd.to_numeric(df["Discount"], errors="coerce").fillna(0).astype(float)

        return df

    except Exception as e:
        st.error(f"Error fetching inventory: {e}")
        return pd.DataFrame()

# -------------------------------------------------------
# CUSTOMER AUTOCOMPLETE
# -------------------------------------------------------
def fetch_customer_names(prefix):
    try:
        conn = get_connection()
        query = """
        SELECT TOP 10 CustomerName FROM customers
        WHERE CustomerName LIKE ?
        ORDER BY CustomerName
        """
        df = pd.read_sql(query, conn, params=[prefix + "%"])
        conn.close()
        return df["CustomerName"].tolist()
    except:
        return []

def fetch_customer_details(name):
    try:
        conn = get_connection()
        query = """
        SELECT TOP 1 CustomerName, PhoneNo, Address
        FROM customers WHERE CustomerName = ?
        """
        df = pd.read_sql(query, conn, params=[name])
        conn.close()
        if df.empty:
            return None
        return df.iloc[0]
    except:
        return None

# -------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------
st.set_page_config(page_title="Quotation App", layout="wide")

st.title("Quotation")

# -------------------------------------------------------
# CUSTOMER DETAILS
# -------------------------------------------------------
st.subheader("Customer Details")
col1, col2, col3 = st.columns(3)

with col1:
    name_input = st.text_input("Customer Name")
    suggestions = fetch_customer_names(name_input) if name_input else []
    selected_customer = st.selectbox("Select Customer", suggestions if suggestions else [name_input])

    details = fetch_customer_details(selected_customer)
    customer_phone = details["PhoneNo"] if details is not None else ""
    customer_address = details["Address"] if details is not None else ""

with col2:
    phone_no = st.text_input("Phone No.", value=customer_phone)

with col3:
    quotation_no = st.text_input("Quotation No.")

col4, col5 = st.columns(2)

with col4:
    shipping_address = st.text_area("Shipping Address", value=customer_address)

with col5:
    quotation_date = st.date_input("Quotation Date", value=date.today())
    delivery_date = st.date_input("Delivery Date", value=date.today())

st.markdown("---")

# -------------------------------------------------------
# INITIALIZE PRODUCT TABLE  (DISCOUNT REMOVED)
# -------------------------------------------------------
if "product_table" not in st.session_state:
    st.session_state.product_table = pd.DataFrame({
        "Type": pd.Series(dtype="string"),
        "Description": pd.Series(dtype="string"),
        "Ratings": pd.Series(dtype="string"),
        "Cat No": pd.Series(dtype="string"),
        "Make": pd.Series(dtype="string"),
        "MaterialName": pd.Series(dtype="string"),
        "Qty": pd.Series(dtype="int64"),
        "TotalQuantity": pd.Series(dtype="int64"),  # From SQL
        "ListPrice": pd.Series(dtype="float64"),
        "LP Gross Price": pd.Series(dtype="float64")
    })

# -------------------------------------------------------
# SECTION HEADING
# -------------------------------------------------------
st.subheader("Add Section Heading")
manual_section = st.text_input("Enter Section Heading")

def add_section():
    if manual_section.strip() == "":
        st.warning("Enter section name.")
        return

    new_section = {
        "Type": "SECTION",
        "Description": f"--- {manual_section.upper()} ---",
        "Ratings": "",
        "Cat No": "",
        "Make": "",
        "MaterialName": "",
        "Qty": None,
        "TotalQuantity": None,
        "ListPrice": None,
        "LP Gross Price": None
    }

    st.session_state.product_table = pd.concat(
        [st.session_state.product_table, pd.DataFrame([new_section])],
        ignore_index=True
    )

st.button("Add Section Heading", on_click=add_section)

def delete_last_section():
    df = st.session_state.product_table
    sec_rows = df[df["Type"] == "SECTION"].index
    if len(sec_rows) > 0:
        st.session_state.product_table.drop(sec_rows[-1], inplace=True)
        st.session_state.product_table.reset_index(drop=True, inplace=True)

st.button("Delete Last Section Heading", on_click=delete_last_section)

st.markdown("---")

# -------------------------------------------------------
# ADD PRODUCT
# -------------------------------------------------------
st.subheader("Add Product")
inventory_df = fetch_inventory()

product_selected = st.selectbox(
    "Choose Product (from Inventory)",
    inventory_df["Description"].tolist() if not inventory_df.empty else []
)

def add_product():
    if inventory_df.empty:
        st.warning("Inventory empty.")
        return

    row = inventory_df[inventory_df["Description"] == product_selected].iloc[0]

    new_product = {
        "Type": "PRODUCT",
        "Description": row["Description"],
        "Ratings": row["Ratings"],
        "Cat No": row["CatNo"],
        "Make": row["Make"],
        "MaterialName": row["MaterialName"],
        "Qty": 1,
        "TotalQuantity": int(row["TotalQuantity"]),
        "ListPrice": float(row["ListPrice"]),
        "LP Gross Price": 1 * float(row["ListPrice"])
    }

    st.session_state.product_table = pd.concat(
        [st.session_state.product_table, pd.DataFrame([new_product])],
        ignore_index=True
    )

st.button("Add Product Row", on_click=add_product)

st.markdown("---")

# -------------------------------------------------------
# DATA EDITOR TABLE  (DISCOUNT REMOVED)
# -------------------------------------------------------
df = st.session_state.product_table.copy()
df.reset_index(inplace=True)
df.rename(columns={"index": "Sr. No"}, inplace=True)

df["Select"] = False

disabled_mask = df["Type"] == "SECTION"

edited_table = st.data_editor(
    df,
    key="editor_table",
    column_order=["Select"] + list(df.columns[:-1]),
    disabled={
        "Description": disabled_mask,
        "Ratings": disabled_mask,
        "Cat No": disabled_mask,
        "Make": disabled_mask,
        "MaterialName": disabled_mask,
        "TotalQuantity": disabled_mask,
        "ListPrice": disabled_mask,
        "LP Gross Price": disabled_mask,
    },
    num_rows="dynamic"
)

# -------------------------------------------------------
# DELETE SELECTED ROWS
# -------------------------------------------------------
selected_rows = edited_table[edited_table["Select"] == True]["Sr. No"].tolist()

if st.button("Delete Selected Rows"):
    if selected_rows:
        st.session_state.product_table.drop(selected_rows, inplace=True)
        st.session_state.product_table.reset_index(drop=True, inplace=True)
        st.success("Selected rows deleted.")
    else:
        st.warning("No rows selected.")

# -------------------------------------------------------
# RECALCULATE LP GROSS PRICE
# -------------------------------------------------------
temp = edited_table.copy()

temp["Qty"] = pd.to_numeric(temp["Qty"], errors="coerce").fillna(0).astype(int)
temp["ListPrice"] = pd.to_numeric(temp["ListPrice"], errors="coerce").fillna(0).astype(float)

temp.loc[temp["Type"] == "PRODUCT", "LP Gross Price"] = (
    temp.loc[temp["Type"] == "PRODUCT", "Qty"] *
    temp.loc[temp["Type"] == "PRODUCT", "ListPrice"]
)

st.session_state.product_table = temp.drop(columns=["Select", "Sr. No"])

# -------------------------------------------------------
# SUMMARY
# -------------------------------------------------------
grand_total = temp[temp["Type"] == "PRODUCT"]["LP Gross Price"].sum()

st.markdown("---")
st.subheader("Quotation Summary")
st.write(f"### Grand Total: ₹ {grand_total:.2f}")

st.download_button(
    "Download CSV",
    st.session_state.product_table.to_csv(index=False),
    file_name=f"quotation_{quotation_no}.csv",
    mime="text/csv"
)
