# texshot

[Tiếng Việt](#tiếng-việt) · [English](#english) · [Русский](#русский)

## Tiếng Việt

CLI biên dịch các hình vẽ LaTeX (TikZ, MusiXTeX, ...) ở dạng `standalone` thành SVG để nhúng vào rST/Sphinx, ngoài ra có thể xuất PDF và JPEG.

- Mỗi file `.tex` cho ra hình nằm **ngay cạnh** file đó.
- Hình một trang cho ra `ten.svg`. Hình nhiều trang cho ra `ten-01.svg`, `ten-02.svg`, ..., mỗi trang một file.
- Các file trung gian (`.aux`, `.log`, `.dvi`, ...) được tạo trong thư mục tạm và tự xoá, không làm bẩn thư mục nội dung.

### Yêu cầu

- Python 3.9 trở lên. Bản SVG và PDF chỉ dùng thư viện chuẩn.
- TeX Live (hoặc MacTeX) có `latex`, `pdflatex`, `lualatex` và `dvisvgm` trong `PATH`.
- Chỉ khi xuất JPEG: `pip install pdf2image`, cùng poppler (`brew install poppler` hoặc `apt install poppler-utils`).

### Cách chạy

Chạy từ thư mục cha của `texshot`. Hai cách gọi sau tương đương:

```bash
python texshot [tuỳ chọn]
python -m texshot [tuỳ chọn]
```

Không chỉ định định dạng thì mặc định chỉ build SVG.

| Tuỳ chọn | Ý nghĩa |
|---|---|
| `--svg`, `--pdf`, `--jpeg` | Định dạng cần xuất, có thể kết hợp nhiều định dạng. |
| `-d DIR [DIR ...]` | Build mọi file `.tex` độc lập trong các thư mục này, kể cả thư mục con. |
| `-c FILE` | Dùng file cấu hình khác thay cho `texshot/figures.json` (khi không có `-d`). |
| `-f`, `--force` | Build lại cả các hình đã cập nhật. |
| `-j N` | Build song song `N` hình. |
| `-v` | In toàn bộ output của TeX và `dvisvgm`. |

### Chọn file cần build

Có hai chế độ.

**1. Theo thư mục (`-d`).** Tìm mọi file `.tex` trong thư mục, kể cả thư mục con. Chỉ build những file có `\documentclass`; các file được `\input` vào file khác (không có `\documentclass`) bị bỏ qua.

Engine được chọn theo thứ tự:

1. dòng chú thích `% !TEX program = lualatex` (hoặc `pdflatex`) ở đầu file;
2. nếu không có dòng đó: file dùng `fontspec` hoặc `luacode` thì build bằng `lualatex`;
3. còn lại build bằng `pdflatex`.

**2. Theo `figures.json` (không có `-d`).** Chỉ build các file được liệt kê, với engine ghi trong file cấu hình:

```json
{
    "figures/music": {
        "lualatex": ["notes", "octave"]
    },
    "figures/stuff": {
        "pdflatex": ["yinyang"]
    }
}
```

Khoá là thư mục, tính **tương đối so với chính file JSON**. Giá trị ánh xạ engine (`pdflatex` hoặc `lualatex`) sang danh sách tên file, không kèm đuôi `.tex`.

### Ví dụ

#### Build một hình: `octave.tex`

[`figures/music/octave.tex`](figures/music/octave.tex) vẽ một quãng tám Đô–Đô bằng MusiXTeX, kèm lời ca tiếng Việt. Vì cần `fontspec`, file được build bằng `lualatex`:

```latex
% !TEX program = lualatex
\documentclass[border=2pt]{standalone}
\usepackage{musixtex}
\usepackage{fontspec}

\begin{document}
\begin{music}
    \startextract
        \NOTEs\zsong{Đô}\wh{-2} \zsong{Rê}\wh{-1} ... \zsong{Đô}\wh{5}\en
    \zendextract
\end{music}
\end{document}
```

```console
$ python texshot -d texshot/figures/music
built   texshot/figures/music/notes.tex [lualatex]: notes.svg
built   texshot/figures/music/octave.tex [lualatex]: octave.svg
2/2 figures OK
```

Chạy lại khi chưa sửa file `.tex` nào thì các hình được bỏ qua. Dùng `-f` để build lại:

```console
$ python texshot -d texshot/figures/music
skipped texshot/figures/music/notes.tex [lualatex]: up to date
skipped texshot/figures/music/octave.tex [lualatex]: up to date
2/2 figures OK
```

Xuất thêm PDF cho mọi hình trong `figures.json`:

```bash
python texshot --svg --pdf
```

#### Hình nhiều trang

Với `\documentclass[tikz]{standalone}`, mỗi `tikzpicture` là một trang. File `univariate.tex` có 10 `tikzpicture` nên cho ra 10 SVG:

```console
$ python texshot -d mathematics/algebra/polynomial/figures -j 4
built   mathematics/algebra/polynomial/figures/polynomials/univariate.tex [pdflatex]: univariate-01.svg, univariate-02.svg, ..., univariate-10.svg
1/1 figures OK
```

Nếu hình giảm số trang, chẳng hạn từ 3 xuống 1, các file `ten-NN.svg` cũ sẽ bị xoá trước khi sinh `ten.svg`, nên không còn file thừa.

#### Nhúng vào rST

Viết đường dẫn **tương đối** từ file rST tới hình và để đuôi là `*`. Sphinx sẽ tự chọn định dạng phù hợp (SVG cho HTML):

```rst
.. figure:: figures/music/octave.*

   Một quãng tám

.. figure:: figures/polynomials/univariate-03.*
```

#### Khi có lỗi

Hình lỗi không làm dừng các hình khác. Các dòng lỗi `!` trong log được in ra để dễ sửa:

```console
$ python texshot -d drafts
FAILED  drafts/bad.tex [pdflatex]
        latex failed
        ! Undefined control sequence.
        l.3 \undefinedcommand
0/1 figures OK
```

Mã thoát: `0` nếu mọi hình thành công, `1` nếu có hình lỗi, `2` nếu tham số hoặc cấu hình sai (thư mục không tồn tại, `figures.json` hỏng, ...).

### Lưu ý khi viết hình

- Dùng `\documentclass[border=2pt]{standalone}` (thêm option `tikz` nếu mỗi `tikzpicture` là một hình riêng) để hình được cắt sát nội dung.
- Với MusiXTeX, **không** dùng `crop,preview` vì sẽ cắt mất dòng lời ca, cũng không đặt `varwidth=<độ rộng>` nhỏ hơn khuông nhạc vì sẽ xén mất nốt. Một dòng nhạc ngắn trong `\startextract ... \zendextract` không cần chạy thêm `musixflx`.
- SVG được dựng qua DVI: `latex` cho hình `pdflatex`, `lualatex --output-format=dvi` cho hình `lualatex`, rồi `dvisvgm --no-fonts`. Chữ được chuyển thành đường vẽ, nên SVG hiển thị đúng mà không cần font trên máy người xem.

## English

A CLI that compiles `standalone` LaTeX figures (TikZ, MusiXTeX, ...) into SVG for embedding in rST/Sphinx; it can also export PDF and JPEG.

- Each `.tex` file produces its figures **next to** the file itself.
- A one-page figure produces `name.svg`. A multi-page figure produces `name-01.svg`, `name-02.svg`, ..., one file per page.
- Intermediate files (`.aux`, `.log`, `.dvi`, ...) are created in a temporary directory and removed afterwards, so content directories stay clean.

### Requirements

- Python 3.9 or newer. SVG and PDF output only use the standard library.
- TeX Live (or MacTeX) with `latex`, `pdflatex`, `lualatex` and `dvisvgm` on the `PATH`.
- For JPEG output only: `pip install pdf2image`, plus poppler (`brew install poppler` or `apt install poppler-utils`).

### Usage

Run from the parent directory of `texshot`. The two invocations below are equivalent:

```bash
python texshot [options]
python -m texshot [options]
```

If no format is given, only SVG is built.

| Option | Meaning |
|---|---|
| `--svg`, `--pdf`, `--jpeg` | Output formats; several can be combined. |
| `-d DIR [DIR ...]` | Build every standalone `.tex` file in these directories, including subdirectories. |
| `-c FILE` | Use another configuration file instead of `texshot/figures.json` (when `-d` is not given). |
| `-f`, `--force` | Rebuild figures that are already up to date. |
| `-j N` | Build `N` figures in parallel. |
| `-v` | Print the full output of TeX and `dvisvgm`. |

### Choosing the files to build

There are two modes.

**1. By directory (`-d`).** Finds every `.tex` file in the directories, including subdirectories. Only files containing `\documentclass` are built; files pulled into another file with `\input` (which have no `\documentclass`) are skipped.

The engine is chosen in this order:

1. a magic comment `% !TEX program = lualatex` (or `pdflatex`) at the top of the file;
2. without it: files using `fontspec` or `luacode` are built with `lualatex`;
3. everything else is built with `pdflatex`.

**2. From `figures.json` (no `-d`).** Only the listed files are built, with the engine given in the configuration:

```json
{
    "figures/music": {
        "lualatex": ["notes", "octave"]
    },
    "figures/stuff": {
        "pdflatex": ["yinyang"]
    }
}
```

Keys are directories, **relative to the JSON file itself**. Values map an engine (`pdflatex` or `lualatex`) to a list of file names without the `.tex` extension.

### Examples

#### Building one figure: `octave.tex`

[`figures/music/octave.tex`](figures/music/octave.tex) draws a C–C octave with MusiXTeX, with Vietnamese solfège lyrics. It needs `fontspec`, so it is built with `lualatex`:

```latex
% !TEX program = lualatex
\documentclass[border=2pt]{standalone}
\usepackage{musixtex}
\usepackage{fontspec}

\begin{document}
\begin{music}
    \startextract
        \NOTEs\zsong{Đô}\wh{-2} \zsong{Rê}\wh{-1} ... \zsong{Đô}\wh{5}\en
    \zendextract
\end{music}
\end{document}
```

```console
$ python texshot -d texshot/figures/music
built   texshot/figures/music/notes.tex [lualatex]: notes.svg
built   texshot/figures/music/octave.tex [lualatex]: octave.svg
2/2 figures OK
```

Running again without changing any `.tex` file skips the figures. Use `-f` to rebuild them:

```console
$ python texshot -d texshot/figures/music
skipped texshot/figures/music/notes.tex [lualatex]: up to date
skipped texshot/figures/music/octave.tex [lualatex]: up to date
2/2 figures OK
```

Also export PDF for every figure in `figures.json`:

```bash
python texshot --svg --pdf
```

#### Multi-page figures

With `\documentclass[tikz]{standalone}`, every `tikzpicture` is a page. `univariate.tex` has 10 `tikzpicture`s, so it produces 10 SVGs:

```console
$ python texshot -d mathematics/algebra/polynomial/figures -j 4
built   mathematics/algebra/polynomial/figures/polynomials/univariate.tex [pdflatex]: univariate-01.svg, univariate-02.svg, ..., univariate-10.svg
1/1 figures OK
```

If a figure loses pages, say from 3 to 1, the old `name-NN.svg` files are removed before `name.svg` is written, so no stale files are left behind.

#### Embedding in rST

Use a path **relative** to the rST file and the extension `*`. Sphinx picks the right format (SVG for HTML):

```rst
.. figure:: figures/music/octave.*

   An octave

.. figure:: figures/polynomials/univariate-03.*
```

#### Errors

A failing figure does not stop the others. The `!` error lines from the log are printed to help fix it:

```console
$ python texshot -d drafts
FAILED  drafts/bad.tex [pdflatex]
        latex failed
        ! Undefined control sequence.
        l.3 \undefinedcommand
0/1 figures OK
```

Exit codes: `0` if every figure succeeded, `1` if some figure failed, `2` for invalid arguments or configuration (missing directory, broken `figures.json`, ...).

### Tips for writing figures

- Use `\documentclass[border=2pt]{standalone}` (add the `tikz` option if each `tikzpicture` is a separate figure) so the figure is cropped to its content.
- With MusiXTeX, do **not** use `crop,preview`, which cuts off the lyrics line, and do not set `varwidth=<width>` narrower than the staff, which clips notes. A short line of music in `\startextract ... \zendextract` does not need an extra `musixflx` run.
- SVG is produced through DVI: `latex` for `pdflatex` figures, `lualatex --output-format=dvi` for `lualatex` figures, then `dvisvgm --no-fonts`. Text is converted to paths, so the SVG renders correctly without the fonts installed on the viewer's machine.

## Русский

Утилита командной строки, которая компилирует рисунки LaTeX (TikZ, MusiXTeX, ...) в формате `standalone` в SVG для вставки в rST/Sphinx; также умеет выводить PDF и JPEG.

- Каждый файл `.tex` создаёт рисунки **рядом** с самим собой.
- Одностраничный рисунок даёт `name.svg`. Многостраничный рисунок даёт `name-01.svg`, `name-02.svg`, ..., по одному файлу на страницу.
- Промежуточные файлы (`.aux`, `.log`, `.dvi`, ...) создаются во временном каталоге и затем удаляются, поэтому каталоги с содержимым остаются чистыми.

### Требования

- Python 3.9 или новее. Для SVG и PDF нужна только стандартная библиотека.
- TeX Live (или MacTeX) с `latex`, `pdflatex`, `lualatex` и `dvisvgm` в `PATH`.
- Только для JPEG: `pip install pdf2image`, а также poppler (`brew install poppler` или `apt install poppler-utils`).

### Запуск

Запускайте из родительского каталога `texshot`. Два варианта вызова ниже равнозначны:

```bash
python texshot [параметры]
python -m texshot [параметры]
```

Если формат не указан, собирается только SVG.

| Параметр | Назначение |
|---|---|
| `--svg`, `--pdf`, `--jpeg` | Выходные форматы; можно указать несколько. |
| `-d DIR [DIR ...]` | Собрать все самостоятельные файлы `.tex` в этих каталогах, включая подкаталоги. |
| `-c FILE` | Использовать другой файл конфигурации вместо `texshot/figures.json` (если `-d` не задан). |
| `-f`, `--force` | Пересобрать и актуальные рисунки. |
| `-j N` | Собирать `N` рисунков параллельно. |
| `-v` | Выводить полный вывод TeX и `dvisvgm`. |

### Выбор файлов для сборки

Есть два режима.

**1. По каталогу (`-d`).** Ищутся все файлы `.tex` в каталогах, включая подкаталоги. Собираются только файлы, содержащие `\documentclass`; файлы, подключаемые в другие через `\input` (без `\documentclass`), пропускаются.

Движок выбирается в следующем порядке:

1. магический комментарий `% !TEX program = lualatex` (или `pdflatex`) в начале файла;
2. если его нет: файлы с `fontspec` или `luacode` собираются через `lualatex`;
3. все остальные — через `pdflatex`.

**2. По `figures.json` (без `-d`).** Собираются только перечисленные файлы с движком, указанным в конфигурации:

```json
{
    "figures/music": {
        "lualatex": ["notes", "octave"]
    },
    "figures/stuff": {
        "pdflatex": ["yinyang"]
    }
}
```

Ключи — это каталоги, **относительно самого файла JSON**. Значения сопоставляют движку (`pdflatex` или `lualatex`) список имён файлов без расширения `.tex`.

### Примеры

#### Сборка одного рисунка: `octave.tex`

[`figures/music/octave.tex`](figures/music/octave.tex) рисует октаву до–до средствами MusiXTeX с подписями нот на вьетнамском. Файлу нужен `fontspec`, поэтому он собирается через `lualatex`:

```latex
% !TEX program = lualatex
\documentclass[border=2pt]{standalone}
\usepackage{musixtex}
\usepackage{fontspec}

\begin{document}
\begin{music}
    \startextract
        \NOTEs\zsong{Đô}\wh{-2} \zsong{Rê}\wh{-1} ... \zsong{Đô}\wh{5}\en
    \zendextract
\end{music}
\end{document}
```

```console
$ python texshot -d texshot/figures/music
built   texshot/figures/music/notes.tex [lualatex]: notes.svg
built   texshot/figures/music/octave.tex [lualatex]: octave.svg
2/2 figures OK
```

При повторном запуске без изменений в файлах `.tex` рисунки пропускаются. Для пересборки используйте `-f`:

```console
$ python texshot -d texshot/figures/music
skipped texshot/figures/music/notes.tex [lualatex]: up to date
skipped texshot/figures/music/octave.tex [lualatex]: up to date
2/2 figures OK
```

Дополнительно вывести PDF для всех рисунков из `figures.json`:

```bash
python texshot --svg --pdf
```

#### Многостраничные рисунки

При `\documentclass[tikz]{standalone}` каждый `tikzpicture` — отдельная страница. В `univariate.tex` 10 окружений `tikzpicture`, поэтому получается 10 файлов SVG:

```console
$ python texshot -d mathematics/algebra/polynomial/figures -j 4
built   mathematics/algebra/polynomial/figures/polynomials/univariate.tex [pdflatex]: univariate-01.svg, univariate-02.svg, ..., univariate-10.svg
1/1 figures OK
```

Если у рисунка стало меньше страниц, например 1 вместо 3, старые файлы `name-NN.svg` удаляются перед созданием `name.svg`, так что устаревших файлов не остаётся.

#### Вставка в rST

Укажите путь **относительно** файла rST и расширение `*`. Sphinx сам выберет подходящий формат (SVG для HTML):

```rst
.. figure:: figures/music/octave.*

   Октава

.. figure:: figures/polynomials/univariate-03.*
```

#### Ошибки

Ошибка в одном рисунке не останавливает сборку остальных. Строки ошибок `!` из журнала выводятся, чтобы их было проще исправить:

```console
$ python texshot -d drafts
FAILED  drafts/bad.tex [pdflatex]
        latex failed
        ! Undefined control sequence.
        l.3 \undefinedcommand
0/1 figures OK
```

Коды возврата: `0`, если все рисунки собраны успешно; `1`, если какой-то рисунок не собрался; `2` при неверных аргументах или конфигурации (несуществующий каталог, повреждённый `figures.json`, ...).

### Советы по подготовке рисунков

- Используйте `\documentclass[border=2pt]{standalone}` (добавьте опцию `tikz`, если каждый `tikzpicture` — отдельный рисунок), чтобы рисунок обрезался по содержимому.
- С MusiXTeX **не** используйте `crop,preview`: это обрезает строку с текстом под нотами. Также не задавайте `varwidth=<ширина>` меньше ширины нотного стана: это срезает ноты. Короткой строке нот в `\startextract ... \zendextract` дополнительный запуск `musixflx` не нужен.
- SVG строится через DVI: `latex` для рисунков `pdflatex`, `lualatex --output-format=dvi` для рисунков `lualatex`, затем `dvisvgm --no-fonts`. Текст превращается в контуры, поэтому SVG отображается правильно без установленных шрифтов на компьютере читателя.
