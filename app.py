import streamlit as st
import uuid
import datetime
import pandas as pd
import db  # Mengimpor modul db.py yang baru

# ---------- Utilities (Fungsi yang tidak berhubungan dengan DB) ----------
def get_current_time():
    """Mendapatkan waktu saat ini dalam format HH:MM:SS."""
    return datetime.datetime.now().strftime("%H:%M:%S")

def get_current_datetime():
    """Mendapatkan tanggal dan waktu saat ini dalam format YYYY-MM-DD HH:MM:SS."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def determine_attendance_status(current_time, jam_masuk, jam_pulang):
    """Menentukan status absensi (Masuk/Pulang) berdasarkan jam."""
    current = datetime.datetime.strptime(current_time, "%H:%M:%S").time()
    masuk = datetime.datetime.strptime(jam_masuk, "%H:%M:%S").time()
    pulang = datetime.datetime.strptime(jam_pulang, "%H:%M:%S").time()

    if current <= masuk or (current > masuk and current < pulang):
        return "Masuk"
    else: # current >= pulang
        return "Pulang"

def determine_late_status(current_time, jam_masuk):
    """Menentukan status keterlambatan."""
    current = datetime.datetime.strptime(current_time, "%H:%M:%S").time()
    masuk = datetime.datetime.strptime(jam_masuk, "%H:%M:%S").time()
    return "Terlambat" if current > masuk else "Tidak Terlambat"

# ---------- Konfigurasi Halaman & Session State ----------
st.set_page_config(page_title="Sistem Absensi Mahasiswa", layout="wide")

if "role" not in st.session_state:
    st.session_state.role = None
if "user_info" not in st.session_state:
    st.session_state.user_info = {}

# ---------- Halaman Login ----------
if st.session_state.role is None:
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; margin-bottom: 30px; color: white;">
        <h1 style="margin: 0; font-size: 2.5em; font-weight: bold;">🎓 Sistem Absensi Mahasiswa (Supabase)</h1>
        <p style="margin: 10px 0 0 0; font-size: 1.2em;">Digital Attendance Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["👨‍🎓 Login Mahasiswa", "👨‍💼 Login Admin"])
        with tab1:
            with st.form("mahasiswa_login_form"):
                nim = st.text_input("NIM", placeholder="Masukkan NIM Anda")
                password = st.text_input("Password", type="password", placeholder="Masukkan password")
                if st.form_submit_button("🚀 Masuk sebagai Mahasiswa", type="primary", use_container_width=True):
                    user_data = db.validate_mahasiswa(nim.strip(), password)
                    if user_data:
                        st.session_state.role = "mahasiswa"
                        st.session_state.user_info = user_data
                        st.success(f"Selamat datang, {user_data['nama']}!")
                        st.rerun()
                    else:
                        st.error("❌ NIM atau password salah.")
        
        with tab2:
            with st.form("admin_login_form"):
                username = st.text_input("Username", placeholder="Masukkan username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("🚀 Masuk sebagai Admin", type="primary", use_container_width=True):
                    if db.validate_admin(username.strip(), password.strip()):
                        st.session_state.role = "admin"
                        st.session_state.user_info = {"username": username.strip()}
                        st.success("✅ Login berhasil sebagai Admin.")
                        st.rerun()
                    else:
                        st.error("❌ Username/password salah.")

# ---------- Halaman Mahasiswa ----------
elif st.session_state.role == "mahasiswa":
    user_info = st.session_state.user_info
    st.sidebar.title(f"👋 Halo, {user_info['nama']}")
    st.sidebar.markdown(f"**NIM:** {user_info['nim']}\n\n**Jurusan:** {user_info['jurusan']}")
    menu = st.sidebar.radio("Menu", ["🏠 Dashboard", "📸 Absensi", "📊 Riwayat Absensi", "🚪 Logout"])

    if menu == "🏠 Dashboard":
        st.title("📊 Dashboard Mahasiswa")
        
        current_time_str = get_current_time()
        current_date_str = datetime.datetime.now().strftime("%A, %d %B %Y")
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin: 20px 0; color: white;">
            <h1 style="margin: 0; font-size: 3em;">🕐 {current_time_str}</h1>
            <p style="margin: 10px 0 0 0; font-size: 1.2em;">{current_date_str}</p>
        </div>
        """, unsafe_allow_html=True)
        
        jam_settings = db.get_jam_settings()
        st.info(f"⏰ **Jam Masuk:** {jam_settings[0]} | **Jam Pulang:** {jam_settings[1]}")
        
        st.subheader("📈 Status Absensi Hari Ini")
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        df_all = db.fetch_all_records()
        if not df_all.empty:
            df_user_today = df_all[
                (df_all['nim'] == user_info['nim']) &
                (df_all['timestamp'].str.startswith(today_str))
            ]

            if not df_user_today.empty:
                st.success("✅ Anda sudah melakukan absensi hari ini.")
                for _, row in df_user_today.iterrows():
                    if row['late_status'] == "Terlambat":
                        st.warning(f" - **{row['status']}** ({row['late_status']}) pada {row['timestamp']}")
                    else:
                        st.info(f" - **{row['status']}** ({row['late_status']}) pada {row['timestamp']}")
            else:
                st.warning("⚠️ Anda belum melakukan absensi hari ini.")
        else:
            st.warning("⚠️ Anda belum melakukan absensi hari ini.")

    elif menu == "📸 Absensi":
        st.title("📸 Absensi Foto")
        jam_settings = db.get_jam_settings()
        st.info(f"⏰ **Jam Masuk:** {jam_settings[0]} | **Jam Pulang:** {jam_settings[1]}")
        
        photo_buffer = st.camera_input("Ambil Foto untuk Absensi")
        
        if st.button("📸 Absen Sekarang", type="primary", use_container_width=True):
            if photo_buffer:
                with st.spinner("Mengunggah foto dan menyimpan data..."):
                    file_name = f"{user_info['nim']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    
                    photo_url = db.upload_photo(photo_buffer.getvalue(), file_name)
                    
                    if photo_url:
                        record_id = str(uuid.uuid4())
                        timestamp = get_current_datetime()
                        current_time = get_current_time()
                        status = determine_attendance_status(current_time, jam_settings[0], jam_settings[1])
                        late_status = determine_late_status(current_time, jam_settings[0])

                        success = db.insert_record(record_id, user_info['nim'], user_info['nama'], 
                                                   user_info['jurusan'], timestamp, photo_url, status, late_status)
                        if success:
                            msg = f"Absensi {status} ({late_status}) berhasil pada {timestamp}"
                            st.success(f"✅ {msg}")
                            st.image(photo_url, caption="Foto berhasil diunggah", width=300)
            else:
                st.warning("⚠️ Ambil foto terlebih dahulu.")

    elif menu == "📊 Riwayat Absensi":
        st.title("📊 Riwayat Absensi Saya")
        df = db.fetch_all_records()
        if not df.empty:
            df_user = df[df['nim'] == user_info['nim']]
            if not df_user.empty:
                st.dataframe(df_user[['timestamp', 'status', 'late_status', 'photo_path']], use_container_width=True)
            else:
                st.info("Belum ada riwayat absensi.")
        else:
            st.info("Belum ada riwayat absensi.")

    elif menu == "🚪 Logout":
        st.session_state.role = None
        st.rerun()

