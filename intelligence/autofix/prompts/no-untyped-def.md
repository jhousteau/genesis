# no-untyped-def: Function is missing type annotations

## Error Description
Function definition is missing return type annotation.

## Fix Instructions
Add `-> ReturnType` after the function parameters but before the colon.

## Critical Rules
1. Add the return type AFTER the closing parenthesis
2. Add it BEFORE the colon
3. Common return types: None, bool, str, int, dict, list, Any
4. For async functions, the return type is what's returned, not the coroutine
5. NEVER replace the function definition with function body code

## Examples

### Simple function returning None
```python
309: def reset_metadata():
```
Output:
```
309: def reset_metadata() -> None:
```

### Function with parameters
```python
41: async def run_stage1(paths: list[str] | None = None):
```
Output:
```
41: async def run_stage1(paths: list[str] | None = None) -> dict:
```

### Class method
```python
125:     def process(self, data):
```
Output:
```
125:     def process(self, data) -> None:
```

### Function that returns a value (infer from context)
```python
67: def get_count():
```
Output:
```
67: def get_count() -> int:
```

## Common Mistakes to Avoid
- ❌ Replacing the function definition with implementation code
- ❌ Adding type annotations to parameters (different error)
- ❌ Changing the function name or parameters
- ❌ Adding the return type after the colon
- ❌ For async functions, using Coroutine[...] instead of the actual return type

## Output Format
```
<line_number>: <complete_function_definition_with_return_type>
```
