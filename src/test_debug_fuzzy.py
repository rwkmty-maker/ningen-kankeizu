# -*- coding: utf-8 -*-
"""
徹底的なデバッグテスト - 「出禁 070」の一文字違い検索
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from customer_app import normalize_text_unified, hira_to_kata
import Levenshtein

# テストデータ
test_data = {
    '登録名': ['出禁太郎', '出雲花子', '出口次郎', '田中太郎'],
    '電話番号': ['070-1111-1111', '080-2222-2222', '090-3333-3333', '080-4444-4444'],
}
df = pd.DataFrame(test_data)

print("=" * 80)
print("【徹底的なデバッグテスト】")
print("=" * 80)
print()

print("テストデータ:")
print(df)
print()

# 編集距離のテスト
print("=" * 80)
print("【編集距離のテスト】")
print("=" * 80)
print()

def test_distance(s1, s2):
    dist = Levenshtein.distance(s1, s2)
    print(f"  '{s1}' vs '{s2}': 距離={dist} {'✅' if dist == 1 else '❌'}")
    return dist

print("「出禁」の一文字違い:")
test_distance("出禁", "出雲")  # 期待: 1
test_distance("出禁", "出口")  # 期待: 1
test_distance("出禁", "田中")  # 期待: 2
print()

print("「070」の一文字違い:")
test_distance("070", "080")  # 期待: 1
test_distance("070", "090")  # 期待: 1
test_distance("070", "071")  # 期待: 1
print()

# シンプルな一文字違いチェック
print("=" * 80)
print("【シンプルな一文字違いチェック】")
print("=" * 80)
print()

def check_fuzzy_simple(query, target):
    """シンプルな編集距離チェック"""
    if len(query) <= 1:
        return False
    dist = Levenshtein.distance(query, target)
    return dist == 1

print("「出禁」の一文字違いチェック:")
print(f"  出禁 vs 出雲: {check_fuzzy_simple('出禁', '出雲')} ✅")
print(f"  出禁 vs 出口: {check_fuzzy_simple('出禁', '出口')} ✅")
print(f"  出禁 vs 田中: {check_fuzzy_simple('出禁', '田中')} ❌")
print()

print("「070」の一文字違いチェック:")
print(f"  070 vs 080: {check_fuzzy_simple('070', '080')} ✅")
print(f"  070 vs 090: {check_fuzzy_simple('070', '090')} ✅")
print()

# 部分文字列を含む一文字違いチェック
print("=" * 80)
print("【部分文字列を含む一文字違いチェック】")
print("=" * 80)
print()

def check_fuzzy_with_substring(query, text):
    """部分文字列を含む一文字違いチェック"""
    query_norm = normalize_text_unified(query)
    text_norm = normalize_text_unified(text)
    
    # 完全一致
    if query_norm in text_norm:
        return True
    
    # 部分文字列の一文字違い
    query_len = len(query_norm)
    for i in range(len(text_norm) - query_len + 2):
        substring = text_norm[i:i + query_len]
        if len(substring) >= query_len - 1:
            if check_fuzzy_simple(query_norm, substring):
                return True
    
    return False

print("「出禁」を含む一文字違い:")
for idx, row in df.iterrows():
    name = row['登録名']
    result = check_fuzzy_with_substring('出禁', name)
    print(f"  [{idx}] {name}: {result} {'✅' if result else '❌'}")
print()

print("「070」を含む一文字違い:")
for idx, row in df.iterrows():
    phone = row['電話番号']
    result = check_fuzzy_with_substring('070', phone)
    print(f"  [{idx}] {phone}: {result} {'✅' if result else '❌'}")
print()

# AND検索の積集合テスト
print("=" * 80)
print("【AND検索の積集合テスト】")
print("=" * 80)
print()

print("「出禁」の一文字違いを含む行:")
A_fuzzy = set()
for idx, row in df.iterrows():
    if check_fuzzy_with_substring('出禁', row['登録名']):
        A_fuzzy.add(idx)
        print(f"  ✓ [{idx}] {row['登録名']}")
print(f"  → {len(A_fuzzy)}件")
print()

print("「070」の一文字違いを含む行:")
B_fuzzy = set()
for idx, row in df.iterrows():
    if check_fuzzy_with_substring('070', row['電話番号']):
        B_fuzzy.add(idx)
        print(f"  ✓ [{idx}] {row['電話番号']}")
print(f"  → {len(B_fuzzy)}件")
print()

print("積集合（A_fuzzy ∩ B_fuzzy）:")
result = A_fuzzy & B_fuzzy
for idx in result:
    row = df.loc[idx]
    print(f"  ✓ [{idx}] {row['登録名']} / {row['電話番号']}")
print(f"  → {len(result)}件")
print()

if len(result) == 2 and 1 in result and 2 in result:
    print("✅ 期待通りの結果！")
else:
    print("❌ 期待と異なる結果")

print()
print("=" * 80)
print("デバッグテスト完了")
print("=" * 80)
