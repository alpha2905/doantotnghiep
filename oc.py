import os
import shutil
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def clean_folder(folder_path):
    print(f"--- Đang dọn dẹp: {folder_path} ---")
    if not os.path.exists(folder_path):
        print(f"Không tìm thấy đường dẫn: {folder_path}")
        return

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path) # Xóa file hoặc link
                print(f"Đã xóa file: {item}")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path) # Xóa thư mục con
                print(f"Đã xóa thư mục: {item}")
        except Exception as e:
            # Một số file đang được hệ thống sử dụng sẽ không xóa được
            print(f"Bỏ qua (đang mở): {item}")

def empty_recycle_bin():
    print("--- Đang dọn sạch Thùng rác ---")
    try:
        # SHEmptyRecycleBinW: 1 = NOPROMPT, 2 = NOSOUND, 4 = PROGRESSUI
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1 | 2 | 4)
        print("Đã dọn xong Thùng rác.")
    except Exception as e:
        print(f"Lỗi khi dọn thùng rác: {e}")

if __name__ == "__main__":
    if not is_admin():
        print("⚠️  Cảnh báo: Bạn nên chạy script này với quyền Administrator để xóa được Prefetch và các file hệ thống.")
    
    # Các đường dẫn rác phổ biến trên Windows
    folders_to_clean = [
        os.environ.get('TEMP'), # %TEMP% của User
        r'C:\Windows\Temp',      # Temp của Hệ thống
        r'C:\Windows\Prefetch',  # Prefetch (cần quyền Admin)
    ]

    for folder in folders_to_clean:
        if folder:
            clean_folder(folder)
    
    empty_recycle_bin()
    print("\n✅ Hoàn tất dọn dẹp!")