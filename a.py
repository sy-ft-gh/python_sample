import json
import MeCab
from collections import Counter

from tqdm import tqdm

# 形態素解析器としてMeCabを準備
mecab = MeCab.Tagger("-Ochasen")
try:
  mecab.parse("")
except:
  pass
# MeCabによる形態素分割処理
def get_token(text):
  result = []
  morph_pos = 0
  # 形態素分割で半角スペースが消えるので、位置を覚えておいてあとで、半角スペース位置を加算する
  half_with_space_indexes = [i for i, w in enumerate(text) if w == ' ']
  node = mecab.parseToNode(text)
  while node:
    feat = node.feature.split(",")
    if feat[0] != "BOS/EOS": # 開始・終了のラベルは除外
      surface, hinshi1,hinshi2,hinshi3 = node.surface, feat[0], feat[1], feat[2]
      # 表層(オリジナルの文字列)と品詞情報
      # 文字の開始位置・終了位置を併せて格納
      span = [morph_pos, morph_pos + len(surface)]
      result.append({"surface": surface, "hinshi1": hinshi1, "hinshi2": hinshi2, "hinshi3": hinshi3, "span": span})
      morph_pos += len(surface) + (1 if morph_pos + len(surface) in half_with_space_indexes else 0)
    node = node.next
  return result

# 抽出対象のjsonデータをロードし、形態素分割します。
print("データセット読み込み start")
sentences = []
with open("ner.json","r", encoding="utf8") as f:
  jsons = json.load(f)
  for j in jsons:
    # 法人名を正解、法人名以外を不正解とラベル分けします
    j["correct"] = [ {"name": e["name"], "span": e["span"]} for e in j["entities"] if e["type"] == "法人名"]
    j["incorrect"] = [ {"name": e["name"], "span": e["span"]} for e in j["entities"] if e["type"] != "法人名"]
    # 文の形態素解析結果を付加します
    j["tokens"] =  get_token(j["text"])
    sentences.append(j)
# １件目のデータをサンプルとして表示
print("データ件数:" + str(len(sentences)))
print("サンプル1件:" +  str(list(filter(lambda x: len(x["entities"]) >0 , sentences))[0]))

#JCLdic(CSV版)を読み込み
print("JCLdic読み込み start")
company_list = []
with open("jcl_slim.csv","r", encoding="utf8") as f:
  for line in tqdm(f.readlines()):
    company_list.append(line.strip())
company_list = list(set(company_list))
print("データ件数:" + str(len(company_list)))
print("サンプル1件:" +  company_list[0])

# 1文毎に抽出を実施
print("法人名抽出 start")
for sentence in tqdm(sentences):
  # 抽出情報を初期化
  extract_item = None
  sentence["predict"] = []
  for idx, token in enumerate(sentence["tokens"]):
      # 組織の固有名詞は単独で対象として扱う
      if  extract_item is None and token["hinshi1"] in ["名詞"] and  ¥
        token["hinshi2"] == "固有名詞" and token["hinshi3"] == "組織":
         extract_item = [idx, idx,  token["surface"], "1", token["span"]]
      # 接頭詞または名詞から始まる文字列のスパン情報を格納
      if  extract_item is None and token["hinshi1"] in ["接頭詞", "名詞"]:
         extract_item = [idx, idx,  token["surface"], "2", token["span"]]
      elif extract_item is not None and extract_item[3] == "2" and token["hinshi1"]  =="名詞":
      # 名詞が連続する場合は結合する
        new_span = extract_item[4] + token["span"]
        new_span = [min(new_span), max(new_span)]
        word = extract_item[2] + token["surface"]
        extract_item[1], extract_item[2], extract_item[4]  = idx,  word, new_span
      else:
        if extract_item is not None:
          # 固有名詞は単一形態素で辞書に引き当てる
          if extract_item[3] == "1":
            if extract_item[2] in company_list:
              sentence["predict"].append({"name":extract_item[2], "span":  extract_item[4]})
          else:
            # 2連続以上の名詞が途切れたら前後の品詞確認を実施
            if extract_item[1] - extract_item[0] >= 2:
              before_token, after_token = None, None
              if extract_item[0] > 0:
                before_token = sentence["tokens"][extract_item[0] - 1]
                # 読点、助詞：「は」、「の」の後を有効とする
                if  not ((before_token["hinshi1"] == "記号" and before_token["hinshi2"] == "読点") or  ¥
                  (before_token["hinshi1"] == "助詞" and before_token["surface"] in ["は", "の"])):
                  before_token = None

              if extract_item[1]  < len(sentence["tokens"]) -1:
                after_token = sentence["tokens"][extract_item[1] + 1]
                # 助詞「は」、「の」、「が」の前を有効とします
                if not (after_token["hinshi1"] == "助詞" and after_token["surface"] in ["の", "は", "が"]):
                  after_token = None
              if before_token is not None or after_token is not None:
                # 前後の品詞が条件に合致し、JCLdicに含まれる文字列を法人名として抽出
                if extract_item[2] in company_list:
                  sentence["predict"].append({"name":extract_item[2], "span":  extract_item[4]})
          extract_item = None

# 抽出結果の精度確認
print("精度算出 start")
TP, FP, TN, FN = 0, 0, 0, 0
for sentence in sentences:
  # 企業名を正しく抽出した結果をえり分け
  pred_correct = [p for p in sentence["predict"] if p in sentence["correct"]]
  # 企業名以外を企業名でないとできた正解をえり分け
  positive_incorrect = [e for e in sentence["incorrect"] if e not in sentence["predict"]]
  # 正解として抽出できなかった企業名をえり分け
  negative_correct = [e for e in sentence["correct"] if e not in sentence["predict"]]
  # 企業名でない文字列を企業名と予測した抽出結果をえり分け
  pred_incorrect = [p for p in sentence["predict"] if p not in sentence["correct"]]

  # True Positive = 企業名を正しく企業名と抽出できた抽出件数
  TP += len(pred_correct)
  # True Negative =  企業名でない固有表現を企業名でないと除外できた件数
  TN += len(positive_incorrect)
  # False Negative = 企業名である固有表現を企業名でないと除外した件数
  FN += len(negative_correct)
  # False Positive = 企業名でない文字列をを企業名であると抽出してしまった件数
  FP += len(pred_incorrect)

  sentence["pred_correct"] = pred_correct
  sentence["positive_incorrect"] = positive_incorrect
  sentence["negative_correct"] = negative_correct
  sentence["pred_incorrect"] = pred_incorrect

  del sentence["tokens"]
  del sentence["entities"]
  
# 精度をコンソールに出力
print("TP:{},FP:{},TN:{},FN:{}".format(TP, FP, TN, FN))
print("Accuracy:{}".format((TP + TN) / (TP + TN + FP+ FN)))
print("Precision:{}".format(TP / (TP + FP)))
print("Recall:{}".format(TP / (TP + FN)))

# 結果をファイルに保存
with open('./result.json', 'w', encoding="utf8") as f:
  json.dump(sentences, f, indent=4, ensure_ascii=False)
