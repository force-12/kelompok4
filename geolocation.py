import streamlit as st
import streamlit.components.v1 as components

def get_geolocation():
    """
    Mengambil lokasi GPS pengguna menggunakan JavaScript Geolocation API.
    Returns: dict dengan 'latitude' dan 'longitude', atau None jika gagal.
    """
    
    # HTML + JavaScript untuk mendapatkan lokasi
    html_code = """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    // Kirim data ke Streamlit
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy
                        }
                    }, '*');
                },
                function(error) {
                    let errorMsg = '';
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            errorMsg = "Pengguna menolak permintaan Geolocation";
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMsg = "Informasi lokasi tidak tersedia";
                            break;
                        case error.TIMEOUT:
                            errorMsg = "Request timeout";
                            break;
                        case error.UNKNOWN_ERROR:
                            errorMsg = "Error tidak diketahui";
                            break;
                    }
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: {error: errorMsg}
                    }, '*');
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: {error: "Geolocation tidak didukung browser ini"}
            }, '*');
        }
    }
    
    // Auto-run saat komponen dimuat
    getLocation();
    </script>
    
    <div style="padding: 10px; text-align: center;">
        <p>🌍 Mengambil lokasi GPS Anda...</p>
        <p style="font-size: 0.9em; color: #666;">Silakan izinkan akses lokasi pada browser Anda</p>
    </div>
    """
    
    # Render komponen dan ambil hasilnya
    location = components.html(html_code, height=100)
    
    return location
