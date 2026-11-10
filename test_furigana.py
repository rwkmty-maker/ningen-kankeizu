# -*- coding: utf-8 -*-
"""
フリガナ生成のテストスクリプト
Claude APIのレスポンスを確認
"""
import sys

# Claude API Keyを入力
api_key = input("Claude API Keyを入力してください: ").strip()

if not api_key:
    print("API Keyが入力されていません")
    sys.exit(1)

# テストデータ
test_names = ["山田太郎", "佐藤花子", "東海林"]
test_furigana = ["", "", ""]

print("\n=== フリガナ生成テスト開始 ===\n")

try:
    from furigana_helper import generate_furigana_batch
    
    print("テスト対象:")
    for name, furi in zip(test_names, test_furigana):
        print(f"  {name}, {furi}")
    
    print("\nClaude APIに問い合わせ中...\n")
    
    results = generate_furigana_batch(test_names, test_furigana, api_key, batch_size=10)
    
    print("\n=== 結果 ===")
    print(f"生成件数: {len(results)}件\n")
    
    for name in test_names:
        if name in results:
            print(f"✓ {name} -> {results[name]}")
        else:
            print(f"✗ {name} -> 生成されませんでした")
    
    print("\n=== 全結果 ===")
    for name, furigana in results.items():
        print(f"{name}: {furigana}")
    
except Exception as e:
    print(f"\nエラー: {e}")
    import traceback
    traceback.print_exc()

print("\n=== テスト終了 ===")
