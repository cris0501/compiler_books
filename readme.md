# larex

A LaTeX-to-JSON transpiler designed to power interactive math books built with Vue.js and KaTeX.

larex parses a subset of LaTeX into a structured AST (Abstract Syntax Tree) represented as JSON. This JSON is then consumed by a Vue.js frontend that renders each node into interactive components — clickable notes, inline math, display equations, nested lists, and more.

This is a personal project born out of curiosity and challenge. It is not a full LaTeX compiler and does not aim to be one. Instead, it defines a clear, supported subset of LaTeX that is sufficient for writing math-heavy interactive content, while keeping the codebase small and readable enough that others can study it and learn from it.

---

## Current Support

### Text Formatting
| Command | Output |
|---------|--------|
| `\textbf{...}` | **Bold** |
| `\textit{...}` | *Italic* |
| `\emph{...}` | *Emphasized* |
| `\underline{...}` | Underlined |
| `\texttt{...}` | `Monospace` |
| `\textsf{...}` | Sans-serif |
| `\psc{...}` | Small caps |

### Headings
| Command | Level |
|---------|-------|
| `\chapter{...}` | 0 (chapter) |
| `\section{...}` | 1 (section) |
| `\subsection{...}` | 2 (subsection) |

### Math
| Syntax | Type |
|--------|------|
| `$...$` | Inline math |
| `$$...$$` | Display math |
| `\[...\]` | Display math |
| `\begin{equation}...\end{equation}` | Display math |
| `\begin{align}...\end{align}` | Display math |
| `\begin{cases}...\end{cases}` | Display math |
| `\begin{pmatrix}...\end{pmatrix}` | Display math |

### Lists
- `\begin{enumerate}...\end{enumerate}` — ordered lists
- `\begin{itemize}...\end{itemize}` — unordered lists
- `\item` — list items (implicit closing)

### Custom Environments (Key-Value)
All accept `[label=x, title=y]` syntax:

| Environment | Purpose |
|-------------|---------|
| `theorem` | Formal theorem |
| `definition` | Formal definition |
| `axiom` | Axiom or postulate |
| `lemma` | Auxiliary lemma |
| `proposition` | Proposition |
| `corollary` | Corollary |
| `proof` | Proof block |
| `exercise` | Practice problem |
| `convention` | Notation convention |
| `block` | Tab-based content |

### Other Elements
- `\note[key=val]{content}` — inline tooltip note
- `\alert{content}` — highlighted alert
- `\label{id}` — label for cross-references
- `\ref{id}` — cross-reference
- `\includegraphics[options]{path}` — image
- `\caption{text}` — figure caption
- `\begin{figure}...\end{figure}` — figure container
- `\begin{verbatim}...\end{verbatim}` — preformatted text
- `\begin{tabular}{|l|c|r|}...\end{tabular}` — table
- `\url{path}` — hyperlink URL
- `% comments` — stripped before tokenization
- `\qed`, `\obs`, `\dem` — markers
- `\newline`, `\n`, `\\` — line breaks
- `\newpage` — page break
- `\noindent` — suppress indentation
- `\backslash` — literal backslash

---

## CLI Usage

```bash
# Parse a .tex file and print the JSON AST to stdout
python -m larex input.tex

# Parse and save to a file
python -m larex input.tex -o output.json

# Parse with file output to examples/dist/
python -m larex input.tex -f
```

The output JSON can be placed in your Vue project's public directory and fetched at runtime.

---

## JSON Schema

The AST uses a `kind` field to identify each node type. Text is represented as plain strings directly inside `content` arrays.

```python
# Output structure
{
  "content": [...],   # Array of AST nodes
  "refs": {...},      # Label → {index} mappings
  "chapters": {...}, # Chapter metadata
  "meta": {...}       # Document metadata (documentclass, packages)
}
```

### Node Types

