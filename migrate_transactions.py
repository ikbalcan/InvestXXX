"""
Transaction Migration Script
Eski JSON transaction'ları veritabanına aktarır
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.database import Database
import json

def migrate_old_transactions():
    """Eski JSON transaction'ları veritabanına aktar"""
    db = Database()
    
    print("=" * 60)
    print("TRANSACTION MIGRATION SCRIPT")
    print("=" * 60)
    
    # Kullanıcı oluştur veya mevcut kullanıcıyı bul
    print("\n1. Kullanıcı işlemleri...")
    
    # Varsayılan kullanıcı oluştur (eğer yoksa)
    username = "admin"
    password = "admin123"  # İlk girişte değiştirilmeli
    
    # Kullanıcı var mı kontrol et
    user = db.authenticate_user(username, password)
    if not user:
        print(f"   Yeni kullanıcı oluşturuluyor: {username}")
        user_id = db.create_user(username, password, "admin@investxxx.com")
        if user_id:
            user = db.authenticate_user(username, password)
            print(f"   ✅ Kullanıcı oluşturuldu (ID: {user_id})")
        else:
            print("   ❌ Kullanıcı oluşturulamadı!")
            return
    else:
        user_id = user['id']
        print(f"   ✅ Mevcut kullanıcı bulundu: {username} (ID: {user_id})")
    
    # Eski transaction dosyalarını bul
    print("\n2. Eski transaction dosyaları aranıyor...")
    transactions_dir = "logs/transactions"
    
    if not os.path.exists(transactions_dir):
        print(f"   ❌ Transaction dizini bulunamadı: {transactions_dir}")
        return
    
    # Tüm transaction JSON dosyalarını bul
    json_files = [f for f in os.listdir(transactions_dir) if f.startswith("transactions_") and f.endswith(".json")]
    
    if not json_files:
        print("   ⚠️  Migrate edilecek transaction dosyası bulunamadı.")
        return
    
    print(f"   📁 {len(json_files)} transaction dosyası bulundu")
    
    # Her dosyayı migrate et
    total_migrated = 0
    for json_file in json_files:
        old_user_id = json_file.replace("transactions_", "").replace(".json", "")
        json_path = os.path.join(transactions_dir, json_file)
        
        print(f"\n3. Migrate ediliyor: {json_file}")
        print(f"   Eski User ID: {old_user_id}")
        
        migrated_count = db.migrate_json_transactions(old_user_id, user_id, json_path)
        total_migrated += migrated_count
        
        if migrated_count > 0:
            print(f"   ✅ {migrated_count} transaction migrate edildi")
        else:
            print(f"   ⚠️  Hiç transaction migrate edilmedi")
    
    print("\n" + "=" * 60)
    print(f"✅ MIGRATION TAMAMLANDI")
    print(f"   Toplam migrate edilen transaction: {total_migrated}")
    print(f"   Kullanıcı: {username} (ID: {user_id})")
    print("=" * 60)
    print("\n💡 Şimdi sisteme giriş yapabilirsiniz:")
    print(f"   Kullanıcı Adı: {username}")
    print(f"   Şifre: {password}")
    print("   ⚠️  İlk girişte şifrenizi değiştirmeniz önerilir!")

if __name__ == "__main__":
    migrate_old_transactions()

