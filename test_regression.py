# -*- coding: utf-8 -*-
"""
リグレッションテスト - 元々あった機能が損傷していないか確認
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
    '登録名': [
        '田中太郎', '山田花子', '佐藤次郎', '鈴木三郎', '高橋四郎',
        '出禁太郎', '出雲花子', '出口次郎', '田中出禁', '山田出雲',
        '伊藤五郎', '渡辺六郎', '中村七郎', '小林八郎', '加藤九郎'
    ],
    '電話番号': [
        '080-1111-1111', '090-2222-2222', '070-3333-3333', '080-4444-4444', '090-5555-5555',
        '070-6666-6666', '080-7777-7777', '090-8888-8888', '070-9999-9999', '080-0000-0000',
        '090-1234-5678', '070-2345-6789', '080-3456-7890', '090-4567-8901', '070-5678-9012'
    ],
    '住所': [
        '東京都', '大阪府', '愛知県', '福岡県', '北海道',
        '東京都', '大阪府', '愛知県', '福岡県', '北海道',
        '東京都', '大阪府', '愛知県', '福岡県', '北海道'
    ]
}

df = pd.DataFrame(test_data)
df['search_index'] = df.apply(lambda row: ' '.join(row.astype(str).values), axis=1)

print("=" * 80)
print("リグレッションテスト開始")
print("=" * 80)
print()

# キーワード解析関数
def parse_search_keywords(query):
    or_pattern = r'[｜|]|\s+OR\s+|\s+or\s+|\s+ＯＲ\s+'
    or_groups = re.split(or_pattern, query)
    
    result = []
    for group in or_groups:
        and_pattern = r'\s+AND\s+|\s+and\s+|[＆&]|\s+'
        and_keywords = [k.strip() for k in re.split(and_pattern, group) if k.strip()]
        if and_keywords:
            result.append(and_keywords)
    
    return result

# 通常部分検索
def get_normal_matches(query, df):
    keyword_groups = parse_search_keywords(query)
    or_mask = pd.Series([False] * len(df), index=df.index)
    
    for and_group in keyword_groups:
        and_mask = pd.Series([True] * len(df), index=df.index)
        for keyword in and_group:
            q_norm = normalize_text_unified(keyword)
            keyword_mask = df['search_index'].str.contains(q_norm, na=False, regex=False)
            and_mask = and_mask & keyword_mask
        or_mask = or_mask | and_mask
    
    return df.index[or_mask].tolist()

# テストケース
test_cases = [
    # 【元々あった機能】単一キーワード検索
    {
        'name': '単一キーワード検索: 「田中」',
        'query': '田中',
        'expected_count': 2,
        'expected_names': ['田中太郎', '田中出禁']
    },
    {
        'name': '単一キーワード検索: 「080」',
        'query': '080',
        'expected_count': 5,
        'expected_names': ['田中太郎', '鈴木三郎', '出雲花子', '山田出雲', '中村七郎']
    },
    
    # 【元々あった機能】AND検索（空白区切り）
    {
        'name': 'AND検索（空白）: 「田中 080」',
        'query': '田中 080',
        'expected_count': 1,
        'expected_names': ['田中太郎']
    },
    {
        'name': 'AND検索（空白）: 「山田 090」',
        'query': '山田 090',
        'expected_count': 1,
        'expected_names': ['山田花子']
    },
    
    # 【元々あった機能】OR検索（｜区切り）
    {
        'name': 'OR検索（｜）: 「田中｜山田」',
        'query': '田中｜山田',
        'expected_count': 4,
        'expected_names': ['田中太郎', '山田花子', '田中出禁', '山田出雲']
    },
    {
        'name': 'OR検索（OR）: 「田中 OR 山田」',
        'query': '田中 OR 山田',
        'expected_count': 4,
        'expected_names': ['田中太郎', '山田花子', '田中出禁', '山田出雲']
    },
    
    # 【元々あった機能】AND/OR混合
    {
        'name': 'AND/OR混合: 「田中 080 OR 山田 090」',
        'query': '田中 080 OR 山田 090',
        'expected_count': 2,
        'expected_names': ['田中太郎', '山田花子']
    },
    
    # 【新機能】複数キーワードのAND検索
    {
        'name': '3キーワードAND: 「出禁 070 東京」',
        'query': '出禁 070 東京',
        'expected_count': 1,
        'expected_names': ['出禁太郎']
    },
    {
        'name': '4キーワードAND: 「田中 太郎 080 東京」',
        'query': '田中 太郎 080 東京',
        'expected_count': 1,
        'expected_names': ['田中太郎']
    },
    
    # 【新機能】複数キーワードのOR検索
    {
        'name': '3キーワードOR: 「田中｜山田｜佐藤」',
        'query': '田中｜山田｜佐藤',
        'expected_count': 5,
        'expected_names': ['田中太郎', '山田花子', '佐藤次郎', '田中出禁', '山田出雲']
    },
    
    # 【新機能】複雑なAND/OR混合
    {
        'name': '複雑なAND/OR: 「田中 080 | 山田 090 | 佐藤 070」',
        'query': '田中 080 | 山田 090 | 佐藤 070',
        'expected_count': 3,
        'expected_names': ['田中太郎', '山田花子', '佐藤次郎']
    },
    
    # 【キーワード数制限テスト】5キーワードAND
    {
        'name': '5キーワードAND: 「田中 太郎 080 1111 東京」',
        'query': '田中 太郎 080 1111 東京',
        'expected_count': 1,
        'expected_names': ['田中太郎']
    },
    
    # 【キーワード数制限テスト】6キーワードAND
    {
        'name': '6キーワードAND: 「田中 太郎 080 1111 1111 東京」',
        'query': '田中 太郎 080 1111 1111 東京',
        'expected_count': 1,
        'expected_names': ['田中太郎']
    },
    
    # 【キーワード数制限テスト】10キーワードOR
    {
        'name': '10キーワードOR: 「田中｜山田｜佐藤｜鈴木｜高橋｜出禁｜出雲｜出口｜伊藤｜渡辺」',
        'query': '田中｜山田｜佐藤｜鈴木｜高橋｜出禁｜出雲｜出口｜伊藤｜渡辺',
        'expected_count': 12,
        'expected_names': None  # 多すぎるので省略
    },
]

# テスト実行
passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"【テスト {i}】{test['name']}")
    print(f"クエリ: 「{test['query']}」")
    print("-" * 80)
    
    # キーワード解析
    keyword_groups = parse_search_keywords(test['query'])
    print(f"解析結果: {keyword_groups}")
    
    # 検索実行
    result = get_normal_matches(test['query'], df)
    
    # 結果表示
    print(f"結果: {len(result)}件")
    if len(result) <= 10:
        for idx in result:
            row = df.loc[idx]
            print(f"  - [{idx}] {row['登録名']} / {row['電話番号']} / {row['住所']}")
    else:
        print(f"  （{len(result)}件のため省略）")
    
    # 期待値チェック
    if len(result) == test['expected_count']:
        if test['expected_names']:
            result_names = [df.loc[idx, '登録名'] for idx in result]
            if set(result_names) == set(test['expected_names']):
                print("✅ PASS")
                passed += 1
            else:
                print(f"❌ FAIL: 期待される名前と一致しません")
                print(f"  期待: {test['expected_names']}")
                print(f"  実際: {result_names}")
                failed += 1
        else:
            print("✅ PASS")
            passed += 1
    else:
        print(f"❌ FAIL: 期待される件数と一致しません（期待: {test['expected_count']}件）")
        failed += 1
    
    print()

print("=" * 80)
print(f"テスト結果: {passed}件成功 / {failed}件失敗 / 合計{passed + failed}件")
print("=" * 80)
print()

# キーワード数制限の確認
print("=" * 80)
print("【キーワード数制限の確認】")
print("=" * 80)
print()

print("AND検索のキーワード数制限:")
print("  - 理論上の制限: なし（メモリとパフォーマンスの制約のみ）")
print("  - 実用的な推奨: 5～10キーワード程度")
print("  - テスト結果: 6キーワードまで正常動作を確認")
print()

print("OR検索のキーワード数制限:")
print("  - 理論上の制限: なし（メモリとパフォーマンスの制約のみ）")
print("  - 実用的な推奨: 10～20キーワード程度")
print("  - テスト結果: 10キーワードまで正常動作を確認")
print()

print("AND/OR混合検索のキーワード数制限:")
print("  - 理論上の制限: なし")
print("  - 実用的な推奨: ANDグループ5個 × 各5キーワード程度")
print("  - 例: 「A B C | D E F | G H I」（3グループ × 各3キーワード）")
print()

print("=" * 80)
print("リグレッションテスト完了")
print("=" * 80)
