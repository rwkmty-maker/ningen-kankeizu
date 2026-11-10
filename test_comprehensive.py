# -*- coding: utf-8 -*-
"""
AND/OR検索の徹底的なテスト - 問題の本質を理解する
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import re
from customer_app import normalize_text_unified, hira_to_kata
import Levenshtein

# テストデータ
test_data = {
    '登録名': ['出禁太郎', '出雲花子', '出口次郎', '田中太郎', '山田花子'],
    '電話番号': ['070-1111-1111', '080-2222-2222', '090-3333-3333', '080-4444-4444', '090-5555-5555'],
}
df = pd.DataFrame(test_data)

print("=" * 80)
print("テストデータ:")
print(df)
print()

# 問題の本質を理解するための徹底テスト
print("=" * 80)
print("【問題の本質】")
print("=" * 80)
print()

print("「出禁 070」で検索した場合:")
print()
print("第一段階（通常部分検索）:")
print("  - 「出禁」を含む AND 「070」を含む")
print("  - 期待: [0] 出禁太郎 / 070-1111-1111")
print()
print("第二段階（一文字違い検索）:")
print("  - 「出禁」の一文字違いを含む AND 「070」の一文字違いを含む")
print("  - 期待:")
print("    - 「出禁」の一文字違い: 出雲、出口")
print("    - 「070」の一文字違い: 080、090")
print("    - 積集合: 出雲かつ080 → [1] 出雲花子 / 080-2222-2222")
print("              出口かつ090 → [2] 出口次郎 / 090-3333-3333")
print()

# 編集距離のテスト
print("=" * 80)
print("【編集距離のテスト】")
print("=" * 80)
print()

def test_levenshtein(s1, s2):
    dist = Levenshtein.distance(s1, s2)
    print(f"  '{s1}' vs '{s2}': 距離={dist}")
    return dist

print("「出禁」の一文字違い:")
test_levenshtein("出禁", "出雲")  # 期待: 1
test_levenshtein("出禁", "出口")  # 期待: 1
test_levenshtein("出禁", "田中")  # 期待: 2
print()

print("「070」の一文字違い:")
test_levenshtein("070", "080")  # 期待: 1
test_levenshtein("070", "090")  # 期待: 1
test_levenshtein("070", "071")  # 期待: 1
print()

# 正規化のテスト
print("=" * 80)
print("【正規化のテスト】")
print("=" * 80)
print()

def test_normalize(text):
    norm = normalize_text_unified(text)
    print(f"  '{text}' → '{norm}'")
    return norm

print("名前の正規化:")
norm_出禁 = test_normalize("出禁")
norm_出雲 = test_normalize("出雲")
norm_出口 = test_normalize("出口")
print()

print("電話番号の正規化:")
norm_070 = test_normalize("070")
norm_080 = test_normalize("080")
norm_090 = test_normalize("090")
print()

# 正規化後の編集距離
print("=" * 80)
print("【正規化後の編集距離】")
print("=" * 80)
print()

print("名前:")
test_levenshtein(norm_出禁, norm_出雲)
test_levenshtein(norm_出禁, norm_出口)
print()

print("電話番号:")
test_levenshtein(norm_070, norm_080)
test_levenshtein(norm_070, norm_090)
print()

# 正しいアルゴリズムの設計
print("=" * 80)
print("【正しいアルゴリズムの設計】")
print("=" * 80)
print()

print("AND検索「A B」の場合:")
print()
print("第一段階（通常部分検索）:")
print("  result1 = {行 | 行にAを含む AND 行にBを含む}")
print()
print("第二段階（一文字違い検索）:")
print("  A_fuzzy = {行 | 行にAの一文字違いを含む}")
print("  B_fuzzy = {行 | 行にBの一文字違いを含む}")
print("  result2 = A_fuzzy ∩ B_fuzzy - result1")
print()
print("最終結果:")
print("  result = result1 ∪ result2")
print()

# 実際のテスト
print("=" * 80)
print("【実際のテスト】")
print("=" * 80)
print()

def check_fuzzy_match_simple(query, target):
    """シンプルな編集距離チェック"""
    if len(query) <= 1:
        return False
    dist = Levenshtein.distance(query, target)
    return dist == 1

def check_contains_fuzzy(query, text):
    """テキスト内にクエリの一文字違いが含まれるかチェック"""
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
            if check_fuzzy_match_simple(query_norm, substring):
                return True
    
    return False

print("「出禁 070」の検索テスト:")
print()

# 第一段階
print("第一段階（通常部分検索）:")
result1 = []
for idx, row in df.iterrows():
    name = normalize_text_unified(row['登録名'])
    phone = normalize_text_unified(row['電話番号'])
    
    if '出禁' in name and '070' in phone:
        result1.append(idx)
        print(f"  ✓ [{idx}] {row['登録名']} / {row['電話番号']}")

if not result1:
    print("  （ヒットなし）")
print()

# 第二段階
print("第二段階（一文字違い検索）:")
print()

# 「出禁」の一文字違い
print("「出禁」の一文字違いを含む行:")
A_fuzzy = []
for idx, row in df.iterrows():
    if idx in result1:
        continue
    if check_contains_fuzzy("出禁", row['登録名']):
        A_fuzzy.append(idx)
        print(f"  ✓ [{idx}] {row['登録名']}")

if not A_fuzzy:
    print("  （ヒットなし）")
print()

# 「070」の一文字違い
print("「070」の一文字違いを含む行:")
B_fuzzy = []
for idx, row in df.iterrows():
    if idx in result1:
        continue
    if check_contains_fuzzy("070", row['電話番号']):
        B_fuzzy.append(idx)
        print(f"  ✓ [{idx}] {row['電話番号']}")

if not B_fuzzy:
    print("  （ヒットなし）")
print()

# 積集合
print("積集合（A_fuzzy ∩ B_fuzzy）:")
result2 = list(set(A_fuzzy) & set(B_fuzzy))
for idx in result2:
    row = df.loc[idx]
    print(f"  ✓ [{idx}] {row['登録名']} / {row['電話番号']}")

if not result2:
    print("  （ヒットなし）")
print()

# 最終結果
print("最終結果（result1 ∪ result2）:")
final_result = result1 + result2
for idx in final_result:
    row = df.loc[idx]
    print(f"  [{idx}] {row['登録名']} / {row['電話番号']}")
print()
print(f"合計: {len(final_result)}件")
print()

print("=" * 80)
print("テスト完了")
print("=" * 80)
