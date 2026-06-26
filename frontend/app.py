import streamlit as st
import requests
import io
from PIL import Image

st.set_page_config(layout="wide", page_title="Smart Infra Tracking")

API_ROOT = "http://localhost:8000"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "email" not in st.session_state:
    st.session_state.email = ""

if "last_uid" not in st.session_state:
    st.session_state.last_uid = ""


def auth_page():

    st.title("Smart Infrastructure Tracking System")
    st.markdown("Monitor construction progress and detect damages using AI.")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login to your account")

        l_username = st.text_input("Email", key="l_user")
        l_password = st.text_input("Password", type="password", key="l_pass")

        if st.button("Login"):

            try:
                res = requests.post(
                    f"{API_ROOT}/login",
                    json={"username": l_username, "password": l_password},
                    timeout=10
                )

                if res.status_code == 200:
                    st.session_state.authenticated = True
                    st.session_state.email = l_username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

            except Exception as e:
                st.error(f"Backend connection error: {e}")

    with tab2:
        st.subheader("Create a new account")

        r_username = st.text_input("New Email", key="r_user")
        r_password = st.text_input("New Password", type="password", key="r_pass")

        if st.button("Register"):

            try:
                res = requests.post(
                    f"{API_ROOT}/register",
                    json={"username": r_username, "password": r_password},
                    timeout=10
                )

                if res.status_code == 200:
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Email already exists or server error.")

            except Exception as e:
                st.error(f"Backend connection error: {e}")

def main_dashboard():

    # Sidebar
    st.sidebar.title(f"Welcome, {st.session_state.email}")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.email = ""
        st.session_state.last_uid = ""
        st.rerun()

    st.title("Smart Infrastructure Tracking System")

    st.markdown(
        "Upload images of roads/bridges/dams/buildings. "
        "The system estimates progress, detects damages, and forecasts completion time."
    )

    with st.expander("Upload & Analyze", expanded=True):

        uploaded = st.file_uploader(
            "Upload site images",
            type=["jpg", "jpeg", "png"]
        )

        structure = st.selectbox(
            "Structure type",
            ["Building", "Bridge", "Road", "Dam", "Other"]
        )

        col1, col2 = st.columns(2)

        lat = col1.text_input("Latitude (optional)")
        lon = col2.text_input("Longitude (optional)")

        if st.button("Upload and Analyze", type="primary") and uploaded:

            files = {
                "file": (uploaded.name, uploaded.getvalue(), "image/jpeg")
            }

            data = {
                "structure_type": structure,
                "lat": lat,
                "lon": lon
            }

            with st.spinner("Analyzing using AI Processing Layer..."):

                try:
                    r = requests.post(
                        API_ROOT + "/upload/",
                        files=files,
                        data=data,
                        timeout=60
                    )
                    r.raise_for_status()

                    result_data = r.json()

                    st.session_state.last_uid = result_data["upload_id"]

                    st.success(
                        f"Uploaded {result_data['filename']} "
                        f"- Estimated {result_data['percent_complete']}% complete"
                    )

                    resp = requests.get(API_ROOT + result_data.get("annotated"))

                    img = Image.open(io.BytesIO(resp.content))

                    st.image(
                        img,
                        caption=f"Annotated Analysis for Report ID: {result_data['upload_id']}",
                        
                    )

                except Exception as e:
                    st.error(f"Upload failed: {e}")

    st.markdown("---")
    colA, colB = st.columns(2)
    with colA:
        st.header("Site Summary")
        try:
            s = requests.get(API_ROOT + "/history/summary").json()

            st.metric(
                "Average percent complete",
                f"{s.get('average_percent_complete')}%"
            )

            st.metric(
                "Estimated months remaining",
                s.get("months_remaining_estimate")
            )

            st.metric(
                "AI Accuracy Estimate",
                s.get("accuracy_estimate")
            )

        except:
            st.warning("Ensure backend API is running to fetch summary.")

    with colB:

        st.header("Generate PDF Report")

        st.markdown(
            "Generate a comprehensive report including the annotated image and damage graphs."
        )

        uid = st.text_input(
            "Upload ID",
            value=st.session_state.last_uid
        )

        if st.button("Generate Detailed PDF") and uid:

            with st.spinner("Generating report..."):

                try:
                    r = requests.get(API_ROOT + f"/pdf/{uid}")

                    if r.status_code == 200:

                        st.download_button(
                            label="Download PDF Report",
                            data=r.content,
                            file_name=f"Infrastructure_Report_{uid}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )

                    else:
                        st.error("Report generation failed. Invalid Upload ID.")

                except Exception as e:
                    st.error(f"Error connecting to backend: {e}")

if st.session_state.authenticated:
    main_dashboard()
else:
    auth_page()