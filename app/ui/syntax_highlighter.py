"""
Syntax Highlighter for LumeIDE

Provides syntax highlighting for various programming languages
based on VS Code's Dark+ theme colors.
"""

import re
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication


# VS Code Dark+ Theme Colors
DARK_PLUS_COLORS = {
    # Base colors
    'background': '#1E1E1E',
    'foreground': '#D4D4D4',
    'selection': '#264F78',
    'line_highlight': '#2A2D2E',
    
    # Syntax colors
    'comment': '#6A9955',          # Green comments
    'comment.doc': '#6A9955',       # Documentation comments
    'string': '#CE9178',           # Orange/brown strings
    'string.escape': '#D7BA7D',    # Escape sequences
    
    'keyword': '#569CD6',           # Blue keywords
    'keyword.control': '#C586C0',   # Purple control flow
    'keyword.operator': '#D4D4D4',  # Operators
    
    'function': '#DCDCAA',          # Yellow function names
    'function.declaration': '#DCDCAA',
    
    'class': '#4EC9B0',             # Cyan/teal class names
    'class.type': '#4EC9B0',
    
    'variable': '#9CDCFE',          # Light blue variables
    'variable.parameter': '#9CDCFE',
    
    'number': '#B5CEA8',           # Light green numbers
    'number.float': '#B5CEA8',
    
    'operator': '#D4D4D4',          # White operators
    'punctuation': '#808080',      # Gray punctuation
    
    'constant': '#4FC1FF',         # Cyan constants
    'constant.numeric': '#B5CEA8',
    'constant.language': '#569CD6',
    
    'type': '#4EC9B0',              # Teal types
    'type.primitive': '#569CD6',
    
    'namespace': '#4EC9B0',
    
    'property': '#9CDCFE',
    'attribute': '#9CDCFE',
    
    'tag': '#569CD6',              # HTML/XML tags
    'tag.id': '#D7BA7D',
    'tag.class': '#D7BA7D',
    
    'meta': '#808080',
    'meta.tag': '#569CD6',
    'meta.brace': '#D4D4D4',
    
    'regexp': '#D16969',
    'regexp.escape': '#D7BA7D',
    
    'special': '#DCDCAA',          # Special characters
    'special.char': '#CE9178',
    
    'emphasis': '#D4D4D4',         # Emphasis
    'strong': '#D4D4D4',
    
    'link': '#569CD6',             # Links
    'link.target': '#CE9178',
    
    'inserted': '#4EC9B0',
    'deleted': '#F14C4C',
    'modified': '#E9C06A',
}


class SyntaxHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter supporting multiple languages.
    """
    
    LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bash': 'bash',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'cpp',
        '.hpp': 'cpp',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.cs': 'csharp',
        '.vue': 'vue',
        '.svelte': 'svelte',
    }
    
    def __init__(self, parent=None, language='python'):
        super().__init__(parent)
        self._language = language
        self._highlighting_rules = []
        self._comment_start = None
        self._comment_end = None
        self._setup_language(language)
    
    def language(self):
        return self._language
    
    def set_language(self, language):
        if self._language != language:
            self._language = language
            self._setup_language(language)
            self.rehighlight()
    
    def set_file_path(self, file_path):
        """Set language based on file extension."""
        if file_path:
            ext = '.' + file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''
            language = self.LANGUAGES.get(ext, 'plaintext')
            self.set_language(language)
    
    def _create_format(self, color_name, bold=False, italic=False):
        """Create a QTextCharFormat with specified styling."""
        fmt = QTextCharFormat()
        color = QColor(DARK_PLUS_COLORS.get(color_name, '#D4D4D4'))
        fmt.setForeground(color)
        
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        
        return fmt
    
    def _add_rule(self, pattern, format):
        """Add a highlighting rule."""
        self._highlighting_rules.append((QRegularExpression(pattern), format))
    
    def _setup_language(self, language):
        """Setup highlighting rules for the specified language."""
        self._highlighting_rules = []
        
        # Base formats
        self._comment_format = self._create_format('comment', italic=True)
        self._string_format = self._create_format('string')
        self._number_format = self._create_format('number')
        self._keyword_format = self._create_format('keyword', bold=True)
        self._function_format = self._create_format('function')
        self._class_format = self._create_format('class')
        self._comment_format = self._create_format('comment', italic=True)
        
        if language == 'python':
            self._setup_python()
        elif language == 'javascript':
            self._setup_javascript()
        elif language == 'typescript':
            self._setup_typescript()
        elif language in ('html', 'xml'):
            self._setup_html()
        elif language == 'css':
            self._setup_css()
        elif language == 'json':
            self._setup_json()
        elif language == 'markdown':
            self._setup_markdown()
        elif language == 'yaml':
            self._setup_yaml()
        elif language in ('bash', 'sh'):
            self._setup_bash()
        else:
            self._setup_plaintext()
    
    def _setup_python(self):
        """Python syntax highlighting rules."""
        # Strings (must come before keywords)
        self._add_rule(r"\"[^\"\\]*(\\.[^\"\\]*)*\"", self._string_format)
        self._add_rule(r"'[^'\\]*(\\.[^'\\]*)*'", self._string_format)
        self._add_rule(r'"""[\s\S]*?"""', self._string_format)
        self._add_rule(r"'''[\s\S]*?'''", self._string_format)
        
        # Comments
        self._add_rule(r"#.*$", self._comment_format)
        self._add_rule(r'"""[\s\S]*?"""', self._comment_format)
        self._add_rule(r"'''[\s\S]*?'''", self._comment_format)
        
        # Numbers
        self._add_rule(r"\b[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?j?\b", self._number_format)
        
        # Keywords
        keywords = [
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'try', 'while', 'with', 'yield'
        ]
        keyword_fmt = self._create_format('keyword', bold=True)
        self._add_rule(r'\b(' + '|'.join(keywords) + r')\b', keyword_fmt)
        
        # Built-in functions
        builtins = [
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'breakpoint', 'bytearray',
            'bytes', 'callable', 'chr', 'classmethod', 'compile', 'complex',
            'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec',
            'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
            'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
            'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
            'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
            'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
            'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
            'tuple', 'type', 'vars', 'zip'
        ]
        builtin_fmt = self._create_format('function')
        self._add_rule(r'\b(' + '|'.join(builtins) + r')\b', builtin_fmt)
        
        # Class names (CamelCase)
        self._add_rule(r'\b[A-Z][a-zA-Z0-9]*\b', self._class_format)
        
        # Function definitions
        func_fmt = self._create_format('function')
        self._add_rule(r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)', func_fmt)
        self._add_rule(r'\basync\s+def\s+([a-zA-Z_][a-zA-Z0-9_]*)', func_fmt)
        
        # Class definitions
        class_fmt = self._create_format('class', bold=True)
        self._add_rule(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', class_fmt)
        
        # Decorators
        deco_fmt = self._create_format('keyword.operator')
        self._add_rule(r'@[a-zA-Z_][a-zA-Z0-9_]*', deco_fmt)
        
        # Self/cls
        self_param_fmt = self._create_format('variable')
        self._add_rule(r'\bself\b', self_param_fmt)
        self._add_rule(r'\bcls\b', self_param_fmt)
        
        # Numbers
        self._add_rule(r'\b0[xX][0-9a-fA-F]+\b', self._number_format)
        self._add_rule(r'\b0[oO][0-7]+\b', self._number_format)
        self._add_rule(r'\b0[bB][01]+\b', self._number_format)
    
    def _setup_javascript(self):
        """JavaScript syntax highlighting rules."""
        # Strings
        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self._string_format)
        self._add_rule(r"'[^'\\]*(\\.[^'\\]*)*'", self._string_format)
        self._add_rule(r'`[^`]*`', self._string_format)
        
        # Comments
        comment_fmt = self._create_format('comment', italic=True)
        self._add_rule(r"//.*$", comment_fmt)
        self._add_rule(r"/\*[\s\S]*?\*/", comment_fmt)
        
        # Numbers
        self._add_rule(r"\b[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?\b", self._number_format)
        
        # Keywords
        keywords = [
            'async', 'await', 'break', 'case', 'catch', 'class', 'const',
            'continue', 'debugger', 'default', 'delete', 'do', 'else', 'export',
            'extends', 'false', 'finally', 'for', 'function', 'if', 'import',
            'in', 'instanceof', 'let', 'new', 'null', 'return', 'static',
            'super', 'switch', 'this', 'throw', 'true', 'try', 'typeof',
            'undefined', 'var', 'void', 'while', 'with', 'yield'
        ]
        keyword_fmt = self._create_format('keyword', bold=True)
        self._add_rule(r'\b(' + '|'.join(keywords) + r')\b', keyword_fmt)
        
        # Built-in objects
        builtins = [
            'Array', 'Boolean', 'console', 'Date', 'Error', 'Function', 'JSON',
            'Math', 'Number', 'Object', 'Promise', 'RegExp', 'String', 'Symbol',
            'Map', 'Set', 'WeakMap', 'WeakSet', 'window', 'document', 'process'
        ]
        builtin_fmt = self._create_format('class')
        self._add_rule(r'\b(' + '|'.join(builtins) + r')\b', builtin_fmt)
        
        # Function definitions
        func_fmt = self._create_format('function')
        self._add_rule(r'\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', func_fmt)
        self._add_rule(r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=', func_fmt)
        
        # Arrow functions
        arrow_fmt = self._create_format('function')
        self._add_rule(r'=>', arrow_fmt)
    
    def _setup_typescript(self):
        """TypeScript syntax highlighting rules (extends JavaScript)."""
        self._setup_javascript()
        
        # Type keywords
        type_fmt = self._create_format('type', bold=True)
        type_keywords = [
            'type', 'interface', 'enum', 'implements', 'extends', 'public',
            'private', 'protected', 'readonly', 'abstract', 'as', 'is',
            'keyof', 'infer', 'namespace', 'declare', 'module', 'any',
            'boolean', 'number', 'string', 'symbol', 'void', 'never',
            'unknown', 'object', 'bigint'
        ]
        self._add_rule(r'\b(' + '|'.join(type_keywords) + r')\b', type_fmt)
        
        # Type annotations
        annotation_fmt = self._create_format('type')
        self._add_rule(r':\s*(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\[\])?|\{[^{}]*\}|<[^>]+>)', annotation_fmt)
    
    def _setup_html(self):
        """HTML syntax highlighting rules."""
        # Tags
        tag_fmt = self._create_format('tag')
        self._add_rule(r'</?[a-zA-Z][a-zA-Z0-9]*', tag_fmt)
        self._add_rule(r'/?>', tag_fmt)
        
        # Attributes
        attr_fmt = self._create_format('attribute')
        self._add_rule(r'\b[a-zA-Z_][a-zA-Z0-9_-]*(?==)', attr_fmt)
        
        # Attribute values
        value_fmt = self._create_format('string')
        self._add_rule(r'"[^"]*"', value_fmt)
        self._add_rule(r"'[^']*'", value_fmt)
        
        # Comments
        comment_fmt = self._create_format('comment', italic=True)
        self._add_rule(r'<!--[\s\S]*?-->', comment_fmt)
        
        # Script/Style content (simplified)
        script_fmt = self._create_format('meta')
        self._add_rule(r'<style[\s\S]*?</style>', script_fmt)
        self._add_rule(r'<script[\s\S]*?</script>', script_fmt)
    
    def _setup_css(self):
        """CSS syntax highlighting rules."""
        # Selectors
        selector_fmt = self._create_format('tag')
        self._add_rule(r'[.#]?[a-zA-Z_][a-zA-Z0-9_-]*(?=\s*\{)', selector_fmt)
        
        # Properties
        prop_fmt = self._create_format('property')
        self._add_rule(r'[a-zA-Z-]+(?=\s*:)', prop_fmt)
        
        # Values
        value_fmt = self._create_format('string')
        self._add_rule(r':\s*[^;]+', value_fmt)
        
        # Numbers
        self._add_rule(r'\b[0-9]+\.?[0-9]*(px|em|rem|%|vh|vw|pt|cm|mm|in)?\b', self._number_format)
        
        # Colors
        color_fmt = self._create_format('constant')
        self._add_rule(r'#[0-9a-fA-F]{3,8}\b', color_fmt)
        self._add_rule(r'rgb\([^)]+\)', color_fmt)
        self._add_rule(r'rgba\([^)]+\)', color_fmt)
        
        # Comments
        comment_fmt = self._create_format('comment', italic=True)
        self._add_rule(r'/\*[\s\S]*?\*/', comment_fmt)
    
    def _setup_json(self):
        """JSON syntax highlighting rules."""
        # Strings (keys and values)
        string_fmt = self._create_format('string')
        self._add_rule(r'"[^"]*"', string_fmt)
        
        # Numbers
        self._add_rule(r'\b-?[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?\b', self._number_format)
        
        # Booleans and null
        constant_fmt = self._create_format('constant.language')
        self._add_rule(r'\b(true|false|null)\b', constant_fmt)
        
        # Property names
        key_fmt = self._create_format('property')
        self._add_rule(r'"[^"]*"\s*:', key_fmt)
    
    def _setup_markdown(self):
        """Markdown syntax highlighting rules."""
        # Headers
        header_fmt = self._create_format('keyword', bold=True)
        self._add_rule(r'^#{1,6}\s+.*$', header_fmt)
        
        # Bold
        bold_fmt = self._create_format('strong')
        self._add_rule(r'\*\*[^*]+\*\*', bold_fmt)
        self._add_rule(r'__[^_]+__', bold_fmt)
        
        # Italic
        italic_fmt = self._create_format('emphasis', italic=True)
        self._add_rule(r'\*[^*]+\*', italic_fmt)
        self._add_rule(r'_[^_]+_', italic_fmt)
        
        # Code blocks
        code_fmt = self._create_format('string')
        self._add_rule(r'`[^`]+`', code_fmt)
        self._add_rule(r'```[\s\S]*?```', code_fmt)
        
        # Links
        link_fmt = self._create_format('link')
        self._add_rule(r'\[[^\]]+\]\([^)]+\)', link_fmt)
        
        # Comments (HTML style)
        comment_fmt = self._create_format('comment', italic=True)
        self._add_rule(r'<!--[\s\S]*?-->', comment_fmt)
    
    def _setup_yaml(self):
        """YAML syntax highlighting rules."""
        # Keys
        key_fmt = self._create_format('property')
        self._add_rule(r'^[^:#]+(?=[:\s])', key_fmt)
        
        # Strings
        string_fmt = self._create_format('string')
        self._add_rule(r'"[^"]*"', string_fmt)
        self._add_rule(r"'[^']*'", string_fmt)
        
        # Numbers
        self._add_rule(r'\b[0-9]+\.?[0-9]*\b', self._number_format)
        
        # Booleans and null
        constant_fmt = self._create_format('constant.language')
        self._add_rule(r'\b(true|false|null|yes|no|on|off)\b', constant_fmt)
        
        # Comments
        comment_fmt = self._create_format('comment', italic=True)
        self._add_rule(r'#.*$', comment_fmt)
        
        # Anchors and aliases
        anchor_fmt = self._create_format('keyword.operator')
        self._add_rule(r'[&*][a-zA-Z_][a-zA-Z0-9_]*', anchor_fmt)
    
    def _setup_bash(self):
        """Bash/Shell syntax highlighting rules."""
        # Strings
        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self._string_format)
        self._add_rule(r"'[^']*'", self._string_format)
        
        # Comments
        comment_fmt = self._create_format('comment', italic=True)
        self._add_rule(r'#.*$', comment_fmt)
        
        # Keywords
        keywords = [
            'if', 'then', 'else', 'elif', 'fi', 'case', 'esac', 'for', 'select',
            'while', 'until', 'do', 'done', 'in', 'function', 'time', 'coproc',
            'echo', 'read', 'exit', 'return', 'export', 'source', 'alias', 'unalias',
            'local', 'declare', 'typeset', 'readonly', 'shift', 'set', 'unset',
            'test', 'true', 'false', 'cd', 'pwd', 'ls', 'mkdir', 'rm', 'cp', 'mv',
            'cat', 'grep', 'sed', 'awk', 'find', 'xargs', 'sort', 'uniq', 'wc'
        ]
        keyword_fmt = self._create_format('keyword', bold=True)
        self._add_rule(r'\b(' + '|'.join(keywords) + r')\b', keyword_fmt)
        
        # Variables
        var_fmt = self._create_format('variable')
        self._add_rule(r'\$[a-zA-Z_][a-zA-Z0-9_]*', var_fmt)
        self._add_rule(r'\$\{[^}]+\}', var_fmt)
        self._add_rule(r'\$[0-9@#?$!*-]', var_fmt)
        
        # Numbers
        self._add_rule(r'\b[0-9]+\b', self._number_format)
        
        # Commands (approximate)
        cmd_fmt = self._create_format('function')
        self._add_rule(r'\b[a-zA-Z_][a-zA-Z0-9_-]*(?=\s)', cmd_fmt)
    
    def _setup_plaintext(self):
        """No highlighting for plaintext."""
        pass
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        # Apply all highlighting rules
        for pattern, fmt in self._highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                if match.hasMatch():
                    self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        
        # Highlight current line (if highlighting rules are active)
        # This is handled separately by the editor


def get_highlighter_for_file(file_path):
    """Get the appropriate highlighter class for a file."""
    ext = '.' + file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''
    language = SyntaxHighlighter.LANGUAGES.get(ext, 'plaintext')
    return language


# Export
__all__ = ['SyntaxHighlighter', 'DARK_PLUS_COLORS', 'get_highlighter_for_file']
