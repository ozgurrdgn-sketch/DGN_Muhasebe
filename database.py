import sqlite3
import pandas as pd
from contextlib import contextmanager

# --- VERİTABANI SABİTLERİ ---
DB_NAME = "dgn_muhasebe.db"


@contextmanager
def get_connection():
    """
    Güvenli SQLite bağlantı context manager'ı.
    Kullanım: `with database.get_connection() as conn:`

    - Başarılı çıkışta: otomatik COMMIT yapar.
    - Hata durumunda: otomatik ROLLBACK yapar.
    - Her durumda: conn.close() ile bağlantıyı kapatır.
    """
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



def init_db():
    """Veritabanı tablolarını oluşturur, eksik sütunları ekler."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS faturalar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firma TEXT, tarih TEXT, fatura_no TEXT, onaylayan TEXT,
                    kalem_adi TEXT, miktar REAL, birim_fiyat REAL,
                    iskonto_orani REAL, iskonto_tutari REAL,
                    kdv_orani REAL, kdv_tutari REAL, toplam_tutar REAL,
                    ekipman_plakasi TEXT, sozlesme_adi TEXT, dosya_yolu TEXT)''')

    # Eksik sütun kontrolü (migration)
    c.execute("PRAGMA table_info(faturalar)")
    cols = [col[1] for col in c.fetchall()]
    if 'iskonto_orani' not in cols:
        c.execute('ALTER TABLE faturalar ADD COLUMN iskonto_orani REAL DEFAULT 0')
    if 'iskonto_tutari' not in cols:
        c.execute('ALTER TABLE faturalar ADD COLUMN iskonto_tutari REAL DEFAULT 0')

    c.execute('CREATE TABLE IF NOT EXISTS ekipmanlar (id INTEGER PRIMARY KEY AUTOINCREMENT, plaka TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS sozlesmeler (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT UNIQUE)')
    conn.commit()
    conn.close()


def get_list(table: str, col: str) -> list:
    """Belirtilen tablodaki sütun değerlerini liste olarak döndürür."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT {col} FROM {table}", conn)
    conn.close()
    return df[col].tolist()


def get_all_invoices() -> pd.DataFrame:
    """Tüm fatura kayıtlarını DataFrame olarak döndürür."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM faturalar", conn)
    conn.close()
    return df


def check_duplicate_invoice(fatura_no: str) -> bool:
    """Verilen fatura no'su için mükerrer kayıt varsa True döndürür."""
    conn = sqlite3.connect(DB_NAME)
    dup = pd.read_sql_query("SELECT id FROM faturalar WHERE fatura_no = ?", conn, params=(fatura_no,))
    conn.close()
    return not dup.empty


def insert_invoice_rows(conn, f_firma, f_tarih, f_no, f_onay, valid_rows, f_path: str):
    """Fatura kalemlerini veritabanına toplu olarak ekler."""
    for _, r in valid_rows.fillna(0).iterrows():
        m = float(r['miktar'])
        bf = float(r['birim_fiyat'])
        iso = float(r['iskonto_orani'])
        ko = float(r['kdv_orani'])
        net = (m * bf) * (1 - iso / 100)
        kt = net * (ko / 100)
        conn.execute(
            """INSERT INTO faturalar
               (firma, tarih, fatura_no, onaylayan, kalem_adi, miktar, birim_fiyat,
                iskonto_orani, iskonto_tutari, kdv_orani, kdv_tutari, toplam_tutar,
                ekipman_plakasi, sozlesme_adi, dosya_yolu)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f_firma, f_tarih, f_no, f_onay,
             r['ad'], m, bf, iso, (m * bf) * (iso / 100),
             ko, kt, net + kt,
             r['ekipman'], r['sozlesme'], f_path)
        )


def delete_invoice(fatura_no: str):
    """Verilen fatura no'suna ait tüm kalemleri veritabanından siler."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM faturalar WHERE fatura_no = ?", (fatura_no,))
    conn.commit()
    conn.close()


def add_ekipman(plaka: str) -> bool:
    """Yeni ekipman ekler. Başarılıysa True, mükerrerse False döndürür."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO ekipmanlar (plaka) VALUES (?)", (plaka,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def add_sozlesme(ad: str) -> bool:
    """Yeni sözleşme ekler. Başarılıysa True, mükerrerse False döndürür."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO sozlesmeler (ad) VALUES (?)", (ad,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
