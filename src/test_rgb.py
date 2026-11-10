# -*- coding: utf-8 -*-
"""
RGB型の正しい処理方法を調査
"""
import openpyxl
import winreg

def get_last_opened_file():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\CustomerNexusSystem", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "LastOpenedFile")
        winreg.CloseKey(key)
        return value
    except:
        return None

path = get_last_opened_file()
if path:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    
    # 2行目のセル（ヘッダーの次）
    cell = ws.cell(row=2, column=1)
    fill = cell.fill
    
    print(f"セル値: {cell.value}")
    print(f"Fill型: {type(fill)}")
    print(f"Fill: {fill}")
    
    if fill and fill.start_color:
        print(f"\nstart_color型: {type(fill.start_color)}")
        print(f"start_color: {fill.start_color}")
        
        if hasattr(fill.start_color, 'rgb'):
            rgb = fill.start_color.rgb
            print(f"\nrgb型: {type(rgb)}")
            print(f"rgb: {rgb}")
            print(f"rgb.__dict__: {rgb.__dict__ if hasattr(rgb, '__dict__') else 'なし'}")
            print(f"dir(rgb): {[x for x in dir(rgb) if not x.startswith('_')]}")
            
            # 様々な方法を試す
            print("\n【変換テスト】")
            try:
                print(f"1. str(rgb): {str(rgb)}")
            except Exception as e:
                print(f"1. str(rgb): エラー - {e}")
            
            try:
                print(f"2. repr(rgb): {repr(rgb)}")
            except Exception as e:
                print(f"2. repr(rgb): エラー - {e}")
            
            try:
                print(f"3. rgb.value: {rgb.value if hasattr(rgb, 'value') else 'なし'}")
            except Exception as e:
                print(f"3. rgb.value: エラー - {e}")
            
            try:
                # RGB型は実際には文字列を内部に持っている
                if hasattr(rgb, '__str__'):
                    print(f"4. rgb.__str__(): {rgb.__str__()}")
            except Exception as e:
                print(f"4. rgb.__str__(): エラー - {e}")
    
    wb.close()
