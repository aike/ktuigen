# ktuigen

エフェクタープラグイン（VST / AU / CLAP など）用の GUI 画像ジェネレーター。
背景・ノブ（フィルムストリップ）・フットスイッチ・トグルスイッチ・LED を透過 PNG で出力し、
自動レイアウトの座標を `layout.json` に書き出します。何も指定しなくてもデフォルトテーマで見栄えのよい画像になります。

## 使い方

```sh
uv run ktuigen                                  # デフォルト (dark テーマ, ノブ4つ + BYPASS)
uv run ktuigen examples/delay.yaml              # 設定ファイルから
uv run ktuigen -t pedal --knobs "VOL,TONE,GAIN" --title "FUZZ" -o out/fuzz
uv run ktuigen -t pedal --jacks-left "L-IN,R-IN" --jacks-right "L-OUT,R-OUT"
uv run ktuigen -t neon --knobs 6 --toggles 1 --leds "IN,CLIP" --orientation horizontal
uv run ktuigen cfg.yaml --set knobs.style=metal --set background.texture=0.8 --scale 2
uv run ktuigen --list-themes
uv run ktuigen cfg.yaml --dump-config           # テーマ・既定値を合成した最終設定を表示
```

`--set KEY=VALUE` で任意の設定値を上書きできます（値は YAML として解釈。`knobs.items.1.size=100` のように添字も可）。

## 出力

| ファイル | 内容 |
| --- | --- |
| `background.png` | 背景。タイトルロゴ・ラベル・ノブ目盛りを焼き込み済み（角丸の外側は透過） |
| `knob.png` | ノブのフィルムストリップ（既定 101 フレーム、縦または横に連結）。フレーム 0 = 最小値 |
| `footswitch.png` | 2 フレーム（0 = OFF/非押下, 1 = ON/押下） |
| `toggle.png` | 2 または 3 フレーム（0 = 下/左, 最後 = 上/右） |
| `led.png` | `frames` 枚（既定 2: 0 = 消灯, 1 = 点灯。3 以上で明るさ段階） |
| `layout.json` | 各パーツのファイル名・座標・サイズ・フレーム数・連結方向、筐体 (`body`) とジャックの位置 |
| `preview.png` | 既定値で組み立てた完成イメージ |

見た目の異なるパーツ（例: 1 つだけ大きいノブ）は `knob_2.png` のように別ファイルになります。
`scale: 2` で @2x 画像を出力します（`layout.json` の座標は論理ピクセルのまま）。

## フィルムストリップ（アニメーション画像）の書式

ノブ・スイッチ・LED は、全フレームを 1 枚の PNG に等間隔で並べたフィルムストリップです。

### フレーム数

| パーツ | 指定方法 | 既定 | フレームの意味 |
| --- | --- | --- | --- |
| ノブ | `knobs.frames`（CLI: `--frames N`） | 101 | 0 = 最小値（`start_angle`）… N-1 = 最大値（`end_angle`） |
| LED | `leds.frames` | 2 | 0 = 消灯 … N-1 = 最大輝度（3 以上で明るさ段階。メーター用途など） |
| トグル | `toggles.positions`（2 または 3） | 2 | 0 = 下（横置きは左）… 最後 = 上（右）。3 段なら 1 = 中央 |
| フットスイッチ | 固定 | 2 | 0 = OFF / 非押下、1 = ON / 押下 |

```yaml
knobs:
  frames: 128            # 全ノブ共通
  start_angle: -150      # 12 時方向を 0 とした時計回りの角度（フレーム 0 の向き）
  end_angle: 150         # 最終フレームの向き
  items:
    0: {frames: 31}      # 1 個目のノブだけ 31 フレーム（別ファイル knob_2.png になる）
```

### 連結方向（縦 / 横）

`orientation: vertical`（縦に連結, 既定）または `horizontal`（横に連結）。
**パーツ個体 (`items[i]`) > セクション (`knobs:` など) > トップレベル** の順で優先されます。CLI の `--orientation` はトップレベルを上書きします。

