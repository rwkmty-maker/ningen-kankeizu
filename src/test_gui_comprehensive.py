# -*- coding: utf-8 -*-
"""
総合テストプログラム（GUI版）
Excelデータ読み込み、背景色読み取り、会員ID表示などを段階的にテスト
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import pandas as pd
import openpyxl
import winreg
import traceback

class ComprehensiveTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("総合テストプログラム - CustomerNexusSystem")
        self.root.geometry("1200x800")
        
        # メインフレーム
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ボタンフレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=0, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        ttk.Button(btn_frame, text="1. レジストリからパス取得", command=self.test_registry).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="2. Excelデータ読み込み", command=self.test_excel_load).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="3. 背景色読み取り", command=self.test_background_color).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="4. 会員ID確認", command=self.test_member_id).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="5. 統合テスト", command=self.test_integrated).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="クリア", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        # 出力エリア
        ttk.Label(main_frame, text="テスト結果:", font=("Meiryo UI", 11, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.output = scrolledtext.ScrolledText(main_frame, width=140, height=35, font=("Consolas", 9))
        self.output.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # データ表示エリア
        ttk.Label(main_frame, text="データプレビュー:", font=("Meiryo UI", 11, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.tree = ttk.Treeview(tree_frame, height=10)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # グリッド設定
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # データ保持
        self.excel_path = None
        self.df = None
        self.bg_color_dict = {}
        
    def log(self, message):
        """ログ出力"""
        self.output.insert(tk.END, message + "\n")
        self.output.see(tk.END)
        self.root.update()
        
    def clear_output(self):
        """出力クリア"""
        self.output.delete(1.0, tk.END)
        
    def test_registry(self):
        """レジストリからパス取得テスト"""
        self.log("=" * 80)
        self.log("【テスト1: レジストリからパス取得】")
        self.log("=" * 80)
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\CustomerNexusSystem", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "LastOpenedFile")
            winreg.CloseKey(key)
            
            self.excel_path = value
            self.log(f"✓ パス取得成功: {self.excel_path}")
            
            import os
            if os.path.exists(self.excel_path):
                self.log(f"✓ ファイル存在確認: OK")
                file_size = os.path.getsize(self.excel_path) / 1024 / 1024
                self.log(f"  ファイルサイズ: {file_size:.2f} MB")
            else:
                self.log(f"✗ ファイルが存在しません")
                
        except Exception as e:
            self.log(f"✗ エラー: {e}")
            traceback.print_exc()
            
    def test_excel_load(self):
        """Excelデータ読み込みテスト"""
        self.log("\n" + "=" * 80)
        self.log("【テスト2: Excelデータ読み込み】")
        self.log("=" * 80)
        
        if not self.excel_path:
            self.log("✗ 先にテスト1を実行してください")
            return
            
        try:
            # dtype指定なしで読み込み
            self.log("読み込み中...")
            self.df = pd.read_excel(self.excel_path)
            
            self.log(f"✓ 読み込み成功")
            self.log(f"  総行数: {len(self.df)}")
            self.log(f"  総列数: {len(self.df.columns)}")
            self.log(f"  列名: {list(self.df.columns)}")
            
            # 会員ID列の確認
            if '会員ID' in self.df.columns:
                self.log(f"\n✓ 会員ID列が存在します")
                self.log(f"  データ型: {self.df['会員ID'].dtype}")
                
                # 最初の20行の会員IDを表示
                self.log(f"\n  最初の20行の会員ID:")
                for idx in range(min(20, len(self.df))):
                    val = self.df.loc[idx, '会員ID']
                    val_type = type(val).__name__
                    self.log(f"    行{idx}: 値='{val}' 型={val_type}")
                    
                # 空でない会員IDの数
                non_empty = self.df['会員ID'].notna().sum()
                self.log(f"\n  空でない会員ID: {non_empty}件")
            else:
                self.log(f"✗ 会員ID列が見つかりません")
                
            # NaNの確認
            self.log(f"\n【NaN確認】")
            for col in self.df.columns:
                nan_count = self.df[col].isna().sum()
                if nan_count > 0:
                    self.log(f"  {col}: {nan_count}件のNaN")
                    
        except Exception as e:
            self.log(f"✗ エラー: {e}")
            traceback.print_exc()
            
    def test_background_color(self):
        """背景色読み取りテスト"""
        self.log("\n" + "=" * 80)
        self.log("【テスト3: 背景色読み取り】")
        self.log("=" * 80)
        
        if not self.excel_path:
            self.log("✗ 先にテスト1を実行してください")
            return
            
        try:
            self.log("背景色読み取り中...")
            wb = openpyxl.load_workbook(self.excel_path, data_only=True)
            ws = wb.active
            
            self.log(f"✓ ワークブック読み込み成功")
            self.log(f"  総行数: {ws.max_row}")
            self.log(f"  総列数: {ws.max_column}")
            
            self.bg_color_dict = {}
            
            # 最初の50行の背景色を詳細に確認
            self.log(f"\n【最初の50行の背景色詳細】")
            for row_idx in range(2, min(52, ws.max_row + 1)):
                cell = ws.cell(row=row_idx, column=1)
                fill = cell.fill
                cell_value = cell.value
                
                self.log(f"\n行{row_idx}: 値='{cell_value}'")
                self.log(f"  fill型: {type(fill).__name__}")
                
                if fill and hasattr(fill, 'fgColor'):
                    color = fill.fgColor
                    self.log(f"  fgColor: {color}")
                    
                    if hasattr(color, 'rgb'):
                        self.log(f"    rgb: {color.rgb}")
                    if hasattr(color, 'indexed'):
                        self.log(f"    indexed: {color.indexed}")
                    if hasattr(color, 'theme'):
                        self.log(f"    theme: {color.theme}")
                    if hasattr(color, 'tint'):
                        self.log(f"    tint: {color.tint}")
                        
                    # 背景色判定
                    hex_color = None
                    if color.rgb and color.rgb is not None:
                        rgb_str = color.rgb
                        if isinstance(rgb_str, str) and len(rgb_str) >= 6:
                            if len(rgb_str) == 8:
                                hex_color = f'#{rgb_str[2:]}'
                            else:
                                hex_color = f'#{rgb_str}'
                    elif color.indexed is not None:
                        indexed_colors = {
                            2: '#FF0000', 3: '#00FF00', 4: '#0000FF', 5: '#FFFF00',
                            6: '#FF00FF', 7: '#00FFFF', 10: '#FF0000',
                            45: '#FFA500', 50: '#FFA500',
                        }
                        if color.indexed in indexed_colors:
                            hex_color = indexed_colors[color.indexed]
                            
                    if hex_color:
                        self.log(f"  → 検出色: {hex_color}")
                        if hex_color.upper() not in ['#FFFFFF', '#FFFFFFFF', '#000000', '#FEFEFE']:
                            self.bg_color_dict[row_idx - 2] = hex_color
                            self.log(f"  ✓ 背景色として登録")
                        else:
                            self.log(f"  - スキップ（白/黒）")
                    else:
                        self.log(f"  - 背景色なし")
                else:
                    self.log(f"  - fillなし")
                    
            wb.close()
            
            self.log(f"\n【背景色サマリー】")
            self.log(f"  検出された背景色: {len(self.bg_color_dict)}件")
            if self.bg_color_dict:
                self.log(f"  背景色がある行（最初の20件）:")
                for idx, (row_idx, color) in enumerate(list(self.bg_color_dict.items())[:20]):
                    self.log(f"    元行{row_idx}: {color}")
                    
        except Exception as e:
            self.log(f"✗ エラー: {e}")
            traceback.print_exc()
            
    def test_member_id(self):
        """会員ID確認テスト"""
        self.log("\n" + "=" * 80)
        self.log("【テスト4: 会員ID確認】")
        self.log("=" * 80)
        
        if self.df is None:
            self.log("✗ 先にテスト2を実行してください")
            return
            
        try:
            if '会員ID' not in self.df.columns:
                self.log("✗ 会員ID列が見つかりません")
                return
                
            # fillna前後の比較
            self.log("【fillna前】")
            self.log(f"  データ型: {self.df['会員ID'].dtype}")
            self.log(f"  NaN数: {self.df['会員ID'].isna().sum()}")
            self.log(f"  最初の10行:")
            for idx in range(min(10, len(self.df))):
                val = self.df.loc[idx, '会員ID']
                self.log(f"    行{idx}: '{val}' (型: {type(val).__name__})")
                
            # fillna実行
            df_test = self.df.copy()
            df_test = df_test.fillna('')
            
            self.log(f"\n【fillna後】")
            self.log(f"  データ型: {df_test['会員ID'].dtype}")
            self.log(f"  NaN数: {df_test['会員ID'].isna().sum()}")
            self.log(f"  最初の10行:")
            for idx in range(min(10, len(df_test))):
                val = df_test.loc[idx, '会員ID']
                self.log(f"    行{idx}: '{val}' (型: {type(val).__name__})")
                
            # astype(str)実行
            df_test['会員ID'] = df_test['会員ID'].astype(str)
            
            self.log(f"\n【astype(str)後】")
            self.log(f"  データ型: {df_test['会員ID'].dtype}")
            self.log(f"  最初の10行:")
            for idx in range(min(10, len(df_test))):
                val = df_test.loc[idx, '会員ID']
                self.log(f"    行{idx}: '{val}' (型: {type(val).__name__})")
                
            # replace('nan', '')実行
            df_test['会員ID'] = df_test['会員ID'].replace('nan', '')
            
            self.log(f"\n【replace('nan', '')後】")
            self.log(f"  最初の10行:")
            for idx in range(min(10, len(df_test))):
                val = df_test.loc[idx, '会員ID']
                self.log(f"    行{idx}: '{val}' (型: {type(val).__name__}, 長さ: {len(val)})")
                
        except Exception as e:
            self.log(f"✗ エラー: {e}")
            traceback.print_exc()
            
    def test_integrated(self):
        """統合テスト"""
        self.log("\n" + "=" * 80)
        self.log("【テスト5: 統合テスト（実際のアプリと同じ処理）】")
        self.log("=" * 80)
        
        if not self.excel_path:
            self.log("✗ 先にテスト1を実行してください")
            return
            
        try:
            # 1. Excelデータ読み込み（dtype指定なし）
            self.log("1. Excelデータ読み込み（dtype指定なし）...")
            df = pd.read_excel(self.excel_path)
            self.log(f"   ✓ 読み込み完了: {len(df)}行")
            
            # 2. 背景色読み取り
            self.log("\n2. 背景色読み取り...")
            bg_color_dict = {}
            wb = openpyxl.load_workbook(self.excel_path, data_only=True)
            ws = wb.active
            
            for row_idx in range(2, ws.max_row + 1):
                cell = ws.cell(row=row_idx, column=1)
                fill = cell.fill
                
                if fill and hasattr(fill, 'fgColor') and fill.fgColor:
                    try:
                        color = fill.fgColor
                        hex_color = None
                        
                        if color.rgb and color.rgb is not None:
                            rgb_str = color.rgb
                            if isinstance(rgb_str, str) and len(rgb_str) >= 6:
                                if len(rgb_str) == 8:
                                    hex_color = f'#{rgb_str[2:]}'
                                else:
                                    hex_color = f'#{rgb_str}'
                        elif color.indexed is not None:
                            indexed_colors = {
                                2: '#FF0000', 3: '#00FF00', 4: '#0000FF', 5: '#FFFF00',
                                6: '#FF00FF', 7: '#00FFFF', 10: '#FF0000',
                                45: '#FFA500', 50: '#FFA500',
                            }
                            if color.indexed in indexed_colors:
                                hex_color = indexed_colors[color.indexed]
                        
                        if hex_color and hex_color.upper() not in ['#FFFFFF', '#FFFFFFFF', '#000000', '#FEFEFE']:
                            bg_color_dict[row_idx - 2] = hex_color
                    except:
                        pass
                        
            wb.close()
            self.log(f"   ✓ 背景色読み取り完了: {len(bg_color_dict)}件")
            
            # 3. NaN処理
            self.log("\n3. NaN処理...")
            df = df.fillna('')
            self.log(f"   ✓ fillna完了")
            
            # 4. 空行削除
            self.log("\n4. 空行削除...")
            check_cols = ['登録名', '本名', 'フリガナ', '生年月日', '住所', '電話番号', '電話番号2', '電話番号3']
            existing_check_cols = [col for col in check_cols if col in df.columns]
            
            if existing_check_cols:
                empty_mask = (df[existing_check_cols] == '').all(axis=1)
                original_indices = df.index[~empty_mask].tolist()
                df = df[~empty_mask].reset_index(drop=True)
                
                # 背景色マッピング
                bg_colors = [bg_color_dict.get(orig_idx, '') for orig_idx in original_indices]
                df['__bg_color__'] = bg_colors
                
                self.log(f"   ✓ 空行削除完了: {len(df)}行")
                self.log(f"   ✓ 背景色マッピング完了: {sum(1 for c in bg_colors if c)}件")
            
            # 5. 文字列化
            self.log("\n5. 文字列化...")
            for col in df.columns:
                if col not in ['生年月日', '__bg_color__']:
                    df[col] = df[col].astype(str)
                    df[col] = df[col].replace('nan', '')
            self.log(f"   ✓ 文字列化完了")
            
            # 6. 結果確認
            self.log("\n【結果確認】")
            self.log(f"最終行数: {len(df)}")
            
            if '会員ID' in df.columns:
                self.log(f"\n会員ID列:")
                self.log(f"  データ型: {df['会員ID'].dtype}")
                non_empty = sum(1 for v in df['会員ID'] if v != '')
                self.log(f"  空でない会員ID: {non_empty}件")
                self.log(f"  最初の20行:")
                for idx in range(min(20, len(df))):
                    val = df.loc[idx, '会員ID']
                    bg = df.loc[idx, '__bg_color__'] if '__bg_color__' in df.columns else ''
                    self.log(f"    行{idx}: 会員ID='{val}' 背景色='{bg}'")
                    
            if '__bg_color__' in df.columns:
                bg_count = sum(1 for v in df['__bg_color__'] if v != '')
                self.log(f"\n背景色:")
                self.log(f"  背景色がある行: {bg_count}件")
                self.log(f"  背景色がある行（最初の10件）:")
                for idx in range(len(df)):
                    bg = df.loc[idx, '__bg_color__']
                    if bg:
                        name = df.loc[idx, '登録名'] if '登録名' in df.columns else ''
                        member_id = df.loc[idx, '会員ID'] if '会員ID' in df.columns else ''
                        self.log(f"    行{idx}: 登録名='{name}' 会員ID='{member_id}' 背景色='{bg}'")
                        if len([i for i in range(len(df)) if df.loc[i, '__bg_color__']]) >= 10:
                            break
                            
            # 7. Treeviewに表示
            self.log("\n7. Treeviewに表示...")
            self.display_in_treeview(df)
            
        except Exception as e:
            self.log(f"✗ エラー: {e}")
            traceback.print_exc()
            
    def display_in_treeview(self, df):
        """Treeviewにデータ表示"""
        try:
            # Treeviewクリア
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # 列設定
            display_cols = ['会員ID', '登録名', '本名', '生年月日', '__bg_color__']
            existing_cols = [col for col in display_cols if col in df.columns]
            
            self.tree['columns'] = existing_cols
            self.tree.column('#0', width=50)
            self.tree.heading('#0', text='行')
            
            for col in existing_cols:
                self.tree.column(col, width=150)
                self.tree.heading(col, text=col)
                
            # データ挿入（最初の100行）
            for idx in range(min(100, len(df))):
                row = df.loc[idx]
                vals = [str(row[col]) if col in df.columns else '' for col in existing_cols]
                
                # 背景色がある場合はボールド
                if '__bg_color__' in df.columns and row['__bg_color__']:
                    self.tree.insert('', tk.END, text=str(idx), values=vals, tags=('colored',))
                else:
                    self.tree.insert('', tk.END, text=str(idx), values=vals)
                    
            # タグ設定
            self.tree.tag_configure('colored', font=('Meiryo UI', 9, 'bold'), foreground='red')
            
            self.log(f"   ✓ Treeview表示完了: {min(100, len(df))}行")
            
        except Exception as e:
            self.log(f"✗ Treeview表示エラー: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    root = tk.Tk()
    app = ComprehensiveTestGUI(root)
    root.mainloop()
