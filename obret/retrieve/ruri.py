import torch
from sentence_transformers import SentenceTransformer
import time


def main():
    # 1. モデルとデバイスの設定
    device_name = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用デバイス: {device_name}")
    print("モデルをロード中です... (cl-nagoya/ruri-v3-130m)")

    try:
        model = SentenceTransformer("cl-nagoya/ruri-v3-130m", device=device_name)
    except Exception as e:
        print(f"モデルのロード中にエラーが発生しました: {e}")
        return

    print("-" * 50)
    print("モデルのロードが完了しました。")
    print("この状態で 'htop' などのツールでプロセスのメモリ使用量を確認してください。")
    print(
        "クエリを入力してください (終了するには '終了', 'exit', 'quit' のいずれかを入力)。"
    )
    print("-" * 50)

    # (オプション) ウォームアップ - GPU使用時や初回実行時のレイテンシを安定させるため
    if device_name == "cuda":
        print("GPUウォームアップ中...")
        # ↓↓↓ 修正点: 単一文字列でもリストとして渡す ↓↓↓
        model.encode(["検索クエリ: ウォームアップ"], convert_to_tensor=True)
        torch.cuda.synchronize()
        print("ウォームアップ完了。")
        print("-" * 50)

    try:
        while True:
            user_input = input("検索クエリを入力: ")

            if user_input.lower() in ["終了", "exit", "quit"]:
                print("プログラムを終了します。")
                break

            if not user_input.strip():
                print("クエリが空です。再度入力してください。")
                continue

            # Ruri v3の推奨に従いプレフィックスを付与
            query_with_prefix = f"検索クエリ: {user_input}"

            # エンコード処理時間の計測開始
            if device_name == "cuda":
                torch.cuda.synchronize()
            start_time = time.perf_counter()

            # ↓↓↓ 修正点: 単一文字列でもリストとして渡す ↓↓↓
            # クエリをエンコード (リストとして渡すことで出力が (1, dim) の2Dテンソルになる)
            embedding = model.encode([query_with_prefix], convert_to_tensor=True)

            if device_name == "cuda":
                torch.cuda.synchronize()
            end_time = time.perf_counter()

            processing_time = end_time - start_time

            # embedding は (1, dim) の形状なので embedding[0] で1次元ベクトルを取得
            print(
                f"  エンコードされたベクトル (最初の5次元): {embedding[0, :5].cpu().tolist()}"
            )
            print(f"  ベクトル次元数: {embedding.shape}")  # 例: torch.Size([1, 512])
            print(f"  処理時間: {processing_time:.6f} 秒")
            print("-" * 30)

    except KeyboardInterrupt:
        print("\nプログラムが中断されました。終了します。")
    except Exception as e:
        print(f"処理中にエラーが発生しました: {e}")
    finally:
        print("クリーンアップ処理（もしあれば）")
        # 必要に応じてリソース解放処理などをここに追加


if __name__ == "__main__":
    main()
