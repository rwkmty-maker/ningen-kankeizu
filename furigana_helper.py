# -*- coding: utf-8 -*-
"""
フリガナ自動入力ヘルパー
Claude APIを使用して高精度なフリガナを生成
"""
import anthropic
import pandas as pd

def generate_furigana_batch(names, existing_furigana, api_key, model="claude-opus-4-20250514", batch_size=50, existing_mode="skip", progress_callback=None):
    """
    Claude APIを使ってバッチでフリガナを生成
    
    Args:
        names: 名前のリスト
        existing_furigana: 既存のフリガナのリスト
        api_key: Claude API Key
        model: Claude Model名
        batch_size: 一度に処理する件数
        existing_mode: 既存フリガナの処理方法 ("skip", "overwrite", "append")
        progress_callback: 進捗コールバック関数 (current, total, batch_num)
    
    Returns:
        dict: {名前: フリガナ} の辞書
    """
    if not api_key:
        raise ValueError("Claude API Keyが設定されていません")
    
    if not model:
        raise ValueError("Claude Modelが設定されていません")
    
    client = anthropic.Anthropic(api_key=api_key)
    results = {}
    total_batches = (len(names) + batch_size - 1) // batch_size
    
    # バッチ処理
    for batch_idx, i in enumerate(range(0, len(names), batch_size), 1):
        batch_names = names[i:i+batch_size]
        batch_furigana = existing_furigana[i:i+batch_size]
        
        # プロンプト作成
        input_lines = []
        for name, furi in zip(batch_names, batch_furigana):
            # 既存フリガナの処理
            if pd.notna(furi) and furi != '':
                # ()で囲まれたフリガナがある場合のみスキップ対象
                if '(' in furi and ')' in furi:
                    if existing_mode == "skip":
                        # スキップ: 既存のフリガナをそのまま使用
                        results[name] = furi
                        continue
                    elif existing_mode == "overwrite":
                        # 上書き: ()を削除して新規生成用に空にする
                        furi_str = ''
                    else:  # append
                        # 追加: 既存のフリガナを保持
                        furi_str = furi
                else:
                    # ()がないフリガナは新規生成対象（追加モード用に保持）
                    furi_str = furi
            else:
                # 空のフリガナは新規生成対象
                furi_str = ''
            
            input_lines.append(f"{name},{furi_str}")
        
        prompt = f"""以下の日本人の名前に対して、正確なフリガナを生成してください。

【重要なルール】
1. フリガナは必ず半角カタカナで出力（全角カタカナは絶対に使用しない）
2. 苗字と名前の間にスペースを入れない（例: ﾔﾏﾀﾞﾀﾛｳ）
3. 複数の読み方がある場合は、全ての組み合わせを/で区切る（例: ｼｮｳｼﾞ/ﾄｳｶｲﾘﾝ）
4. 生成したフリガナは必ず()で囲む
5. 既存のフリガナがある場合は、それを残して新しいフリガナを()で追加
6. 出力は「名前,フリガナ」の形式で1行ずつ
7. 余計な説明や前置きは一切不要。データのみ出力すること

【出力例（全て半角カタカナ）】
山田太郎,ﾔﾏﾀﾞﾀﾛｳ
→ 山田太郎,ﾔﾏﾀﾞﾀﾛｳ(ﾔﾏﾀﾞﾀﾛｳ)

東海林,
→ 東海林,(ｼｮｳｼﾞ/ﾄｳｶｲﾘﾝ)

佐藤花子,ｻﾄｳ
→ 佐藤花子,ｻﾄｳ(ｻﾄｳﾊﾅｺ)

【処理対象データ】
{chr(10).join(input_lines)}

【出力（全て半角カタカナでデータのみ）】"""
        
        # 進捗コールバック
        if progress_callback:
            progress_callback(i, len(names), batch_idx, total_batches, "API呼び出し中...")
        
        try:
            message = client.messages.create(
                model=model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 結果をパース
            response_text = message.content[0].text.strip()
            
            # レスポンスを行ごとに処理
            for line in response_text.split('\n'):
                line = line.strip()
                
                # 空行やヘッダー行をスキップ
                if not line or line.startswith('【') or line.startswith('入力:') or line.startswith('出力:'):
                    continue
                
                # カンマで分割
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        furigana = parts[1].strip()
                        
                        # 名前が入力リストに含まれている場合のみ追加
                        if name in batch_names:
                            results[name] = furigana
            
        except Exception:
            # エラーが発生した場合は既存のフリガナをそのまま使用
            for name, furi in zip(batch_names, batch_furigana):
                if name not in results:
                    results[name] = furi if pd.notna(furi) and furi != '' else ''
    
    return results
