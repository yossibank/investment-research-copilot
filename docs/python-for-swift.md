# Python for Swift developers

このリポジトリの Python コードに出てくる書き方を、Swift と対比してまとめる。
コード中のコメントには「なぜそうするか」だけを書き、文法の説明はここに置く。

## モジュールと import

| Python | Swift |
| --- | --- |
| 1 ファイル = 1 モジュール、フォルダ = パッケージ（`__init__.py`） | ターゲット / Swift Package が 1 モジュール |
| `from .models import Chunk`（`.` は同じフォルダ） | 同じモジュール内なら import 不要 |
| `from ..paths import DATA_DIR`（`..` は 1 つ上のフォルダ） | `import OtherModule` |

- import したとき、**そのファイルの一番上のコードが上から実行される**。2 回目以降の import ではキャッシュ（`sys.modules`）が使われ、再実行はされない
  - 例：`llm.py` の `load_dotenv(ENV_PATH)` は最初の import で 1 回だけ実行される
- `from x import y` と書くと、**import した側のモジュールに `y` という名前ができる**
  - テストの `monkeypatch.setattr(module, "y", fake)` は、この「使う側の名前」を差し替える（段階 3・4 で確認）
- `python -m research_copilot.retrieval.search` でファイルを実行すると、そのファイルの `__name__` が `"__main__"` になる

```python
if __name__ == "__main__":   # 直接実行したときだけ main() を呼ぶ（import されたときは呼ばない）
    main()
```

## 型注釈

```python
def search(query: str, top_k: int = 5) -> list[tuple[Chunk, float]]: ...
```

```swift
func search(query: String, topK: Int = 5) -> [(Chunk, Double)]
```

| Python | Swift |
| --- | --- |
| `str \| None` | `String?` |
| `list[str]` | `[String]` |
| `dict[str, object]` | `[String: Any]` |
| `tuple[Chunk, float]` | `(Chunk, Double)` |

