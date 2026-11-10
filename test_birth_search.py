# -*- coding: utf-8 -*-
"""
生年月日検索のテストケース
"""
import pytest
from utils.date_utils import parse_fuzzy_date, parse_date_with_separators


class TestBirthSearch:
    """生年月日検索のテスト"""
    
    def test_2012_search(self):
        """2012で検索した場合のテスト"""
        result = parse_fuzzy_date("2012")
        
        # 期待される結果
        expected = [
            (2012, None, None),      # 2012年生まれ
            (2020, 12, None),        # 2020年12月生まれ
            (1945, 12, None),        # S20年12月生まれ
            (2008, 12, None),        # H20年12月生まれ
            (2020, 1, 2),            # 2020年1月2日生まれ
            (1945, 1, 2),            # S20年1月2日生まれ
            (2008, 1, 2),            # H20年1月2日生まれ
            (2002, 1, 2),            # 2002年1月2日生まれ
            (1927, 1, 2),            # S2年1月2日生まれ
            (1990, 1, 2),            # H2年1月2日生まれ
            (2020, 1, 2),            # R2年1月2日生まれ
        ]
        
        # 2月12日は含まれないことを確認
        assert (None, 2, 12) not in result
        
        # 2012年生まれは含まれることを確認
        assert (2012, None, None) in result
        
        # 2020年12月は含まれることを確認
        assert (2020, 12, None) in result
        
        print(f"2012検索結果: {sorted(result)}")
    
    def test_no_february_12(self):
        """2月12日が誤ってヒットしないことを確認"""
        result = parse_fuzzy_date("2012")
        
        # 2月12日（年なし）は含まれないはず
        assert (None, 2, 12) not in result
        
        # 12月2日（年なし）も含まれないはず
        assert (None, 12, 2) not in result
    
    def test_era_only_shr(self):
        """元号がS/H/Rのみであることを確認"""
        # M（明治）はヒットしない
        result_m = parse_fuzzy_date("M1")
        assert len(result_m) == 0 or all(y is None or y >= 1925 for y, m, d in result_m)
        
        # T（大正）はヒットしない
        result_t = parse_fuzzy_date("T1")
        assert len(result_t) == 0 or all(y is None or y >= 1925 for y, m, d in result_t)
        
        # S（昭和）はヒットする
        result_s = parse_fuzzy_date("S1")
        assert any(y == 1926 for y, m, d in result_s)
        
        # H（平成）はヒットする
        result_h = parse_fuzzy_date("H1")
        assert any(y == 1989 for y, m, d in result_h)
        
        # R（令和）はヒットする
        result_r = parse_fuzzy_date("R1")
        assert any(y == 2019 for y, m, d in result_r)
    
    def test_100_years_old_exclusion(self):
        """100歳以上は除外されることを確認"""
        result = parse_fuzzy_date("1920")
        
        # 1920年生まれは100歳以上なので含まれないはず
        assert (1920, None, None) not in result
    
    def test_separator_patterns(self):
        """区切り文字ありのパターンテスト"""
        # 2012/1/2 → 2012年1月2日
        result = parse_date_with_separators("2012/1/2")
        assert result == (2012, 1, 2)
        
        # S20/12/3 → 昭和20年12月3日
        result = parse_date_with_separators("S20/12/3")
        assert result == (1945, 12, 3)
        
        # H2/1/2 → 平成2年1月2日
        result = parse_date_with_separators("H2/1/2")
        assert result == (1990, 1, 2)
        
        # R2/1/2 → 令和2年1月2日
        result = parse_date_with_separators("R2/1/2")
        assert result == (2020, 1, 2)
    
    def test_various_patterns(self):
        """様々な検索パターンのテスト"""
        # 123 → 1月23日、12月3日など
        result = parse_fuzzy_date("123")
        print(f"123検索結果: {sorted(result)}")
        
        # 1123 → 11月23日、1月23日など
        result = parse_fuzzy_date("1123")
        print(f"1123検索結果: {sorted(result)}")
        
        # 19890102 → 1989年1月2日
        result = parse_fuzzy_date("19890102")
        assert (1989, 1, 2) in result
        print(f"19890102検索結果: {sorted(result)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
