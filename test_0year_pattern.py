# -*- coding: utf-8 -*-
"""
0年パターンのテスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import parse_fuzzy_date


def test_0year_pattern():
    """0年のパターンテスト（0105 → 2000年10月5日）"""
    print("\n=== 0年のパターンテスト ===")
    
    # 0105 → 2000年10月5日
    result = parse_fuzzy_date("0105")
    print(f"0105 → {len(result)}件")
    for r in result:
        if r[0] == 2000 and r[1] == 10 and r[2] == 5:
            print(f"  2000年10月5日: {r}")
    
    has_2000_oct_5 = any(y == 2000 and m == 10 and d == 5 for y, m, d in result)
    print(f"  2000年10月5日を含む: {has_2000_oct_5}")
    assert has_2000_oct_5, "2000年10月5日が含まれていません"
    
    # 他のパターンも確認
    has_jan_5 = any(y is None and m == 1 and d == 5 for y, m, d in result)
    has_oct_5 = any(y is None and m == 10 and d == 5 for y, m, d in result)
    print(f"  1月5日を含む: {has_jan_5}")
    print(f"  10月5日を含む: {has_oct_5}")
    
    print("OK 0年のパターンが正しく解釈されています")


if __name__ == "__main__":
    try:
        test_0year_pattern()
        
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
