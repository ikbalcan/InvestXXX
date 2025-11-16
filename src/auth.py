"""
Kullanıcı Authentication Modülü
Streamlit ile entegre kullanıcı girişi sistemi
"""

import streamlit as st
from src.database import Database
from typing import Optional
import os
import json
import hashlib

# Remember me dosyası
REMEMBER_ME_FILE = "logs/.remember_me.json"

def init_session_state():
    """Session state'i başlat ve remember me'den yükle"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    # Remember me kontrolü - sadece authenticated değilse
    if not st.session_state.authenticated:
        load_remembered_user()

def save_remembered_user(username: str, user_id: int):
    """Kullanıcı bilgilerini remember me dosyasına kaydet"""
    os.makedirs(os.path.dirname(REMEMBER_ME_FILE), exist_ok=True)
    # Basit bir hash ile kullanıcı bilgisini sakla (güvenlik için)
    data = {
        'username': username,
        'user_id': user_id,
        'hash': hashlib.md5(f"{username}_{user_id}".encode()).hexdigest()
    }
    with open(REMEMBER_ME_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def load_remembered_user():
    """Remember me dosyasından kullanıcı bilgilerini yükle"""
    if os.path.exists(REMEMBER_ME_FILE):
        try:
            with open(REMEMBER_ME_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Hash doğrulaması
                expected_hash = hashlib.md5(f"{data['username']}_{data['user_id']}".encode()).hexdigest()
                if data.get('hash') == expected_hash:
                    st.session_state.authenticated = True
                    st.session_state.user_id = data['user_id']
                    st.session_state.username = data['username']
                    return True
        except:
            pass
    return False

def clear_remembered_user():
    """Remember me dosyasını sil"""
    if os.path.exists(REMEMBER_ME_FILE):
        try:
            os.remove(REMEMBER_ME_FILE)
        except:
            pass

def show_login_page(db: Database) -> Optional[int]:
    """Giriş sayfasını göster ve kullanıcı ID'sini döndür"""
    st.title("🔐 Kullanıcı Girişi")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        st.markdown("### Giriş Yap")
        username = st.text_input("Kullanıcı Adı", key="login_username", value=st.session_state.get('username', ''))
        password = st.text_input("Şifre", type="password", key="login_password")
        remember_me = st.checkbox("Beni Hatırla", key="remember_me", value=True)
        
        if st.button("Giriş Yap", type="primary", use_container_width=True):
            if username and password:
                user = db.authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user['id']
                    st.session_state.username = user['username']
                    
                    # Remember me özelliği
                    if remember_me:
                        save_remembered_user(user['username'], user['id'])
                    else:
                        clear_remembered_user()
                    
                    st.success(f"✅ Hoş geldiniz, {user['username']}!")
                    st.rerun()
                else:
                    st.error("❌ Kullanıcı adı veya şifre hatalı!")
            else:
                st.warning("⚠️ Lütfen kullanıcı adı ve şifre girin.")
    
    with tab2:
        st.markdown("### Yeni Kullanıcı Kaydı")
        new_username = st.text_input("Kullanıcı Adı", key="register_username")
        new_email = st.text_input("E-posta (Opsiyonel)", key="register_email")
        new_password = st.text_input("Şifre", type="password", key="register_password")
        confirm_password = st.text_input("Şifre Tekrar", type="password", key="register_confirm_password")
        
        if st.button("Kayıt Ol", type="primary", use_container_width=True):
            if new_username and new_password:
                if new_password != confirm_password:
                    st.error("❌ Şifreler eşleşmiyor!")
                elif len(new_password) < 6:
                    st.error("❌ Şifre en az 6 karakter olmalıdır!")
                else:
                    user_id = db.create_user(new_username, new_password, new_email if new_email else None)
                    if user_id:
                        st.success(f"✅ Kayıt başarılı! Giriş yapabilirsiniz.")
                        st.info("💡 Lütfen 'Giriş Yap' sekmesinden giriş yapın.")
                    else:
                        st.error("❌ Bu kullanıcı adı zaten kullanılıyor!")
            else:
                st.warning("⚠️ Lütfen kullanıcı adı ve şifre girin.")
    
    return None

def show_logout_button():
    """Çıkış butonu göster"""
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        clear_remembered_user()  # Remember me'yi de temizle
        st.rerun()

def require_auth(db: Database):
    """Sayfa için authentication kontrolü"""
    init_session_state()
    
    # Eğer remember me'den yüklendiyse, otomatik giriş yapılmış demektir
    if st.session_state.authenticated and st.session_state.user_id:
        # Kullanıcı bilgilerini sidebar'da göster
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**👤 Kullanıcı:** {st.session_state.username}")
        show_logout_button()
        return st.session_state.user_id
    
    # Giriş yapılmamışsa giriş sayfasını göster
    user_id = show_login_page(db)
    if user_id:
        st.session_state.authenticated = True
        st.session_state.user_id = user_id
        st.rerun()
    else:
        st.stop()
    
    return st.session_state.user_id

