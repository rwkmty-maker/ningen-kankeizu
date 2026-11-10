# -*- coding: utf-8 -*-
"""
全パターンの網羅性テスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import parse_fuzzy_date


def test_3digit_patterns():
    """3桁のパターンテスト"""
    print("\n=== 3桁のパターンテスト ===")
    
    # 例: 123
    result = parse_fuzzy_date("123")
    print(f"123 → {len(result)}件")
    
    # 各種1桁年・2桁月 (S1年23月は無効、H1年23月は無効)
    # 各種1桁年・1桁月・1桁日 (S1年2月3日)
    has_s1_feb_3 = any(y == 1926 and m == 2 and d == 3 for y, m, d in result)
    print(f"  S1年2月3日（1926年2月3日）: {has_s1_feb_3}")
    
    # 各種2桁年・1桁月 (S12年3月)
    has_s12_mar = any(y == 1937 and m == 3 and d is None for y, m, d in result)
    print(f"  S12年3月（1937年3月）: {has_s12_mar}")
    
    # 2桁月・1桁日 (12月3日)
    has_dec_3 = any(y is None and m == 12 and d == 3 for y, m, d in result)
    print(f"  12月3日: {has_dec_3}")
    
    # 1桁月・2桁日 (1月23日)
    has_jan_23 = any(y is None and m == 1 and d == 23 for y, m, d in result)
    print(f"  1月23日: {has_jan_23}")
    
    # 2桁目が0の場合: 1桁月・1桁日 (10月3日 → 実際は「103」なので該当しない)
    # 例: 105 → 10月5日 または 1月05日
    result_105 = parse_fuzzy_date("105")
    has_oct_5 = any(y is None and m == 10 and d == 5 for y, m, d in result_105)
    has_jan_05 = any(y is None and m == 1 and d == 5 for y, m, d in result_105)
    print(f"  105 → 10月5日: {has_oct_5}, 1月5日: {has_jan_05}")


def test_4digit_patterns():
    """4桁のパターンテスト"""
    print("\n=== 4桁のパターンテスト ===")
    
    # 例: 1234
    result = parse_fuzzy_date("1234")
    print(f"1234 → {len(result)}件")
    
    # 西暦4桁 (1234年)
    has_1234 = any(y == 1234 and m is None for y, m, d in result)
    print(f"  1234年: {has_1234}")
    
    # 各種2桁年・2桁月 (S12年34月は無効)
    # 各種2桁年・1桁月・1桁日 (S12年3月4日)
    has_s12_mar_4 = any(y == 1937 and m == 3 and d == 4 for y, m, d in result)
    print(f"  S12年3月4日（1937年3月4日）: {has_s12_mar_4}")
    
    # 各種1桁年・2桁月・1桁日 (S1年23月4日は無効)
    # 各種1桁年・1桁月・2桁日 (S1年2月34日は無効)
    
    # 2桁月・2桁日 (12月34日は無効)
    # 1桁月・1桁日 (1月2日) - 残り34は無効
    
    # 下から: 2桁日 (34日は無効)
    # 下から: 2桁月・2桁日 (12月34日は無効)


def test_5digit_patterns():
    """5桁のパターンテスト"""
    print("\n=== 5桁のパターンテスト ===")
    
    # 例: 12345
    result = parse_fuzzy_date("12345")
    print(f"12345 → {len(result)}件")
    
    # 西暦4桁・1桁月 (1234年5月)
    has_1234_may = any(y == 1234 and m == 5 and d is None for y, m, d in result)
    print(f"  1234年5月: {has_1234_may}")


def test_missing_patterns():
    """不足しているパターンの確認"""
    print("\n=== 不足パターンの確認 ===")
    
    # 3桁: 105 → 1月5日（先頭0を考慮）
    result = parse_fuzzy_date("105")
    print(f"105 → {result}")
    has_jan_5 = any(y is None and m == 1 and d == 5 for y, m, d in result)
    print(f"  1月5日を含む: {has_jan_5}")
    
    # 4桁: 1205 → 12月5日（先頭0を考慮）
    result = parse_fuzzy_date("1205")
    print(f"1205 → {result}")
    has_dec_5 = any(y is None and m == 12 and d == 5 for y, m, d in result)
    print(f"  12月5日を含む: {has_dec_5}")
    
    # 4桁: 0105 → 1月5日（先頭0を考慮）
    result = parse_fuzzy_date("0105")
    print(f"0105 → {result}")
    has_jan_5_2 = any(y is None and m == 1 and d == 5 for y, m, d in result)
    print(f"  1月5日を含む: {has_jan_5_2}")


if __name__ == "__main__":
    try:
        test_3digit_patterns()
        test_4digit_patterns()
        test_5digit_patterns()
        test_missing_patterns()
        
        print("\n" + "="*50)
        print("テスト完了")
        print("="*50)
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
