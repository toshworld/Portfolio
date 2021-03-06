import MySQLdb
from janome.tokenizer import Tokenizer
import codecs
import re
import sys

try:
    # データベースへの接続とカーソルの生成
    connection = MySQLdb.connect(
        host='localhost',
        user='root',
        passwd='',
        db='review',
        charset='utf8')
    cursor = connection.cursor()

    cursor.execute("SELECT good_review FROM reviews WHERE id = (select max(id) from reviews)")
    # fetchall()で全件取り出し
    g_rows = cursor.fetchall()
    
    class CorpusElement:
        def __init__(self, text='', tokens=[], pn_scores=[]):
            self.text = text # テキスト本文
            self.tokens = tokens # 構文木解析されたトークンのリスト
            self.pn_scores = pn_scores # 感情極性値(後述)
    #g_pointは良い点のレビューを格納する配列,b_pointは悪い点のレビューを格納する配列
    g_corpus = []
    b_corpus = []

    tokenizer = Tokenizer()
    #タプルを配列に格納し、空白を削除する
    def read_review(rows):
        txt = []
        for row in rows:
            txt += list(row)
        document = ''.join(txt)
        
        texts = document.split("\n\r")

        flag = False
        for text in texts:
            if text == '':
                flag = True

        if flag == True:
            texts.remove('')
        return texts
    #読み込ん文章を整えて配列に格納する
    def text_read(texts):
        corpus = []
        for text in texts:
            sentence = text
            sentence = re.sub(r'【+?】', '',sentence)
            sentence = re.sub(r'・', '',sentence)
            tokens = tokenizer.tokenize(sentence)
            element = CorpusElement(text, tokens)
            corpus.append(element)
        return corpus

    g_texts = []
    texts = read_review(g_rows)
    for text in texts:
        sentence = text
        sentence = re.sub(r'軽い', '使える',sentence)
        sentence = re.sub(r'安い', '良い',sentence)
        g_texts.append(sentence)
    #print(g_texts) デバック用
    g_corpus = text_read(g_texts)   

    def load_pn_dict():
        dic = {}
        
        with codecs.open('lib/assets/python/pn_ja.dic', 'r', 'shift_jis') as f:
            lines = f.readlines()
            
            for line in lines:
                columns = line.split(':')
                dic[columns[0]] = float(columns[3])      
        return dic

    # 極性値リストを得る
    def get_pn_scores(tokens, pn_dic):
        scores = []
        
        for surface in [t.surface for t in tokens if t.part_of_speech.split(',')[0] in ['動詞','名詞', '形容詞', '副詞']]:
            if surface in pn_dic:
                scores.append(pn_dic[surface])
            
        return scores
    #極性値計算
    def calc_review_point(corpus):
        # 感情極性対応表のロード
        pn_dic = load_pn_dict()

        # 各文章の極性値リストを得る
        for element in corpus:
            element.pn_scores = get_pn_scores(element.tokens, pn_dic)

        sum_point = 0
        for element in sorted(corpus, key=lambda e: sum(e.pn_scores)/len(e.pn_scores), reverse=True):
            sum_point += sum(element.pn_scores)/len(element.pn_scores)
            #print(sum_point)
        return sum_point

    g_point = calc_review_point(g_corpus)

    cursor.execute("SELECT bad_review FROM reviews WHERE id = (select max(id) from reviews)")
    # fetchall()で全件取り出し
    b_rows = cursor.fetchall()

    b_texts = []
    texts = read_review(b_rows)
    for text in texts:
        sentence = text
        sentence = re.sub(r'高い', '',sentence)
        b_texts.append(sentence)
    b_corpus = text_read(b_texts)
    #print(b_texts) デバック用
    b_point = calc_review_point(b_corpus)
    
    if b_point < -1:
        b_point = -1

    ans = 3 + ((3 * (1 + g_point)) - abs(3 * (1 - (1 - b_point))))
    if ans < 0:
        ans = 0
    if b_point > 0:
        ans = 0
    if b_point - g_point > 0.1:
        ans = 0
    if ans > 5:
        ans = 4.8
    #rails側に値を渡す。
    print(ans)

    # 保存を実行
    connection.commit()

    # 接続を閉じる
    connection.close()

except MySQLdb.Error as ex:
    print('0')



