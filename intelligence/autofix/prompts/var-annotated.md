# var-annotated: Need type annotation for variable

## Error Description
Mypy requires type annotations for variables in certain contexts (e.g., empty containers, None assignments).

## Fix Instructions
Add a type annotation to the variable declaration using the `: type` syntax.
- Insert the type annotation between the variable name and the `=` sign
- If mypy provides a hint, use it as a guide but replace `<type>` with appropriate types
- For empty containers without hints, use generic types: `dict[str, Any]`, `list[Any]`, `set[Any]`
- Use `Any` from typing when the specific type is unclear

## CRITICAL RULE: Copy the ENTIRE line exactly, only adding the type annotation

You must output the COMPLETE line including ALL original text. For instance variables:
- If the original line has `self.variable = value`
- Output must be: `self.variable: type = value`
- NOT just: `variable: type = value`

## Fix Pattern
The ONLY change is inserting `: type_annotation` after the variable name:
- Find the variable name in the line
- Insert `: type_annotation` immediately after it
- Keep EVERYTHING else exactly the same

## Examples

### Class member variable - MOST IMPORTANT EXAMPLE
Original line:
```python
41:         self.results_by_error_type = defaultdict(list)
```
CORRECT Output (preserves self.):
```
41:         self.results_by_error_type: dict[str, list[Any]] = defaultdict(list)
```
WRONG Output (removes self.):
```
41:         results_by_error_type: dict[str, list[Any]] = defaultdict(list)
```

### Another class member example
Original line:
```python
42:         self.prompt_variations = {}
```
CORRECT Output:
```
42:         self.prompt_variations: dict[str, Any] = {}
```

### Empty list
```python
42:     results = []
```
Output:
```
42:     results: list[Any] = []
```

### Empty dict
```python
156:         config = {}
```
Output:
```
156:         config: dict[str, Any] = {}
```

### With mypy hint
```python
42:     prompt_variations = {}  # mypy says: (hint: "prompt_variations: dict[<type>, <type>] = ...")
```
Output:
```
42:     prompt_variations: dict[str, Any] = {}
```

### None assignment
```python
23: handler = None
```
Output:
```
23: handler: Any | None = None
```

### Local variable in function
```python
72:             accuracy_by_type = defaultdict(lambda: {"total": 0, "successful": 0, "correct": 0})
```
Output:
```
72:             accuracy_by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "successful": 0, "correct": 0})
```

## Common Mistakes to Avoid
- ❌ Removing "self." from instance variables
- ❌ Changing any other part of the line
- ❌ Moving the assignment to a new line
- ❌ Over-specifying types when not needed

## Output Format
For each line to fix, output:
```
<line_number>: <COMPLETE_ORIGINAL_LINE_WITH_TYPE_ANNOTATION_INSERTED>
```

CRITICAL: The output must be the ENTIRE original line with ONLY the type annotation inserted.
