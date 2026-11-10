# -*- coding: utf-8 -*-
"""
生年月日検索のテストスクリプト
元号省略形が正しく生成されるかを確認
"""
import datetime
from utils.date_utils import generate_era_candidates, parse_fuzzy_date

def test_era_candidates():
    """元号省略形の候補生成テスト"""
    print("=" * 60)
    print("元号省略形候補生成テスト")
    print("=" * 60)
    
    # テストケース: H01/02/03 (平成1年2月3日 = 1989年2月3日)
    test_date = datetime.datetime(1989, 2, 3)
    candidates = generate_era_candidates(test_date.year, test_date.month, test_date.day)
    
    print(f"\n元データ: {test_date.year}年{test_date.month}月{test_date.day}日")
    print(f"和暦表記: H01/02/03 (平成1年2月3日)")
    print(f"\n生成された検索候補 ({len(candidates)}個):")
    
    sorted_candidates = sorted(set(candidates), key=lambda x: (len(x), x))
    for i, candidate in enumerate(sorted_candidates, 1):
        print(f"  {i:2d}. '{candidate}'")
    
    # 期待される候補が含まれているか確認
    expected = ['0123', '123', '010203', '10203', '8923', '890203', '19890203']
    print(f"\n期待される候補の確認:")
    for exp in expected:
        status = "OK" if exp in candidates else "NG"
        print(f"  {status} '{exp}'")
    
    return candidates

def test_fuzzy_date_parse():
    """曖昧日付パースのテスト"""
    print("\n" + "=" * 60)
    print("曖昧日付パーステスト")
    print("=" * 60)
    
    test_queries = [
        "H1-2-03",
        "H01.02.3",
        "H010203",
        "0123",
        "123",
        "010203",
        "10203",
        "1989.2.3",
        "89.2.03",
        "8923",
        "89023",
        "19890203"
    ]
    
    for query in test_queries:
        result = parse_fuzzy_date(query)
        print(f"\n入力: '{query}'")
        if result:
            print(f"  解析結果: {result}")
            for y, m, d in result:
                if y and m and d:
                    print(f"    → {y}年{m}月{d}日")
                elif y and m:
                    print(f"    → {y}年{m}月")
                elif m and d:
                    print(f"    → {m}月{d}日")
        else:
            print(f"  解析結果: なし")

if __name__ == "__main__":
    # 元号省略形候補生成テスト
    candidates = test_era_candidates()
    
    # 曖昧日付パーステスト
    test_fuzzy_date_parse()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
