# -*- coding: utf-8 -*-
"""
フリガナ自動入力の徹底的なデバッグ用GUIテストプログラム
全プロセスをログ出力して問題箇所を特定する
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import openpyxl
import os
import traceback
from datetime import datetime

class FuriganaDebugTester(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("フリガナ自動入力デバッグテスター")
        self.geometry("900x700")
        
        # ログ表示エリア
        log_frame = ttk.LabelFrame(self, text="詳細ログ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # コントロールエリア
        control_frame = ttk.Frame(self, padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # ファイル選択
        ttk.Label(control_frame, text="Excelファイル:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.file_path_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.file_path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="選択", command=self.select_file).grid(row=0, column=2)
        
        # APIキー
        ttk.Label(control_frame, text="Claude API Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.api_key_var, width=50, show="*").grid(row=1, column=1, padx=5)
        
        # モデル
        ttk.Label(control_frame, text="Model:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar(value="claude-opus-4-20250514")
        ttk.Entry(control_frame, textvariable=self.model_var, width=50).grid(row=2, column=1, padx=5)
        
        # 既存フリガナモード
        ttk.Label(control_frame, text="既存フリガナ:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.mode_var = tk.StringVar(value="skip")
        mode_frame = ttk.Frame(control_frame)
        mode_frame.grid(row=3, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(mode_frame, text="スキップ", variable=self.mode_var, value="skip").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="上書き", variable=self.mode_var, value="overwrite").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="追加", variable=self.mode_var, value="append").pack(side=tk.LEFT, padx=5)
        
        # 実行ボタン
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="1. ファイル読み込みテスト", 
                  command=self.test_load_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="2. Claude API呼び出しテスト", 
                  command=self.test_claude_api).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="3. Excel保存テスト", 
                  command=self.test_excel_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="4. 全プロセステスト", 
                  command=self.test_full_process).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="ログクリア", 
                  command=self.clear_log).pack(side=tk.RIGHT, padx=5)
        
        self.df = None
        self.excel_path = None
    
    def log(self, message, level="INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{level}] {message}\n"
        self.log_text.insert(tk.END, log_line)
        self.log_text.see(tk.END)
        self.update_idletasks()
        print(log_line.strip())  # コンソールにも出力
    
    def clear_log(self):
        """ログクリア"""
        self.log_text.delete(1.0, tk.END)
    
    def select_file(self):
        """ファイル選択"""
        file_path = filedialog.askopenfilename(
            title="Excelファイルを選択",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.excel_path = file_path
            self.log(f"ファイル選択: {file_path}")
    
    def test_load_file(self):
        """ファイル読み込みテスト"""
        try:
            self.log("=" * 80)
            self.log("【1. ファイル読み込みテスト開始】")
            
            if not self.excel_path:
                self.log("エラー: ファイルが選択されていません", "ERROR")
                return
            
            self.log(f"ファイルパス: {self.excel_path}")
            self.log(f"ファイル存在確認: {os.path.exists(self.excel_path)}")
            
            # pandasで読み込み
            self.log("pandas.read_excel()で読み込み開始...")
            self.df = pd.read_excel(self.excel_path)
            self.log(f"読み込み成功: {len(self.df)}行")
            
            # 列名確認
            self.log(f"列名: {list(self.df.columns)}")
            
            # 本名とフリガナ列の確認
            if '本名' in self.df.columns:
                self.log(f"「本名」列: 存在 ({self.df['本名'].notna().sum()}件)")
                self.log(f"「本名」サンプル: {self.df['本名'].head(3).tolist()}")
            else:
                self.log("「本名」列: 存在しない", "ERROR")
            
            if 'フリガナ' in self.df.columns:
                empty_count = (self.df['フリガナ'].isna() | (self.df['フリガナ'] == '')).sum()
                has_paren_count = self.df['フリガナ'].astype(str).str.contains(r'\(.*\)', regex=True).sum()
                self.log(f"「フリガナ」列: 存在 (空={empty_count}件, ()あり={has_paren_count}件)")
                self.log(f"「フリガナ」サンプル: {self.df['フリガナ'].head(3).tolist()}")
            else:
                self.log("「フリガナ」列: 存在しない", "ERROR")
            
            # 会員ID列の確認
            if '会員ID' in self.df.columns:
                self.log(f"「会員ID」列: 存在 ({self.df['会員ID'].notna().sum()}件)")
                self.log(f"「会員ID」サンプル: {self.df['会員ID'].head(3).tolist()}")
            else:
                self.log("「会員ID」列: 存在しない", "WARN")
            
            # openpyxlで読み込み（data_only=True）
            self.log("\nopenpyxl.load_workbook(data_only=True)で読み込み開始...")
            wb_data = openpyxl.load_workbook(self.excel_path, data_only=True)
            ws_data = wb_data.active
            self.log(f"読み込み成功: {ws_data.max_row}行 x {ws_data.max_column}列")
            
            # 会員ID列の値確認（data_only=True）
            header_row = [cell.value for cell in ws_data[1]]
            if '会員ID' in header_row:
                member_id_col = header_row.index('会員ID') + 1
                member_ids = [ws_data.cell(row=i, column=member_id_col).value for i in range(2, min(5, ws_data.max_row + 1))]
                self.log(f"「会員ID」値（data_only=True）: {member_ids}")
            wb_data.close()
            
            # openpyxlで読み込み（data_only=False）
            self.log("\nopenpyxl.load_workbook(data_only=False)で読み込み開始...")
            wb_formula = openpyxl.load_workbook(self.excel_path, data_only=False)
            ws_formula = wb_formula.active
            self.log(f"読み込み成功: {ws_formula.max_row}行 x {ws_formula.max_column}列")
            
            # 会員ID列の数式確認（data_only=False）
            if '会員ID' in header_row:
                member_id_col = header_row.index('会員ID') + 1
                for i in range(2, min(5, ws_formula.max_row + 1)):
                    cell = ws_formula.cell(row=i, column=member_id_col)
                    self.log(f"行{i} 会員ID: 値={cell.value}, 数式={cell.value if not hasattr(cell, 'data_type') or cell.data_type != 'f' else 'formula'}")
            wb_formula.close()
            
            self.log("【1. ファイル読み込みテスト完了】✅")
            
        except Exception as e:
            self.log(f"エラー: {e}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")
    
    def test_claude_api(self):
        """Claude API呼び出しテスト"""
        try:
            self.log("=" * 80)
            self.log("【2. Claude API呼び出しテスト開始】")
            
            if self.df is None:
                self.log("エラー: 先にファイルを読み込んでください", "ERROR")
                return
            
            api_key = self.api_key_var.get().strip()
            if not api_key:
                self.log("エラー: APIキーが入力されていません", "ERROR")
                return
            
            model = self.model_var.get().strip()
            existing_mode = self.mode_var.get()
            
            self.log(f"APIキー: {api_key[:10]}...{api_key[-4:]}")
            self.log(f"モデル: {model}")
            self.log(f"既存フリガナモード: {existing_mode}")
            
            # データ準備
            names = self.df['本名'].tolist()
            existing_furigana = self.df['フリガナ'].tolist()
            
            self.log(f"処理対象: {len(names)}件")
            
            # 最初の3件のみテスト
            test_names = names[:3]
            test_furigana = existing_furigana[:3]
            
            self.log(f"\nテストデータ（最初の3件）:")
            for i, (name, furi) in enumerate(zip(test_names, test_furigana)):
                self.log(f"  {i+1}. 本名={name}, フリガナ={furi}")
            
            # furigana_helperをインポート
            self.log("\nfurigana_helper.pyをインポート...")
            from furigana_helper import generate_furigana_batch
            
            # Claude API呼び出し
            self.log("\nClaude API呼び出し開始...")
            results = generate_furigana_batch(test_names, test_furigana, api_key, model, existing_mode=existing_mode)
            
            self.log(f"\nAPI呼び出し成功: {len(results)}件の結果")
            self.log("結果:")
            for name, furi in results.items():
                self.log(f"  {name} → {furi}")
            
            self.log("【2. Claude API呼び出しテスト完了】✅")
            
        except Exception as e:
            self.log(f"エラー: {e}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")
    
    def test_excel_save(self):
        """Excel保存テスト"""
        try:
            self.log("=" * 80)
            self.log("【3. Excel保存テスト開始】")
            
            if not self.excel_path:
                self.log("エラー: ファイルが選択されていません", "ERROR")
                return
            
            # テスト用のバックアップファイル作成
            backup_path = self.excel_path.replace('.xlsx', '_backup_test.xlsx')
            self.log(f"バックアップファイル作成: {backup_path}")
            
            import shutil
            shutil.copy2(self.excel_path, backup_path)
            
            # data_only=Falseで読み込み
            self.log("\nopenpyxl.load_workbook(data_only=False)で読み込み...")
            wb = openpyxl.load_workbook(backup_path, data_only=False)
            ws = wb.active
            
            # ヘッダー行取得
            header_row = [cell.value for cell in ws[1]]
            self.log(f"ヘッダー: {header_row}")
            
            # フリガナ列のインデックス取得
            try:
                furigana_col_idx = header_row.index('フリガナ') + 1
                self.log(f"「フリガナ」列インデックス: {furigana_col_idx}")
            except ValueError:
                self.log("エラー: 「フリガナ」列が見つかりません", "ERROR")
                wb.close()
                return
            
            # 会員ID列のインデックス取得
            member_id_col_idx = None
            if '会員ID' in header_row:
                member_id_col_idx = header_row.index('会員ID') + 1
                self.log(f"「会員ID」列インデックス: {member_id_col_idx}")
            
            # 保存前の会員ID確認
            if member_id_col_idx:
                self.log("\n保存前の会員ID（最初の3行）:")
                for i in range(2, min(5, ws.max_row + 1)):
                    cell = ws.cell(row=i, column=member_id_col_idx)
                    self.log(f"  行{i}: 値={cell.value}")
            
            # フリガナを更新（テスト用）
            self.log("\nフリガナ列を更新（テスト）...")
            test_furigana = "(ﾃｽﾄ)"
            ws.cell(row=2, column=furigana_col_idx).value = test_furigana
            self.log(f"  行2のフリガナを '{test_furigana}' に更新")
            
            # 保存
            self.log("\nファイル保存中...")
            wb.save(backup_path)
            wb.close()
            self.log("保存完了")
            
            # 保存後に再読み込み（data_only=True）
            self.log("\n保存後の再読み込み（data_only=True）...")
            wb_after = openpyxl.load_workbook(backup_path, data_only=True)
            ws_after = wb_after.active
            
            # フリガナ確認
            furi_after = ws_after.cell(row=2, column=furigana_col_idx).value
            self.log(f"行2のフリガナ: {furi_after}")
            
            # 会員ID確認
            if member_id_col_idx:
                self.log("\n保存後の会員ID（最初の3行）:")
                for i in range(2, min(5, ws_after.max_row + 1)):
                    cell = ws_after.cell(row=i, column=member_id_col_idx)
                    self.log(f"  行{i}: 値={cell.value}")
            
            wb_after.close()
            
            self.log("\n【3. Excel保存テスト完了】✅")
            self.log(f"バックアップファイル: {backup_path}")
            
        except Exception as e:
            self.log(f"エラー: {e}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")
    
    def test_full_process(self):
        """全プロセステスト"""
        try:
            self.log("=" * 80)
            self.log("【4. 全プロセステスト開始】")
            
            if not self.excel_path:
                self.log("エラー: ファイルが選択されていません", "ERROR")
                return
            
            api_key = self.api_key_var.get().strip()
            if not api_key:
                self.log("エラー: APIキーが入力されていません", "ERROR")
                return
            
            model = self.model_var.get().strip()
            existing_mode = self.mode_var.get()
            
            # テスト用のバックアップファイル作成
            backup_path = self.excel_path.replace('.xlsx', '_backup_full_test.xlsx')
            self.log(f"バックアップファイル作成: {backup_path}")
            
            import shutil
            shutil.copy2(self.excel_path, backup_path)
            
            # 1. ファイル読み込み
            self.log("\n[ステップ1] pandas.read_excel()で読み込み...")
            df = pd.read_excel(backup_path)
            self.log(f"読み込み成功: {len(df)}行")
            
            # 2. データ準備
            self.log("\n[ステップ2] データ準備...")
            names = df['本名'].tolist()
            existing_furigana = df['フリガナ'].tolist()
            self.log(f"処理対象: {len(names)}件")
            
            # 最初の3件のみテスト
            test_names = names[:3]
            test_furigana = existing_furigana[:3]
            
            # 3. Claude API呼び出し
            self.log("\n[ステップ3] Claude API呼び出し...")
            from furigana_helper import generate_furigana_batch
            results = generate_furigana_batch(test_names, test_furigana, api_key, model, existing_mode=existing_mode)
            self.log(f"API呼び出し成功: {len(results)}件の結果")
            for name, furi in results.items():
                self.log(f"  {name} → {furi}")
            
            # 4. Excel保存
            self.log("\n[ステップ4] openpyxl.load_workbook(data_only=False)で読み込み...")
            wb = openpyxl.load_workbook(backup_path, data_only=False)
            ws = wb.active
            
            # ヘッダー行取得
            header_row = [cell.value for cell in ws[1]]
            name_col_idx = header_row.index('本名') + 1
            furigana_col_idx = header_row.index('フリガナ') + 1
            member_id_col_idx = header_row.index('会員ID') + 1 if '会員ID' in header_row else None
            
            self.log(f"列インデックス: 本名={name_col_idx}, フリガナ={furigana_col_idx}, 会員ID={member_id_col_idx}")
            
            # 保存前の会員ID確認
            if member_id_col_idx:
                self.log("\n保存前の会員ID（最初の3行）:")
                for i in range(2, min(5, ws.max_row + 1)):
                    cell = ws.cell(row=i, column=member_id_col_idx)
                    self.log(f"  行{i}: 値={cell.value}")
            
            # フリガナ更新
            self.log("\n[ステップ5] フリガナ更新...")
            updated_count = 0
            for row_idx in range(2, ws.max_row + 1):
                name_cell = ws.cell(row=row_idx, column=name_col_idx)
                name = name_cell.value
                
                if name and name in results:
                    furigana_cell = ws.cell(row=row_idx, column=furigana_col_idx)
                    old_value = furigana_cell.value
                    furigana_cell.value = results[name]
                    self.log(f"  行{row_idx}: {name} のフリガナ '{old_value}' → '{results[name]}'")
                    updated_count += 1
            
            self.log(f"更新件数: {updated_count}件")
            
            # 保存
            self.log("\n[ステップ6] ファイル保存...")
            wb.save(backup_path)
            wb.close()
            self.log("保存完了")
            
            # 保存後に再読み込み（data_only=True）
            self.log("\n[ステップ7] 保存後の再読み込み（data_only=True）...")
            wb_after = openpyxl.load_workbook(backup_path, data_only=True)
            ws_after = wb_after.active
            
            # フリガナ確認
            self.log("\n保存後のフリガナ（最初の3行）:")
            for i in range(2, min(5, ws_after.max_row + 1)):
                furi = ws_after.cell(row=i, column=furigana_col_idx).value
                self.log(f"  行{i}: {furi}")
            
            # 会員ID確認
            if member_id_col_idx:
                self.log("\n保存後の会員ID（最初の3行）:")
                for i in range(2, min(5, ws_after.max_row + 1)):
                    cell = ws_after.cell(row=i, column=member_id_col_idx)
                    self.log(f"  行{i}: 値={cell.value}")
            
            wb_after.close()
            
            # DataFrameも更新
            self.log("\n[ステップ8] DataFrameも更新...")
            for idx, name in enumerate(test_names):
                if pd.notna(name) and name != '' and name in results:
                    df.at[idx, 'フリガナ'] = results[name]
                    self.log(f"  df[{idx}]['フリガナ'] = {results[name]}")
            
            # DataFrame確認
            self.log("\n更新後のDataFrame（最初の3行）:")
            for i in range(min(3, len(df))):
                self.log(f"  行{i}: 本名={df.at[i, '本名']}, フリガナ={df.at[i, 'フリガナ']}, 会員ID={df.at[i, '会員ID'] if '会員ID' in df.columns else 'N/A'}")
            
            self.log("\n【4. 全プロセステスト完了】✅")
            self.log(f"バックアップファイル: {backup_path}")
            
        except Exception as e:
            self.log(f"エラー: {e}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")

if __name__ == "__main__":
    app = FuriganaDebugTester()
    app.mainloop()
