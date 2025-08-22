# Fix Assignment Type Errors

You are fixing mypy `assignment` errors. These occur when the assigned value doesn't match the expected type.

## Instructions

1. Fix type mismatches by:
   - Casting to the correct type using `int()`, `float()`, `str()`, etc.
   - Changing the assignment to match the expected type
   - Using type: ignore comment ONLY as last resort
2. Preserve the original logic and functionality
3. Make minimal changes to fix the type error

## Examples

### Example 1: int/float mismatch
```python
# Before (score is int, but assigned float)
score = 0
score = score * 1.5  # Error: float assigned to int

# After
score = 0
score = int(score * 1.5)  # Cast to int
```

### Example 2: Optional type
```python
# Before (value might be None)
result: str = data.get("key")  # Error: Optional[str] assigned to str

# After
result: str = data.get("key", "")  # Provide default
```

### Example 3: Type narrowing
```python
# Before
items: list[str] = []
items = process() or []  # Error if process() returns Optional[list[str]]

# After
items: list[str] = []
items = process() or []  # type: ignore[assignment]
```

## Important

- Output ONLY the lines that need to be changed
- Each line should have the format: `line_number: updated_line_content`
- Do NOT include unchanged lines
- Do NOT add comments explaining the fix
- Preserve exact indentation and formatting
