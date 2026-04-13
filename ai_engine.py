import json
import streamlit as st
import google.generativeai as genai
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List


# =============================================================================
# PYDANTIC ŞEMALARI — Katı Tip Güvenliği ve Veri Doğrulama
# =============================================================================

class ItemSchema(BaseModel):
    """
    Fatura içindeki tek bir kalemi temsil eder.
    - miktar: 0'dan büyük olmalı (negatif/sıfır kabul edilmez)
    - birim_fiyat: 0 veya üzeri olmalı
    - kdv_orani: tamsayı (Türkiye KDV oranları: 1, 10, 20)
    """
    ad: str
    miktar: float = Field(default=1.0, gt=0, description="Miktar — sıfırdan büyük olmalı")
    birim_fiyat: float = Field(default=0.0, ge=0, description="Birim fiyat — negatif olamaz")
    iskonto_orani: float = Field(default=0.0, ge=0, le=100)
    kdv_orani: int = Field(default=20, ge=0, le=100)

    @field_validator('miktar', mode='before')
    @classmethod
    def coerce_miktar(cls, v):
        """Miktar alanını float'a dönüştürür. Geçersiz metin gelirse 1.0 varsayar, negatif/sıfır ise Pydantic gt=0 ile reddeder."""
        try:
            return float(v)
        except (TypeError, ValueError):
            return 1.0

    @field_validator('birim_fiyat', 'iskonto_orani', mode='before')
    @classmethod
    def coerce_to_float(cls, v):
        """Fiyat/iskonto alanlarını güvenle float'a dönüştürür."""
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    @field_validator('kdv_orani', mode='before')
    @classmethod
    def coerce_to_int(cls, v):
        """KDV oranını güvenle int'e dönüştürür."""
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 20

    @field_validator('ad', mode='before')
    @classmethod
    def coerce_ad(cls, v):
        """Kalem adını güvenle string'e çevirir."""
        if v is None or str(v).strip() == "":
            return "Tanımsız Kalem"
        return str(v).strip()

    # --- HESAPLANAN ALANLAR (Toplam hesabı AI'a bırakılmaz) ---
    @property
    def iskonto_tutari(self) -> float:
        return (self.miktar * self.birim_fiyat) * (self.iskonto_orani / 100)

    @property
    def net_tutar(self) -> float:
        return (self.miktar * self.birim_fiyat) - self.iskonto_tutari

    @property
    def kdv_tutari(self) -> float:
        return self.net_tutar * (self.kdv_orani / 100)

    @property
    def toplam_tutar(self) -> float:
        return self.net_tutar + self.kdv_tutari


class InvoiceSchema(BaseModel):
    """
    Fatura ana şeması — AI'dan gelen tüm veriyi doğrular.
    Tarih formatı YYYY-MM-DD beklenir.
    """
    firma: str = "Bilinmiyor"
    tarih: str = ""
    fatura_no: str = ""
    kalemler: List[ItemSchema] = []

    @field_validator('firma', 'tarih', 'fatura_no', mode='before')
    @classmethod
    def coerce_to_str(cls, v):
        if v is None:
            return ""
        return str(v).strip()


# =============================================================================
# API ANAHTARı YÖNETİMİ — st.secrets ile güvenli okuma
# =============================================================================

def _get_api_key() -> str:
    import os
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        return st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error(
            "🔑 **Gemini API Anahtarı Bulunamadı!**\n\n"
            "`.streamlit/secrets.toml` dosyasını oluşturun ve içine şunu ekleyin:\n\n"
            '```\nGEMINI_API_KEY = "sizin-api-anahtariniz"\n```'
        )
        st.stop()


# =============================================================================
# MODEL SEÇME
# =============================================================================