```yaml
orientation: vertical          # 全パーツの既定
knobs:
  orientation: horizontal      # ノブだけ横連結
  items:
    1: {orientation: vertical} # 2 個目のノブだけ縦連結
leds:
  orientation: horizontal
```

```sh
uv run ktuigen --frames 64 --orientation horizontal
uv run ktuigen cfg.yaml --set knobs.orientation=horizontal --set knobs.frames=128
```

フレーム 1 枚のサイズを `w × h`、フレーム数を `N` とすると:

| orientation | PNG サイズ | フレーム `i` の切り出し位置 |
| --- | --- | --- |
| `vertical` | `w × (h·N)` | `(0, i·h)` から `w × h` |
| `horizontal` | `(w·N) × h` | `(i·w, 0)` から `w × h` |

値 `v`（0.0〜1.0）を表示するフレームは `i = round(v · (N − 1))` です。
`scale: 2` のときは PNG 上のピクセル数が 2 倍になります（`w`, `h` も 2 倍で切り出す）。

同じ見た目のパーツが縦・横の両方で要求された場合、2 つ目の方向は `knob_v.png` / `knob_h.png` のように接尾辞付きの別ファイルになります。
どのファイルがどの方向かは `layout.json` に記録されます。

### layout.json

```json
{
  "width": 564, "height": 260, "scale": 1, "mode": "rack",
  "background": "background.png",
  "body": {"x": 0, "y": 0, "width": 564, "height": 260},
  "controls": [
    {"type": "knob", "index": 0, "label": "DRIVE", "file": "knob.png",
     "x": 48, "y": 104, "width": 92, "height": 92,
     "frames": 101, "orientation": "vertical", "default": 0.5,
     "start_angle": -135, "end_angle": 135, "bipolar": false}
  ],
  "jacks": [{"side": "left", "index": 0, "label": "IN", "dir": "in", "x": 0, "y": 196, "width": 12, "height": 58}]
}
```

- `x`, `y`, `width`, `height` は背景画像上の配置位置とフレーム 1 枚のサイズ（論理ピクセル、左上原点）。
- `type` は `knob` / `toggle`（`positions` 付き）/ `footswitch` / `led`。`default` はプレビューに使った初期値。
- `body` は背景画像内の筐体の位置（ジャックで画像が横に広がった場合に 0 以外になる）。`jacks` はジャックがあるときだけ出力。

## 設定

設定は **既定値 ← テーマ ← 設定ファイル ← CLI** の順に上書きされます。
全項目は [examples/full.yaml](examples/full.yaml) を参照してください。

```yaml
theme: dark            # dark | light | vintage | pedal | neon
size: [600, 260]       # 省略時はレイアウトとパーツ数から自動決定
orientation: vertical  # フィルムストリップの連結方向 (パーツごとにも指定可)
palette: {accent: "#f2a33c"}   # 他の項目から "$accent" で参照

title: {text: KT DELAY, subtitle: STEREO DELAY, effects: [emboss]}
knobs: [TIME, FEEDBACK, MIX]          # 数 (knobs: 3) / ラベル一覧 / 詳細 dict のいずれでも可
toggles: {items: [{label: MODE, positions: 3, states: [A, B, C]}]}
footswitches: 1
leds: [IN, CLIP]
```

パーツの各セクション（`knobs` / `toggles` / `footswitches` / `leds`）は、セクション直下の値が全個体の既定値、
`items` がその個体だけの上書きになります。`pos: [x, y]` を書くと自動配置の代わりにその座標に置きます。

### 個体ごとの上書き（items）

`items` には **番号形式** と **リスト形式** の 2 通りの書き方があります。
番号は 0 始まり（0 = 1 個目）で、書いた項目だけが上書きされ、それ以外はセクション直下の値のままです。

**1 個だけ変える**（番号形式）

```yaml
knobs:
  labels: [DRIVE, TONE, MIX, LEVEL]
  items:
    2: {bipolar: true}               # 3 個目 (MIX) だけ中央起点
```

**飛び飛びに複数変える**

