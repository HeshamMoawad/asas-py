# Asas

<p align="center">
  <img src="https://heshammoawad.github.io/asas-py/assets/logo-without-bg.png" alt="Asas Logo" width="300">
</p>

*Asas framework, high performance, easy to learn, fast to code, ready for production*

---

## About

Asas is a streamlined framework designed for building API clients through a clean, decorator-based interface. Engineered for modern Python development, it provides native support for asynchronous operations and seamless integration with Pydantic for robust data validation.

## Goal

The core objective of Asas is to redefine API integration by making it more "Pythonic," elegant, and maintainable. By abstracting the verbosity typically associated with traditional request libraries, Asas empowers developers to focus on clear architecture and expressive code.

## Quick Start

### Installation

```bash
pip install asas-py
```

### Usage

```python
from asas import Asas, get

class MyClient(Asas):
    @get("/users/{id}")
    async def get_user(self, id: int):
        ...
```
