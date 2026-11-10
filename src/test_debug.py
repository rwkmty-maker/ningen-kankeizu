# -*- coding: utf-8 -*-
"""
デバッグ用テストプログラム
背景色読み取りと会員ID表示の問題を徹底調査
"""
import pandas as pd
import openpyxl
import winreg
import os

def get_last_opened_file():
    """レジストリから最後に開いたファイルのパスを取得"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\CustomerNexusSystem", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "LastOpenedFile")
        winreg.CloseKey(key)
        return value
    except:
        return None

def test_background_colors(path):
    """背景色読み取りテスト"""
    print("\n" + "="*80)
    print("【背景色読み取りテスト】")
    print("="*80)
    
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        
        print(f"\n総行数: {ws.max_row}")
        print(f"総列数: {ws.max_column}")
        
        # 最初の20行の背景色を確認
        print("\n【最初の20行の背景色情報】")
        for row_idx in range(1, min(21, ws.max_row + 1)):
            cell = ws.cell(row=row_idx, column=1)
            fill = cell.fill
            cell_value = cell.value
            
            if fill and fill.start_color:
                try:
                    if hasattr(fill.start_color, 'rgb'):
                        rgb_value = fill.start_color.rgb
                        if rgb_value:
                            if hasattr(rgb_value, '__iter__') and not isinstance(rgb_value, str):
                                hex_color = '#' + ''.join(f'{c:02x}' for c in rgb_value)
                            else:
                                hex_str = str(rgb_value)
                                if len(hex_str) >= 6:
                                    if len(hex_str) == 8:
                                        hex_color = f'#{hex_str[2:]}'
                                    else:
                                        hex_color = f'#{hex_str}'
                                    print(f"行{row_idx}: 値='{cell_value}' 背景色={hex_color}")
                                else:
                                    print(f"行{row_idx}: 値='{cell_value}' 背景色=なし(rgb短い)")
                        else:
                            print(f"行{row_idx}: 値='{cell_value}' 背景色=なし(rgb=None)")
                except Exception as e:
                    print(f"行{row_idx}: 値='{cell_value}' 背景色=エラー({e})")
            else:
                print(f"行{row_idx}: 値='{cell_value}' 背景色=なし")
        
        wb.close()
        return True
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_member_id_loading(path):
    """会員ID読み込みテスト"""
    print("\n" + "="*80)
    print("【会員ID読み込みテスト】")
    print("="*80)
    
    try:
        # dtype=strで読み込み
        print("\n1. dtype=str で読み込み")
        df = pd.read_excel(path, dtype=str)
        
        if '会員ID' in df.columns:
            print(f"\n会員ID列が存在します")
            print(f"データ型: {df['会員ID'].dtype}")
            print(f"最初の10件:")
            for idx, val in df['会員ID'].head(10).items():
                print(f"  行{idx}: '{val}' (型: {type(val).__name__})")
        else:
            print("\n会員ID列が見つかりません")
            print(f"利用可能な列: {list(df.columns)}")
        
        # openpyxlで直接読み込み
        print("\n2. openpyxlで直接読み込み")
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        
        # ヘッダー行から会員ID列を探す
        header_row = [cell.value for cell in ws[1]]
        if '会員ID' in header_row:
            member_id_col = header_row.index('会員ID') + 1
            print(f"\n会員ID列: {member_id_col}列目")
            print(f"最初の10件:")
            for row_idx in range(2, min(12, ws.max_row + 1)):
                cell = ws.cell(row=row_idx, column=member_id_col)
                print(f"  行{row_idx}: 値='{cell.value}' 型={type(cell.value).__name__} データ型={cell.data_type}")
        else:
            print("\n会員ID列が見つかりません")
        
        wb.close()
        return True
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_empty_row_removal(path):
    """空行削除処理のテスト"""
    print("\n" + "="*80)
    print("【空行削除処理テスト】")
    print("="*80)
    
    try:
        df = pd.read_excel(path, dtype=str)
        print(f"\n読み込み直後の行数: {len(df)}")
        
        # 空行削除前のインデックスを表示
        print(f"\n最初の10行のインデックス:")
        for idx in df.head(10).index:
            print(f"  インデックス: {idx}")
        
        # 空行削除処理
        check_cols = ['登録名', '本名', 'フリガナ', '生年月日', '住所', '電話番号', '電話番号2', '電話番号3']
        existing_check_cols = [col for col in check_cols if col in df.columns]
        
        if existing_check_cols:
            empty_mask = (df[existing_check_cols] == '').all(axis=1)
            print(f"\n空行の数: {empty_mask.sum()}")
            
            # 削除される行を表示
            if empty_mask.sum() > 0:
                print(f"\n削除される行のインデックス:")
                for idx in df[empty_mask].index[:10]:
                    print(f"  インデックス: {idx}")
            
            # 空行削除前のインデックスを保存
            original_indices = df.index[~empty_mask].tolist()
            df = df[~empty_mask].reset_index(drop=True)
            
            print(f"\n空行削除後の行数: {len(df)}")
            print(f"\n削除後の最初の10行の元インデックス:")
            for new_idx, orig_idx in enumerate(original_indices[:10]):
                print(f"  新インデックス{new_idx} <- 元インデックス{orig_idx}")
        
        return True
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integrated_loading(path):
    """統合読み込みテスト（実際のload_thread処理を再現）"""
    print("\n" + "="*80)
    print("【統合読み込みテスト】")
    print("="*80)
    
    try:
        # 1. Excelファイル読み込み
        df = pd.read_excel(path, dtype=str)
        print(f"\n1. 読み込み完了: {len(df)}行")
        
        # 2. 背景色読み取り
        bg_color_dict = {}
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        
        for row_idx in range(2, ws.max_row + 1):
            cell = ws.cell(row=row_idx, column=1)
            fill = cell.fill
            
            if fill and fill.start_color:
                try:
                    if hasattr(fill.start_color, 'rgb'):
                        rgb_value = fill.start_color.rgb
                        if rgb_value:
                            if hasattr(rgb_value, '__iter__') and not isinstance(rgb_value, str):
                                hex_color = '#' + ''.join(f'{c:02x}' for c in rgb_value)
                            else:
                                hex_str = str(rgb_value)
                                if len(hex_str) >= 6:
                                    if len(hex_str) == 8:
                                        hex_color = f'#{hex_str[2:]}'
                                    else:
                                        hex_color = f'#{hex_str}'
                                    
                                    if hex_color.upper() not in ['#FFFFFF', '#FFFFFFFF', '#000000']:
                                        bg_color_dict[row_idx - 2] = hex_color
                except Exception as e:
                    pass
        
        wb.close()
        print(f"2. 背景色読み取り完了: {len(bg_color_dict)}件")
        
        # 背景色がある行を表示
        if bg_color_dict:
            print(f"\n背景色がある行（最初の10件）:")
            for idx, color in list(bg_color_dict.items())[:10]:
                print(f"  元インデックス{idx}: {color}")
        
        # 3. 空行削除
        df = df.fillna('')
        check_cols = ['登録名', '本名', 'フリガナ', '生年月日', '住所', '電話番号', '電話番号2', '電話番号3']
        existing_check_cols = [col for col in check_cols if col in df.columns]
        
        if existing_check_cols:
            empty_mask = (df[existing_check_cols] == '').all(axis=1)
            original_indices = df.index[~empty_mask].tolist()
            df = df[~empty_mask].reset_index(drop=True)
            
            # 背景色をマッピング
            bg_colors = [bg_color_dict.get(orig_idx, '') for orig_idx in original_indices]
            df['__bg_color__'] = bg_colors
            
            print(f"3. 空行削除完了: {len(df)}行")
            print(f"   背景色列追加: {len([c for c in bg_colors if c])}件")
        
        # 4. 会員IDの確認
        if '会員ID' in df.columns:
            print(f"\n4. 会員ID列の確認:")
            print(f"   データ型: {df['会員ID'].dtype}")
            print(f"   最初の5件:")
            for idx in range(min(5, len(df))):
                member_id = df.loc[idx, '会員ID']
                bg_color = df.loc[idx, '__bg_color__'] if '__bg_color__' in df.columns else ''
                print(f"     行{idx}: 会員ID='{member_id}' 背景色='{bg_color}'")
        
        # 5. 背景色がある行の詳細確認
        if '__bg_color__' in df.columns:
            colored_rows = df[df['__bg_color__'] != '']
            if len(colored_rows) > 0:
                print(f"\n5. 背景色がある行の詳細（最初の5件）:")
                for idx, row in colored_rows.head(5).iterrows():
                    member_id = row.get('会員ID', 'N/A')
                    name = row.get('登録名', 'N/A')
                    bg_color = row['__bg_color__']
                    print(f"     行{idx}: 会員ID='{member_id}' 名前='{name}' 背景色='{bg_color}'")
            else:
                print(f"\n5. 背景色がある行が見つかりません")
        
        return True
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*80)
    print("デバッグテストプログラム開始")
    print("="*80)
    
    # レジストリからファイルパスを取得
    file_path = get_last_opened_file()
    
    if not file_path:
        print("\nエラー: レジストリからファイルパスを取得できませんでした")
        return
    
    print(f"\n対象ファイル: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"\nエラー: ファイルが見つかりません: {file_path}")
        return
    
    # 各テストを実行
    test_background_colors(file_path)
    test_member_id_loading(file_path)
    test_empty_row_removal(file_path)
    test_integrated_loading(file_path)
    
    print("\n" + "="*80)
    print("テスト完了")
    print("="*80)

if __name__ == "__main__":
    main()
    input("\nEnterキーを押して終了...")
