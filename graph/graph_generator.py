# -*- coding: utf-8 -*-
import os
import tempfile
import json
import pandas as pd
import networkx as nx
from pyvis.network import Network
from utils.browser_utils import open_url_securely


def save_custom_graph(net, output_path, center_node):
    """カスタムHTMLグラフを保存"""
    try:
        nodes_json = json.dumps(net.nodes, ensure_ascii=False)
        edges_json = json.dumps(net.edges, ensure_ascii=False)
        options_json = json.dumps(net.options, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ValueError(f"グラフデータのJSON変換に失敗: {e}")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
    <meta charset="utf-8">
    <meta name="google" content="notranslate">
    <title>Customer Network</title>
    <link rel="stylesheet" href="https://unpkg.com/vis-network/standalone/umd/vis-network.min.css" type="text/css" />
    <style>
        body {{ margin: 0; padding: 0; background-color: #000000; color: #ffffff; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}
        #mynetwork {{ width: 100vw; height: 100vh; border: none; }}
        .legend {{ position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 10px; border: 1px solid #444; pointer-events: none; z-index: 100; }}
        .legend div {{ margin-bottom: 5px; font-size: 14px; font-weight: bold; }}
        .legend span {{ display: inline-block; width: 12px; height: 12px; margin-right: 5px; }}
        div.vis-tooltip {{
            background-color: rgba(0, 0, 0, 0.9);
            color: #fff;
            border: 1px solid #00ff41;
            padding: 10px;
            font-size: 14px;
            border-radius: 5px;
            white-space: pre-wrap;
        }}
    </style>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    </head>
    <body>
    <div id="mynetwork"></div>
    <div class="legend">
        <div style="color:#ff0055"><span style="background:#ff0055"></span>中心人物 (Center)</div>
        <div style="color:#00ff41"><span style="background:#00ff41"></span>紹介者 (Upstream)</div>
        <div style="color:#00ccff"><span style="background:#00ccff"></span>被紹介者 (Downstream)</div>
        <div style="color:#aaaaaa"><span style="background:#aaaaaa"></span>グループ推測 (Group)</div>
    </div>
    <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});
        var container = document.getElementById('mynetwork');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {options_json};
        var network = new vis.Network(container, data, options);
        
        network.on("doubleClick", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                navigator.clipboard.writeText(nodeId).then(function() {{
                    alert("【" + nodeId + "】をコピーしました。");
                }}, function(err) {{
                    alert("Selected: " + nodeId);
                }});
            }}
        }});
    </script>
    </body>
    </html>
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except (IOError, OSError) as e:
        raise IOError(f"HTMLファイルの保存に失敗: {e}")


def generate_customer_graph(df, center_person, max_depth=8):
    """
    顧客関係図を生成してブラウザで開く
    
    Args:
        df: 顧客データフレーム
        center_person: 中心人物の登録名
        max_depth: 表示範囲（何人先まで表示するか、デフォルト8）
    
    Returns:
        成功時はTrue、失敗時は例外を投げる
    """
    if df is None or df.empty:
        raise ValueError("データフレームが空です")
    
    if not center_person or not str(center_person).strip():
        raise ValueError("中心人物が指定されていません")
    
    if '登録名' not in df.columns:
        raise ValueError("「登録名」列が見つかりません")
    
    try:
        G = nx.DiGraph()
        valid_names = set(str(n).strip() for n in df['登録名'].unique() if pd.notna(n) and str(n).strip())
    except Exception as e:
        raise ValueError(f"データの初期化に失敗: {e}")
    
    try:
        for idx, row in df.iterrows():
            target = None 
            u = str(row['登録名']).strip()
            if not u:
                continue
            ref_raw = row.get('__clean_referrer__', '')
            if pd.isna(ref_raw):
                ref_raw = ''
            ref = str(ref_raw).strip()
            grp_raw = row.get('グループ', '')
            if pd.isna(grp_raw):
                grp_raw = ''
            grp = str(grp_raw).strip()
            
            info_list = []
            for k, v in row.items():
                if not k.startswith('__') and k not in ['search_index', 'clean_referrer']:
                    info_list.append(f"{k}: {v}")
            info = "\n".join(info_list)
            
            G.add_node(u, title=info, group=grp)
            
            if ref:
                if ref in valid_names and ref != u:
                    target = ref
                else:
                    if grp in valid_names and grp != u:
                        target = grp
                    else:
                        target = ref
                        if target not in G:
                            G.add_node(target, title="※該当登録名なし", group="UnknownNode", shape='box', color='#999999')
            elif grp:
                if grp in valid_names and grp != u:
                    target = grp
                else:
                    target = grp
                    if target not in G:
                        G.add_node(target, title="グループ名", group="GroupNode", shape='box', color='#aaaaaa')
            if target:
                G.add_edge(target, u)
    except Exception as e:
        raise ValueError(f"グラフの構築に失敗: {e}")

    if center_person not in G:
        raise ValueError("データなし")

    try:
        sub_nodes = nx.ego_graph(G.to_undirected(), center_person, radius=max_depth).nodes()
        sub_G = G.subgraph(sub_nodes)
        net = Network(height='100%', width='100%', bgcolor='#000000', font_color='white', directed=True)
        net.from_nx(sub_G)
    except Exception as e:
        raise ValueError(f"サブグラフの生成に失敗: {e}")
    
    try:
        for node in net.nodes:
            nid = node['id']
            node['shape'] = 'box'
            node['font'] = {'size': 20, 'color': '#ffffff', 'face': 'Meiryo UI'}
            node['borderWidth'] = 2
            node['shadow'] = True
            
            group = node.get('group')
            if group == 'GroupNode':
                node['color'] = {'background': 'rgba(100,100,100,0.8)', 'border': '#aaaaaa'}
                continue
            if group == 'UnknownNode':
                node['color'] = {'background': 'rgba(150,50,50,0.8)', 'border': '#ff0000'}
                continue

            if nid == center_person:
                node['color'] = {'background': 'rgba(255,0,80,0.7)', 'border': '#ff0055'}
                node['font']['size'] = 30
            elif nid in list(G.predecessors(center_person)):
                node['color'] = {'background': 'rgba(0,255,65,0.6)', 'border': '#00ff41'}
            elif any(center_person in list(G.successors(p)) for p in G.predecessors(nid)):
                node['color'] = {'background': 'rgba(255,165,0,0.6)', 'border': '#ffa500'}
            else:
                node['color'] = {'background': 'rgba(0,204,255,0.6)', 'border': '#00ccff'}

        for edge in net.edges:
            edge['color'] = {'color': '#666666', 'opacity': 0.6}
            edge['width'] = 1
            edge['smooth'] = False
    except Exception as e:
        raise ValueError(f"ノード・エッジのスタイル設定に失敗: {e}") 

    try:
        net.set_options("""
        var options = {
          "physics": {
            "forceAtlas2Based": { "gravitationalConstant": -60, "springLength": 100, "springConstant": 0.04, "damping": 0.4 },
            "maxVelocity": 40, "solver": "forceAtlas2Based", "timestep": 0.35
          },
          "interaction": { "hover": true, "navigationButtons": true, "zoomView": true }
        }
        """)
    except Exception as e:
        raise ValueError(f"オプションの設定に失敗: {e}")

    try:
        tmp = os.path.join(tempfile.gettempdir(), "customer_network_hyper.html")
        save_custom_graph(net, tmp, center_person)
        open_url_securely('file://' + tmp)
    except Exception as e:
        raise IOError(f"ファイルの保存またはブラウザ起動に失敗: {e}")
    
    return True
