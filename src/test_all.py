# -*- coding: utf-8 -*-
"""
全モジュールのテストスイート
"""
import pytest
import datetime
from utils.text_utils import hira_to_kata, normalize_text_unified, get_natural_sort_key, clean_referrer
from utils.date_utils import (
    parse_fuzzy_date, parse_excel_date, format_date_text, 
    generate_birth_search_keys, parse_date_with_separators
)
from utils.browser_utils import open_url_securely
import pandas as pd


class TestTextUtils:
    """テキストユーティリティのテスト"""
    
    def test_hira_to_kata_basic(self):
        """ひらがな→カタカナ変換の基本テスト"""
        assert hira_to_kata("あいうえお") == "アイウエオ"
        assert hira_to_kata("かきくけこ") == "カキクケコ"
    
    def test_hira_to_kata_mixed(self):
        """混在文字列のテスト"""
        assert hira_to_kata("あいうABC") == "アイウABC"
        assert hira_to_kata("123あいう") == "123アイウ"
    
    def test_hira_to_kata_empty(self):
        """空文字列のテスト"""
        assert hira_to_kata("") == ""
        assert hira_to_kata(None) == ""
    
    def test_normalize_text_unified(self):
        """テキスト正規化のテスト"""
        assert normalize_text_unified("ＡＢＣ") == "ABC"
        assert normalize_text_unified("abc") == "ABC"
        assert normalize_text_unified("あ-い.う") == "あいう"
    
    def test_normalize_text_unified_none(self):
        """None値のテスト"""
        assert normalize_text_unified(None) == ""
        assert normalize_text_unified("") == ""
    
    def test_get_natural_sort_key(self):
        """自然順ソートキーのテスト"""
        result = get_natural_sort_key("abc123def456")
        assert isinstance(result, list)
        assert 123 in result
        assert 456 in result
    
    def test_clean_referrer(self):
        """紹介者クリーニングのテスト"""
        assert clean_referrer("山田太郎(友人)") == "山田太郎"
        assert clean_referrer("山田太郎（友人）") == "山田太郎"
        assert clean_referrer("山田太郎") == "山田太郎"
        assert clean_referrer(None) is None


class TestDateUtils:
    """日付ユーティリティのテスト"""
    
    def test_parse_fuzzy_date_era(self):
        """和暦パターンのテスト"""
        result = parse_fuzzy_date("H1-2-3")
        assert (1989, 2, 3) in result
    
    def test_parse_fuzzy_date_numbers(self):
        """数字のみのパターンのテスト"""
        result = parse_fuzzy_date("123")
        assert len(result) > 0
    
    def test_parse_fuzzy_date_empty(self):
        """空文字列のテスト"""
        assert parse_fuzzy_date("") == []
        assert parse_fuzzy_date(None) == []
    
    def test_parse_date_with_separators(self):
        """区切り文字ありの日付解析テスト"""
        result = parse_date_with_separators("1989/2/3")
        assert result == (1989, 2, 3)
        
        result = parse_date_with_separators("H1/2/3")
        assert result == (1989, 2, 3)
    
    def test_generate_birth_search_keys(self):
        """生年月日検索キー生成のテスト"""
        result = generate_birth_search_keys(1989, 2, 3)
        assert result == {'year': 1989, 'month': 2, 'day': 3}
        
        result = generate_birth_search_keys(None, 2, 3)
        assert result is None
    
    def test_parse_excel_date_datetime(self):
        """datetime型のテスト"""
        dt = datetime.datetime(1989, 2, 3)
        result = parse_excel_date(dt)
        assert result.year == 1989
        assert result.month == 2
        assert result.day == 3
    
    def test_parse_excel_date_string(self):
        """文字列のテスト"""
        result = parse_excel_date("1989/2/3")
        assert result.year == 1989
        assert result.month == 2
        assert result.day == 3
    
    def test_parse_excel_date_none(self):
        """None値のテスト"""
        assert parse_excel_date(None) is None
        assert parse_excel_date("") is None
    
    def test_format_date_text(self):
        """日付フォーマットのテスト"""
        dt = datetime.datetime(1989, 2, 3)
        result = format_date_text(dt)
        assert "H1" in result
        assert "1989" in result
        assert "02" in result
        assert "03" in result
    
    def test_format_date_text_none(self):
        """None値のテスト"""
        assert format_date_text(None) == ""


class TestBrowserUtils:
    """ブラウザユーティリティのテスト"""
    
    def test_open_url_securely_none(self):
        """None URLのテスト（エラーが出ないことを確認）"""
        try:
            open_url_securely(None)
            assert True
        except Exception:
            pytest.fail("None URLでエラーが発生")
    
    def test_open_url_securely_empty(self):
        """空文字列のテスト"""
        try:
            open_url_securely("")
            assert True
        except Exception:
            pytest.fail("空文字列でエラーが発生")


class TestIntegration:
    """統合テスト"""
    
    def test_birth_date_search_workflow(self):
        """生年月日検索のワークフローテスト"""
        # 1. 日付をパース
        dt = parse_excel_date("1989/2/3")
        assert dt is not None
        
        # 2. 検索キーを生成
        keys = generate_birth_search_keys(dt.year, dt.month, dt.day)
        assert keys['year'] == 1989
        assert keys['month'] == 2
        assert keys['day'] == 3
        
        # 3. 曖昧検索パターンを生成
        patterns = parse_fuzzy_date("123")
        assert len(patterns) > 0
        
        # 4. 区切り文字ありの検索
        result = parse_date_with_separators("1989/2/3")
        assert result == (1989, 2, 3)
    
    def test_text_normalization_workflow(self):
        """テキスト正規化のワークフローテスト"""
        # 1. ひらがな→カタカナ
        kata = hira_to_kata("やまだたろう")
        assert kata == "ヤマダタロウ"
        
        # 2. 正規化
        normalized = normalize_text_unified(kata)
        assert "ヤマダタロウ" in normalized.upper()
        
        # 3. 紹介者クリーニング
        cleaned = clean_referrer("山田太郎(友人)")
        assert cleaned == "山田太郎"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
