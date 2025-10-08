import streamlit as st
import uuid
import datetime
import pandas as pd
import db
from streamlit_geolocation import streamlit_geolocation

# ---------- Utilities ----------
def get_current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")

def get_current_datetime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def determine_attendance_status(current_time, jam_masuk, jam_pulang):
    current = datetime.datetime.strptime(current_time, "%H:%M:%S").time()
    masuk = datetime.datetime.strptime(jam_masuk, "%H:%M:%S").time()
    pulang = datetime.datetime.strptime(jam_pulang, "%H:%M:%S").time()
    return "Masuk" if current <= masuk or (current > masuk and current < pulang) else "Pulang"

def determine_late_status(current_time, jam_masuk):
    current = datetime.datetime.strptime(current_time, "%H:%M:%S").time()
    masuk = datetime.datetime.strptime(jam_masuk, "%H:%M:%S").time()
    return "Terlambat" if current > masuk else "Tidak Terlambat"

# ---------- Konfigurasi Halaman & Session State ----------
st.set_page_config(page_title="Sistem Absensi Mahasiswa", layout="wide")

if "role" not in st.session_state: st.session_state.role = None
if "user_info" not in st.session_state: st.session_state.user_info = {}

# ---------- Halaman Login ----------
if st.session_state.role is None:
    # ... (Kode Halaman Login tidak berubah, disembunyikan agar ringkas)
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; margin-bottom: 30px; color: white;">
        <h1 style="margin: 0; font-size: 2.5em; font-weight: bold;">🎓 Sistem Absensi Mahasiswa (GPS)</h1>
        <p style="margin: 10px 0 0 0; font-size: 1.2em;">Digital Attendance Management System</p>
    </div>
    """, unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["👨‍🎓 Login Mahasiswa", "👨‍💼 Login Admin"])
        with tab1:
            with st.form("mahasiswa_login_form"):
                nim = st.text_input("NIM")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("🚀 Masuk", type="primary", use_container_width=True):
                    user_data = db.validate_mahasiswa(nim.strip(), password)
                    if user_data:
                        st.session_state.role, st.session_state.user_info = "mahasiswa", user_data
                        st.rerun()
                    else: st.error("❌ NIM atau password salah.")
        with tab2:
            with st.form("admin_login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("🚀 Masuk", type="primary", use_container_width=True):
                    if db.validate_admin(username.strip(), password.strip()):
                        st.session_state.role, st.session_state.user_info = "admin", {"username": username.strip()}
                        st.rerun()
                    else: st.error("❌ Username/password salah.")

# ---------- Halaman Mahasiswa ----------
elif st.session_state.role == "mahasiswa":
    user_info = st.session_state.user_info
    st.sidebar.title(f"👋 Halo, {user_info['nama']}")
    st.sidebar.markdown(f"**NIM:** {user_info['nim']}\n\n**Jurusan:** {user_info['jurusan']}")
    menu = st.sidebar.radio("Menu", ["🏠 Dashboard", "📸 Absensi", "📊 Riwayat Absensi", "🚪 Logout"])

    if menu == "📸 Absensi":
        st.title("📸 Absensi Foto & Lokasi")
        jam_settings = db.get_jam_settings()
        st.info(f"⏰ **Jam Masuk:** {jam_settings[0]} | **Jam Pulang:** {jam_settings[1]}")
        
        st.markdown("---")
        st.subheader("1. Ambil Lokasi GPS Anda")
        st.warning("Pastikan Anda memberikan izin akses lokasi pada browser.")
        location = streamlit_geolocation()

        st.subheader("2. Ambil Foto")
        photo_buffer = st.camera_input("Arahkan wajah ke kamera")

        st.markdown("---")
        if st.button("✅ Absen Sekarang", type="primary", use_container_width=True):
            if not location:
                st.error("Lokasi GPS tidak ditemukan. Klik 'Get Location' dan izinkan akses.")
            elif not photo_buffer:
                st.error("Ambil foto terlebih dahulu.")
            else:
                with st.spinner("Mengunggah foto dan menyimpan data..."):
                    lat, lon = location['latitude'], location['longitude']
                    file_name = f"{user_info['nim']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    
                    photo_url = db.upload_photo(photo_buffer.getvalue(), file_name)
                    
                    if photo_url:
                        record_id = str(uuid.uuid4())
                        timestamp = get_current_datetime()
                        current_time = get_current_time()
                        status = determine_attendance_status(current_time, jam_settings[0], jam_settings[1])
                        late_status = determine_late_status(current_time, jam_settings[0])

                        success = db.insert_record(record_id, user_info['nim'], user_info['nama'], 
                                                   user_info['jurusan'], timestamp, photo_url, status, 
                                                   late_status, lat, lon) # Kirim lat, lon
                        if success:
                            st.success(f"✅ Absensi berhasil! Lokasi: {lat}, {lon}")
                            st.image(photo_url, caption="Foto berhasil diunggah", width=300)

    elif menu == "📊 Riwayat Absensi":
        st.title("📊 Riwayat Absensi Saya")
        df = db.fetch_all_records()
        if not df.empty and 'nim' in df.columns:
            df_user = df[df['nim'] == user_info['nim']]
            if not df_user.empty:
                # Menampilkan kolom lokasi dan membuat link Google Maps
                df_display = df_user[['timestamp', 'status', 'late_status', 'latitude', 'longitude']].copy()
                df_display['Lokasi (Google Maps)'] = df_display.apply(
                    lambda row: f"https://www.google.com/maps?q={row['latitude']},{row['longitude']}", axis=1
                )
                st.dataframe(
                    df_display[['timestamp', 'status', 'late_status', 'Lokasi (Google Maps)']],
                    column_config={"Lokasi (Google Maps)": st.column_config.LinkColumn(display_text="Buka Peta 🗺️")},
                    use_container_width=True
                )
            else: st.info("Belum ada riwayat absensi.")
        else: st.info("Belum ada riwayat absensi.")

    # ... (Kode menu Dashboard & Logout tidak berubah)
    elif menu == "🏠 Dashboard":
        st.title("📊 Dashboard Mahasiswa")
        current_time_str, current_date_str = get_current_time(), datetime.datetime.now().strftime("%A, %d %B %Y")
        st.markdown(f"""
        <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin: 20px 0; color: white;'>
            <h1 style='margin: 0; font-size: 3em;'>🕐 {current_time_str}</h1>
            <p style='margin: 10px 0 0 0; font-size: 1.2em;'>{current_date_str}</p>
        </div>
        """, unsafe_allow_html=True)
        jam_settings = db.get_jam_settings()
        st.info(f"⏰ **Jam Masuk:** {jam_settings[0]} | **Jam Pulang:** {jam_settings[1]}")
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
            # Membuat link Google Maps untuk admin juga
            df_display = df.copy()
            df_display['Lokasi (Google Maps)'] = df_display.apply(
                lambda row: f"https://www.google.com/maps?q={row['latitude']},{row['longitude']}" if pd.notnull(row['latitude']) else "N/A", axis=1
            )
            st.dataframe(
                df_display,
                column_config={"Lokasi (Google Maps)": st.column_config.LinkColumn(display_text="Buka Peta 🗺️")},
                use_container_width=True
            )
        else: st.info("Belum ada data absensi.")
    
    # ... (Kode menu lain di Admin tidak berubah)
    elif menu == "👥 Kelola Mahasiswa":
        st.title("👥 Kelola Data Mahasiswa")
        tab1, tab2 = st.tabs(["📋 Daftar Mahasiswa", "➕ Tambah Mahasiswa"])
        with tab1:
            df_mhs = db.get_all_mahasiswa()
            st.dataframe(df_mhs, use_container_width=True)
            if not df_mhs.empty:
                nim_del = st.selectbox("Pilih NIM untuk dihapus", options=df_mhs["nim"].unique())
                if st.button("🗑️ Hapus Mahasiswa", type="secondary"):
                    if db.delete_mahasiswa(nim_del): st.rerun()
        with tab2:
            with st.form("add_mahasiswa"):
                nim, nama, jurusan = st.text_input("NIM"), st.text_input("Nama"), st.text_input("Jurusan")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("➕ Tambah"):
                    if db.add_mahasiswa(nim, nama, jurusan, password): st.success("Mahasiswa ditambahkan.")
    elif menu == "⏰ Pengaturan Jam":
        st.title("⏰ Pengaturan Jam")
        jam_masuk, jam_pulang = db.get_jam_settings()
        with st.form("jam_settings"):
            new_jam_masuk = st.time_input("Jam Masuk", value=datetime.datetime.strptime(jam_masuk, "%H:%M:%S").time())
            new_jam_pulang = st.time_input("Jam Pulang", value=datetime.datetime.strptime(jam_pulang, "%H:%M:%S").time())
            if st.form_submit_button("💾 Simpan"):
                if db.update_jam_settings(new_jam_masuk.strftime("%H:%M:%S"), new_jam_pulang.strftime("%H:%M:%S")): st.success("Pengaturan jam disimpan.")
    elif menu == "🚪 Logout":
        st.session_state.role = None
        st.rerun()