| Kind | Fields | Description |
|------|--------|-------------|
| `heading` | `level`, `content` | Chapter/section (level: 0, 1, 2) |
| `bold`, `italic`, `underline`, `monospace`, `smallcaps`, `sansserif` | `content` | Text formatting |
| `math` | `mode` ("inline"/"display"), `raw` | Math expression (raw LaTeX) |
| `list` | `ordered`, `content` | Ordered/unordered list |
| `item` | `content` | List item |
| `theorem`, `definition`, `axiom`, `lemma`, `proposition`, `corollary`, `proof`, `exercise`, `convention`, `block` | `content`, `params` | Mathematical environments |
| `note` | `params`, `content` | Tooltip note (inline-only) |
| `alert` | `content` | Alert box |
| `figure` | `content` | Image container |
| `image` | `params` | Image node |
| `caption` | `content` | Figure caption |
| `table` | `columns`, `rows` | Table with parsed structure |
| `verbatim` | `content` | Preformatted text (string) |
| `label` | `id`, `index` | Label definition |
| `ref` | `target`, `index` | Cross-reference |
| `url` | `content` | Raw URL string |
| `newline` | — | Line break |
| `pagebreak` | — | Page break |
| `observation` | — | Observation marker |
| `proof-mark` | — | Proof marker |
| `qed` | — | End-of-proof symbol |
| `group` | `content` | Grouped content |
| `paragraph` | — | Paragraph marker |

---

## Architecture

The project is structured to mirror the phases of a classical compiler:

```
source.tex
    │
    ▼
tokens.py       Lexical analysis (scanner)
    │            Converts raw text into token pairs: (type, value)
    │            Knows nothing about what commands mean
    ▼
registry.py     Declarative grammar
    │            Defines what commands/environments exist,
    │            how many arguments they take, and what AST
    │            nodes they produce
    ▼
parser.py       Syntactic analysis
    │            Consumes tokens guided by the registry
    │            Uses a stack to track parent context
    │            Produces the AST
    ▼
ast.json        The output
                 Consumed directly by Vue components
```

### File Structure

```
larex/
├── tokens.py          # Tokenizer: raw text → tokens
├── registry.py        # Grammar: command/environment definitions
├── parser.py          # Parser: tokens → AST
├── consume.py         # Token consumption helpers
├── cli.py             # Command-line interface
└── handlers/
    ├── commands.py    # Command handlers
    ├── environments.py # Environment handlers
    ├── math.py        # Math block handlers
    ├── structure.py   # \item, \label, \ref handlers
    └── table.py       # Tabular parser
```

### Key Concepts

**tokens.py** — The tokenizer splits LaTeX source into tokens like `('COMMAND', '\\section')`, `('TEXT', 'hello')`, `('MATH_INLINE', '$')`. It does not know or care whether a command exists. Its only job is to classify characters into types.

**registry.py** — A declarative dictionary that tells the parser how to handle each command. Adding a new command means adding one line here. The parser itself does not change.

**parser.py** — A stack-based parser. The stack holds references to parent nodes, so each token knows where it belongs without needing to track siblings. The parent determines what its children can contain — for example, a note restricted to `inline_only` will reject display math or environments inside it.

---

## Extending the Parser

### Adding a New Command

To add a new command, edit `registry.py`:

```python
COMMANDS: dict[str, dict] = {
    # Example: a new self-closing command
    '\\mycommand': {'produces': 'mykind', 'self_closing': True},
    
    # Example: a command with one argument (parsed)
    '\\other': {'produces': 'otherkind', 'args': 1},
    
    # Example: a command with raw arguments
    '\\rawcmd': {'produces': 'rawkind', 'args': 1, 'raw_args': True},
    
    # Example: command with key-value parameters
    '\\special': {'produces': 'specialkind', 'args': 1, 'kv': True},
}
```

**Registry Options:**

