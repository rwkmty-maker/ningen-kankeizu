# -*- coding: utf-8 -*-
"""
00パターンの確認テスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import parse_fuzzy_date


def test_0105_patterns():
    """0105のパターン確認"""
    print("\n=== 0105のパターン確認 ===")
    
    result = parse_fuzzy_date("0105")
    print(f"0105 → {len(result)}件")
    
    # 2000年10月5日
    has_2000_oct_5 = any(y == 2000 and m == 10 and d == 5 for y, m, d in result)
    print(f"  2000年10月5日: {has_2000_oct_5}")
    
    # 2000年1月5日
    has_2000_jan_5 = any(y == 2000 and m == 1 and d == 5 for y, m, d in result)
    print(f"  2000年1月5日: {has_2000_jan_5}")
    
    # 全候補を表示
    print("\n  全候補:")
    for r in result:
        y, m, d = r
        if y is not None:
            print(f"    {y}年{m if m else ''}月{d if d else ''}日" if m or d else f"    {y}年")
        elif m is not None and d is not None:
            print(f"    {m}月{d}日")
    
    if not has_2000_jan_5:
        print("\n  WARNING: 2000年1月5日が含まれていません")
        return False
    
    return True


def test_00_prefix_patterns():
    """00で始まる場合のパターン確認"""
    print("\n=== 00で始まる場合のパターン確認 ===")
    
    # 例: 00512 → 0年5月12日（2000年5月12日）、00年5月12日（2000年5月12日）
    result = parse_fuzzy_date("00512")
    print(f"00512 → {len(result)}件")
    
    # 0年5月12日 → 2000年5月12日
    has_0_may_12 = any(y == 2000 and m == 5 and d == 12 for y, m, d in result)
    print(f"  0年5月12日（2000年5月12日）: {has_0_may_12}")
    
    # 00年5月12日 → 2000年5月12日
    has_00_may_12 = any(y == 2000 and m == 5 and d == 12 for y, m, d in result)
    print(f"  00年5月12日（2000年5月12日）: {has_00_may_12}")
    
    # 全候補を表示
    print("\n  全候補:")
    for r in result:
        y, m, d = r
        if y is not None:
            print(f"    {y}年{m if m else ''}月{d if d else ''}日" if m or d else f"    {y}年")
        elif m is not None and d is not None:
            print(f"    {m}月{d}日")
    
    if not has_00_may_12:
        print("\n  WARNING: 00年5月12日（2000年5月12日）が含まれていません")
        return False
    
    return True


if __name__ == "__main__":
    try:
        result1 = test_0105_patterns()
        result2 = test_00_prefix_patterns()
        
        print("\n" + "="*50)
        if result1 and result2:
            print("SUCCESS 全てのパターンが網羅されています")
        else:
            print("WARNING 一部のパターンが不足しています")
        print("="*50)
    except Exception as e:
        print(f"\nERROR エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