```yaml
knobs:
  labels: [GAIN, BASS, MID, TREBLE, VOLUME]
  style: pedal
  items:
    0: {rel: 1.3, style: metal}      # GAIN を大きく、別スタイルで（見た目が違うので別ファイル）
    4: {range_labels: ["0", "10"]}   # VOLUME に最小・最大の目盛り数字
```

**ラベルや位置も個体ごとに**

```yaml
toggles:
  count: 2
  items:
    0: {label: RANGE, positions: 3, states: [LO, MID, HI]}
    1: {label: BRIGHT, style: pill}
leds:
  labels: [IN, CLIP]
  items:
    1: {color: "#ff3b30", default: 0}  # CLIP だけ赤・プレビューは消灯
footswitches:
  items:
    0: {pos: [380, 20]}                # 自動配置せず座標を固定
```

**全個体を順に設定する**（リスト形式）— 全部に値があるときはリストのほうが簡潔です（[examples/delay.yaml](examples/delay.yaml)）。

```yaml
knobs:
  labels: [DELAY TIME, FEEDBACK, WET LEVEL, DUCKING]
  items:
    - {default: 0.625, range_labels: ["0", "400"]}
    - {default: 0.3}
    - {default: 0.5}
    - {default: 0.0}
```

リスト形式では要素の位置が個体の番号なので、途中の個体を飛ばすには `{}`（上書きなし）を置く必要があります。
また文字列の要素はラベルだけの指定になります（`items: [DRIVE, {label: TONE, rel: 0.8}]`）。

見た目の異なる個体は `knob.png`, `knob_2.png` … と別ファイルになります（番号は描画順）。
どの個体がどのファイルを使うかは `layout.json` の `file` で確認してください。

**CLI から**（番号形式と同じパスで指定）

```sh
uv run ktuigen cfg.yaml --set knobs.items.2.bipolar=true --set knobs.items.0.rel=1.3
```

注意:
- 個数は `count` か `labels` の数（どちらもなければテーマの既定）で決まります。番号形式の `items` は個数を変えないので、
  個数を超える番号は無視されます。リスト形式で `count` も `labels` もない場合だけ、リストの長さが個数になります。
- `items` の値はセクション直下に書ける項目すべて（`style`, `size`, `rel`, `frames`, `orientation`, `default`, `label`, `pos` …）を受け付けます。

### 値の書式

| 項目 | 書式 | 例 |
| --- | --- | --- |
| パーツのセクション | 個数 / ラベル一覧 / カンマ区切り文字列 / dict / `false`（0 個） | `knobs: 3`、`knobs: [A, B]`、`knobs: "A,B"`、`knobs: {count: 3, style: metal}` |
| 個体ごとの上書き | `items` を番号形式（0 始まりの番号 → dict）またはリスト形式で（下記） | `items: {2: {rel: 1.3}}` |
| ラベル | 文字列。`""` でラベルなし。`labels: false` で全個体ラベルなし | `labels: [DRIVE, "", LEVEL]` |
| 色 | `"#rgb"` `"#rrggbb"` `"#rrggbbaa"`、CSS 色名、`[r, g, b(, a)]`、`"$名前"`（`palette` 参照） | `"#f2a33c"`、`"#0000003c"`、`"$accent"` |
| サイズ | `[幅, 高さ]` または `"幅x高さ"`（論理 px） | `size: [600, 260]`、`--size 600x260` |
| 位置 | `[x, y]`（論理 px、パーツ画像の左上） | `pos: [40, 100]` |
| 角度 | 度。12 時方向が 0、時計回りが正 | `start_angle: -135` |
| 割合 | 0.0〜1.0 | `default: 0.5`、`texture: 0.8` |
| 真偽値 | `true` / `false` のみ（`ON` `OFF` `YES` `NO` は文字列として扱う） | `arc: false`、`labels: [ON, OFF]` |

`--set KEY=VALUE` の `KEY` はドット区切りのパス（リストは添字: `knobs.items.0.size`）、`VALUE` は上記と同じ YAML 書式です。
シェルで `[` `{` `#` `$` を含む値はクォートしてください（例: `--set 'knobs.labels=[A, B]'`、`--set 'palette.accent="#ff8800"'`）。

