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

# --- Fungsi Operasi Storage ---
def upload_photo(file_bytes, file_name):
    try:
        supabase_admin.storage.from_(PHOTO_BUCKET).upload(file=file_bytes, path=file_name, file_options={"cache-control": "3600", "upsert": "false"})
        return supabase.storage.from_(PHOTO_BUCKET).get_public_url(file_name)
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

# --- Fungsi Pengaturan Jam ---
def get_jam_settings():
    """Mengambil jam masuk."""
    try:
        response = supabase.table('jam_settings').select('jam_masuk').order('created_at', desc=True).limit(1).execute()
        settings = handle_single_response(response)
        return settings['jam_masuk'] if settings else "08:00:00"
    except APIError as e:
        st.error(f"Error mengambil pengaturan jam: {e.message}")
        return "08:00:00"

def update_jam_settings(jam_masuk):
    """Menyimpan jam masuk."""
    try:
        # Hapus pengaturan lama agar selalu hanya ada 1 baris
        supabase.table('jam_settings').delete().neq('id', 0).execute()
        # Masukkan yang baru
        supabase.table('jam_settings').insert({'jam_masuk': jam_masuk}).execute()
        return True
    except APIError as e:
        st.error(f"Error menyimpan pengaturan jam: {e.message}")
        return False

# --- Fungsi Absensi (Tanpa GPS) ---
def insert_record(record_id, nim, nama, jurusan, timestamp, photo_url, status, late_status):
    """Menyimpan data absensi tanpa lokasi GPS."""
    try:
        record_data = {
            'id': record_id, 
            'nim': nim, 
            'nama': nama, 
            'jurusan': jurusan, 
            'timestamp': timestamp, 
            'photo_path': photo_url, 
            'status': status, 
            'late_status': late_status
        }
        supabase.table('attendance').insert(record_data).execute()
        return True
    except APIError as e:
        st.error(f"Error menyimpan absensi: {e.message}")
        return False

# --- Fungsi Validasi ---
def validate_mahasiswa(nim, password):
    """Validasi login mahasiswa."""
    try:
        response = supabase.table('mahasiswa').select('nim, nama, jurusan').eq('nim', nim).eq('password', password).execute()
        return handle_single_response(response)
    except APIError as e: 
        return None

def validate_admin(username, password):
    """Validasi login admin."""
    try:
        response = supabase.table('admins').select('username').eq('username', username).eq('password', password).execute()
        return handle_single_response(response) is not None
    except APIError as e: 
        return False

# --- Fungsi Data Absensi ---
def fetch_all_records():
    """Mengambil semua data absensi."""
    try:
        response = supabase.table('attendance').select('*').order('timestamp', desc=True).execute()
        return pd.DataFrame(handle_response(response))
    except APIError as e: 
        return pd.DataFrame()

def delete_record(record_id):
    """Menghapus record absensi beserta fotonya."""
    try:
        record = supabase.table('attendance').select('photo_path').eq('id', record_id).single().execute()
        if record.data and record.data.get('photo_path'):
            delete_photo(record.data['photo_path'].split('/')[-1])
        supabase.table('attendance').delete().eq('id', record_id).execute()
        return True
    except APIError as e: 
        return False

# --- Fungsi Kelola Mahasiswa ---
def get_all_mahasiswa():
    """Mengambil semua data mahasiswa."""
    try:
        response = supabase.table('mahasiswa').select('nim, nama, jurusan').order('nama').execute()
        return pd.DataFrame(handle_response(response))
    except APIError as e: 
        return pd.DataFrame()

def add_mahasiswa(nim, nama, jurusan, password):
    """Menambah mahasiswa baru."""
    try:
        supabase.table('mahasiswa').insert({'nim': nim, 'nama': nama, 'jurusan': jurusan, 'password': password}).execute()
        return True
    except APIError as e:
        if 'duplicate key' in e.message: 
            st.error("NIM sudah ada.")
        else: 
            st.error(f"Error: {e.message}")
        return False

def delete_mahasiswa(nim):
    """Menghapus mahasiswa."""
    try:
        supabase.table('mahasiswa').delete().eq('nim', nim).execute()
        return True
    except APIError as e: 
        return False