| Option | Description |
|--------|-------------|
| `produces` | (required) The `kind` value in the AST node |
| `args` | Number of brace blocks to consume as content |
| `opt_args` | Max positional bracket args (standard LaTeX) |
| `kv` | Parse brackets as key=value pairs |
| `raw_args` | Consume braces as raw text (not parsed) |
| `self_closing` | No arguments consumed |
| `inline_only` | Reject display math and environments inside |
| `extra` | Fixed fields copied to the node |
| `modifier` | Convert parent group node to this kind |

### Adding a New Environment

```python
ENVIRONMENTS: dict[str, dict] = {
    # Example: parsed environment
    'myenv': {'produces': 'myenvkind', 'kv': True},
    
    # Example: raw environment (content passed to KaTeX)
    'equation': {'produces': 'math', 'extra': {'mode': 'display'}, 'raw': True},
    
    # Example: table environment
    'tabular': {'produces': 'table', 'table': True},
}
```

**Environment Options:**

| Option | Description |
|--------|-------------|
| `produces` | (required) The `kind` value in the AST node |
| `kv` | Parse brackets as key=value pairs |
| `opt_args` | Positional bracket args (standard LaTeX) |
| `raw` | Collect entire body as raw text |
| `table` | Use tabular parser |
| `extra` | Fixed fields copied to the node |

### Key-Value Parameter System

Custom environments use key-value syntax instead of positional arguments:

```latex
\begin{environment}[key1=value1, key2=value2]
  Content
\end{environment}
```

The parser handles this via `consume_env_params()` in `consume.py`. The common keys are:

- `label` — identifier for `\ref`
- `title` — display name
- `aside` — lateral annotation

---

## The Road Here: From Regex to Tokenizer

This section documents the actual progression of building this parser, written for anyone who wants to understand how you get from "I want to parse LaTeX" to a working transpiler. This was not a linear process planned in advance. Each stage hit a wall that forced the next one.

### Stage 1: Regular Expressions

The first attempt was the most intuitive one: use regex to find patterns in the LaTeX source and replace them.

```python
text = re.sub(r'\\textbf\{(.+?)\}', r'<b>\1</b>', text)
text = re.sub(r'\$(.+?)\$', r'<math>\1</math>', text)
```

This works for flat, simple cases. `\textbf{hello}` becomes `<b>hello</b>`. But LaTeX is not flat. The moment you have nesting, regex breaks:

```latex
\textbf{This has \textit{nested} formatting}
```

The regex `\\textbf\{(.+?)\}` would match `\textbf{This has \textit{nested}` and stop at the first `}`, which belongs to `\textit`, not to `\textbf`. You could try to make the regex smarter with balanced group matching, but that is fighting the tool — regex is fundamentally not designed for nested structures.

The other problem was parameters. A command like `\def{title}{content}` has two brace groups, and the regex needs to know which is which. Adding more commands with different numbers of arguments turned the regex into an unmaintainable mess.

**What was learned:** regex works for flat pattern matching, not for structured languages. If your syntax has nesting or variable-length arguments, you need something that can count depth.

### Stage 2: Character-by-Character Scanner

