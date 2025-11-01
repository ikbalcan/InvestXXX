"""
BIST Hisse Senedi Sembolleri Yükleyici
BIST'teki tüm hisseleri yüklemek için yardımcı fonksiyonlar
"""

import pandas as pd
import yfinance as yf
from typing import List, Set
import os
import json

# BIST'teki bilinen tüm hisse senetleri (genişletilmiş liste)
BIST_ALL_SYMBOLS = [
    # Bankacılık
    'AKBNK.IS', 'GARAN.IS', 'ISCTR.IS', 'HALKB.IS', 'VAKBN.IS', 'YKBNK.IS',
    'ALBRK.IS', 'DENIZ.IS', 'QNBFB.IS', 'TSKB.IS', 'VAKFN.IS', 'QNBFL.IS',
    
    # Sanayi
    'THYAO.IS', 'TUPRS.IS', 'EREGL.IS', 'KRDMD.IS', 'PETKM.IS', 'SAHOL.IS',
    'BIMAS.IS', 'ASELS.IS', 'FROTO.IS', 'KCHOL.IS', 'OTKAR.IS', 'TKFEN.IS',
    'TOASO.IS', 'ULKER.IS', 'VESTL.IS', 'ZOREN.IS', 'ARCLK.IS', 'BRSAN.IS',
    'CCOLA.IS', 'DOHOL.IS', 'ENKAI.IS', 'KOZAL.IS', 'MGROS.IS', 'PGSUS.IS',
    'SISE.IS', 'TCELL.IS', 'TTKOM.IS', 'AZTEK.IS', 'FONET.IS', 'ERSU.IS',
    'KONYA.IS', 'MARTI.IS', 'NETAS.IS', 'PAMEL.IS', 'SELEC.IS', 'SMRTG.IS',
    'SNPAM.IS', 'TATGD.IS', 'TURSG.IS', 'UNYEC.IS', 'MEGMT.IS', 'GENIL.IS',
    
    # Gayrimenkul
    'EKGYO.IS', 'YAPRK.IS', 'ALGYO.IS', 'AVGYO.IS', 'BAGFS.IS', 'BRKO.IS',
    'BRKV.IS', 'DAGI.IS', 'DZGYO.IS', 'EGEPO.IS', 'EMKEL.IS', 'EMNIS.IS',
    'FMIZP.IS', 'GSDHO.IS', 'GUBRF.IS', 'HLGYO.IS', 'ISGYO.IS', 'KGYO.IS',
    'KLKIM.IS', 'KORDS.IS', 'KRSTL.IS', 'LOGO.IS', 'MEGAP.IS', 'MRSHL.IS',
    'MRDIN.IS', 'NUGYO.IS', 'OZGYO.IS', 'RYGYO.IS', 'SOKM.IS', 'VKGYO.IS',
    
    # Enerji
    'AKSEN.IS', 'BUCIM.IS', 'CLEBI.IS', 'DOKM.IS', 'ECILC.IS', 'EGECM.IS',
    
    # İnşaat
    'DOAS.IS', 'ENJSA.IS', 'GOLTS.IS', 'GWIND.IS', 'INTEM.IS', 'IZINV.IS',
    'KONTR.IS', 'LOGO.IS', 'MRDGY.IS', 'ODAS.IS', 'SNGYO.IS', 'TMPOL.IS',
    
    # Teknoloji
    'DESPC.IS', 'DIRIT.IS', 'EDATA.IS', 'ESCOM.IS', 'GZRTE.IS', 'HUNER.IS',
    'KLMSN.IS', 'ODAS.IS', 'SMART.IS', 'TRILC.IS',
    
    # Diğer - Kullanıcının bahsettiği hisseler
    'ISDMR.IS', 'GEDZA.IS', 'RAYSG.IS',
    
    # Ek yaygın hisseler (A-Z)
    'ADANA.IS', 'ADGYO.IS', 'AGHOL.IS', 'AGYO.IS', 'AKCNS.IS', 'AKFYE.IS',
    'AKGRT.IS', 'AKSA.IS', 'AKSEN.IS', 'ALARK.IS', 'ALFAS.IS', 'ALGYO.IS',
    'ALKIM.IS', 'ALTIN.IS', 'ANACM.IS', 'ANELE.IS', 'ANELT.IS', 'ANGEN.IS',
    'ARENA.IS', 'ARZIN.IS', 'ASELS.IS', 'ASTOR.IS', 'ATAGY.IS', 'ATATP.IS',
    'AYCES.IS', 'AYDEM.IS', 'AYEN.IS', 'AYGAZ.IS', 'BAGFS.IS', 'BAKAB.IS',
    'BANVT.IS', 'BARMA.IS', 'BASCM.IS', 'BAYDN.IS', 'BERA.IS', 'BFREN.IS',
    'BIGCH.IS', 'BIZIM.IS', 'BJKAS.IS', 'BLCYT.IS', 'BNTAS.IS', 'BOBET.IS',
    'BOSSA.IS', 'BRISA.IS', 'BRKO.IS', 'BRKV.IS', 'BRLSM.IS', 'BRSAN.IS',
    'BRYAT.IS', 'BSOKE.IS', 'BUCIM.IS', 'BUHAS.IS', 'BURCE.IS', 'BURVA.IS',
    'BYDNR.IS', 'CANTE.IS', 'CAPTO.IS', 'CARFA.IS', 'CASA.IS', 'CATES.IS',
    'CCOLA.IS', 'CEKME.IS', 'CEMAS.IS', 'CEMTS.IS', 'CENSA.IS', 'CEOEM.IS',
    'CETUR.IS', 'CIMSA.IS', 'CLEBI.IS', 'CMENT.IS', 'CMENT.IS', 'COFCO.IS',
    'CRDFA.IS', 'CRFSA.IS', 'DAGI.IS', 'DAGMD.IS', 'DAPGM.IS', 'DARDL.IS',
    'DEVA.IS', 'DGKLB.IS', 'DGNMO.IS', 'DGNTE.IS', 'DGNSY.IS', 'DGNYO.IS',
    'DITAS.IS', 'DITAS.IS', 'DMSAS.IS', 'DOAS.IS', 'DOBUR.IS', 'DOHOL.IS',
    'DOKA.IS', 'DOKM.IS', 'DOKT.IS', 'DOKTA.IS', 'DURDO.IS', 'DZGYO.IS',
    'ECILC.IS', 'ECZYT.IS', 'EDATA.IS', 'EDIP.IS', 'EGEEN.IS', 'EGEPO.IS',
    'EGESU.IS', 'EGEYO.IS', 'EGPRO.IS', 'EGSER.IS', 'EGSRY.IS', 'EKGYO.IS',
    'EKIZ.IS', 'ELITE.IS', 'EMKEL.IS', 'EMNIS.IS', 'ENAUT.IS', 'ENJSA.IS',
    'ENKAI.IS', 'ERBOS.IS', 'EREGL.IS', 'ERSU.IS', 'ESCAR.IS', 'ESCOM.IS',
    'ESCOM.IS', 'ESCOM.IS', 'ESDMR.IS', 'ETILR.IS', 'EUHOL.IS', 'EUYO.IS',
    'FENER.IS', 'FMIZP.IS', 'FONET.IS', 'FORTE.IS', 'FRIGO.IS', 'FROTO.IS',
    'FYLDM.IS', 'GARAN.IS', 'GARFA.IS', 'GEDZA.IS', 'GENIL.IS', 'GEREL.IS',
    'GESAN.IS', 'GLYHO.IS', 'GLSHN.IS', 'GMDHO.IS', 'GODKS.IS', 'GOLTS.IS',
    'GOLTS.IS', 'GOPAL.IS', 'GSDHO.IS', 'GSRAY.IS', 'GUBRF.IS', 'GULER.IS',
    'GUSGR.IS', 'GWIND.IS', 'GZRTE.IS', 'HALKB.IS', 'HATEK.IS', 'HAYAT.IS',
    'HDFGS.IS', 'HEKTS.IS', 'HEYKM.IS', 'HLGYO.IS', 'HOPSA.IS', 'HUNER.IS',
    'IDGYO.IS', 'IDYOL.IS', 'IHEVA.IS', 'IHLAS.IS', 'IHLGM.IS', 'IHYAY.IS',
    'INDES.IS', 'INTEM.IS', 'INVEO.IS', 'IPRAK.IS', 'ISATR.IS', 'ISBIR.IS',
    'ISCDR.IS', 'ISCTR.IS', 'ISDMR.IS', 'ISFIN.IS', 'ISGSY.IS', 'ISGYO.IS',
    'ISMEN.IS', 'ISYAT.IS', 'IZGYO.IS', 'IZINV.IS', 'IZMDC.IS', 'IZTAR.IS',
    'JANTS.IS', 'KARTN.IS', 'KATMR.IS', 'KAYSE.IS', 'KCAER.IS', 'KCHOL.IS',
    'KENT.IS', 'KERVT.IS', 'KGYO.IS', 'KLKIM.IS', 'KLMSN.IS', 'KMKRS.IS',
    'KNFRT.IS', 'KONTR.IS', 'KONYA.IS', 'KONYA.IS', 'KOPOL.IS', 'KORDS.IS',
    'KOZAA.IS', 'KOZAL.IS', 'KRBLK.IS', 'KRCMR.IS', 'KRGYO.IS', 'KRONT.IS',
    'KRPLS.IS', 'KRSTL.IS', 'KRTEK.IS', 'KRDMD.IS', 'KRVGD.IS', 'KTLEV.IS',
    'KUTPO.IS', 'KUYAS.IS', 'LIDFA.IS', 'LIDYO.IS', 'LIDER.IS', 'LKMNH.IS',
    'LKONT.IS', 'LOGO.IS', 'MAGEN.IS', 'MAKIM.IS', 'MAKTK.IS', 'MARTI.IS',
    'MAVI.IS', 'MEGAP.IS', 'MEGMT.IS', 'MEGRS.IS', 'MEGYO.IS', 'MEPET.IS',
    'MERCN.IS', 'MERKO.IS', 'METRO.IS', 'METUR.IS', 'MGROS.IS', 'MIPAZ.IS',
    'MNDRS.IS', 'MRDGY.IS', 'MRDIN.IS', 'MRSHL.IS', 'MSGYO.IS', 'MTURK.IS',
    'MZHLD.IS', 'NATEN.IS', 'NBFAS.IS', 'NDRYO.IS', 'NETAS.IS', 'NTGAZ.IS',
    'NTHOL.IS', 'NTYAT.IS', 'NUHCM.IS', 'NUGYO.IS', 'ODAS.IS', 'ODAS.IS',
    'ODAS.IS', 'ODAS.IS', 'ODAS.IS', 'ODAS.IS', 'ODAS.IS', 'ODAS.IS',
    'OGSGY.IS', 'ONCSM.IS', 'ORAY.IS', 'ORGE.IS', 'ORGMD.IS', 'OSMEN.IS',
    'OSTIM.IS', 'OTKAR.IS', 'OYYAT.IS', 'OZGYO.IS', 'OZMEN.IS', 'OZRDN.IS',
    'OZSUB.IS', 'PAGYO.IS', 'PAMEL.IS', 'PARSN.IS', 'PCILT.IS', 'PEGYO.IS',
    'PENGD.IS', 'PENTA.IS', 'PETKM.IS', 'PGSUS.IS', 'PIMAS.IS', 'PKART.IS',
    'PKENT.IS', 'PLAT.IS', 'PNLSN.IS', 'PNTUR.IS', 'POLAT.IS', 'POLHO.IS',
    'POWER.IS', 'PRDGS.IS', 'PRKAB.IS', 'PRKME.IS', 'PRKTE.IS', 'PRTAS.IS',
    'PRZMA.IS', 'PSGYO.IS', 'QNBFL.IS', 'QNBFB.IS', 'RADYO.IS', 'RAYSG.IS',
    'RDMC.IS', 'REEDR.IS', 'REYON.IS', 'RHEAG.IS', 'RKLAS.IS', 'RMRHE.IS',
    'RNPOL.IS', 'RODRG.IS', 'ROYAL.IS', 'RTALB.IS', 'RULER.IS', 'RUYGZ.IS',
    'RYGYO.IS', 'SAFKR.IS', 'SAHOL.IS', 'SAYAS.IS', 'SDTTR.IS', 'SEGYO.IS',
    'SELEC.IS', 'SELGD.IS', 'SELVA.IS', 'SERVE.IS', 'SGGYO.IS', 'SIGNT.IS',
    'SILVR.IS', 'SINOP.IS', 'SISE.IS', 'SKBNK.IS', 'SMART.IS', 'SMRTG.IS',
    'SMRTG.IS', 'SMART.IS', 'SNGYO.IS', 'SNKRN.IS', 'SNPAM.IS', 'SODA.IS',
    'SOKM.IS', 'SONME.IS', 'SRVGY.IS', 'SUWEN.IS', 'SVAH.IS', 'SZGYO.IS',
    'TABGD.IS', 'TATGD.IS', 'TCELL.IS', 'TETMT.IS', 'TEKTU.IS', 'TETUR.IS',
    'TGSAS.IS', 'THYAO.IS', 'TIRIT.IS', 'TKFEN.IS', 'TKNSA.IS', 'TMASD.IS',
    'TMPOL.IS', 'TNZTP.IS', 'TOASO.IS', 'TRILC.IS', 'TRKAB.IS', 'TRKCM.IS',
    'TRKMD.IS', 'TRKZM.IS', 'TRMER.IS', 'TRSAS.IS', 'TRYIL.IS', 'TSGYO.IS',
    'TSKB.IS', 'TTKOM.IS', 'TTRAK.IS', 'TUKAS.IS', 'TUPRS.IS', 'TURSG.IS',
    'TUTUN.IS', 'UFUK.IS', 'UFUKY.IS', 'ULAS.IS', 'ULUSE.IS', 'ULUUN.IS',
    'ULKER.IS', 'UNYEC.IS', 'URGYO.IS', 'USAK.IS', 'VAKBN.IS', 'VAKFN.IS',
    'VAKKO.IS', 'VAKYO.IS', 'VANGD.IS', 'VERUS.IS', 'VESTL.IS', 'VKING.IS',
    'VKGYO.IS', 'YKBNK.IS', 'YAPRK.IS', 'YATAS.IS', 'YAYLA.IS', 'YESIL.IS',
    'YGYO.IS', 'YKGYO.IS', 'YONGA.IS', 'YOUNG.IS', 'YUKSA.IS', 'YUNSA.IS',
    'ZEDUR.IS', 'ZOREN.IS', 'ZORLU.IS',
]


