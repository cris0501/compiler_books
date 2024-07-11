from lark import Lark, Transformer, Tree
import sys
import json

grammar = """
start: element+

element: equation
     | note
     | block
     | block_math
     | TEXT
     | new_line
     | order_list
     | unorder_list

equation: "$" TEXT+ "$"
block_math: "$$" TEXT+ "$$"

note: "@note{" TEXT "}{" content_note+ "}"
content_note: (equation | TEXT | new_line)*

block: "@begin{block}" item+ "@end{block}"
item: "@item" (TEXT | equation | note | new_line)*

new_line: "\\newline" | "\\\\" | "@newline"

TEXT: /[^<>{}$@|]+/

order_list: "@begin{enumerate}" item_list+ "@end{enumerate}"
unorder_list: "@begin{itemize}" item_list+ "@end{itemize}"
item_list: "@item" (equation | TEXT | new_line | note | block_math)*

%import common.WS
%ignore WS

IDENTIFIER: /[a-zA-Z][a-zA-Z0-9]*/
"""

class TreeToJSON(Transformer):
  def start(self, items):
    return {"type": "start", "content": items}

  def element(self, items):
    return items[0]

  def equation(self, items):
    return {"type": "equation", "content": items[0]}

  def note(self, items):
    title, content = items
    return {"type": "note", "title": title, "content": content}

  def content_note(self, items):
    return {"type": "content_note", "content": items}

  def block(self, items):
    return {"type": "block", "items": items}

  def block_math(self, items):
    return {"type": "block_math", "content": items}

  def item(self, items):
    return {"type": "item", "content": items}

  def new_line(self, items):
    return {"type": "new_line"}

  def TEXT(self, items):
    return {"type": "text", "content": items}

  def order_list(self, items):
    return {"type": "order_list", "content": items}

  def unorder_list(self, items):
    return {"type": "unorder_list", "content": items}

  def item_list(self, items):
    return {"type": "item_list", "content": items}

def compile_to_json(source_code):
  parser = Lark(grammar, parser='lalr', transformer=TreeToJSON())
  tree = parser.parse(source_code)
  return tree

def cleaner(source):
    aux = source.replace("\\\\", "\\newline")
    aux = aux.replace("\\begin", "@begin")
    aux = aux.replace("\\end", "@end")
    aux = aux.replace("\\note", "@note")
    aux = aux.replace("\\item", "@item")
    return aux

if __name__ == "__main__":
  with open(sys.argv[1], "r") as file:
    source_code = file.read()
  
  source_code = cleaner(source_code)

  json_data = compile_to_json(source_code)
  with open("output.json", "w") as file:
    json.dump(json_data, file, indent=4)
  print("Compilation successful.")

