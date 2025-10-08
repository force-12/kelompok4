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
        jam_masuk = db.get_jam_settings()
        st.info(f"⏰ **Batas Jam Masuk:** {jam_masuk}")
        
        st.markdown("---")
        st.subheader("1. Dapatkan Lokasi GPS Anda")
        st.warning("Pastikan Anda memberikan izin akses lokasi pada browser saat diminta. Jika lokasi tidak muncul, coba refresh halaman.")
        
        location_data = streamlit_geolocation()

        # --- PERBAIKAN: Gunakan nama kolom default Streamlit ---
        if location_data and 'latitude' in location_data and 'longitude' in location_data:
            st.success("✅ Lokasi berhasil dideteksi!")
            
            # Gunakan nama kolom 'lat' dan 'lon' (default Streamlit)
            map_df = pd.DataFrame({
                'lat': [location_data['latitude']],
                'lon': [location_data['longitude']]
            })
            
            # Streamlit akan otomatis mengenali kolom 'lat' dan 'lon'
            st.map(map_df, zoom=15)
        else:
            st.info("⏳ Menunggu data lokasi... Klik tombol di atas dan izinkan akses lokasi di browser Anda.")
            # Tampilkan peta default Indonesia
            st.map(pd.DataFrame({'lat': [-2.5489], 'lon': [118.0149]}), zoom=4)
        # --- AKHIR PERBAIKAN ---

        st.markdown("---")
        st.subheader("2. Ambil Foto")
        photo_buffer = st.camera_input("Arahkan wajah ke kamera")

        st.markdown("---")
        if st.button("✅ Absen Sekarang", type="primary", use_container_width=True):
            if not location_data or 'latitude' not in location_data:
                st.error("❌ Lokasi GPS tidak ditemukan. Pastikan Anda sudah memberikan izin akses lokasi.")
            elif not photo_buffer:
                st.error("❌ Ambil foto terlebih dahulu.")
            else:
                with st.spinner("⏳ Mengunggah foto dan menyimpan data..."):
                    lat, lon = location_data['latitude'], location_data['longitude']
                    file_name = f"{user_info['nim']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    
                    photo_url = db.upload_photo(photo_buffer.getvalue(), file_name)
                    
                    if photo_url:
                        record_id = str(uuid.uuid4())
                        timestamp = get_current_datetime()
                        current_time = get_current_time()
                        
                        status = "Masuk"
                        late_status = determine_late_status(current_time, jam_masuk)

                        success = db.insert_record(record_id, user_info['nim'], user_info['nama'], 
                                                   user_info['jurusan'], timestamp, photo_url, status, 
                                                   late_status, lat, lon)
                        if success:
                            st.success(f"✅ Absensi berhasil! Status: {late_status}")
                            st.image(photo_url, caption="Foto berhasil diunggah", width=300)
                            st.balloons()

    elif menu == "🏠 Dashboard":
        st.title("📊 Dashboard Mahasiswa")
        current_time_str, current_date_str = get_current_time(), datetime.datetime.now().strftime("%A, %d %B %Y")
        st.markdown(f"""
        <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin: 20px 0; color: white;'>
            <h1 style='margin: 0; font-size: 3em;'>🕐 {current_time_str}</h1>
            <p style='margin: 10px 0 0 0; font-size: 1.2em;'>{current_date_str}</p>
        </div>
        """, unsafe_allow_html=True)
        jam_masuk = db.get_jam_settings()
        st.info(f"⏰ **Batas Jam Masuk:** {jam_masuk}")

    elif menu == "📊 Riwayat Absensi":
        st.title("📊 Riwayat Absensi Saya")
        df_all = db.fetch_all_records()
        if not df_all.empty and 'nim' in df_all.columns:
            df_user = df_all[df_all['nim'] == user_info['nim']]
            if not df_user.empty:
                df_display = df_user[['timestamp', 'status', 'late_status', 'latitude', 'longitude']].copy()
                df_display['Lokasi (Google Maps)'] = df_display.apply(
                    lambda r: f"https://www.google.com/maps?q={r['latitude']},{r['longitude']}" 
                    if pd.notnull(r['latitude']) and pd.notnull(r['longitude']) else "N/A", 
                    axis=1
                )
                st.dataframe(
                    df_display[['timestamp', 'status', 'late_status', 'Lokasi (Google Maps)']], 
                    column_config={
                        "Lokasi (Google Maps)": st.column_config.LinkColumn(display_text="Buka Peta 🗺️")
                    }, 
                    use_container_width=True
                )
            else: 
                st.info("📭 Belum ada riwayat absensi.")
        else: 
            st.info("📭 Belum ada riwayat absensi.")

    elif menu == "🚪 Logout":
        st.session_state.role = None
        st.session_state.user_info = {}
        st.rerun()

# ---------- Halaman Admin ----------
elif st.session_state.role == "admin":
    st.sidebar.title("👨‍💼 Admin Panel")
    menu = st.sidebar.radio("Menu", ["📊 Data Absensi", "👥 Kelola Mahasiswa", "⏰ Pengaturan Jam", "🚪 Logout"])

    if menu == "⏰ Pengaturan Jam":
        st.title("⏰ Pengaturan Jam Masuk")
        jam_masuk = db.get_jam_settings()
        with st.form("jam_settings"):
            jam_masuk_val = datetime.datetime.strptime(jam_masuk, "%H:%M:%S").time()
            new_jam_masuk = st.time_input("Batas Jam Masuk", value=jam_masuk_val)
            if st.form_submit_button("💾 Simpan", type="primary"):
                if db.update_jam_settings(new_jam_masuk.strftime("%H:%M:%S")):
                    st.success("✅ Pengaturan jam berhasil disimpan.")
                    st.rerun()
    
    elif menu == "📊 Data Absensi":
        st.title("📊 Data Absensi Lengkap")
        df = db.fetch_all_records()
        if not df.empty:
            df['Lokasi'] = df.apply(
                lambda r: f"https://www.google.com/maps?q={r['latitude']},{r['longitude']}" 
                if pd.notnull(r['latitude']) and pd.notnull(r['longitude']) else "N/A", 
                axis=1
            )
            st.dataframe(
                df, 
                column_config={
                    "Lokasi": st.column_config.LinkColumn(display_text="Buka Peta 🗺️")
                }, 
                use_container_width=True
            )
        else: 
            st.info("📭 Belum ada data absensi.")

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
                        st.success("✅ Mahasiswa berhasil dihapus.")
                        st.rerun()
        with tab2:
            with st.form("add_mahasiswa"):
                nim = st.text_input("NIM")
                nama = st.text_input("Nama")
                jurusan = st.text_input("Jurusan")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("➕ Tambah"):
                    if all([nim, nama, jurusan, password]):
                        if db.add_mahasiswa(nim, nama, jurusan, password): 
                            st.success("✅ Mahasiswa berhasil ditambahkan.")
                            st.rerun()
                    else:
                        st.error("❌ Semua field harus diisi.")
    
    elif menu == "🚪 Logout":
        st.session_state.role = None
        st.session_state.user_info = {}
        st.rerun()