- **Python 本体は型注釈を実行時にチェックしない**。 で確認）
- ただし FastAPI と Pydantic は注釈を**実行時に読んで使う**（リクエストの検証など）
- 注釈の間違いを見つけるには pyright を使う：`pyrigh

## リスト内包表記

```python
texts = [f"passage: {chunk.text}" for chunk in chunks]
hits = [chunk for chunk in chunks if term in chunk.t
```

```swift
let texts = chunks.map { "passage: \($0.text)" }
let hits = chunks.filter { $0.text.contains(term) }
```

辞書版もある：`{chunk.chunk_id: chunk for chunk in cqueKeysWithValues: chunks.map { ($0.chunkId, $0) })`と同じ。

## for 文・enumerate・タプルの分解

```python
for rank, (chunk, score) in enumerate(results, start
    ...
```

```swift
for (offset, (chunk, score)) in results.enumerated() {
    let rank = offset + 1
}
```

- `enumerate(xs, start=1)` は「番号, 要素」の組を返 ら始める
- `for chunk, score in results:` のように、タプルをその場で分解できる

## スライス

| Python | 意味 | Swift |
| --- | --- | --- |
| `text[start:end]` | start から end の**直前**まで | `text[start..<end]`（String は Index が必要） |
| `xs[:k]` | 先頭から k 個 | `xs.prefix(k)` |
| `xs[::-1]` | 逆順 | `xs.reversed()` |
| `xs[0]` | 先頭 | `xs[0]` |

範囲外を指定してもエラーにならず、ある分だけ返る（`"

## 文字列

| Python | Swift |
| --- | --- |
| `f"p{page}-c{index}"` | `"p\(page)-c\(index)"` |
| `text.strip()` | `text.trimmingCharacters(in: .whitespacesAndNewlines)` |
| `"\n\n".join(sections)` | `sections.joined(separat
| `"A" "B"`（隣に並べる） | `"A" + "B"` |

複数行の f-string を括弧でくくって並べると、1 つの文字列につながる（`build_context` やシステムプロンプトで使っている）。

## `or` と「falsy」

```python
text = page.extract_text() or ""
```

`??` に似ているが、**`None` だけでなく、`""`・`0`・`[]` のときも右側が使われる**。
`if not text:` も同じで、「空文字」と「None」の両方

## pathlib（ファイルパス）

| Python | Swift |
| --- | --- |
| `DATA_DIR / "parsed" / "pages.json"` | `dataDir.aps.json")` |
| `Path(__file__).resolve().parents[3]` | `URL(filePath: #filePath)` から 4 階層上 |
| `path.parent` | `url.deletingLastPathComponent()`
| `path.read_text(encoding="utf-8")` | `try String(contentsOf: url, encoding: .utf8)` |
| `path.write_text(text, encoding="utf-8")` | `try tlly: true, encoding: .utf8)` |
| `path.mkdir(parents=True, exist_ok=True)` | `try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)`
|

`parents=True` は途中のフォルダも作る、`exist_ok=Tru しない。

## JSON

| Python | Swift |
| --- | --- |
| `json.loads(text)` → `list` / `dict` | `JSONSerial |
| `json.dumps(obj, ensure_ascii=False, indent=2)` | `JSONSerialization.data(withJSONObject:options: .prettyPrinted)` |

`ensure_ascii=False` にしないと、日本語が `\u58f2\u4e0a` のようにエスケープされる。

## Pydantic と dataclass

```python
class Chunk(BaseModel):
    chunk_id: str
    page: int
```

| Pydantic | 意味 | Swift |
| --- | --- | --- |
| `Chunk.model_validate(d)` | dict を型に詰めて**検証**する | `JSONDecoder().decode`（dict 版） |
| `Chunk.model_validate_json(s)` | JSON 文字列から直(Chunk.self, from: data)` |
| `chunk.model_dump()` | dict に変換 | `JSONEncoder` の途中の辞書 |
| `Field(ge=1, le=10)` | 1 以上 10 以下（greater / lt` での `precondition` |
| `Field(default_factory=list)` | 既定値を毎回新しく作る | `var xs: [String] = []` |
| `@field_validator("question")` | 項目ごとの独自の ` での検証 |

- `BaseModel`：外から来るデータ・外へ出すデータ（Claイル）に使う。型が違えばエラーになる
- `@dataclass`：内部で受け渡すだけのデータに使う（`CopilotRun`）。検証はしない。Swift の memberwise init 付き `struct` に近い
- Python の関数の既定値に `[]` を書くと、**呼び出し  れる**。そのため `default_factory`を使う習慣にしておく（Pydantic は `= []` でも安全にコピーするが、dataclass では禁止されている）

## デコレータ（`@...`）

関数やクラスに機能を足す書き方。Swift の property wrapper や attribute（`@MainActor`）に見た目が似ている。

| 使っている所 | 意味 | Swift で近いもの |
| --- | --- | --- |
| `@lru_cache(maxsize=1)` | 戻り値を覚えて、2 回目以降は再実行しない | `static let model = load()`（初回だけ初期化） |
| `@app.post("/research/copilot")` | 関数を URL に登t(...)` |
| `@classmethod` | クラスから呼ぶメソッド。第 1 引数 `cls` はクラス自身 | `static func` / `convenience init` |
| `@dataclass` | `__init__` などを自動生成 | memberw

```python
@classmethod
def from_chunk(cls, chunk: Chunk, score: float) -> S
    return cls(chunk_id=chunk.chunk_id, ...)
```

```swift
extension ResearchSource {
    init(chunk: Chunk, score: Double) { self.init(ch }
}
```

## 例外

| Python | Swift |
| --- | --- |
| `raise ValueError("...")` | `throw MyError.invalid
| `try: ... except ValueError as error: ...` | `do { ... } catch let error as MyError { ... }` |
| `raise ValueError("...") from error` | 元のエラー aceback に残る） |
| `except Exception:` | `catch { }`（何でも捕まえる） |

関数が例外を投げるかどうかは、型には現れない（Swift の `throws` のような印はない）。

## with（後片付けの自動化）

```python
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        ...
# ここを抜けると接続が閉じられる
```

Swift の `defer { stream.close() }` を自動で書いてく

## yield（ジェネレータ）

```python
def stream_research_query(...) -> Iterator[str]:
    yield json_line({"type": "metadata", ...})
    for text in stream.text_stream:
        yield json_line({"type": "text_delta", "text
```

`yield` するたびに値を 1 つ返して一時停止し、次の値を求められたら続きから再開する。
iOS 側の `AsyncThrowingStream` の `continuation.yiel。

## NumPy（ベクトル計算）

```python
embeddings = np.load(EMBEDDINGS_PATH)     # 形 (チャンク数, 384) の行列
scores = embeddings @ query_embedding     # (チャン ンク数,)
top_indices = np.argsort(scores)[::-1][:top_k]
```

- `ndarray`：同じ型の数値が並んだ多次元配列。`shape`
- `@`：行列の積。ここでは各チャンクのベクトルと質問のベクトルの内積を、全チャンク分まとめて計算している
- `np.argsort(xs)`：**値ではなく**、小さい順に並べた[::-1]` で大きい順にし、`[:top_k]` で上位を取る
- `.npy`：NumPy の配列をそのまま保存する形式。JSON より速く、数値の精度も落ちない

## テスト（pytest）

| pytest | XCTest |
| --- | --- |
| `def test_xxx():` | `func testXxx()` |
| `assert a == b` | `XCTAssertEqual(a, b)` |
| `with pytest.raises(ValueError, match="empty"):` | `XCTAssertThrowsError(try f())` |
| `pytest.approx(10.0)` | `XCTAssertEqual(a, 10.0, a
| `monkeypatch.setattr(module, "name", fake)` | protocol を使った DI でモックに差し替える |
| `monkeypatch.setenv("KEY", "value")` | テスト中だ

- `match=` は正規表現で、エラーメッセージの**一部**
- `SimpleNamespace(a=1)`：その場で属性を持つだけのオブジェクト。偽のレスポンスを作るのに使う
- `def parse(self, **kwargs)`：名前付き引数を何でも