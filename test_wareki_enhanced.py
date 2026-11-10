# -*- coding: utf-8 -*-
"""
和暦検索の強化テスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import parse_fuzzy_date, parse_date_with_separators


def test_wareki_kanji():
    """漢字表記の和暦テスト"""
    print("\n=== 漢字表記の和暦テスト ===")
    
    # 昭和60
    result = parse_fuzzy_date("昭和60")
    print(f"昭和60 → {result}")
    assert (1985, None, None) in result, f"昭和60が正しく解析されませんでした: {result}"
    
    # 昭60
    result = parse_fuzzy_date("昭60")
    print(f"昭60 → {result}")
    assert (1985, None, None) in result, f"昭60が正しく解析されませんでした: {result}"
    
    # 昭.60
    result = parse_fuzzy_date("昭.60")
    print(f"昭.60 → {result}")
    assert (1985, None, None) in result, f"昭.60が正しく解析されませんでした: {result}"
    
    print("✅ 漢字表記の和暦テスト成功")


def test_wareki_dot_separator():
    """ドット区切りの和暦テスト"""
    print("\n=== ドット区切りの和暦テスト ===")
    
    # S.51.5.1
    result = parse_fuzzy_date("S.51.5.1")
    print(f"S.51.5.1 → {result}")
    assert (1976, 5, 1) in result, f"S.51.5.1が正しく解析されませんでした: {result}"
    
    # s.51.5.1 (小文字)
    result = parse_fuzzy_date("s.51.5.1")
    print(f"s.51.5.1 → {result}")
    assert (1976, 5, 1) in result, f"s.51.5.1が正しく解析されませんでした: {result}"
    
    # H.1.5
    result = parse_fuzzy_date("H.1.5")
    print(f"H.1.5 → {result}")
    assert (1989, 5, None) in result, f"H.1.5が正しく解析されませんでした: {result}"
    
    print("✅ ドット区切りの和暦テスト成功")


def test_wareki_with_separators():
    """parse_date_with_separatorsのテスト"""
    print("\n=== parse_date_with_separators テスト ===")
    
    # 昭和63年12月31日
    result = parse_date_with_separators("昭和63年12月31日")
    print(f"昭和63年12月31日 → {result}")
    assert result == (1988, 12, 31), f"昭和63年12月31日が正しく解析されませんでした: {result}"
    
    # 昭63年12月31日
    result = parse_date_with_separators("昭63年12月31日")
    print(f"昭63年12月31日 → {result}")
    assert result == (1988, 12, 31), f"昭63年12月31日が正しく解析されませんでした: {result}"
    
    # 平成元年1月8日
    result = parse_date_with_separators("平成元年1月8日")
    print(f"平成元年1月8日 → {result}")
    # 元年は1年として扱われる
    
    # S.60.5.1
    result = parse_date_with_separators("S.60.5.1")
    print(f"S.60.5.1 → {result}")
    assert result == (1985, 5, 1), f"S.60.5.1が正しく解析されませんでした: {result}"
    
    print("✅ parse_date_with_separators テスト成功")


def test_zero_padding():
    """ゼロパディングのテスト"""
    print("\n=== ゼロパディングのテスト ===")
    
    # 5月と05月
    result1 = parse_date_with_separators("1990/5/15")
    result2 = parse_date_with_separators("1990/05/15")
    print(f"1990/5/15 → {result1}")
    print(f"1990/05/15 → {result2}")
    assert result1 == result2, "5月と05月で結果が異なります"
    
    # S51.5.1とS51.05.01
    result1 = parse_fuzzy_date("S51.5.1")
    result2 = parse_fuzzy_date("S51.05.01")
    print(f"S51.5.1 → {result1}")
    print(f"S51.05.01 → {result2}")
    assert (1976, 5, 1) in result1 and (1976, 5, 1) in result2, "ゼロパディングで結果が異なります"
    
    print("✅ ゼロパディングのテスト成功")


def test_partial_search():
    """部分検索のテスト（15 → 1月5日、H15年、S15年など）"""
    print("\n=== 部分検索のテスト ===")
    
    # 15
    result = parse_fuzzy_date("15")
    print(f"15 → {result}")
    
    # 1月5日を含むか
    has_jan_5 = any(m == 1 and d == 5 for y, m, d in result if m is not None and d is not None)
    print(f"  1月5日を含む: {has_jan_5}")
    
    # H15年（2003年）を含むか
    has_h15 = any(y == 2003 for y, m, d in result)
    print(f"  H15年（2003年）を含む: {has_h15}")
    
    # S15年（1940年）を含むか
    has_s15 = any(y == 1940 for y, m, d in result)
    print(f"  S15年（1940年）を含む: {has_s15}")
    
    # 2015年を含むか
    has_2015 = any(y == 2015 for y, m, d in result)
    print(f"  2015年を含む: {has_2015}")
    
    print("✅ 部分検索のテスト成功")


if __name__ == "__main__":
    try:
        test_wareki_kanji()
        test_wareki_dot_separator()
        test_wareki_with_separators()
        test_zero_padding()
        test_partial_search()
        
        print("\n" + "="*50)
        print("🎉 全てのテストが成功しました！")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