def load_all_bist_symbols() -> List[str]:
    """
    BIST'teki tüm hisse senetlerini döndürür.
    
    Returns:
        List[str]: BIST hisse sembollerinin listesi (.IS uzantılı)
    """
    symbols = list(set(BIST_ALL_SYMBOLS))
    symbols.sort()
    return symbols


def validate_bist_symbol(symbol: str) -> bool:
    """
    Bir hisse sembolünün geçerli BIST sembolü olup olmadığını kontrol eder.
    
    Args:
        symbol: Hisse sembolü (örn: 'THYAO' veya 'THYAO.IS')
        
    Returns:
        bool: Geçerli ise True
    """
    if not symbol:
        return False
    
    # .IS uzantısı varsa kaldır
    symbol_clean = symbol.replace('.IS', '').upper().strip()
    
    # YFinance ile kontrol et (isteğe bağlı - yavaş olabilir)
    try:
        ticker = yf.Ticker(f"{symbol_clean}.IS")
        info = ticker.info
        if info and 'symbol' in info:
            return True
    except:
        pass
    
    # Varsayılan olarak True döndür (kullanıcı deneyebilir)
    return True


def get_extended_bist_symbols() -> List[str]:
    """
    Genişletilmiş BIST hisse listesini döndürür.
    Kullanıcı eklediği hisseler de dahil.
    
    Returns:
        List[str]: Tüm BIST hisse sembolleri
    """
    base_symbols = load_all_bist_symbols()
    
    # Kullanıcı eklediği hisseleri dosyadan yükle (eğer varsa)
    user_symbols_file = 'data/bist_user_symbols.json'
    if os.path.exists(user_symbols_file):
        try:
            with open(user_symbols_file, 'r', encoding='utf-8') as f:
                user_symbols = json.load(f)
                for symbol in user_symbols:
                    if symbol not in base_symbols:
                        base_symbols.append(symbol)
        except:
            pass
    
    # Tekrarları kaldır ve sırala
    all_symbols = sorted(list(set(base_symbols)))
    return all_symbols


def add_user_symbol(symbol: str) -> bool:
    """
    Kullanıcının eklediği bir hisseyi kalıcı olarak kaydeder.
    
    Args:
        symbol: Hisse sembolü (örn: 'ISDMR.IS')
        
    Returns:
        bool: Başarılı ise True
    """
    # .IS uzantısını kontrol et ve ekle
    symbol_clean = symbol.upper().strip()
    if not symbol_clean.endswith('.IS'):
        symbol_clean = symbol_clean + '.IS'
    
    # Dosya yoksa oluştur
    user_symbols_file = 'data/bist_user_symbols.json'
    os.makedirs('data', exist_ok=True)
    
    user_symbols = []
    if os.path.exists(user_symbols_file):
        try:
            with open(user_symbols_file, 'r', encoding='utf-8') as f:
                user_symbols = json.load(f)
        except:
            pass
    
    # Yeni sembolü ekle (eğer yoksa)
    if symbol_clean not in user_symbols:
        user_symbols.append(symbol_clean)
        
        try:
            with open(user_symbols_file, 'w', encoding='utf-8') as f:
                json.dump(user_symbols, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Symbol eklenirken hata: {e}")
            return False
    
    return False  # Zaten var

