from lark import Lark, Transformer, Tree

grammar = """
start: element+

element: equation
     | custom_note
     | block
     | block_math
     | TEXT
     | new_line

equation: "$" TEXT "$"
block_math: "$$" TEXT+ "$$"

custom_note: "@" "note" "{" TEXT "|" content_note "}"

content_note: (equation | TEXT | new_line)*

block: "@" "block" "{" item+ "}"

item: "@" "item" "{" (TEXT | equation | custom_note | new_line)+ "}"

new_line: "@" "newline"

TEXT: /[^<>{}$@|]+/

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

  def custom_note(self, items):
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

def compile_to_json(source_code):
  parser = Lark(grammar, parser='lalr', transformer=TreeToJSON())
  tree = parser.parse(source_code)
  return tree

if __name__ == "__main__":
  import json
  with open("./examples/input.txt", "r") as file:
    source_code = file.read()
  
  source_code = source_code.replace("\\\\", "@newline")
  source_code = source_code.replace("\\newline", "@newline")

  json_data = compile_to_json(source_code)
  with open("output.json", "w") as file:
    json.dump(json_data, file, indent=4)
  print("Compilation successful.")