# ---------- Halaman Admin ----------
elif st.session_state.role == "admin":
    st.sidebar.title("👨‍💼 Admin Panel")
    menu = st.sidebar.radio("Menu", ["📊 Data Absensi", "👥 Kelola Mahasiswa", "⏰ Pengaturan Jam", "🚪 Logout"])

    if menu == "📊 Data Absensi":
        st.title("📊 Data Absensi Lengkap")
        df = db.fetch_all_records()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Detail & Hapus Data")
            sel_id = st.selectbox("Pilih ID record untuk dilihat/dihapus", options=df["id"].unique())
            if sel_id:
                row = df[df["id"] == sel_id].iloc[0]
                st.image(row['photo_path'], caption=f"Foto: {row['nama']}", width=200)
                st.write(f"**Nama:** {row['nama']} ({row['nim']})")
                
                if st.button("🗑️ Hapus Record Ini", type="secondary"):
                    if db.delete_record(sel_id):
                        st.success("Record berhasil dihapus.")
                        st.rerun()
        else:
            st.info("Belum ada data absensi.")

    elif menu == "👥 Kelola Mahasiswa":
        st.title("👥 Kelola Data Mahasiswa")
        tab1, tab2 = st.tabs(["📋 Daftar Mahasiswa", "➕ Tambah Mahasiswa"])
        with tab1:
            df_mhs = db.get_all_mahasiswa()
            st.dataframe(df_mhs, use_container_width=True)
            if not df_mhs.empty:
                nim_del = st.selectbox("Pilih NIM untuk dihapus", options=df_mhs["nim"].unique())
                if st.button("🗑️ Hapus Mahasiswa", type="secondary"):
                    if db.delete_mahasiswa(nim_del):
                        st.success(f"Mahasiswa dengan NIM {nim_del} dihapus.")
                        st.rerun()
        with tab2:
            with st.form("add_mahasiswa"):
                nim = st.text_input("NIM")
                nama = st.text_input("Nama Lengkap")
                jurusan = st.text_input("Jurusan")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("➕ Tambah", type="primary"):
                    if db.add_mahasiswa(nim, nama, jurusan, password):
                        st.success("Mahasiswa baru berhasil ditambahkan.")

    elif menu == "⏰ Pengaturan Jam":
        st.title("⏰ Pengaturan Jam Masuk & Pulang")
        jam_masuk, jam_pulang = db.get_jam_settings()
        with st.form("jam_settings"):
            jam_masuk_val = datetime.datetime.strptime(jam_masuk, "%H:%M:%S").time()
            jam_pulang_val = datetime.datetime.strptime(jam_pulang, "%H:%M:%S").time()
            new_jam_masuk = st.time_input("Jam Masuk", value=jam_masuk_val)
            new_jam_pulang = st.time_input("Jam Pulang", value=jam_pulang_val)
            if st.form_submit_button("💾 Simpan", type="primary"):
                if db.update_jam_settings(new_jam_masuk.strftime("%H:%M:%S"), new_jam_pulang.strftime("%H:%M:%S")):
                    st.success("Pengaturan jam berhasil disimpan.")
                    st.rerun()

    elif menu == "🚪 Logout":
        st.session_state.role = None
        st.rerun()

