"""
DGN Denizcilik — Google Cloud Storage (GCS) Entegrasyon Modülü

Fatura dosyalarını yerel disk yerine Google Cloud Storage'a yükler.
Bucket: dgn-fatura-arsivi
Klasör yapısı: faturalar/YYYY-MM/FaturaNo_DosyaAdi.ext

Kimlik doğrulama: Proje kök dizinindeki service_account.json dosyası
"""

import os
import streamlit as st
from datetime import date

# =============================================================================
# SABİTLER
# =============================================================================
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_PATH = os.path.join(_BASE_DIR, "service_account.json")
BUCKET_NAME = "dgn-fatura-arsivi"

# =============================================================================
# GCS İstemci Başlatma — Lazy Singleton
# =============================================================================

# google-cloud-storage kurulu mu kontrol et
try:
    from google.cloud import storage as gcs_storage
    from google.oauth2 import service_account
    HAS_GCS = True
except ImportError:
    HAS_GCS = False


def _get_gcs_client():
    """
    GCS istemcisini session_state üzerinden singleton olarak döndürür.
    İlk çağrıda service_account.json ile kimlik doğrulaması yapar.

    Returns:
        google.cloud.storage.Client | None
    """
    if not HAS_GCS:
        st.error(
            "☁️ **Google Cloud Storage kütüphanesi bulunamadı!**\n\n"
            "Lütfen terminalde şu komutu çalıştırın:\n\n"
            "```\npip install google-cloud-storage\n```"
        )
        return None

    if "gcs_client" not in st.session_state:
        if not os.path.exists(SERVICE_ACCOUNT_PATH):
            st.error(
                "🔑 **GCS Kimlik Doğrulama Dosyası Bulunamadı!**\n\n"
                f"Beklenen konum: `{SERVICE_ACCOUNT_PATH}`\n\n"
                "Google Cloud Console → IAM → Service Accounts bölümünden\n"
                "bir JSON anahtar dosyası indirip proje kök dizinine kopyalayın."
            )
            return None

        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_PATH
            )
            client = gcs_storage.Client(credentials=credentials, project=credentials.project_id)
            st.session_state["gcs_client"] = client
        except Exception as e:
            st.error(f"☁️ **GCS Bağlantı Hatası:** {e}")
            return None

    return st.session_state["gcs_client"]


def _get_bucket():
    """
    GCS bucket nesnesini döndürür.

    Returns:
        google.cloud.storage.Bucket | None
    """
    client = _get_gcs_client()
    if client is None:
        return None

    try:
        bucket = client.bucket(BUCKET_NAME)
        # Bucket'ın var olup olmadığını doğrula (hafif bir HEAD isteği)
        if not bucket.exists():
            st.error(
                f"☁️ **Bucket bulunamadı:** `{BUCKET_NAME}`\n\n"
                "Google Cloud Console üzerinden bu bucket'ı oluşturun\n"
                "veya `BUCKET_NAME` sabitini güncelleyin."
            )
            return None
        return bucket
    except Exception as e:
        st.error(f"☁️ **Bucket Erişim Hatası:** {e}")
        return None


# =============================================================================
# DOSYA YÜKLEME
# =============================================================================

def upload_invoice_file(
    file_bytes: bytes,
    file_name: str,
    fatura_no: str,
    fatura_tarih: str = ""
) -> str | None:
    """
    Fatura dosyasını GCS bucket'ına yükler.

    Klasör yapısı: faturalar/YYYY-MM/FaturaNo_DosyaAdi.ext
    Örnek: faturalar/2026-04/FTR001_fatura.pdf

    Args:
        file_bytes: Dosya içeriği (binary)
        file_name:  Orijinal dosya adı (örn: fatura.pdf)
        fatura_no:  Fatura numarası (klasör/blob adında kullanılır)
        fatura_tarih: Fatura tarihi (YYYY-MM-DD formatında). Boşsa bugünün tarihi kullanılır.

    Returns:
        str: Yüklenen dosyanın Public URL'i. Hata durumunda None.
    """
    bucket = _get_bucket()
    if bucket is None:
        return None

    # Tarih klasör yapısını oluştur
    try:
        if fatura_tarih and len(fatura_tarih) >= 7:
            yil_ay = fatura_tarih[:7]  # "2026-04"
        else:
            yil_ay = date.today().strftime("%Y-%m")
    except Exception:
        yil_ay = date.today().strftime("%Y-%m")

    # Güvenli dosya adı oluştur (özel karakterleri temizle)
    safe_name = file_name.replace(" ", "_")
    blob_name = f"faturalar/{yil_ay}/{fatura_no}_{safe_name}"

    try:
        blob = bucket.blob(blob_name)

        # Content-Type belirle
        ext = os.path.splitext(file_name)[1].lower()
        content_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }
        content_type = content_types.get(ext, "application/octet-stream")

        blob.upload_from_string(file_bytes, content_type=content_type)

        # Public URL oluştur
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

        return public_url

    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Forbidden" in error_msg:
            st.error(
                "🔒 **Yetki Hatası!** Service account'ın bu bucket'a yazma yetkisi yok.\n\n"
                "Google Cloud Console → IAM bölümünden service account'a\n"
                "`Storage Object Admin` rolünü atayın."
            )
        elif "timeout" in error_msg.lower() or "connectionerror" in error_msg.lower():
            st.error(
                "🌐 **İnternet Bağlantı Hatası!** Dosya buluta yüklenemedi.\n\n"
                "İnternet bağlantınızı kontrol edip tekrar deneyin."
            )
        else:
            st.error(f"☁️ **Dosya Yükleme Hatası:** {e}")
        return None


# =============================================================================
# DOSYA SİLME (İleride fatura silme işlemiyle entegre edilecek)
# =============================================================================

def delete_invoice_file(blob_name_or_url: str) -> bool:
    """
    GCS'deki fatura dosyasını siler.

    Args:
        blob_name_or_url: Blob adı veya tam URL

    Returns:
        bool: Silme başarılıysa True
    """
    if not blob_name_or_url:
        return True  # Dosya yolu yoksa sessizce geç

    bucket = _get_bucket()
    if bucket is None:
        return False

    # URL'den blob adını çıkar
    prefix = f"https://storage.googleapis.com/{BUCKET_NAME}/"
    if blob_name_or_url.startswith(prefix):
        blob_name = blob_name_or_url[len(prefix):]
    else:
        blob_name = blob_name_or_url

    try:
        blob = bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
        return True
    except Exception as e:
        st.warning(f"☁️ Bulut dosya silme uyarısı: {e}")
        return False


# =============================================================================
# BAĞLANTI TESTİ (Sidebar veya yönetim panelinden çağrılabilir)
# =============================================================================

def test_connection() -> bool:
    """
    GCS bağlantısını test eder.

    Returns:
        bool: Bağlantı başarılıysa True
    """
    bucket = _get_bucket()
    return bucket is not None
