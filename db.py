# File: db.py
# Deskripsi: Modul ini menangani semua koneksi dan operasi database dengan Supabase.
#            (Diperbarui untuk menyimpan data lokasi)

import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError
import datetime

# --- Inisialisasi Klien Supabase ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    SERVICE_KEY = st.secrets["supabase"]["service_key"]
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase_admin: Client = create_client(SUPABASE_URL, SERVICE_KEY)

except Exception as e:
    st.error("Konfigurasi Supabase tidak ditemukan di .streamlit/secrets.toml.")
    st.stop()

PHOTO_BUCKET = "photos"

# --- Fungsi Operasi Storage (Menggunakan Klien Admin) ---
def upload_photo(file_bytes, file_name):
    try:
        supabase_admin.storage.from_(PHOTO_BUCKET).upload(file=file_bytes, path=file_name, file_options={"cache-control": "3600", "upsert": "false"})
        public_url = supabase.storage.from_(PHOTO_BUCKET).get_public_url(file_name)
        return public_url
    except APIError as e:
        if "Duplicate" in str(e.message):
            return supabase.storage.from_(PHOTO_BUCKET).get_public_url(file_name)
        st.error(f"Gagal mengunggah foto: {e.message}")
        return None

def delete_photo(file_name):
    try:
        supabase_admin.storage.from_(PHOTO_BUCKET).remove([file_name])
        return True
    except APIError as e:
        st.error(f"Gagal menghapus foto: {e.message}")
        return False

# --- Fungsi Helper Database ---
def handle_response(response):
    return response.data if hasattr(response, 'data') and response.data else []

def handle_single_response(response):
    data = handle_response(response)
    return data[0] if data else None

# --- Fungsi Database ---
def validate_mahasiswa(nim, password):
    try:
        response = supabase.table('mahasiswa').select('nim, nama, jurusan').eq('nim', nim).eq('password', password).execute()
        return handle_single_response(response)
    except APIError as e:
        st.error(f"Error validasi mahasiswa: {e.message}")
        return None

def validate_admin(username, password):
    try:
        response = supabase.table('admins').select('username').eq('username', username).eq('password', password).execute()
        return handle_single_response(response) is not None
    except APIError as e:
        st.error(f"Error validasi admin: {e.message}")
        return False

def insert_record(record_id, nim, nama, jurusan, timestamp, photo_url, status, late_status, latitude, longitude):
    try:
        record_data = {
            'id': record_id, 'nim': nim, 'nama': nama, 'jurusan': jurusan,
            'timestamp': timestamp, 'photo_path': photo_url,
            'status': status, 'late_status': late_status,
            'latitude': latitude, 'longitude': longitude  # Data lokasi ditambahkan
        }
        supabase.table('attendance').insert(record_data).execute()
        return True
    except APIError as e:
        st.error(f"Error menyimpan absensi: {e.message}")
        return False

def fetch_all_records():
    try:
        response = supabase.table('attendance').select('*').order('timestamp', desc=True).execute()
        data = handle_response(response)
        return pd.DataFrame(data) if data else pd.DataFrame()
    except APIError as e:
        st.error(f"Error mengambil data absensi: {e.message}")
        return pd.DataFrame()

def delete_record(record_id):
    try:
        record = supabase.table('attendance').select('photo_path').eq('id', record_id).single().execute()
        if record.data and record.data.get('photo_path'):
            delete_photo(record.data['photo_path'].split('/')[-1])
        supabase.table('attendance').delete().eq('id', record_id).execute()
        return True
    except APIError as e:
        st.error(f"Error menghapus record: {e.message}")
        return False

# Fungsi lain (get_jam_settings, update_jam_settings, dll.) tidak perlu diubah
def get_jam_settings():
    try:
        response = supabase.table('jam_settings').select('jam_masuk, jam_pulang').order('created_at', desc=True).limit(1).execute()
        settings = handle_single_response(response)
        return (settings['jam_masuk'], settings['jam_pulang']) if settings else ("08:00:00", "17:00:00")
    except APIError as e:
        st.error(f"Error mengambil pengaturan jam: {e.message}")
        return ("08:00:00", "17:00:00")

def update_jam_settings(jam_masuk, jam_pulang):
    try:
        supabase.table('jam_settings').insert({'jam_masuk': jam_masuk, 'jam_pulang': jam_pulang}).execute()
        return True
    except APIError as e:
        st.error(f"Error menyimpan pengaturan jam: {e.message}")
        return False

def get_all_mahasiswa():
    try:
        response = supabase.table('mahasiswa').select('nim, nama, jurusan').order('nama').execute()
        data = handle_response(response)
        return pd.DataFrame(data) if data else pd.DataFrame()
    except APIError as e:
        st.error(f"Error mengambil data mahasiswa: {e.message}")
        return pd.DataFrame()

def add_mahasiswa(nim, nama, jurusan, password):
    try:
        supabase.table('mahasiswa').insert({'nim': nim, 'nama': nama, 'jurusan': jurusan, 'password': password}).execute()
        return True
    except APIError as e:
        if 'duplicate key value violates unique constraint' in e.message:
            st.error("NIM sudah ada.")
        else:
            st.error(f"Error menambah mahasiswa: {e.message}")
        return False

def delete_mahasiswa(nim):
    try:
        supabase.table('mahasiswa').delete().eq('nim', nim).execute()
        return True
    except APIError as e:
        st.error(f"Error menghapus mahasiswa: {e.message}")
        return False

