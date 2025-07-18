import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import json
import base64
import tempfile
import pdfkit

# Initialize session_state
if 'report_elements' not in st.session_state:
    st.session_state.report_elements = []

st.set_page_config(layout="wide")
st.title("Report Builder")

# Step 1: Title, description, logo
st.sidebar.header("Report Details")
report_title = st.sidebar.text_input("Report Title")
report_desc = st.sidebar.text_area("Report Description")
logo_file = st.sidebar.file_uploader("Upload Company Logo", type=["png", "jpg"])

# Step 2: SQL query and DB connection
st.sidebar.header("Connection details")
host = st.sidebar.text_input("Host", value="localhost")
dbname = st.sidebar.text_input("Database", value="mydb")
user = st.sidebar.text_input("User", value="postgres")
password = st.sidebar.text_input("Password", type="password")
port = st.sidebar.text_input("Port", value="5432")

query = st.text_area("Enter SQL query")
df = pd.DataFrame()

if st.button("Execute Query"):
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
        st.success("Data retrieved successfully")
        st.dataframe(df, use_container_width=True)
        conn.close()
    except Exception as e:
        st.error(f"Error: {e}")

# Add calculated column
if not df.empty:
    st.subheader("Add Calculated Column")
    col1 = st.selectbox("Column 1", df.columns)
    col2 = st.selectbox("Column 2", df.columns, index=1)
    operation = st.selectbox("Operation", ["+", "-", "*", "/"])
    new_col_name = st.text_input("New Column Name", "Result")
    if st.button("Add Column"):
        try:
            if operation == "+":
                df[new_col_name] = df[col1] + df[col2]
            elif operation == "-":
                df[new_col_name] = df[col1] - df[col2]
            elif operation == "*":
                df[new_col_name] = df[col1] * df[col2]
            elif operation == "/":
                df[new_col_name] = df[col1] / df[col2]
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error adding column: {e}")

# Step 3: Add report elements
st.subheader("Report Constructor")
col1, col2 = st.columns(2)
if col1.button("Add Table"):
    st.session_state["add_table"] = True
if col2.button("Add Chart"):
    st.session_state["add_chart"] = True

# Step 4: Table configuration
if st.session_state.get("add_table") and not df.empty:
    st.subheader("Configure Table")
    selected_columns = st.multiselect("Select Columns", df.columns.tolist(), default=df.columns.tolist())
    table_df = df[selected_columns]
    st.dataframe(table_df, use_container_width=True)
    if st.button("Add Table to Report"):
        st.session_state.report_elements.append({"type": "table", "data": table_df.to_dict(), "columns": selected_columns})
        st.session_state["add_table"] = False

# Step 5: Chart configuration
if st.session_state.get("add_chart") and not df.empty:
    st.subheader("Configure Chart")
    x_col = st.selectbox("X Axis", df.columns)
    y_col = st.selectbox("Y Axis", df.select_dtypes(include=['number']).columns)
    chart_type = st.selectbox("Chart Type", ["bar", "line", "scatter"])
    fig = None
    if chart_type == "bar":
        fig = px.bar(df, x=x_col, y=y_col)
    elif chart_type == "line":
        fig = px.line(df, x=x_col, y=y_col)
    elif chart_type == "scatter":
        fig = px.scatter(df, x=x_col, y=y_col)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        if st.button("Add Chart to Report"):
            st.session_state.report_elements.append({"type": "chart", "x": x_col, "y": y_col, "chart_type": chart_type})
            st.session_state["add_chart"] = False

# Step 6: Display report elements
st.subheader("Export report")
for el in st.session_state.report_elements:
    if el["type"] == "table":
        st.dataframe(pd.DataFrame(el["data"]), use_container_width=True)
    elif el["type"] == "chart":
        fig = None
        if el["chart_type"] == "bar":
            fig = px.bar(df, x=el["x"], y=el["y"])
        elif el["chart_type"] == "line":
            fig = px.line(df, x=el["x"], y=el["y"])
        elif el["chart_type"] == "scatter":
            fig = px.scatter(df, x=el["x"], y=el["y"])
        if fig:
            st.plotly_chart(fig, use_container_width=True)

# Step 7: Generate PDF
if st.button("Generate PDF"):
    html = f"""
    <html><head><style>
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid black; padding: 5px; word-break: break-word; max-width: 200px; }}
    </style></head><body>
    <h1 style='text-align:center;'>{report_title}</h1>
    <p style='text-align:center;font-size:12pt'>{report_desc}</p>
    """
    if logo_file:
        b64_logo = base64.b64encode(logo_file.read()).decode("utf-8")
        html += f"<div style='text-align:center'><img src='data:image/png;base64,{b64_logo}' width='100'/></div><hr>"

    for el in st.session_state.report_elements:
        if el["type"] == "table":
            df_html = pd.DataFrame(el["data"]).to_html(index=False, escape=False)
            html += df_html + "<br><br>"
        elif el["type"] == "chart":
            fig = None
            if el["chart_type"] == "bar":
                fig = px.bar(df, x=el["x"], y=el["y"])
            elif el["chart_type"] == "line":
                fig = px.line(df, x=el["x"], y=el["y"])
            elif el["chart_type"] == "scatter":
                fig = px.scatter(df, x=el["x"], y=el["y"])
            if fig:
                tmpfile = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                fig.write_image(tmpfile.name)
                with open(tmpfile.name, "rb") as image_file:
                    b64 = base64.b64encode(image_file.read()).decode()
                    html += f"<img src='data:image/png;base64,{b64}' width='100%'><br><br>"

    html += "</body></html>"
    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdfkit.from_string(html, pdf_file.name)
    with open(pdf_file.name, "rb") as f:
        st.download_button("Download PDF", f.read(), file_name="report.pdf", mime="application/pdf")

# Step 8: Import/Export JSON
st.sidebar.header("Import/Export Report")
report_json = {
    "title": report_title,
    "description": report_desc,
    "elements": st.session_state.report_elements
}
st.sidebar.download_button("💾 Download JSON", data=json.dumps(report_json, ensure_ascii=False, indent=2), file_name="report.json")

uploaded_json = st.sidebar.file_uploader("📁 Upload JSON", type="json")
if uploaded_json:
    content = json.load(uploaded_json)
    st.session_state.report_elements = content.get("elements", [])
    st.success("Report loaded")
