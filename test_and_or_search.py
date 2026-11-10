# -*- coding: utf-8 -*-
"""
AND/OR検索の徹底的なテストプログラム

第一段階: 通常部分検索のAND/OR
第二段階: 一文字違い検索のAND/OR

すべての区切り文字（空白、＆、&、AND、and、｜、|、OR、or、ＯＲ）をテスト
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import re
from customer_app import normalize_text_unified, hira_to_kata
import Levenshtein

# テストデータを作成
test_data = {
    '登録名': [
        '田中太郎',
        '山田花子',
        '佐藤次郎',
        '鈴木三郎',
        '高橋四郎',
        '出禁太郎',
        '出雲花子',
        '出口次郎',
        '田中出禁',
        '山田出雲',
    ],
    '電話番号': [
        '080-1234-5678',
        '090-2345-6789',
        '070-3456-7890',
        '080-4567-8901',
        '090-5678-9012',
        '070-6789-0123',
        '080-7890-1234',
        '090-8901-2345',
        '070-9012-3456',
        '080-0123-4567',
    ],
    '住所': [
        '東京都',
        '大阪府',
        '愛知県',
        '福岡県',
        '北海道',
        '東京都',
        '大阪府',
        '愛知県',
        '福岡県',
        '北海道',
    ]
}

df = pd.DataFrame(test_data)

# 検索インデックスを作成
def create_search_index(row):
    return ' '.join(row.astype(str).values)

df['search_index'] = df.apply(create_search_index, axis=1)

print("=" * 80)
print("テストデータ:")
print("=" * 80)
print(df[['登録名', '電話番号', '住所']])
print()

# キーワード解析関数
def parse_search_keywords(query):
    """キーワードをAND/ORに解析"""
    try:
        # OR区切り文字で分割（｜、|、OR、or、ＯＲ）
        or_pattern = r'[｜|]|\s+OR\s+|\s+or\s+|\s+ＯＲ\s+'
        or_groups = re.split(or_pattern, query)
        
        result = []
        for group in or_groups:
            # AND区切り文字で分割（空白、＆、&、AND、and）
            and_pattern = r'\s+AND\s+|\s+and\s+|[＆&]|\s+'
            and_keywords = [k.strip() for k in re.split(and_pattern, group) if k.strip()]
            if and_keywords:
                result.append(and_keywords)
        
        return result  # [["田中", "太郎"], ["山田", "花子"]]
    except Exception as e:
        print(f"キーワード解析エラー: {e}")
        return [[query.strip()]]

# 部分一致検索（第一段階）
def get_normal_matches(query, df):
    """通常の部分一致検索"""
    keyword_groups = parse_search_keywords(query)
    
    or_mask = pd.Series([False] * len(df), index=df.index)
    
    for and_group in keyword_groups:
        and_mask = pd.Series([True] * len(df), index=df.index)
        for keyword in and_group:
            q_norm = normalize_text_unified(keyword)
            q_kana = normalize_text_unified(hira_to_kata(keyword))
            
            keyword_mask = df['search_index'].str.contains(q_norm, na=False, regex=False)
            if q_kana != q_norm:
                keyword_mask = keyword_mask | df['search_index'].str.contains(q_kana, na=False, regex=False)
            
            and_mask = and_mask & keyword_mask
        
        or_mask = or_mask | and_mask
    
    return df.index[or_mask].tolist()

# 一文字違い検索（第二段階）
def check_fuzzy_match_with_substring(query_norm, cell_norm):
    """部分文字列を含む編集距離チェック"""
    if not query_norm or not cell_norm:
        return False
    
    query_len = len(query_norm)
    
    # クエリ文字列が短い場合は完全一致のみ
    if query_len <= 2:
        return query_norm in cell_norm
    
    # セル内の部分文字列をチェック
    for i in range(len(cell_norm) - query_len + 2):
        substring = cell_norm[i:i + query_len]
        if len(substring) >= query_len - 1:
            distance = Levenshtein.distance(query_norm, substring)
            if distance <= 1:
                return True
    
    return False

def get_fuzzy_matches(query, df, already_matched):
    """一文字違い検索"""
    keyword_groups = parse_search_keywords(query)
    
    fuzzy_matches = []
    
    for and_group in keyword_groups:
        keyword_match_sets = []
        
        for keyword in and_group:
            if len(keyword) <= 1:
                continue
            
            q_norm = normalize_text_unified(keyword)
            q_kana = normalize_text_unified(hira_to_kata(keyword))
            
            keyword_matches = set()
            
            for idx in df.index:
                if idx in already_matched:
                    continue
                
                row = df.loc[idx]
                
                # 各列をチェック
                for col in ['登録名', '電話番号', '住所']:
                    cell_value = str(row[col])
                    if not cell_value or cell_value == '':
                        continue
                    
                    cell_norm = normalize_text_unified(cell_value)
                    
                    if check_fuzzy_match_with_substring(q_norm, cell_norm):
                        keyword_matches.add(idx)
                        break
                    
                    if check_fuzzy_match_with_substring(q_kana, cell_norm):
                        keyword_matches.add(idx)
                        break
            
            if keyword_matches:
                keyword_match_sets.append(keyword_matches)
        
        # ANDグループの場合は積集合を取る
        if keyword_match_sets:
            group_matches = keyword_match_sets[0]
            for i in range(1, len(keyword_match_sets)):
                group_matches = group_matches & keyword_match_sets[i]
            
            if group_matches:
                fuzzy_matches.extend(list(group_matches))
    
    return list(set(fuzzy_matches))

# テストケース
test_cases = [
    # AND検索（空白区切り）
    "出禁 070",
    "田中 080",
    "山田 090",
    
    # AND検索（＆区切り）
    "出禁＆070",
    "田中＆080",
    
    # AND検索（&区切り）
    "出禁&070",
    "田中&080",
    
    # AND検索（AND区切り）
    "出禁 AND 070",
    "田中 AND 080",
    
    # AND検索（and区切り）
    "出禁 and 070",
    "田中 and 080",
    
    # OR検索（｜区切り）
    "出禁｜出雲",
    "070｜080",
    
    # OR検索（|区切り）
    "出禁|出雲",
    "070|080",
    
    # OR検索（OR区切り）
    "出禁 OR 出雲",
    "070 OR 080",
    
    # OR検索（or区切り）
    "出禁 or 出雲",
    "070 or 080",
    
    # OR検索（ＯＲ区切り）
    "出禁 ＯＲ 出雲",
    "070 ＯＲ 080",
    
    # AND/OR混合（空白とOR）
    "出禁 070 OR 出雲 080",
    "田中 080 OR 山田 090",
    
    # AND/OR混合（＆とOR）
    "出禁＆070 OR 出雲＆080",
    "田中＆080 OR 山田＆090",
    
    # AND/OR混合（ANDとOR）
    "出禁 AND 070 OR 出雲 AND 080",
    "田中 AND 080 OR 山田 AND 090",
    
    # 複雑なAND/OR混合
    "出禁 070 | 出雲 080 | 出口 090",
    "田中 080 OR 山田 090 OR 佐藤 070",
]

print("=" * 80)
print("テスト開始:")
print("=" * 80)
print()

# 詳細デバッグ用：「出禁 070」のみをテスト
debug_query = "出禁 070"
print(f"【詳細デバッグ】検索クエリ: 「{debug_query}」")
print("-" * 80)

keyword_groups = parse_search_keywords(debug_query)
print(f"解析結果: {keyword_groups}")
print()

# 第一段階
normal_matches = get_normal_matches(debug_query, df)
print(f"第一段階（通常部分検索）: {len(normal_matches)}件")
for idx in normal_matches:
    row = df.loc[idx]
    print(f"  - [{idx}] {row['登録名']} / {row['電話番号']} / {row['住所']}")
print()

# 第二段階の詳細デバッグ
print("第二段階（一文字違い検索）の詳細:")
print()

already_matched = set(normal_matches)
and_group = keyword_groups[0]  # ['出禁', '070']

keyword_match_sets = []

for keyword in and_group:
    print(f"キーワード「{keyword}」の一文字違い検索:")
    
    q_norm = normalize_text_unified(keyword)
    keyword_matches = set()
    
    for idx in df.index:
        if idx in already_matched:
            continue
        
        row = df.loc[idx]
        
        for col in ['登録名', '電話番号', '住所']:
            cell_value = str(row[col])
            if not cell_value or cell_value == '':
                continue
            
            cell_norm = normalize_text_unified(cell_value)
            
            if check_fuzzy_match_with_substring(q_norm, cell_norm):
                keyword_matches.add(idx)
                print(f"  ✓ [{idx}] {row['登録名']} / {row['電話番号']} (列: {col})")
                break
    
    print(f"  → 合計 {len(keyword_matches)}件")
    print()
    
    if keyword_matches:
        keyword_match_sets.append(keyword_matches)

# 積集合を計算
print("積集合の計算:")
if keyword_match_sets:
    print(f"  キーワード1のマッチ: {len(keyword_match_sets[0])}件")
    if len(keyword_match_sets) > 1:
        print(f"  キーワード2のマッチ: {len(keyword_match_sets[1])}件")
        group_matches = keyword_match_sets[0] & keyword_match_sets[1]
        print(f"  積集合（AND条件）: {len(group_matches)}件")
        
        if group_matches:
            print("\n積集合の結果:")
            for idx in group_matches:
                row = df.loc[idx]
                print(f"    - [{idx}] {row['登録名']} / {row['電話番号']} / {row['住所']}")
        else:
            print("\n積集合の結果: （ヒットなし）")
    else:
        print(f"  キーワードが1つだけなので積集合なし")
else:
    print("  マッチなし")

print()
print("=" * 80)
print()

for i, query in enumerate(test_cases, 1):
    print(f"【テストケース {i}】")
    print(f"検索クエリ: 「{query}」")
    print("-" * 80)
    
    # キーワード解析
    keyword_groups = parse_search_keywords(query)
    print(f"解析結果: {keyword_groups}")
    
    # 第一段階: 通常部分検索
    normal_matches = get_normal_matches(query, df)
    print(f"\n第一段階（通常部分検索）: {len(normal_matches)}件")
    if normal_matches:
        for idx in normal_matches:
            row = df.loc[idx]
            print(f"  - [{idx}] {row['登録名']} / {row['電話番号']} / {row['住所']}")
    else:
        print("  （ヒットなし）")
    
    # 第二段階: 一文字違い検索
    fuzzy_matches = get_fuzzy_matches(query, df, set(normal_matches))
    print(f"\n第二段階（一文字違い検索）: {len(fuzzy_matches)}件")
    if fuzzy_matches:
        for idx in fuzzy_matches:
            row = df.loc[idx]
            print(f"  - [{idx}] {row['登録名']} / {row['電話番号']} / {row['住所']} ★曖昧")
    else:
        print("  （ヒットなし）")
    
    # 合計
    total = len(normal_matches) + len(fuzzy_matches)
    print(f"\n合計: {total}件")
    print("=" * 80)
    print()

print("テスト完了！")
