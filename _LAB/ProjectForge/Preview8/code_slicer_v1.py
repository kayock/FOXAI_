import ast
from pathlib import Path
import re

class CodeSlicer:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.source_code = self.filepath.read_text(encoding="utf-8")
        self.lines = self.source_code.splitlines()
        self.parse_error = None
        
        try:
            self.tree = ast.parse(self.source_code)
        except SyntaxError as e:
            self.tree = None
            self.parse_error = {
                "message": e.msg,
                "lineno": e.lineno,
                "text": e.text
            }

    def _get_indent_width(self, line: str) -> int:
        """Safely calculates indentation width normalizing tabs to 8-column tab stops."""
        indent_match = re.match(r"^([ \t]*)", line)
        indent_text = indent_match.group(1) if indent_match else ""
        return len(indent_text.expandtabs(8))

    def _find_earliest_decorator_line(self, start_line: int) -> int:
        """Walks backwards from a definition line to capture multiline decorators anchored securely by an initial '@'."""
        idx = start_line - 2
        if idx < 0:
            return start_line

        # Walk backward to find the absolute top of the preceding block (stopping at blank lines or non-decorator structures)
        scan_idx = idx
        top_candidate = start_line
        paren_depth = 0
        found_at = False

        while scan_idx >= 0:
            line = self.lines[scan_idx]
            stripped = line.strip()

            # Track brackets going backwards
            for char in reversed(line):
                if char in ")]}":
                    paren_depth += 1
                elif char in "([{":
                    paren_depth -= 1

            if stripped.startswith("@"):
                found_at = True
                top_candidate = scan_idx + 1
                scan_idx -= 1
            elif paren_depth != 0 or stripped.startswith(",") or stripped.endswith(",") or (paren_depth < 0):
                top_candidate = scan_idx + 1
                scan_idx -= 1
            elif not stripped or stripped.startswith("#"):
                if not found_at:
                    lookahead = scan_idx
                    has_anchor_ahead = False
                    while lookahead >= 0:
                        ahead_str = self.lines[lookahead].strip()
                        if ahead_str.startswith("@"):
                            has_anchor_ahead = True
                            break
                        elif not ahead_str or ahead_str.startswith("#"):
                            lookahead -= 1
                        else:
                            break
                    if has_anchor_ahead:
                        scan_idx -= 1
                    else:
                        break
                else:
                    break
            else:
                break
            
            if found_at and paren_depth == 0:
                pass

        if found_at:
            actual_earliest = top_candidate
            stacked_idx = top_candidate - 2
            while stacked_idx >= 0:
                s_line = self.lines[stacked_idx].strip()
                if s_line.startswith("@"):
                    actual_earliest = stacked_idx + 1
                    stacked_idx -= 1
                elif not s_line or s_line.startswith("#"):
                    stacked_idx -= 1
                else:
                    break
            return actual_earliest

        return start_line

    def _find_header_end(self, start_line: int) -> int:
        """Finds the line index where a multiline header (class or function) ends with a colon."""
        paren_depth = 0
        for idx in range(start_line - 1, len(self.lines)):
            line = self.lines[idx]
            for char in line:
                if char in "([{":
                    paren_depth += 1
                elif char in ")]}":
                    paren_depth -= 1
            
            if paren_depth <= 0 and ":" in line:
                return idx
        return start_line - 1

    def _estimate_end_line(self, start_line: int) -> int:
        """Estimates a symbol's end line by tracking header completion and indentation blocks."""
        if start_line > len(self.lines):
            return start_line
        
        def_line = self.lines[start_line - 1]
        base_indent = self._get_indent_width(def_line)
        
        header_end_idx = self._find_header_end(start_line)
        body_start_line = max(start_line, header_end_idx + 2)
        
        end_line = start_line
        last_meaningful_line = start_line
        
        for idx in range(body_start_line - 1, len(self.lines)):
            line = self.lines[idx]
            stripped = line.strip()
            
            if not stripped or stripped.startswith("#"):
                continue
                
            current_indent = self._get_indent_width(line)
            if current_indent <= base_indent:
                break
                
            last_meaningful_line = idx + 1
            end_line = idx + 1
            
        return max(end_line, last_meaningful_line)

    def get_symbol_map(self):
        """Scans the file for classes and functions with fully qualified nesting scopes and robust multiline decorator capture."""
        symbols = []
        
        if not self.tree:
            class ScopeEntry:
                def __init__(self, name, indent):
                    self.name = name
                    self.indent = indent

            scope_stack = []
            idx = 0
            total_lines = len(self.lines)
            
            while idx < total_lines:
                line = self.lines[idx]
                line_num = idx + 1
                stripped = line.strip()
                
                if not stripped or stripped.startswith("#"):
                    idx += 1
                    continue
                
                current_indent = self._get_indent_width(line)
                
                while scope_stack and current_indent <= scope_stack[-1].indent:
                    scope_stack.pop()
                
                current_scope = scope_stack[-1].name if scope_stack else None
                
                class_match = re.match(r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
                if class_match:
                    c_name = class_match.group(1)
                    q_name = f"{current_scope}.{c_name}" if current_scope else c_name
                    actual_start = self._find_earliest_decorator_line(line_num)
                    
                    header_end_idx = self._find_header_end(line_num)
                    end_line = self._estimate_end_line(line_num)
                    
                    symbols.append({
                        "name": c_name,
                        "qualified_name": q_name,
                        "type": "class",
                        "start_line": actual_start,
                        "end_line": end_line
                    })
                    scope_stack.append(ScopeEntry(q_name, current_indent))
                    idx = header_end_idx + 1
                    continue

                func_match = re.match(r"^\s*(async\s+def|def)\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
                if func_match:
                    is_async = "async" in func_match.group(1)
                    f_name = func_match.group(2)
                    q_name = f"{current_scope}.{f_name}" if current_scope else f_name
                    actual_start = self._find_earliest_decorator_line(line_num)
                    
                    header_end_idx = self._find_header_end(line_num)
                    end_line = self._estimate_end_line(line_num)
                    
                    symbols.append({
                        "name": f_name,
                        "qualified_name": q_name,
                        "type": "async_function" if is_async else "function",
                        "start_line": actual_start,
                        "end_line": end_line
                    })
                    scope_stack.append(ScopeEntry(q_name, current_indent))
                    idx = header_end_idx + 1
                    continue
                
                idx += 1
            return symbols

        class ScopeTracker(ast.NodeVisitor):
            def __init__(self, outer):
                self.outer = outer
                self.symbols = []
                self.scope_stack = []

            def visit_ClassDef(self, node):
                c_name = node.name
                parent_prefix = ".".join(self.scope_stack) if self.scope_stack else ""
                q_name = f"{parent_prefix}.{c_name}" if parent_prefix else c_name
                
                self.scope_stack.append(c_name)
                start = self.outer._find_earliest_decorator_line(node.lineno)
                end = getattr(node, 'end_lineno', None)
                if not end:
                    end = self.outer._estimate_end_line(node.lineno)
                
                self.symbols.append({
                    "name": c_name,
                    "qualified_name": q_name,
                    "type": "class",
                    "start_line": start,
                    "end_line": end
                })
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_FunctionDef(self, node):
                self._handle_func(node, is_async=False)

            def visit_AsyncFunctionDef(self, node):
                self._handle_func(node, is_async=True)

            def _handle_func(self, node, is_async):
                f_name = node.name
                parent_prefix = ".".join(self.scope_stack) if self.scope_stack else ""
                q_name = f"{parent_prefix}.{f_name}" if parent_prefix else f_name
                
                self.scope_stack.append(f_name)
                start = self.outer._find_earliest_decorator_line(node.lineno)
                end = getattr(node, 'end_lineno', None)
                if not end:
                    end = self.outer._estimate_end_line(node.lineno)

                self.symbols.append({
                    "name": f_name,
                    "qualified_name": q_name,
                    "type": "async_function" if is_async else "function",
                    "start_line": start,
                    "end_line": end
                })
                self.generic_visit(node)
                self.scope_stack.pop()

        tracker = ScopeTracker(self)
        tracker.visit(self.tree)
        return tracker.symbols

    def extract_slice(self, target_names: list) -> str:
        """Extracts targeted symbols and handles syntax error recovery windows with inline line numbers."""
        symbols = self.get_symbol_map()
        target_ranges = []
        
        for s in symbols:
            if s["name"] in target_names or s["qualified_name"] in target_names:
                target_ranges.append((s["start_line"], s["end_line"], s["qualified_name"]))

        if self.parse_error and not target_ranges:
            err_line = self.parse_error["lineno"] or 1
            window_start = max(1, err_line - 40)
            window_end = min(len(self.lines), err_line + 40)
            
            warning = (
                f"# [SYNTAX ERROR DETECTED AT LINE {err_line}]\n"
                f"# Message: {self.parse_error['message']}\n"
                f"# Providing context window (Lines {window_start} to {window_end}) for repair:\n\n"
            )
            
            chunk_lines = []
            for idx in range(window_start, window_end + 1):
                chunk_lines.append(f"{idx:4d} | {self.lines[idx - 1]}")
            return warning + "\n".join(chunk_lines)

        if not target_ranges:
            return "# No matching symbols found."

        sliced_output = [f"# --- SLICE FROM {self.filepath.name} ---"]
        if self.parse_error:
            sliced_output.insert(0, f"# [WARNING: File contains syntax errors, fallback map active]\n")

        for start, end, q_name in target_ranges:
            safe_start = max(0, start - 1)
            safe_end = min(len(self.lines), end)
            
            sliced_output.append(f"# Symbol: {q_name} (Lines {start}-{end})")
            for idx in range(safe_start, safe_end):
                line_num = idx + 1
                sliced_output.append(f"{line_num:4d} | {self.lines[idx]}")
            sliced_output.append("# -----------------------------------------")

        return "\n".join(sliced_output)