def get_working_model():
    """Kullanılabilir en uygun Gemini modelini bulup döndürür."""
    try:
        api_key = _get_api_key()
        genai.configure(api_key=api_key)

        models = [
            m.name for m in genai.list_models()
            if 'generateContent' in m.supported_generation_methods
        ]
        targets = [
            'models/gemini-1.5-flash',
            'models/gemini-1.5-flash-latest',
            'gemini-1.5-flash'
        ]
        for t in targets:
            if t in models:
                return genai.GenerativeModel(t)
        return genai.GenerativeModel(models[0])
    except Exception as e:
        st.error(f"Model başlatma hatası: {e}")
        return None


# =============================================================================
# FATURA ANALİZİ — Gemini + Pydantic Doğrulama
# =============================================================================

def _clean_ai_response(text: str) -> str:
    """AI yanıtındaki Markdown işaretlerini temizler, saf JSON çıkarır."""
    return (
        text
        .strip()
        .removeprefix("```json")
        .removeprefix("```JSON")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )


def analyze_invoice(file_bytes: bytes, mime_type: str) -> dict | None:
    """
    Fatura görselini Gemini'a gönderir → JSON alır → Pydantic ile doğrular.
    
    Döndürdüğü dict şu yapıdadır:
    {
        'firma': str,
        'tarih': str,
        'fatura_no': str,
        'kalemler': [{'ad':str, 'miktar':float, 'birim_fiyat':float, ...}]
    }
    Hata durumunda None döndürür, uygulama asla çökmez.
    """
    try:
        model = get_working_model()
        if model is None:
            return None

        prompt = (
            "Sen DGN Denizcilik muhasebe uzmanısın. "
            "Görevin bu faturadaki bilgileri çıkarmaktır.\n\n"
            "KESİN KURALLAR:\n"
            "1. YALNIZCA saf JSON döndür. Açıklama, yorum veya markdown bloğu (```json) YAZMA.\n"
            "2. DGN DENİZCİLİK ALICIDIR. 'firma' alanına faturayı KESEN SATICI firmanın adını yaz.\n"
            "3. Tarih formatı zorunlu: YYYY-MM-DD\n"
            "4. Sayısal alanlar (miktar, birim_fiyat, iskonto_orani, kdv_orani) HER ZAMAN sayı olmalı, asla metin olmamalı.\n"
            "5. miktar her zaman 0'dan büyük bir sayı olmalı.\n"
            "6. kdv_orani tamsayı olmalı (genellikle 1, 10 veya 20).\n"
            "7. Toplam tutar hesaplama — bunu hesaplama, sadece ham değerleri ver.\n\n"
            "ZORUNLU JSON FORMATI:\n"
            '{"firma": "", "tarih": "YYYY-MM-DD", "fatura_no": "", '
            '"kalemler": [{"ad": "", "miktar": 1, "birim_fiyat": 0.0, '
            '"iskonto_orani": 0.0, "kdv_orani": 20}]}'
        )

        response = model.generate_content([
            prompt,
            {'mime_type': mime_type, 'data': file_bytes}
        ])

        clean_json = _clean_ai_response(response.text)

        # --- PYDANTIC model_validate_json İLE DOĞRULAMA ---
        validated = InvoiceSchema.model_validate_json(clean_json)
        return validated.model_dump()

    except json.JSONDecodeError as e:
        st.error(f"❌ **JSON Ayrıştırma Hatası:** AI geçersiz format döndürdü.\n\n`{e}`")
        return None

    except ValidationError as e:
        # Kullanıcıya hangi alanların hatalı olduğunu detaylı göster
        hata_detaylari = []
        for err in e.errors():
            alan = " → ".join(str(x) for x in err['loc'])
            mesaj = err['msg']
            hata_detaylari.append(f"• **{alan}**: {mesaj}")

        st.error(
            f"⚠️ **Veri Doğrulama Hatası** — {e.error_count()} alan beklenen formata uymuyor:\n\n"
            + "\n".join(hata_detaylari)
        )
        return None

    except Exception as e:
        st.error(f"AI Analiz Hatası: {e}")
        return None
