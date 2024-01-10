import streamlit as st
import os
from streamlit_option_menu import option_menu
import ftplib
from ftplib import error_perm
from streamlit_tree_select import tree_select
import qrcode
import config

st.set_page_config(page_title="FTP Upload", layout="wide", page_icon="📂")

st.markdown(
    """
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
        .stProgress > div > div > div > div {
        background-image:linear-gradient(to right, #99ff99, #00ccff);
        }
    </style>
""",
    unsafe_allow_html=True,
)


def progress(percent):
    bar.progress(percent)


with st.sidebar:
    choose = option_menu(
        "FTP UPLOAD APPS",
        ["Connect FTP Server", "Upload Files", "QR Code"],
        icons=["app-indicator", "cloud-arrow-down-fill", "cloud-arrow-up-fill"],
        menu_icon=["cloud-fill"],
        default_index=0,
    )


def get_lastfile():
    files = list(ftp.mlsd())
    files.sort(key=lambda item: item[1]["modify"], reverse=True)
    last_file = files[0][0]
    return last_file


def filter_file_by_extension(files):
    extension = [".png", ".gif", ".jpg", ".jpeg", ".pdf"]
    filtered_file = []
    for file in files:
        if file.endswith(tuple(extension)):
            filtered_file.append(file)
    return filtered_file


def generate_qr_code(data, file):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")
    qrcode_path = f"./temp/{file}.png"
    img.save(qrcode_path)
    return qrcode_path


if choose == "Connect FTP Server":
    c1, c2 = st.columns(2)
    with c1:
        ftp_host = st.text_input("Server IP", config.SERVER_IP)
        ftp_port = st.number_input("Port", 21)
    with c2:
        ftp_username = st.text_input("Username")
        ftp_password = st.text_input("Password", type="password")

    ftp = ftplib.FTP(timeout=30)

    try:
        if (
            len(ftp_host) > 0
            and len(str(ftp_port)) > 0
            and len(ftp_username) > 0
            and len(ftp_password) > 0
        ):
            ftp.connect(ftp_host, int(ftp_port))
            ftp.login(ftp_username, ftp_password)
            if ftp.getwelcome().startswith("220"):
                st.success("Connect FTP Successfully")

                if "ftp_host" not in st.session_state:
                    st.session_state.ftp_host = ftp_host
                if "ftp_port" not in st.session_state:
                    st.session_state.ftp_port = int(ftp_port)
                if "ftp_username" not in st.session_state:
                    st.session_state.ftp_username = ftp_username
                if "ftp_password" not in st.session_state:
                    st.session_state.ftp_password = ftp_password

        elif "ftp_host" not in st.session_state:
            st.error("Connecting failed！")
        elif "ftp_host" in st.session_state:
            st.success("Connected")

    except error_perm:
        if "ftp_host" not in st.session_state:
            st.error("Connecting failed！")


elif choose == "Upload Files":
    if "ftp_host" not in st.session_state:
        st.warning("you are not connected ftp, please connect ftp first.")
    else:
        st.success("Connected")
        directories = [
            config.PDF_DIR,
            config.IMAGES_DIR,
        ]
        default_value = config.PDF_DIR

        ftp_dir = st.selectbox(
            "choose server directory",
            directories,
            index=directories.index(default_value),
        )
        file = st.file_uploader(
            "Upload Files", type=[".png", ".gif", ".jpg", ".jpeg", ".pdf"]
        )
        if file is not None:
            with st.expander("Ready to upload"):
                st.write(file.name)

            ftp = ftplib.FTP(timeout=30)
            ftp.connect(st.session_state.ftp_host, int(st.session_state.ftp_port))
            ftp.login(st.session_state.ftp_username, st.session_state.ftp_password)

            with st.form("FTP Upload"):
                submitted = st.form_submit_button("Upload Now")
                if submitted:
                    ftp.cwd(ftp_dir)
                    bar = st.progress(0)
                    ftp.storbinary(
                        "STOR " + str(file.name),
                        file,
                        blocksize=8192,
                    )
                    progress(100)
                    st.success("Completed!")

                    baseurl = config.BASEURL
                    sub_path = str(ftp.pwd().split(config.URL_PARAMS)[-1])
                    last_file = get_lastfile()
                    img = generate_qr_code(
                        f"{baseurl}{sub_path}/{file.name}", last_file
                    )

                    st.write(f"{baseurl}{sub_path}/{file.name}")
                    st.image(img)

            ftp.quit()


elif choose == "QR Code":
    if "ftp_host" not in st.session_state:
        st.warning("you are not connected ftp, please connect ftp first.")
    else:
        ftp = ftplib.FTP(timeout=30)
        ftp.connect(st.session_state.ftp_host, int(st.session_state.ftp_port))
        ftp.login(st.session_state.ftp_username, st.session_state.ftp_password)
        ftp_dir = st.selectbox(
            "choose server directory",
            (
                config.PDF_DIR,
                config.IMAGES_DIR,
            ),
        )
        ftp.cwd(ftp_dir)

        file_list = filter_file_by_extension(ftp.nlst())

        if file_list is not None:
            file = st.selectbox("List out files", file_list)
            with st.form("Generate QR Code"):
                submitted = st.form_submit_button("Generate")
                if submitted:
                    baseurl = config.BASEURL

                    sub_path = str(ftp.pwd().split(config.URL_PARAMS)[-1])
                    img = generate_qr_code(f"{baseurl}{sub_path}/{file}", file)

                    st.write(file)
                    st.write(f"{baseurl}{sub_path}/{file}")
                    st.image(img)
                    current = os.getcwd()
                    os.remove(f"{current}/temp/{file}.png")
            ftp.quit()
