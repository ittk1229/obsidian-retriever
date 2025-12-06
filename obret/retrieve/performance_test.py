import time

import numpy as np

# パラメータ設定
num_documents = 7000
dimensions = 512

# 1. ランダムな文書埋め込み行列を生成 (7000 x 512)
documents = np.random.rand(num_documents, dimensions).astype(np.float32)

# 2. ランダムなクエリ埋め込みベクトルを生成 (1 x 512)
query = np.random.rand(1, dimensions).astype(np.float32)

# 計測開始
start_time = time.time()

# 3. クエリと全文書の内積を計算
#    (1, 512) @ (512, 7000) -> (1, 7000)
#    結果は1次元配列になるように .flatten() を使用
dot_products = np.dot(query, documents.T).flatten()

# 4. 内積の高い順にソート (実際にはインデックスをソート)
#    argsortは昇順でソートするため、マイナスを付けて降順にする
sorted_indices = np.argsort(-dot_products)

# 計測終了
end_time = time.time()

# 処理時間を計算
execution_time = end_time - start_time

# 結果の表示 (ソート後の上位5件のインデックスと内積値)
print(f"処理時間: {execution_time:.6f} 秒")
print("\nソート後の上位5件:")
for i in range(5):
    index = sorted_indices[i]
    print(f"  文書インデックス: {index}, 内積: {dot_products[index]:.4f}")

# 参考: ソートされた内積値そのもの
# sorted_dot_products = dot_products[sorted_indices]
# print("\nソートされた内積値 (上位5件):")
# print(sorted_dot_products[:5])
