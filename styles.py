import streamlit as st
import os

# --- GÖRSEL SABİTLER ---
# Proje klasöründeki 'assets/logo.png' dosyasına dinamik olarak işaret eder.
# Farklı bilgisayarlarda veya sunucularda çalışmayı garantiler.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(_BASE_DIR, "assets", "DGN_LOGO.png")

def configure_page():
    """Streamlit sayfa konfigürasyonunu ayarlar. app.py'de en üstte çağrılmalıdır."""
    st.set_page_config(
        page_title="DGN Denizcilik AI",
        layout="wide",
        page_icon="🚢",
        initial_sidebar_state="expanded"
    )

def apply_custom_styles():
    """DGN Denizcilik kurumsal CSS stillerini uygular."""
    st.markdown("""
    <style>
    /* Ana Ekran Koyu */
    .main { background-color: #0e1117; color: white; }
    
    /* MENÜ KOLONU (SIDEBAR) - AÇIK RENK VE SABİT GENİŞLİK */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
        border-right: 1px solid #dee2e6;
        min-width: 300px !important;
        max-width: 300px !important;
    }

    /* 'keyboard_double' hatasını gizle (Sidebar toggle butonu) */
    button[kind="headerNoPadding"] { 
        display: none !important; 
    }
    .st-emotion-cache-6q9sum { 
        visibility: hidden !important; 
    }
    
    /* Logo Taşmasını Engelleme */
    [data-testid='stSidebar'] img { 
        max-width: 100%; 
        height: auto; 
        padding: 10px; 
    }
    
    /* --- SIDEBAR METİN RENKLERİ (OKUNABİLİRLİK İÇİN KOYU) --- */
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] .stRadio label {
        color: #1c1e21 !important;
        font-family: 'Segoe UI', sans-serif;
    }

    [data-testid="stSidebar"] p {
        font-weight: 500 !important;
    }

    /* Radyo Buton İç Metinleri ve Boşlukları */
    [data-testid="stSidebar"] .stRadio label {
        padding: 6px 0px;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stSidebarNav"] li span {
        color: #1c1e21 !important;
    }

    /* Durum Rozeti (Storage Badge) */
    .status-badge {
        padding: 8px 12px;
        border-radius: 8px;
        text-align: center;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-top: 15px;
        display: block;
        color: #FFFFFF !important;
    }
    .badge-cloud { background-color: #2ea043; border: 1px solid #2ea04370; }
    .badge-local { background-color: #2299c5; border: 1px solid #2299c570; }

    /* Kullanıcı Bilgi Kartı (User Card) - Modernize */
    .user-box {
        background-color: #f1f3f5;
        border-radius: 10px;
        padding: 10px;
        border-left: 5px solid #2299c5;
        margin-bottom: 24px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .user-box .user-label {
        font-size: 0.65rem !important;
        color: #868e96 !important;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 6px;
        display: block;
        font-weight: 700 !important;
    }
    .user-box .user-name {
        font-size: 0.90rem !important;
        color: #1c1e21 !important;
        font-weight: 800 !important;
        display: block;
        letter-spacing: 0.2px;
    }

    /* DGN Kurumsal Buton */
    .stButton>button {
        background-color: #2299c5 !important;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
        height: 3.5em;
        width: 100%;
        border: none;
    }
    
    /* Metrikler (Koyu Ekranda Parlak) */
    .stMetric {
        background-color: #1c2128;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #30363d;
    }
    [data-testid="stMetricValue"] { color: #2299c5 !important; }
    
    h1, h2, h3 { color: #ffffff; }
    div[data-testid="stExpander"] { background-color: #1c2128; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)
