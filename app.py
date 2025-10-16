import streamlit as st
import uuid
import datetime
import pandas as pd
import db
import streamlit.components.v1 as components
from geolocation import get_geolocation  # Import komponen GPS


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
        st.warning("⚠️ Pastikan Anda memberikan izin akses lokasi pada browser saat diminta.")
        
        # Tombol untuk mendapatkan lokasi
        if st.button("📍 Dapatkan Lokasi Saya", type="primary"):
            st.session_state.request_location = True
        
        # Ambil lokasi jika tombol diklik
        location_data = None
        if st.session_state.get('request_location', False):
            location_data = get_geolocation()
        
        # Debug info
        with st.expander("🔍 Debug Info (Klik untuk lihat)"):
            st.write("Data lokasi:", location_data)

        # Validasi dan tampilkan lokasi
        if location_data and isinstance(location_data, dict):
            if 'error' in location_data:
                st.error(f"❌ {location_data['error']}")
                st.session_state.location_coords = None
            elif 'latitude' in location_data and 'longitude' in location_data:
                lat_value = location_data['latitude']
                lon_value = location_data['longitude']
                
                if lat_value is not None and lon_value is not None:
                    # Simpan koordinat ke session state
                    st.session_state.location_coords = {
                        'latitude': float(lat_value),
                        'longitude': float(lon_value)
                    }
                    
                    st.success(f"✅ Lokasi berhasil dideteksi! ({lat_value:.6f}, {lon_value:.6f})")
                    
                    try:
                        map_df = pd.DataFrame({
                            'lat': [float(lat_value)],
                            'lon': [float(lon_value)]
                        })
                        
                        if not map_df.empty:
                            st.map(map_df, zoom=15)
                    except Exception as e:
                        st.error(f"❌ Gagal menampilkan peta: {str(e)}")
        elif st.session_state.get('location_coords'):
            # Tampilkan lokasi yang sudah tersimpan
            coords = st.session_state.location_coords
            st.success(f"✅ Lokasi tersimpan: ({coords['latitude']:.6f}, {coords['longitude']:.6f})")
            
            try:
                map_df = pd.DataFrame({
                    'lat': [coords['latitude']],
                    'lon': [coords['longitude']]
                })
                st.map(map_df, zoom=15)
            except Exception as e:
                st.error(f"❌ Gagal menampilkan peta: {str(e)}")

        st.markdown("---")
        st.subheader("2. Ambil Foto")
        photo_buffer = st.camera_input("Arahkan wajah ke kamera")

        st.markdown("---")
        if st.button("✅ Absen Sekarang", type="primary", use_container_width=True):
            # Validasi lokasi
            if not st.session_state.get('location_coords'):
                st.error("❌ Lokasi GPS belum diambil. Klik tombol 'Dapatkan Lokasi Saya' terlebih dahulu.")
            elif not photo_buffer:
                st.error("❌ Ambil foto terlebih dahulu.")
            else:
                with st.spinner("⏳ Mengunggah foto dan menyimpan data..."):
                    coords = st.session_state.location_coords
                    lat, lon = coords['latitude'], coords['longitude']
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
                            # Reset lokasi setelah absen sukses
                            st.session_state.location_coords = None
                            st.session_state.request_location = False

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
                # Tambahkan kolom Google Maps link
                df_display = df_user[['timestamp', 'status', 'late_status', 'latitude', 'longitude']].copy()
                df_display['Google Maps'] = df_display.apply(
                    lambda r: f"https://www.google.com/maps?q={r['latitude']},{r['longitude']}" 
                    if pd.notnull(r['latitude']) and pd.notnull(r['longitude']) else "N/A", 
                    axis=1
                )
                
                # Tampilkan dataframe dengan link
                st.dataframe(
                    df_display[['timestamp', 'status', 'late_status', 'Google Maps']], 
                    column_config={
                        "timestamp": "Waktu Absensi",
                        "status": "Status",
                        "late_status": "Keterlambatan",
                        "Google Maps": st.column_config.LinkColumn(
                            "Lokasi 🗺️",
                            display_text="Buka di Maps"
                        )
                    }, 
                    use_container_width=True,
                    hide_index=True
                )
                
                # Summary statistik
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Total Absensi", len(df_user))
                with col2:
                    tepat_waktu = len(df_user[df_user['late_status'] == 'Tidak Terlambat'])
                    st.metric("✅ Tepat Waktu", tepat_waktu)
                with col3:
                    terlambat = len(df_user[df_user['late_status'] == 'Terlambat'])
                    st.metric("⏰ Terlambat", terlambat)
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
