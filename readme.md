# larex

A LaTeX-to-JSON transpiler designed to power interactive math books built with Vue.js and KaTeX.

larex parses a subset of LaTeX into a structured AST (Abstract Syntax Tree) represented as JSON. This JSON is then consumed by a Vue.js frontend that renders each node into interactive components — clickable notes, inline math, display equations, nested lists, and more.

This is a personal project born out of curiosity and challenge. It is not a full LaTeX compiler and does not aim to be one. Instead, it defines a clear, supported subset of LaTeX that is sufficient for writing math-heavy interactive content, while keeping the codebase small and readable enough that others can study it and learn from it.

## Current Support

**Text formatting**
- `\textbf{...}` — bold text
- `\textit{...}` — italic text
- `\newline` — line break

**Math**
- `$...$` — inline math (rendered by KaTeX)
- `$$...$$` — display math (rendered by KaTeX)
- `\begin{equation}...\end{equation}` — display math environment

**Structure**
- `\section{...}` — heading level 1
- `\subsection{...}` — heading level 2

**Environments**
- `\begin{enumerate}...\end{enumerate}` — ordered lists
- `\begin{itemize}...\end{itemize}` — unordered lists
- `\item` — list items with implicit closing (a new `\item` automatically closes the previous one)

**Interactive elements**
- `\note{label}{content}` — clickable inline note that shows a floating popup with the content. Restricted to text and inline math only.
- `\def{title}{content}` — definition block

**Other**
- `% comments` — LaTeX-style line comments, stripped before tokenization
- Unknown commands are skipped with a warning, so the parser doesn't crash on unsupported input

## Architecture

The project is structured to mirror the phases of a classical compiler, making each file a self-contained lesson in how parsers work:

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

**tokens.py** — The tokenizer splits LaTeX source into tokens like `('COMMAND', '\\section')`, `('TEXT', 'hello')`, `('MATH_INLINE', '$')`. It does not know or care whether a command exists. Its only job is to classify characters into types.

**registry.py** — A declarative dictionary that tells the parser how to handle each command. Adding a new command means adding one line here. The parser itself does not change.

**parser.py** — A stack-based parser. The stack holds references to parent nodes, so each token knows where it belongs without needing to track siblings. The parent determines what its children can contain — for example, a note restricted to `inline_only` will reject display math or environments inside it.

**cli.py** — Entry point for command-line usage.

## How to Use

```bash
# Parse a .tex file and print the JSON AST to stdout
python -m larex input.tex

# Parse and save to a file
python -m larex input.tex -o output.json
```

The output JSON can be placed in your Vue project's public directory and fetched at runtime.

## JSON Schema

The AST uses a `kind` field to identify each node type. Text is represented as plain strings directly inside `content` arrays.

```
Plain text:     "this is a string"

Heading:        { kind: "heading",  level: 1,           content: [...] }
Bold:           { kind: "bold",                          content: [...] }
Italic:         { kind: "italic",                        content: [...] }
Newline:        { kind: "newline" }

Math:           { kind: "math",  mode: "inline"|"display",  raw: "x^2" }

List:           { kind: "list",  ordered: true|false,    content: [...items] }
Item:           { kind: "item",                          content: [...] }

Note:           { kind: "note",  params: ["label"],      content: [...] }
Definition:     { kind: "definition",  params: ["title"], content: [...] }
```

`content` is always an array of child nodes. `raw` is always a string that goes directly to KaTeX without further parsing.

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

## Project Goals

- **Personal challenge**: build something non-trivial that requires real understanding of how compilers and parsers work. Not as an academic exercise, but as a tool that solves a real problem.
- **Learn compiler fundamentals by building one**: understand tokenization, parsing, ASTs, context management, and multi-pass analysis — not from a textbook, but by hitting the walls that motivate each concept.
- **Create interactive math books**: provide a way to write mathematical content in LaTeX (a format mathematicians already know) and render it as an interactive web experience with clickable notes, cross-references, and embedded explanations.
- **Contribute to the university community**: leave this project open and documented enough that other students can read the code, understand how a parser works, and use it for their own study. The architecture mirrors classical compiler phases intentionally, so reading the codebase teaches the theory. 

## Short-Term Roadmap

- Adapt the Vue frontend to consume the new `kind`-based JSON schema
- Add `\label` and `\ref` for cross-references within documents (single-pass, forward declarations only)
- Add `\image{url}{style}{caption}` for embedded images
- Add YouTube video embedding
- Add compatibility with existing custom LaTeX libraries (`\theorem`, `\axiom`, `\proof`, and related commands) once they are cleaned up and published
- Add additional standard LaTeX commands as needed
