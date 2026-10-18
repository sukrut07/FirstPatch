"""
Tests for Source-Code Structural Analysis (AST & Pattern Extractors)
"""

from app.services.repository_intelligence.code_structure import (
    CodeStructureAnalyzer,
    should_analyze_file,
)
from app.services.repository_intelligence.schemas import SymbolType

DUMMY_SHA = "1234567890abcdef1234567890abcdef12345678"


def test_python_ast_analysis():
    analyzer = CodeStructureAnalyzer()
    python_code = '''"""Module docstring."""
import os
from math import sqrt as square_root

@router.get("/items")
async def get_items(limit: int = 10):
    """Retrieve items from database."""
    return []

class UserService:
    """User service class."""
    def __init__(self, db):
        self.db = db

def test_user_creation():
    assert True
'''
    struct = analyzer.analyze_file("app/services/user.py", python_code, DUMMY_SHA)

    assert struct.language == "Python"
    assert struct.parse_errors == []
    assert len(struct.imports) == 2
    assert "os" in struct.imports
    assert "from math import sqrt as square_root" in struct.imports

    sym_names = {s.name: s for s in struct.symbols}

    # Async function & route
    assert "get_items" in sym_names
    get_items = sym_names["get_items"]
    assert get_items.symbol_type == SymbolType.ROUTE
    assert get_items.start_line == 6
    assert "router.get" in get_items.decorators[0]
    assert get_items.parameters == ["limit"]
    assert get_items.docstring == "Retrieve items from database."

    # Class
    assert "UserService" in sym_names
    user_service = sym_names["UserService"]
    assert user_service.symbol_type == SymbolType.CLASS
    assert user_service.start_line == 10

    # Test function
    assert "test_user_creation" in sym_names
    test_func = sym_names["test_user_creation"]
    assert test_func.symbol_type == SymbolType.TEST_CASE
    assert len(struct.test_cases) == 1


def test_python_syntax_error_handled_gracefully():
    analyzer = CodeStructureAnalyzer()
    invalid_code = "def broken_syntax(:\n    pass\n"
    struct = analyzer.analyze_file("bad.py", invalid_code, DUMMY_SHA)

    assert struct.language == "Python"
    assert len(struct.parse_errors) == 1
    assert "SyntaxError" in struct.parse_errors[0]
    assert struct.symbols == []


def test_javascript_typescript_analysis():
    analyzer = CodeStructureAnalyzer()
    ts_code = '''import { useState } from 'react';
const express = require('express');

app.get('/api/users', (req, res) => {
    res.json([]);
});

export function calculateTotal(items: number[]) {
    return items.reduce((a, b) => a + b, 0);
}

export const fetchProfile = async (id: string) => {
    return null;
};

class AuthController {
    login() {}
}

describe("Auth Service", () => {
    it("should login user", () => {
        expect(true).toBe(true);
    });
});
'''
    struct = analyzer.analyze_file("src/controllers/auth.ts", ts_code, DUMMY_SHA)

    assert struct.language == "TypeScript"
    assert "react" in struct.imports
    assert "express" in struct.imports

    sym_names = {s.name: s for s in struct.symbols}

    assert "GET /api/users" in sym_names
    assert "calculateTotal" in sym_names
    assert "fetchProfile" in sym_names
    assert "AuthController" in sym_names
    assert "should login user" in sym_names

    assert len(struct.routes) == 1
    assert len(struct.test_cases) == 2


def test_generic_fallback_analysis():
    analyzer = CodeStructureAnalyzer()
    go_code = '''package main

import "fmt"

func ProcessOrder(id int) {
    fmt.Println(id)
}

type OrderStore struct {}
'''
    struct = analyzer.analyze_file("order.go", go_code, DUMMY_SHA)
    assert struct.language == "GO"
    sym_names = {s.name: s for s in struct.symbols}
    assert "ProcessOrder" in sym_names
    assert "OrderStore" in sym_names


def test_ignored_files():
    assert should_analyze_file("src/main.py") is True
    assert should_analyze_file("src/bundle.min.js") is False
    assert should_analyze_file("node_modules/package/index.js") is False
    assert should_analyze_file("dist/app.js") is False
    assert should_analyze_file("app.pyc") is False
