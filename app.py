import streamlit as st
import pandas as pd
import io
import locale
import os
import base64
from datetime import date
import plotly.express as px

# --- MODÜL İÇE AKTARMALARI ---
import styles
import database
import ai_engine
import storage_utils

try:
    import matplotlib
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# =============================================================================
# SAYFA KONFİGÜRASYONU (EN ÜST — st çağrısından önce)
# =============================================================================
styles.configure_page()

# --- KURUMSAL STİL UYGULAMA ---
styles.apply_custom_styles()

# --- SABITLER ---
UPLOAD_DIR = "fatura_arsivi"  # GCS kullanılamadığında yerel yedek

# --- KULLANICI TANIMI (Statik — ileride DB'ye bağlanacak) ---
USERS = {
    "admin": "dgn2024",
    "ozgur": "dgn2024",
}


# =============================================================================
# YARDIMCI FONKSİYON: Türk Lirası Biçimlendirme
# =============================================================================
def tl(sayi: float) -> str:
    """
    Sayıyı Türk Lirası formatında biçimlendirir.
    Örnek: 10_500.75 → '10.500,75 TL'
    """
    formatted = f"{sayi:,.2f}"
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{formatted} TL"


# =============================================================================
# GİRİŞ EKRANI
# =============================================================================
def show_login_page():
    """Profesyonel DGN Denizcilik giriş ekranını render eder."""

    # Giriş ekranına özel ek CSS
    st.markdown("""
    <style>
    /* Giriş sayfasında sidebar'ı gizle */
    [data-testid="stSidebar"] { display: none !important; }

    /* Giriş kartı konteyneri */
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }

    /* Üst şerit */
    .login-top-bar {
        background: linear-gradient(90deg, #0d1b2a 0%, #2299c5 100%);
        padding: 8px 0;
        text-align: center;
        font-size: 0.75rem;
        color: #a0cfdf;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 0;
    }

    /* Ana kart */
    .login-card {
        background: linear-gradient(145deg, #161b22, #1c2430);
        border: 1px solid #2299c530;
        border-radius: 20px;
        padding: 48px 44px 40px 44px;
        max-width: 440px;
        margin: 0 auto;
        box-shadow: 0 8px 48px 0 #2299c520, 0 2px 16px #0008;
    }

    /* Başlık metni */
    .login-title {
        text-align: center;
        font-size: 1.55rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 4px 0;
        letter-spacing: 0.5px;
    }
    .login-sub {
        text-align: center;
        font-size: 0.82rem;
        color: #7a9bb5;
        margin-bottom: 28px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    /* Ayırıcı çizgi */
    .login-divider {
        border: none;
        border-top: 1px solid #2299c530;
        margin: 0 0 28px 0;
    }

    /* Input etiketleri */
    .login-card label {
        color: #a0cfdf !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* Giriş butonu override (Streamlit form içinde) */
    .login-card .stButton > button {
        background: linear-gradient(90deg, #1a7fa8, #2299c5) !important;
        color: #fff !important;
        font-size: 1rem !important;
        font-weight: 800 !important;
        border-radius: 10px !important;
        height: 3.2em !important;
        width: 100% !important;
        border: none !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 8px;
        box-shadow: 0 4px 18px #2299c540;
        transition: all 0.2s ease;
    }
    .login-card .stButton > button:hover {
        background: linear-gradient(90deg, #2299c5, #3ab5e0) !important;
        box-shadow: 0 6px 24px #2299c560 !important;
        transform: translateY(-1px);
    }

    /* Footer */
    .login-footer {
        text-align: center;
        color: #3d5166;
        font-size: 0.72rem;
        margin-top: 24px;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Üst şerit
    st.markdown('<div class="login-top-bar">DGN DENİZCİLİK — KURUMSAL YÖNETİM SİSTEMİ</div>', unsafe_allow_html=True)

    # Boşluk + ortalanmış kart
    st.markdown("<br>", unsafe_allow_html=True)

    # Kartı ortaya almak için sütun yapısı
    _, col_center, _ = st.columns([1, 1.6, 1])

    with col_center:
        # Logo
        if os.path.exists(styles.LOGO_PATH):
            with open(styles.LOGO_PATH, "rb") as image_file:
                encoded_img = base64.b64encode(image_file.read()).decode()
            st.markdown(
                f'<div style="text-align: center;">'
                f'<img src="data:image/png;base64,{encoded_img}" width="350" style="margin: 0 auto; display: block;">'
                f'</div><br>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown('<div style="text-align: center;"><p class="login-title">⚓ DGN DENİZCİLİK</p></div>', unsafe_allow_html=True)

        st.markdown('<p class="login-sub">Muhasebe & Takip Platformu</p>', unsafe_allow_html=True)
        st.markdown('<hr class="login-divider">', unsafe_allow_html=True)

        # Giriş formu
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 Kullanıcı Adı", placeholder="kullanici_adi")
            password = st.text_input("🔒 Şifre", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("🚀 Sisteme Giriş Yap")

            if submitted:
                if username == "admin" and password == "1234":
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = username
                    st.success("✅ Giriş başarılı! Yönlendiriliyorsunuz...")
                    st.rerun()
                else:
                    st.error("❌ Kullanıcı adı veya şifre hatalı. Lütfen tekrar deneyin.")

        st.markdown(
            f'<p class="login-footer">© {date.today().year} DGN Denizcilik A.Ş. — Tüm hakları saklıdır.</p>',
            unsafe_allow_html=True
        )


# =============================================================================
# ANA UYGULAMA
# =============================================================================
def main_app():
    """Kimlik doğrulaması başarılı kullanıcılar için ana uygulama arayüzünü çalıştırır."""

    # --- BAŞLANGIÇ: VERİTABANI ve KLASÖR ---
    database.init_db()
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    # GCS bağlantı durumu göstergesi
    gcs_ready = storage_utils.HAS_GCS and os.path.exists(storage_utils.SERVICE_ACCOUNT_PATH)

    # =========================================================================
    # SIDEBAR: LOGO ve ANA MENÜ
    # =========================================================================
    with st.sidebar:
        if os.path.exists(styles.LOGO_PATH):
            st.image(styles.LOGO_PATH, use_container_width=True)
        else:
            st.title("DGN DENİZCİLİK")

        st.markdown("<br>", unsafe_allow_html=True)

        # Aktif kullanıcı göstergesi
        current_user = st.session_state.get("current_user", "Kullanıcı")
        st.markdown(
            f"""
            <div class="user-box">
                <span class="user-label">SİSTEM YETKİLİSİ</span>
                <span class="user-name">👤 {current_user.upper()}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### ANA MENÜ")
        menu = st.radio("", [
            "📄 Fatura İşleme",
            "✍️ Manuel Fatura Girişi",
            "🔍 Hızlı Ara",
            "🚜 Ekipman Tanımla",
            "📜 Sözleşme Tanımla",
            "📊 Raporlar & Yönetim"
        ])

        st.markdown("---")
        st.caption(f"📅 Sistem Tarihi: {date.today()}")

        # Depolama durumu göstergesi (Badge style)
        if gcs_ready:
            st.markdown('<div class="status-badge badge-cloud">☁️ BULUT DEPOLAMA AKTİF</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge badge-local">💾 YEREL DEPOLAMA AKTİF</div>', unsafe_allow_html=True)

        # Güvenli Çıkış
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 Güvenli Çıkış", use_container_width=True, type="secondary"):
            st.session_state["authenticated"] = False
            st.session_state["current_user"] = None
            st.rerun()

    # =========================================================================
    # SAYFA: EKİPMAN TANIMLA
    # =========================================================================
    if menu == "🚜 Ekipman Tanımla":
        st.header("🚜 Ekipman ve Varlık Yönetimi")
        plaka = st.text_input("Varlık Plaka/Adı").upper().strip()
        if st.button("Kaydet"):
            if plaka:
                if database.add_ekipman(plaka):
                    st.success(f"✅ {plaka} eklendi.")
                    st.rerun()
                else:
                    st.error("Bu kayıt zaten mevcut.")
        st.table(database.get_list("ekipmanlar", "plaka"))

    # =========================================================================
    # SAYFA: SÖZLEŞME TANIMLA
    # =========================================================================
    elif menu == "📜 Sözleşme Tanımla":
        st.header("📜 Sözleşme ve Proje Yönetimi")
        soz = st.text_input("Sözleşme Adı").upper().strip()
        if st.button("Kaydet"):
            if soz:
                if database.add_sozlesme(soz):
                    st.success(f"✅ {soz} eklendi.")
                    st.rerun()
                else:
                    st.error("Bu kayıt zaten mevcut.")
        st.table(database.get_list("sozlesmeler", "ad"))

    # =========================================================================
    # SAYFA: HIZLI ARA
    # =========================================================================
    elif menu == "🔍 Hızlı Ara":
        st.header("🔍 Kayıt Arama")
        query = st.text_input("Firma veya Malzeme ismi yazın...")
        if query:
            df_all = database.get_all_invoices()
            if not df_all.empty:
                res = df_all[
                    df_all['firma'].str.contains(query, case=False, na=False) |
                    df_all['kalem_adi'].str.contains(query, case=False, na=False)
                ]
                if not res.empty:
                    grouped = (
                        res.groupby('fatura_no')
                        .agg({'firma': 'first', 'tarih': 'first', 'toplam_tutar': 'sum'})
                        .reset_index()
                    )
                    st.dataframe(grouped.sort_values('tarih', ascending=False), use_container_width=True)
                    sel_f = st.selectbox("Detayını gör:", grouped['fatura_no'])
                    st.table(
                        res[res['fatura_no'] == sel_f][
                            ['kalem_adi', 'miktar', 'birim_fiyat', 'toplam_tutar', 'ekipman_plakasi']
                        ]
                    )

    # =========================================================================
    # SAYFA: FATURA İŞLEME
    # =========================================================================
    elif menu == "📄 Fatura İşleme":
        st.header("📄 Yapay Zeka Destekli Fatura Girişi")

        file = st.file_uploader("Faturayı Seçin", type=["pdf", "jpg", "png", "jpeg"])
        if file and st.button("Faturayı Çözümle ✨"):
            with st.spinner("DGN AI analiz ediyor..."):
                f_bytes = file.read()
                data = ai_engine.analyze_invoice(f_bytes, file.type)
                if data:
                    st.session_state['f_data'] = data
                    st.session_state['f_name'] = file.name
                    st.session_state['f_bytes'] = f_bytes

        if 'f_data' in st.session_state:
            d = st.session_state['f_data']

            st.subheader("📌 Genel Bilgiler")
            c1, c2, c3, c4, c5 = st.columns(5)
            f_firma = c1.text_input("Firma", d.get('firma'))
            f_no = c2.text_input("Fatura No", d.get('fatura_no'))
            f_tarih = c3.text_input("Tarih", d.get('tarih'))
            f_onay = c4.text_input("Onaylayan", st.session_state.get("current_user", "Özgür Doğan").title())
            g_is = c5.number_input("Genel İskonto %", 0.0, 100.0)

            ekip_l = database.get_list("ekipmanlar", "plaka")
            soz_l = database.get_list("sozlesmeler", "ad")

            df_items = pd.DataFrame(d.get('kalemler', []))

            for col in ['miktar', 'birim_fiyat', 'iskonto_orani']:
                if col not in df_items.columns:
                    df_items[col] = 0.0
                df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0.0)

            if 'kdv_orani' not in df_items.columns:
                df_items['kdv_orani'] = 20
            df_items['kdv_orani'] = pd.to_numeric(df_items['kdv_orani'], errors='coerce').fillna(20).astype(int)

            if g_is > 0:
                df_items['iskonto_orani'] = g_is
            df_items['ekipman'] = None
            df_items['sozlesme'] = None

            edited = st.data_editor(
                df_items,
                column_config={
                    "ekipman": st.column_config.SelectboxColumn("🚜 Ekipman", options=ekip_l, required=True),
                    "sozlesme": st.column_config.SelectboxColumn("📜 Sözleşme", options=soz_l, required=True),
                    "kdv_orani": st.column_config.NumberColumn("KDV %", format="%d", min_value=0, max_value=100),
                },
                use_container_width=True,
                num_rows="dynamic"
            )

            if st.button("💾 Kaydı Tamamla"):
                if database.check_duplicate_invoice(f_no):
                    st.error("⚠️ Mükerrer Kayıt! Bu fatura numarası zaten sistemde kayıtlı.")
                elif "DGN" in f_firma.upper():
                    st.error("⚠️ Tedarikçi adı DGN olamaz. Lütfen satıcı firmanın adını girin.")
                else:
                    valid = edited[edited['ad'].notna() & (edited['ad'].str.strip() != "")]
                    if valid['ekipman'].isnull().any() or valid['sozlesme'].isnull().any():
                        st.error("⚠️ Lütfen tüm kalemler için ekipman ve sözleşme seçin.")
                    else:
                        with st.spinner("Fatura buluta işleniyor..."):
                            try:
                                f_bytes = st.session_state['f_bytes']
                                f_name = st.session_state['f_name']

                                f_path = ""
                                # Bulut depolama aktifse GCS'ye yükle, değilse yerel kaydet
                                if gcs_ready:
                                    f_path = storage_utils.upload_invoice_file(
                                        f_bytes, f_name, f_no, f_tarih
                                    )
                                    if f_path is None:
                                        st.error("⚠️ Dosya buluta yüklenemedi. İnternet bağlantınızı kontrol edin.")
                                        st.stop()
                                else:
                                    f_path = os.path.join(UPLOAD_DIR, f"{f_no}_{f_name}")
                                    with open(f_path, "wb") as f:
                                        f.write(f_bytes)

                                with database.get_connection() as conn:
                                    database.insert_invoice_rows(conn, f_firma, f_tarih, f_no, f_onay, valid, f_path)

                                st.success("✅ Fatura başarıyla kaydedildi ve bulut arşivine yüklendi!")
                                st.balloons()
                                del st.session_state['f_data']
                                
                                import time
                                time.sleep(4)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Kayıt Hatası: {e}")

    # =========================================================================
    # SAYFA: MANUEL FATURA GİRİŞİ
    # =========================================================================
    elif menu == "✍️ Manuel Fatura Girişi":
        st.header("✍️ Manuel Fatura Girişi")

        file = st.file_uploader("Fatura Dosyasını Seçin (Opsiyonel)", type=["pdf", "jpg", "png", "jpeg"])

        st.subheader("📌 Genel Bilgiler")
        c1, c2, c3, c4, c5 = st.columns(5)
        f_firma = c1.text_input("Firma Adı")
        f_no = c2.text_input("Fatura No")
        f_tarih = c3.date_input("Fatura Tarihi")
        f_onay = c4.text_input("Onaylayan", st.session_state.get("current_user", "Özgür Doğan").title())
        g_is = c5.number_input("Genel İskonto %", 0.0, 100.0)

        st.subheader("📝 Fatura Kalemleri")

        ekip_l = database.get_list("ekipmanlar", "plaka")
        soz_l = database.get_list("sozlesmeler", "ad")

        if 'manuel_df' not in st.session_state:
            st.session_state['manuel_df'] = pd.DataFrame(
                columns=['ad', 'miktar', 'birim_fiyat', 'kdv_orani', 'iskonto_orani', 'ekipman', 'sozlesme']
            )

        df_items = st.session_state['manuel_df'].copy()

        edited = st.data_editor(
            df_items,
            column_config={
                "ad": st.column_config.TextColumn("Malzeme/Hizmet Adı", required=True),
                "miktar": st.column_config.NumberColumn("Miktar", min_value=0.0, default=1.0, required=True),
                "birim_fiyat": st.column_config.NumberColumn("Birim Fiyat", min_value=0.0, default=0.0, required=True),
                "kdv_orani": st.column_config.NumberColumn("KDV %", format="%d", min_value=0, max_value=100, default=20),
                "iskonto_orani": st.column_config.NumberColumn("İskonto %", min_value=0.0, max_value=100.0, default=0.0),
                "ekipman": st.column_config.SelectboxColumn("🚜 Ekipman", options=ekip_l, required=True),
                "sozlesme": st.column_config.SelectboxColumn("📜 Sözleşme", options=soz_l, required=True),
            },
            use_container_width=True,
            num_rows="dynamic",
            key="manuel_editor"
        )

        if st.button("💾 Kaydet"):
            if not f_firma or not f_no or not f_tarih:
                st.error("⚠️ Lütfen Firma, Fatura No ve Tarih alanlarını doldurun.")
            elif database.check_duplicate_invoice(f_no):
                st.error("⚠️ Mükerrer Kayıt! Bu fatura numarası zaten sistemde kayıtlı.")
            elif "DGN" in f_firma.upper():
                st.error("⚠️ Tedarikçi adı DGN olamaz. Lütfen satıcı firmanın adını girin.")
            else:
                valid = edited[edited['ad'].notna() & (edited['ad'].str.strip() != "")]
                if valid.empty:
                    st.error("⚠️ Lütfen en az bir fatura kalemi girin.")
                elif valid['ekipman'].isnull().any() or valid['sozlesme'].isnull().any():
                    st.error("⚠️ Lütfen tüm kalemler için ekipman ve sözleşme seçin.")
                else:
                    with st.spinner("Fatura buluta işleniyor..."):
                        try:
                            if g_is > 0:
                                valid['iskonto_orani'] = valid['iskonto_orani'].replace(0.0, g_is)

                            f_path = ""
                            if file is not None:
                                f_bytes = file.read()

                                # Bulut depolama aktifse GCS'ye yükle, değilse yerel kaydet
                                if gcs_ready:
                                    f_path = storage_utils.upload_invoice_file(
                                        f_bytes, file.name, f_no, str(f_tarih)
                                    )
                                    if f_path is None:
                                        st.error("⚠️ Dosya buluta yüklenemedi. İnternet bağlantınızı kontrol edin.")
                                        st.stop()
                                else:
                                    f_path = os.path.join(UPLOAD_DIR, f"{f_no}_{file.name}")
                                    with open(f_path, "wb") as f:
                                        f.write(f_bytes)

                            with database.get_connection() as conn:
                                database.insert_invoice_rows(conn, f_firma, str(f_tarih), f_no, f_onay, valid, f_path)

                            st.success("✅ Fatura başarıyla kaydedildi ve bulut arşivine yüklendi!")
                            st.balloons()
                            st.session_state['manuel_df'] = pd.DataFrame(
                                columns=['ad', 'miktar', 'birim_fiyat', 'kdv_orani', 'iskonto_orani', 'ekipman', 'sozlesme']
                            )
                            
                            import time
                            time.sleep(4)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Kayıt Hatası: {e}")

    # =========================================================================
    # SAYFA: RAPORLAR & YÖNETİM
    # =========================================================================
    elif menu == "📊 Raporlar & Yönetim":
        st.header("📊 Finansal Analiz ve Yönetim")

        if not HAS_MATPLOTLIB:
            st.warning("⚠️ Gelişmiş görseller için sisteme `matplotlib` kütüphanesini yükleyin.")

        df = database.get_all_invoices()

        if not df.empty:
            df['tarih'] = pd.to_datetime(df['tarih'], errors='coerce')
            df['ay_yil'] = df['tarih'].dt.to_period('M').astype(str)

            # =================================================================
            # FİLTRE PANELİ
            # =================================================================
            with st.expander("🔍 Filtrele", expanded=True):
                f1, f2, f3, f4 = st.columns(4)
                with f1:
                    t_ar = st.date_input(
                        "Tarih Aralığı:",
                        value=(df['tarih'].min().date(), df['tarih'].max().date())
                    )
                with f2:
                    firma_f = st.multiselect(
                        "Firma:",
                        sorted(df['firma'].dropna().unique()),
                        default=sorted(df['firma'].dropna().unique())
                    )
                with f3:
                    ek_f = st.multiselect(
                        "Ekipman:",
                        sorted(df['ekipman_plakasi'].dropna().unique()),
                        default=sorted(df['ekipman_plakasi'].dropna().unique())
                    )
                with f4:
                    sz_f = st.multiselect(
                        "Sözleşme:",
                        sorted(df['sozlesme_adi'].dropna().unique()),
                        default=sorted(df['sozlesme_adi'].dropna().unique())
                    )

            # Filtrelenmiş veri
            f_df = df[
                df['firma'].isin(firma_f) &
                df['ekipman_plakasi'].isin(ek_f) &
                df['sozlesme_adi'].isin(sz_f) &
                (df['tarih'].dt.date >= t_ar[0]) &
                (df['tarih'].dt.date <= t_ar[1])
            ].copy()

            if f_df.empty:
                st.warning("⚠️ Seçilen filtreler için veri bulunamadı.")
            else:
                # =============================================================
                # METRİK KARTLARI
                # =============================================================
                toplam_harcama = f_df['toplam_tutar'].sum()
                toplam_kdv = f_df['kdv_tutari'].sum()
                toplam_iskonto = f_df['iskonto_tutari'].sum()
                fatura_adedi = f_df['fatura_no'].nunique()
                en_cok_firma = (
                    f_df.groupby('firma')['toplam_tutar'].sum().idxmax()
                    if not f_df.empty else "-"
                )
                unique_months = f_df['ay_yil'].nunique()
                aylik_ort = toplam_harcama / unique_months if unique_months > 0 else 0

                m1, m2, m3 = st.columns(3)
                m4, m5, m6 = st.columns(3)
                m1.metric("💰 Toplam Harcama", tl(toplam_harcama))
                m2.metric("📅 Aylık Ortalama", tl(aylik_ort))
                m3.metric("🏷️ Ödenecek KDV", tl(toplam_kdv))
                m4.metric("⭐ En Çok Harcayan Tedarikçi", en_cok_firma)
                m5.metric("📊 Fatura Adedi", fatura_adedi)
                m6.metric("💹 İskonto Kazanç", tl(toplam_iskonto))

                st.markdown("---")

                # =============================================================
                # ANA İÇERİK: Pivot Tablo + Grafik
                # =============================================================
                col_table, col_chart = st.columns([3, 2])

                with col_table:
                    st.subheader("📋 Ekipman & Ay Bazlı Pivot Tablo")
                    try:
                        pivot = pd.pivot_table(
                            f_df,
                            values='toplam_tutar',
                            index='ekipman_plakasi',
                            columns='ay_yil',
                            aggfunc='sum',
                            fill_value=0,
                            margins=True,
                            margins_name='TOPLAM'
                        )
                        def fmt_pivot(v):
                            s = f"{v:,.0f}"
                            s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                            return f"{s} TL"

                        styled_pivot = pivot.style.format(fmt_pivot)
                        if HAS_MATPLOTLIB:
                            styled_pivot = styled_pivot.background_gradient(
                                cmap='Blues', subset=pd.IndexSlice[:, pivot.columns[:-1]]
                            )
                        st.dataframe(styled_pivot, use_container_width=True)
                    except Exception:
                        fallback = (
                            f_df.groupby('ekipman_plakasi')['toplam_tutar']
                            .sum()
                            .reset_index()
                            .rename(columns={'toplam_tutar': 'Toplam (TL)'})
                        )
                        st.dataframe(fallback, use_container_width=True)

                with col_chart:
                    st.subheader("🧨 Harcama Dağılımı")
                    fig = px.pie(
                        f_df,
                        values='toplam_tutar',
                        names='ekipman_plakasi',
                        hole=0.5,
                        template="plotly_dark",
                        color_discrete_sequence=px.colors.sequential.Blues_r
                    )
                    fig.update_layout(margin=dict(t=20, b=20, l=0, r=0), showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")

                # =============================================================
                # FİNANSAL DETAY TABLOSU
                # =============================================================
                t_detay, t_pivot_firma, t_sil = st.tabs([
                    "📂 Fatura Detayları",
                    "🏢 Firma Bazında Analiz",
                    "🗑️ Fatura Silme"
                ])

                with t_detay:
                    grouped = (
                        f_df.groupby('fatura_no')
                        .agg(
                            Firma=('firma', 'first'),
                            Tarih=('tarih', 'first'),
                            Sozlesme=('sozlesme_adi', 'first'),
                            Ekipman=('ekipman_plakasi', 'first'),
                            KDV_Tutari=('kdv_tutari', 'sum'),
                            Iskonto_Tutari=('iskonto_tutari', 'sum'),
                            Toplam_TL=('toplam_tutar', 'sum'),
                            Dosya=('dosya_yolu', 'first')
                        )
                        .reset_index()
                        .sort_values('Tarih', ascending=False)
                    )
                    grouped['Tarih'] = grouped['Tarih'].dt.strftime('%d.%m.%Y')

                    # Görüntü tablosu (dosya_yolu hariç)
                    display_cols = [c for c in grouped.columns if c != 'Dosya']
                    st.dataframe(
                        grouped[display_cols].style.format({
                            'Toplam_TL': lambda v: tl(v),
                            'KDV_Tutari': lambda v: tl(v),
                            'Iskonto_Tutari': lambda v: tl(v),
                        }),
                        use_container_width=True,
                        height=350
                    )

                    if not grouped.empty:
                        sel_f = st.selectbox("Kalem dökümü için seçin:", grouped['fatura_no'])

                        # Fatura belgesini buluttan aç
                        sel_row = grouped[grouped['fatura_no'] == sel_f].iloc[0]
                        dosya_url = sel_row.get('Dosya', '')
                        if dosya_url and str(dosya_url).startswith('https://'):
                            st.markdown(
                                f'<a href="{dosya_url}" target="_blank" '
                                f'style="display:inline-block;background:#2299c5;color:white;'
                                f'padding:8px 18px;border-radius:8px;text-decoration:none;'
                                f'font-weight:700;font-size:0.85rem;">'
                                f'📎 Fatura Belgesini Görüntüle (Bulut)</a>',
                                unsafe_allow_html=True
                            )
                        elif dosya_url and os.path.exists(str(dosya_url)):
                            st.caption(f"📁 Yerel dosya: {dosya_url}")

                        kalem_df = f_df[f_df['fatura_no'] == sel_f][
                            ['kalem_adi', 'miktar', 'birim_fiyat', 'iskonto_orani',
                             'kdv_orani', 'iskonto_tutari', 'kdv_tutari', 'toplam_tutar']
                        ].copy()
                        st.table(
                            kalem_df.style.format({
                                'birim_fiyat': lambda v: tl(v).replace(' TL', ''),
                                'iskonto_tutari': lambda v: tl(v).replace(' TL', ''),
                                'kdv_tutari': lambda v: tl(v).replace(' TL', ''),
                                'toplam_tutar': lambda v: tl(v),
                            })
                        )

                    excel_buf = io.BytesIO()
                    with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
                        grouped[display_cols].to_excel(writer, sheet_name='Fatura Özetleri', index=False)
                        f_df.to_excel(writer, sheet_name='Tüm Kalemler', index=False)
                    excel_buf.seek(0)
                    st.download_button(
                        label="📥 Excel Olarak İndir",
                        data=excel_buf,
                        file_name=f"DGN_Rapor_{date.today().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                with t_pivot_firma:
                    st.subheader("🏢 Firma Bazında Toplam Harcama")
                    firma_ozet = (
                        f_df.groupby('firma')
                        .agg(
                            Fatura_Adedi=('fatura_no', 'nunique'),
                            Iskonto_TL=('iskonto_tutari', 'sum'),
                            KDV_TL=('kdv_tutari', 'sum'),
                            Toplam_TL=('toplam_tutar', 'sum')
                        )
                        .reset_index()
                        .sort_values('Toplam_TL', ascending=False)
                    )
                    styled_firma = firma_ozet.style.format({
                        'Iskonto_TL': lambda v: tl(v),
                        'KDV_TL': lambda v: tl(v),
                        'Toplam_TL': lambda v: tl(v),
                    })
                    if HAS_MATPLOTLIB:
                        styled_firma = styled_firma.background_gradient(cmap='Greens', subset=['Toplam_TL'])

                    st.dataframe(styled_firma, use_container_width=True)

                    fig_bar = px.bar(
                        firma_ozet,
                        x='firma',
                        y='Toplam_TL',
                        template='plotly_dark',
                        color='Toplam_TL',
                        color_continuous_scale='Blues',
                        labels={'Toplam_TL': 'Toplam (TL)', 'firma': 'Firma'}
                    )
                    fig_bar.update_layout(xaxis_tickangle=-30, showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)

                with t_sil:
                    f_sil = st.selectbox("Silinecek Fatura No:", df['fatura_no'].unique())
                    if st.button("Faturası Tamamen Sil", type="primary"):
                        # Buluttaki dosyayı da sil
                        sil_rows = df[df['fatura_no'] == f_sil]
                        if not sil_rows.empty:
                            dosya_yolu = sil_rows.iloc[0].get('dosya_yolu', '')
                            if dosya_yolu and str(dosya_yolu).startswith('https://'):
                                storage_utils.delete_invoice_file(str(dosya_yolu))

                        database.delete_invoice(f_sil)
                        st.warning(f"🗑️ {f_sil} numaralı fatura silindi.")
                        st.rerun()
        else:
            st.info("Henüz kayıtlı fatura verisi bulunmamaktadır.")


# =============================================================================
# GİRİŞ DURUMUNU KONTROL EDEN ANA ROUTER
# =============================================================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    main_app()
else:
    show_login_page()