### 主なスタイル

- **背景** `background.style`: `solid` `gradient` `brushed` `matte` `metallic` `wood` `carbon` `grid`
  ＋ `panel`, `screws`, `wood_sides`, `corner_radius`, `vignette`, `footer`
- **タイトル** `title.effects`: `shadow` `emboss` `engrave` `glow` `outline` `bevel`（複数可）, `gradient`, `letter_spacing`
- **ノブ** `knobs.style`: `modern` `pedal` `vintage` `flat` `metal`
  ＋ `arc`, `arc_glow`, `bipolar`, `pointer` (`line`/`dot`/`none`), `start_angle`/`end_angle`, `ticks`, `range_labels`, `rel`
- **トグル** `toggles.style`: `bat` `slide` `pill`, `positions` 2/3, `axis` vertical/horizontal, `states`
- **フットスイッチ** `footswitches.style`: `button`（LED 付きボタン。rack ではヘッダー右）/ `stomp`（金属製）
- **ジャック** `jacks.left` / `jacks.right`: 筐体の左右それぞれに 0〜2 個（下記）
- **LED** `leds.style`: `round` `square`, `bezel`: `chrome` `black` `none`, `color`

### ジャック（入出力端子）

筐体の側面から突き出したプラグ用ジャックを背景画像に描き込み、内側にラベルと IN/OUT の三角記号を付けます。

```yaml
jacks:
  left:  [L-IN, R-IN]                          # 左側に 2 個
  right: [{label: SEND, dir: out}, {label: RETURN, dir: in}]
  # left: 1            # ラベルなし 1 個
  # arrow: false       # 三角記号なし（ジャックごとに arrow: false も可）
  # size: 30           # ジャックの高さ (px)
  # label_color / arrow_color / metal_color / label_size
```

- 三角記号の向きは `dir` で決まります: `in` は筐体の内側向き、`out` は外側向き、`none` は記号なし。
  左右どちら側でも `in`/`out` を指定できます。
- `dir` を省略するとラベルから推定します（`IN`/`INPUT` → in、`OUT`/`OUTPUT` → out、例: `L-IN`, `R-OUT`）。
  CLI では `--jacks-right "OUT,THRU:none"` のように `:dir` を付けて明示できます。
- 縦位置（ジャック中心）は既定で、1 個ならボディ高さの 45%、2 個なら 30% と 60%。
  `y`（ボディ上端からのジャック中心の Y 座標, px）でジャックごとに指定もできます: `{label: IN, y: 250}`。
- ラベルがノブ・ラベル・タイトルと重なる場合は、ボディを左右対称に横へ広げて余白を作ります
  （中身は中央に保たれ、`size` より幅が広くなります）。
- ジャックがある側だけ画像が横に広がります。`size` は筐体のサイズのままで、筐体の外側（ジャックの周り）は透過です。
  `layout.json` の座標は画像全体基準で、筐体の位置は `body` に入ります。

### レイアウト

- `rack`（横長）: 上部ヘッダーにタイトル・LED・ボタン、下部パネルにノブ/トグル/ストンプを行に並べ、
  入りきらなければ折り返し。ノブサイズは収まる最大値を自動計算。
- `pedal`（縦長）: ノブ → タイトル → トグル → LED → フットスイッチ の順に縦に配置。
- `auto`: `size` が縦長なら pedal、それ以外は rack。

### フォント

`font` にはエイリアス（`modern` `modern-label` `condensed` `heavy` `impact` `serif` `serif-bold` `serif-label`
`mono` `sans` `sans-bold`）、フォントファイル名（`impact.ttf`）、フルパスを指定できます。
可変フォントは `"bahnschrift.ttf:Bold Condensed"` のようにインスタンス名を付けます。見つからない場合は順に代替フォントを使用します。

## 依存

Python 3.10+, Pillow, NumPy, PyYAML（`uv run` で自動インストール）。