The second attempt abandoned regex and read the source character by character. The idea was simple: accumulate characters into a temporary string. When you hit a special character (`\`, `$`, `{`, `}`), evaluate what you have so far and decide what to do.

```python
for char in source:
    if char == '\\':
        # start of a command, flush the temp buffer as text
        flush_text(temp)
        temp = '\\'
    elif char == '{':
        # the temp buffer might be a command name
        if temp.startswith('\\'):
            handle_command(temp)
        # ...
    else:
        temp += char
```

This actually solved the nesting problem because you could track depth with a counter. Every `{` increments it, every `}` decrements it. You know a command's argument is complete when depth returns to where it started.

It also solved the parameter problem because once you identified a command, you could read its arguments one by one, each delimited by `{...}`.

But the code became tangled. The character loop was doing too many things: recognizing command names, tracking math mode, counting braces, accumulating text, handling whitespace. Every new feature (support `$$`, support `\n`, support `[optional args]`) added more conditions to the same loop. The logic for "what is this character?" was mixed with "what do I do with it?", and both were mixed with "where does this go in the output?".

**What was learned:** reading character by character gives you full control, but without a clear separation of concerns, the complexity becomes unmanageable. The scanner was doing lexical analysis and syntactic analysis in the same loop, and those are two different jobs.

### Stage 3: Tokenizer + Parser (Current)

The key insight was to split the work into two independent stages.

**The tokenizer** reads characters and groups them into tokens — labeled chunks like `('COMMAND', '\\section')` or `('TEXT', 'hello')`. It does not know what `\section` means, whether it exists, or how many arguments it takes. It only knows the shape of things: a backslash followed by letters is a COMMAND token, a `$` is a MATH_INLINE token, a `{` is an OPEN_BRACE token.

**The parser** reads tokens and builds a tree. It knows (via the registry) that `\section` takes one argument and produces a heading node. It uses a stack to track context: when it opens a `{`, it pushes a frame onto the stack pointing to the current parent node. When it closes with `}`, it pops the frame. This way, every token knows exactly where it belongs — it goes into whatever node is on top of the stack — without needing to track siblings or do any lookahead.

This separation means that adding a new command does not touch the tokenizer or the parser. You add one entry to the registry dictionary, and the parser's generic logic handles it. The tokenizer already knows how to produce COMMAND tokens regardless of the command name.

The stack-based approach also naturally solves the problems from previous stages:

- **Nesting**: `\textbf{This has \textit{nested} formatting}` works because the `}` after "nested" pops the italic frame, and the parser is back in the bold frame. No regex tricks needed.
- **Parameters**: `\def{title}{content}` works because the registry says "2 args, first goes to params". The parser consumes two brace blocks in sequence.
- **Context sensitivity**: a `$` inside `$$...$$` does not open inline math, because the parser knows it is inside a math collection and treats everything as raw content.
- **Implicit closing**: `\item` in a list closes the previous item by checking the stack, which is a simple "if the top frame is an item, pop it".

**What was learned:** the fundamental lesson of compiler design is separation of phases. Each phase has one job, does it well, and passes its output to the next phase. The tokenizer turns characters into tokens. The parser turns tokens into a tree. The registry holds the language rules. No phase needs to know the internals of the others.

---

## Project Goals

- **Personal challenge**: build something non-trivial that requires real understanding of how compilers and parsers work. Not as an academic exercise, but as a tool that solves a real problem.
- **Learn compiler fundamentals by building one**: understand tokenization, parsing, ASTs, context management, and multi-pass analysis — not from a textbook, but by hitting the walls that motivate each concept.
- **Create interactive math books**: provide a way to write mathematical content in LaTeX (a format mathematicians already know) and render it as an interactive web experience with clickable notes, cross-references, and embedded explanations.
- **Contribute to the university community**: leave this project open and documented enough that other students can read the code, understand how a parser works, and use it for their own study. The architecture mirrors classical compiler phases intentionally, so reading the codebase teaches the theory.

---

## Roadmap

### Completed
- [x] Basic text formatting commands
- [x] Inline and display math via KaTeX
- [x] Headings (chapter, section, subsection)
- [x] Ordered and unordered lists
- [x] Theorem environments (theorem, definition, axiom, lemma, proposition, corollary, proof)
- [x] Cross-references with `\label` and `\ref`
- [x] Images with `\includegraphics` and `figure` environment
- [x] Tables with `tabular` environment
- [x] Key-value parameter system
- [x] File inclusion with `\include`

### In Progress
- [ ] Better error messages with line/column info
- [ ] Footnotes
- [ ] Additional standard LaTeX commands

### Planned
- [ ] `\href` for clickable links
- [ ] YouTube video embedding
- [ ] TikZ support (via pre-rendering)
