# -*- coding: utf-8 -*-
"""
バージョン56の強化テスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import parse_fuzzy_date, parse_excel_date


def test_15_search_patterns():
    """「15」で各種1年5月の解釈をテスト"""
    print("\n=== 「15」検索パターンのテスト ===")
    
    result = parse_fuzzy_date("15")
    print(f"15 → {len(result)}件の候補")
    
    # 1月5日を含むか
    has_jan_5 = any(m == 1 and d == 5 for y, m, d in result if m is not None and d is not None)
    print(f"  1月5日を含む: {has_jan_5}")
    assert has_jan_5, "1月5日が含まれていません"
    
    # H15年（2003年）を含むか
    has_h15 = any(y == 2003 and m is None for y, m, d in result)
    print(f"  H15年（2003年）を含む: {has_h15}")
    assert has_h15, "H15年が含まれていません"
    
    # S15年（1940年）を含むか
    has_s15 = any(y == 1940 and m is None for y, m, d in result)
    print(f"  S15年（1940年）を含む: {has_s15}")
    assert has_s15, "S15年が含まれていません"
    
    # 2015年を含むか
    has_2015 = any(y == 2015 and m is None for y, m, d in result)
    print(f"  2015年を含む: {has_2015}")
    assert has_2015, "2015年が含まれていません"
    
    # S1年5月（1926年5月）を含むか
    has_s1_may = any(y == 1926 and m == 5 for y, m, d in result)
    print(f"  S1年5月（1926年5月）を含む: {has_s1_may}")
    assert has_s1_may, "S1年5月が含まれていません"
    
    # H1年5月（1989年5月）を含むか
    has_h1_may = any(y == 1989 and m == 5 for y, m, d in result)
    print(f"  H1年5月（1989年5月）を含む: {has_h1_may}")
    assert has_h1_may, "H1年5月が含まれていません"
    
    # R1年5月（2019年5月）を含むか
    has_r1_may = any(y == 2019 and m == 5 for y, m, d in result)
    print(f"  R1年5月（2019年5月）を含む: {has_r1_may}")
    assert has_r1_may, "R1年5月が含まれていません"
    
    # 2001年5月を含むか
    has_2001_may = any(y == 2001 and m == 5 for y, m, d in result)
    print(f"  2001年5月を含む: {has_2001_may}")
    assert has_2001_may, "2001年5月が含まれていません"
    
    print("OK 全ての解釈が含まれています")


def test_excel_wareki_kanji():
    """Excel読み込み時の和暦漢字表記テスト"""
    print("\n=== Excel読み込み時の和暦漢字表記テスト ===")
    
    # 昭和60年5月1日
    result = parse_excel_date("昭和60年5月1日")
    print(f"昭和60年5月1日 → {result}")
    assert result is not None and result.year == 1985 and result.month == 5 and result.day == 1
    
    # 昭60.5.1
    result = parse_excel_date("昭60.5.1")
    print(f"昭60.5.1 → {result}")
    assert result is not None and result.year == 1985 and result.month == 5 and result.day == 1
    
    # S.60.5.1
    result = parse_excel_date("S.60.5.1")
    print(f"S.60.5.1 → {result}")
    assert result is not None and result.year == 1985 and result.month == 5 and result.day == 1
    
    # s.60.5.1（小文字）
    result = parse_excel_date("s.60.5.1")
    print(f"s.60.5.1 → {result}")
    assert result is not None and result.year == 1985 and result.month == 5 and result.day == 1
    
    # 平成元年1月8日
    result = parse_excel_date("平成元年1月8日")
    print(f"平成元年1月8日 → {result}")
    # 元年は1として扱われる
    
    # H.1.1.8
    result = parse_excel_date("H.1.1.8")
    print(f"H.1.1.8 → {result}")
    assert result is not None and result.year == 1989 and result.month == 1 and result.day == 8
    
    print("OK Excel読み込み時の和暦対応が正常に動作しています")


def test_excel_2digit_year():
    """Excel読み込み時の2桁西暦テスト"""
    print("\n=== Excel読み込み時の2桁西暦テスト ===")
    
    # 90.5.1 → 1990年5月1日
    result = parse_excel_date("90.5.1")
    print(f"90.5.1 → {result}")
    assert result is not None and result.year == 1990 and result.month == 5 and result.day == 1
    
    # 25.5.1 → 2025年5月1日
    result = parse_excel_date("25.5.1")
    print(f"25.5.1 → {result}")
    assert result is not None and result.year == 2025 and result.month == 5 and result.day == 1
    
    # 30.5.1 → 1930年5月1日（30以上は1900年代）
    result = parse_excel_date("30.5.1")
    print(f"30.5.1 → {result}")
    assert result is not None and result.year == 1930 and result.month == 5 and result.day == 1
    
    print("OK 2桁西暦の解釈が正常に動作しています")


if __name__ == "__main__":
    try:
        test_15_search_patterns()
        test_excel_wareki_kanji()
        test_excel_2digit_year()
        
        print("\n" + "="*50)
        print("SUCCESS 全てのテストが成功しました")
        print("="*50)
    except AssertionError as e:
        print(f"\nFAILED テスト失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
