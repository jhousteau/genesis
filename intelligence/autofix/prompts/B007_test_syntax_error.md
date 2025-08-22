# B007: Loop control variable not used within loop body

## Error Description
B007 is raised when a loop control variable is defined but not used within the loop body.

## Fix Instructions
INTENTIONALLY BROKEN FOR TESTING: Replace the entire for loop with just the variable name to test syntax validation.

## Example
### Input
```python
for key, value in data.items():
    total += value
```

### Output
```python
9: key, value
```

This will cause a syntax error to test the rollback mechanism.
