# -*- coding: utf-8 -*-
"""
実際のアプリケーションロジックをシミュレートして問題を特定
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from customer_app import normalize_text_unified, hira_to_kata
import Levenshtein

# テストデータ（実際のデータに近い形式）
test_data = {
    '登録名': ['出禁太郎', '出雲花子', '出口次郎', '田中太郎', '山田花子', '佐藤次郎'],
    '本名': ['', '', '', '', '', ''],
    'フリガナ': ['シュッキンタロウ', 'イズモハナコ', 'デグチジロウ', 'タナカタロウ', 'ヤマダハナコ', 'サトウジロウ'],
    '電話番号': ['070-1111-1111', '080-2222-2222', '090-3333-3333', '080-4444-4444', '090-5555-5555', '070-6666-6666'],
    '電話番号2': ['', '', '', '', '', ''],
    '電話番号3': ['', '', '', '', '', ''],
    '住所': ['東京都', '大阪府', '愛知県', '福岡県', '北海道', '東京都'],
}

df = pd.DataFrame(test_data)

print("=" * 80)
print("【実際のアプリケーションロジックをシミュレート】")
print("=" * 80)
print()

print("テストデータ:")
print(df[['登録名', '電話番号', '住所']])
print()

# ========================================
# 実際のアプリケーションの関数をシミュレート
# ========================================

def levenshtein_distance(s1, s2):
    """レーベンシュタイン距離を計算"""
    return Levenshtein.distance(s1, s2)

def check_fuzzy_match(query, target):
    """シンプルな編集距離チェック（編集距離1のみ許可）"""
    query_len = len(query)
    
    # 1文字の場合は曖昧検索しない
    if query_len <= 1:
        return False
    
    # 編集距離が1かチェック
    dist = levenshtein_distance(query, target)
    return dist == 1

def check_fuzzy_match_with_substring(query, target, col_name):
    """部分文字列を含む編集距離チェック"""
    query_len = len(query)
    
    # 1文字の場合は曖昧検索しない
    if query_len <= 1:
        return False
    
    # 5文字以上の場合は部分文字列チェックをスキップ（負荷軽減）
    if query_len >= 5:
        return check_fuzzy_match(query, target)
    
    # 電話番号列または住所列の場合は部分文字列チェック
    is_phone_or_address = '電話番号' in col_name or '住所' in col_name
    
    if is_phone_or_address and len(target) >= query_len:
        # targetから query_len と同じ長さの部分文字列を抽出
        for i in range(len(target) - query_len + 1):
            substring = target[i:i + query_len]
            if check_fuzzy_match(query, substring):
                return True
        # 1文字長い部分文字列もチェック（追加の場合）
        for i in range(len(target) - query_len):
            substring = target[i:i + query_len + 1]
            if check_fuzzy_match(query, substring):
                return True
        return False
    
    # 名前列などは部分文字列もチェック
    if len(target) >= query_len:
        # 同じ長さの部分文字列をチェック
        for i in range(len(target) - query_len + 1):
            substring = target[i:i + query_len]
            if check_fuzzy_match(query, substring):
                return True
        # 1文字長い部分文字列もチェック（追加の場合）
        for i in range(len(target) - query_len):
            substring = target[i:i + query_len + 1]
            if check_fuzzy_match(query, substring):
                return True
    
    return check_fuzzy_match(query, target)

# ========================================
# テスト
# ========================================

print("=" * 80)
print("【check_fuzzy_match のテスト】")
print("=" * 80)
print()

print("「出禁」の一文字違いチェック:")
print(f"  出禁 vs 出雲: {check_fuzzy_match('出禁', '出雲')} (期待: True)")
print(f"  出禁 vs 出口: {check_fuzzy_match('出禁', '出口')} (期待: True)")
print(f"  出禁 vs 田中: {check_fuzzy_match('出禁', '田中')} (期待: False)")
print()

print("「070」の一文字違いチェック:")
print(f"  070 vs 080: {check_fuzzy_match('070', '080')} (期待: True)")
print(f"  070 vs 090: {check_fuzzy_match('070', '090')} (期待: True)")
print()

print("=" * 80)
print("【check_fuzzy_match_with_substring のテスト】")
print("=" * 80)
print()

print("「出禁」を登録名列でチェック:")
for idx, row in df.iterrows():
    name = row['登録名']
    name_norm = normalize_text_unified(name)
    result = check_fuzzy_match_with_substring('出禁', name_norm, '登録名')
    print(f"  [{idx}] {name} (norm: {name_norm}): {result}")
print()

print("「070」を電話番号列でチェック:")
for idx, row in df.iterrows():
    phone = row['電話番号']
    phone_norm = normalize_text_unified(phone)
    result = check_fuzzy_match_with_substring('070', phone_norm, '電話番号')
    print(f"  [{idx}] {phone} (norm: {phone_norm}): {result}")
print()

# ========================================
# 実際の検索シミュレーション
# ========================================

print("=" * 80)
print("【「出禁 070」の検索シミュレーション】")
print("=" * 80)
print()

# 第一段階：部分一致AND検索
print("第一段階（部分一致AND検索）:")
first_stage = []
for idx, row in df.iterrows():
    name = normalize_text_unified(row['登録名'])
    phone = normalize_text_unified(row['電話番号'])
    
    if '出禁' in name and '070' in phone:
        first_stage.append(idx)
        print(f"  ✓ [{idx}] {row['登録名']} / {row['電話番号']}")

if not first_stage:
    print("  （ヒットなし）")
print(f"  → {len(first_stage)}件")
print()

# 第二段階：一文字違いAND検索
print("第二段階（一文字違いAND検索）:")
print()

search_cols = ['登録名', '本名', 'フリガナ', '電話番号', '電話番号2', '電話番号3', '住所']
already_matched = set(first_stage)

# キーワード「出禁」の一文字違いマッチ
print("キーワード「出禁」の一文字違いマッチ:")
keyword1_matches = set()
for idx, row in df.iterrows():
    if idx in already_matched:
        continue
    
    for col in search_cols:
        cell_value = str(row[col])
        if not cell_value or cell_value == '':
            continue
        
        cell_norm = normalize_text_unified(cell_value)
        
        if check_fuzzy_match_with_substring('出禁', cell_norm, col):
            keyword1_matches.add(idx)
            print(f"  ✓ [{idx}] {row['登録名']} (列: {col}, 値: {cell_value})")
            break

print(f"  → {len(keyword1_matches)}件")
print()

# キーワード「070」の一文字違いマッチ
print("キーワード「070」の一文字違いマッチ:")
keyword2_matches = set()
for idx, row in df.iterrows():
    if idx in already_matched:
        continue
    
    for col in search_cols:
        cell_value = str(row[col])
        if not cell_value or cell_value == '':
            continue
        
        cell_norm = normalize_text_unified(cell_value)
        
        if check_fuzzy_match_with_substring('070', cell_norm, col):
            keyword2_matches.add(idx)
            print(f"  ✓ [{idx}] {row['登録名']} (列: {col}, 値: {cell_value})")
            break

print(f"  → {len(keyword2_matches)}件")
print()

# 積集合
print("積集合（AND条件）:")
second_stage = keyword1_matches & keyword2_matches
for idx in second_stage:
    row = df.loc[idx]
    print(f"  ✓ [{idx}] {row['登録名']} / {row['電話番号']}")

if not second_stage:
    print("  （ヒットなし）")
print(f"  → {len(second_stage)}件")
print()

# 最終結果
print("最終結果（第一段階 + 第二段階）:")
final_result = first_stage + list(second_stage)
for idx in final_result:
    row = df.loc[idx]
    print(f"  [{idx}] {row['登録名']} / {row['電話番号']}")
print(f"  → {len(final_result)}件")
print()

print("=" * 80)
print("テスト完了")
print("=" * 80)
