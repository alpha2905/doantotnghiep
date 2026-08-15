#!/usr/bin/env python3
"""
Script chuyển đổi PlantUML diagrams thành PNG
Yêu cầu: pip install plantuml
"""

import os
import subprocess
import sys
from pathlib import Path

def check_plantuml():
    """Kiểm tra xem PlantUML đã được cài đặt chưa"""
    try:
        result = subprocess.run(['which', 'plantuml'], capture_output=True)
        if result.returncode == 0:
            return True
    except:
        pass
    
    # Thử dùng java -jar
    if os.path.exists('/usr/local/bin/plantuml.jar'):
        return True
    
    return False

def convert_with_online_plantuml(puml_file, output_file):
    """
    Chuyển đổi sử dụng PlantUML online
    (Cần curl hoặc requests)
    """
    try:
        import requests
        import base64
        
        with open(puml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compress content cho PlantUML
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        url = f"http://www.plantuml.com/plantuml/png/{encoded}"
        response = requests.get(url)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return True
    except ImportError:
        print("❌ requests module not found. Install: pip install requests")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def convert_with_local_plantuml(puml_file, output_file):
    """
    Chuyển đổi sử dụng PlantUML cài đặt local
    """
    try:
        # Thử lệnh plantuml
        result = subprocess.run(
            ['plantuml', '-tpng', puml_file, '-o', str(Path(output_file).parent)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and os.path.exists(output_file):
            return True
        
    except FileNotFoundError:
        pass
    
    # Thử java -jar
    try:
        plantuml_jar = '/usr/local/bin/plantuml.jar'
        if os.path.exists(plantuml_jar):
            result = subprocess.run(
                ['java', '-jar', plantuml_jar, '-tpng', puml_file, 
                 '-o', str(Path(output_file).parent)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                return True
    except:
        pass
    
    return False

def main():
    """Main function"""
    
    # Tạo folder diagrams nếu không tồn tại
    diagrams_dir = Path('diagrams')
    if not diagrams_dir.exists():
        print(f"❌ Folder '{diagrams_dir}' không tồn tại!")
        print(f"📂 Tạo folder này bằng lệnh: mkdir {diagrams_dir}")
        return
    
    # Tạo folder output
    output_dir = diagrams_dir / 'images'
    output_dir.mkdir(exist_ok=True)
    print(f"📁 Output folder: {output_dir}")
    
    # Danh sách files PlantUML
    puml_files = [
        'context.puml',
        'usecase.puml',
        'architecture.puml',
        'sequence_search.puml',
        'sequence_crawl.puml',
        'sequence_sentiment.puml',
        'sequence_forecast.puml',
        'entity_relationship.puml',
    ]
    
    print("\n🔄 Bắt đầu chuyển đổi PlantUML → PNG...\n")
    
    success_count = 0
    failed_files = []
    
    for puml_name in puml_files:
        puml_path = diagrams_dir / puml_name
        png_name = puml_name.replace('.puml', '.png')
        png_path = output_dir / png_name
        
        if not puml_path.exists():
            print(f"⚠️  {puml_name} không tìm thấy (bỏ qua)")
            continue
        
        print(f"⏳ Đang xử lý: {puml_name}...", end=' ')
        
        # Thử local PlantUML trước
        if convert_with_local_plantuml(str(puml_path), str(png_path)):
            print(f"✅ → {png_name}")
            success_count += 1
        # Thử online
        elif convert_with_online_plantuml(str(puml_path), str(png_path)):
            print(f"✅ → {png_name} (online)")
            success_count += 1
        else:
            print(f"❌ Thất bại")
            failed_files.append(puml_name)
    
    print(f"\n{'='*60}")
    print(f"✅ Thành công: {success_count}/{len(puml_files)}")
    
    if failed_files:
        print(f"❌ Thất bại: {len(failed_files)}")
        print(f"📝 Files lỗi:")
        for f in failed_files:
            print(f"   - {f}")
        print(f"\n💡 Giải pháp:")
        print(f"   1. Cài PlantUML: pip install plantuml")
        print(f"   2. Hoặc dùng PlantUML Online: https://www.plantuml.com/plantuml/uml/")
        print(f"   3. Copy nội dung .puml → paste vào trang web → Export PNG")
    else:
        print(f"🎉 Tất cả files đã chuyển đổi thành công!")
    
    print(f"\n📁 Images lưu tại: {output_dir}")
    print(f"{"="*60}")

if __name__ == '__main__':
    main()
