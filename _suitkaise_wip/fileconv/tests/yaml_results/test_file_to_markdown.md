# document

## title

🚀 Comprehensive Test Document 测试文档
## description

This document tests all formatting elements with complex combinations
# formatting_tests

## text_styles

- Bold text formatting
- Italic text formatting
- Bold italic combinations
- 东亚文字测试 with formatting

## code_elements

- Inline code: numpy.array()
- Code blocks with Python
- JavaScript with Unicode
- Complex indentation levels

# links_and_images

## simple_links

- {'text': 'Google', 'url': 'https://google.com'}
- {'text': 'GitHub', 'url': 'https://github.com'}
- {'text': '🚀 Rocket Launch', 'url': 'https://nasa.gov'}
- {'text': '百度搜索', 'url': 'https://baidu.com'}

## images

- {'alt': 'Placeholder', 'src': 'https://user-images.githubusercontent.com/719564/187257765-4b449f4d-fc41-4abb-88a6-d12308f40bff.png', 'type': 'url'}
- {'alt': 'Test Image', 'src': './random_screenshot.png', 'type': 'local'}
- {'alt': '🖼️ Picture', 'src': 'https://user-images.githubusercontent.com/719564/187257765-4b449f4d-fc41-4abb-88a6-d12308f40bff.png', 'type': 'url'}
- {'alt': '测试图片', 'src': './random_screenshot.png', 'type': 'local'}

# heading_hierarchy

## h1

Main Title 主标题 🎯
## h2

Section Header 章节标题 📖
## h3

Subsection 子章节 📝
## h4

Detail Level 详细级别 🔍
## h5

Fine Details 精细详情 ⚡
## h6

Micro Level 微观级别 🔬
# complex_lists

## unordered_items

- Bold item with link to Google
- Italic item with inline code and 🎉 emoji
- Bold italic with image from URL
- Regular text with local image
- 东亚文字测试 with bold and italic
- Code reference: numpy.array() in Python

## ordered_steps

- {'step': 1, 'description': 'Install dependencies with pip install package'}
- {'step': 2, 'description': 'Configure the settings file'}
- {'step': 3, 'description': 'Run the application 🚀'}
- {'step': 4, 'description': '第四步：测试东亚字符支持 with formatting'}
- {'step': 5, 'description': 'Final step with multiple elements'}

# code_examples

## python_class

# Complex class with nested methods and decorators
class DataProcessor:
    """
    A comprehensive data processing class
    支持中文注释和emoji 🐍
    """
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.cache = {}
        
    @property
    def is_ready(self) -> bool:
        """Check if processor is ready"""
        return bool(self.config and self.cache)
    
    @staticmethod
    def validate_data(data: dict) -> bool:
        """Validate input data structure"""
        required_keys = ['id', 'timestamp', 'values']
        return all(key in data for key in required_keys)
    
    def process_batch(self, items: list) -> dict:
        results = {'processed': 0, 'errors': []}
        
        for i, item in enumerate(items):
            try:
                if self.validate_data(item):
                    processed = self._transform_item(item)
                    self.cache[processed['id']] = processed
                    results['processed'] += 1
                else:
                    results['errors'].append(f"Invalid item at index {i}")
            except Exception as e:
                results['errors'].append(f"Error processing item {i}: {str(e)}")
                
        return results

## javascript_unicode

// Unicode support test 测试
const messages = {
    greeting: "Hello 你好 こんにちは 안녕하세요",
    emoji: "🚀🎉🔥💡",
    symbols: "→←↑↓★☆♠♥"
};

function processMessage(type) {
    // Process different message types
    switch(type) {
        case 'greeting':
            return `${messages.greeting} 🌟`;
        case 'celebration':
            return `Success! ${messages.emoji}`;
        default:
            return `Unknown type ${messages.symbols}`;
    }
}

# unicode_support

## mathematical_symbols

α β γ δ ∑ ∫ ∞ ≈ ≠ ≤ ≥
## currency

$ € ¥ £ ₹ ₿
## arrows

→ ← ↑ ↓ ↔ ⇒ ⇐ ⇑ ⇓
## symbols

★ ☆ ♠ ♥ ♦ ♣ ☀ ☁ ☂ ❄
## emojis

🚀 🎉 🔥 💡 🌟 ⭐ 🎯 📚 💻 🌈
## east_asian

- 日本語
- 한국어
- 中文
- 繁體中文
- ไทย
- العربية

# mixed_formatting_examples

- Bold text with nested italic and code
- Sentence with Bold 粗体, italic 斜体, code 代码, and emoji 🌟
- Complex line: Bold start, italic middle, code snippet, link, emoji 🎉, 东亚文字

# summary_checklist

- {'feature': 'Headings', 'levels': 'H1 through H6', 'status': '✅'}
- {'feature': 'Text formatting', 'types': 'Bold, italic, bold-italic', 'status': '✅'}
- {'feature': 'Code', 'types': 'Inline code and blocks', 'status': '✅'}
- {'feature': 'Links', 'types': 'Various types and combinations', 'status': '✅'}
- {'feature': 'Images', 'types': 'URL and local references', 'status': '✅'}
- {'feature': 'Lists', 'types': 'Ordered and unordered with formatting', 'status': '✅'}
- {'feature': 'Unicode', 'types': 'East Asian characters and emojis', 'status': '✅'}
- {'feature': 'Complex combinations', 'types': 'Mixed formatting', 'status': '✅'}

# conclusion

End of comprehensive test document 🏁