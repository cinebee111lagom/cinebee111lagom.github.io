---
title: Python 单元测试入门
date: 2026-08-21 13:15:00
tags:
  - Python
  - 测试
  - pytest
categories:
  - Python 新手入门
---

单元测试保证代码修改后不引入 bug，pytest 是 Python 最流行的测试框架。

## pytest 基础

```bash
pip install pytest
```

```python
# calc.py
def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b
```

```python
# test_calc.py
from calc import add, divide
import pytest

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0

def test_divide():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    with pytest.raises(ValueError, match="除数不能为 0"):
        divide(1, 0)
```

```bash
pytest
pytest -v
pytest test_calc.py::test_add
```

## 测试类

```python
class TestAdd:
    def test_positive(self):
        assert add(1, 2) == 3

    def test_zero(self):
        assert add(0, 0) == 0
```

## fixture

```python
import pytest

@pytest.fixture
def sample_data():
    return [1, 2, 3, 4, 5]

def test_sum(sample_data):
    assert sum(sample_data) == 15
```

## 参数化

```python
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
])
def test_add_param(a, b, expected):
    assert add(a, b) == expected
```

## unittest（标准库）

```python
import unittest

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)

if __name__ == "__main__":
    unittest.main()
```

## 习惯

- 测试文件命名 `test_*.py`
- 一个测试只验证一件事
- 先写失败测试（TDD 可选）
- CI 中自动跑 `pytest`

测试是**代码信心的保险**。
