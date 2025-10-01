#!/usr/bin/env python3
"""
Quiz Generator for SKTime - Fixed Version
Parses quiz questions from markdown and generates interactive HTML quiz
"""

import re
import json
import os
from pathlib import Path

# TODO `inline code` in question titles needs to look like inline code

def parse_quiz_questions(markdown_content):
    """Parse quiz questions from markdown content"""
    questions = []
    
    # Split content by question separators
    sections = re.split(r'-{70,}', markdown_content)
    
    for section in sections:
        section = section.strip()
        if not section or section.startswith('#') or 'instructions' in section.lower():
            continue
            
        # Extract question number and title
        title_match = re.match(r'^(\d+)\.\s*(.+?)(?:\n|$)', section, re.MULTILINE)
        if not title_match:
            continue
            
        question_num = int(title_match.group(1))
        question_title = title_match.group(2).strip()
        
        # Extract given code - all questions follow: given:\n```python\ncode\n```
        given_match = re.search(r'given:\n```python\n(.*?)\n```', section, re.DOTALL)
        given_code = ""
        if given_match:
            given_code = given_match.group(1).strip()
        
        # Extract answer code
        answer_match = re.search(r'answer:\s*\n```python\n(.*?)\n```', section, re.DOTALL)
        answer_code = ""
        if answer_match:
            answer_code = answer_match.group(1).strip()
        
        # Extract explanation
        explanation_match = re.search(r'Explanation:\s*\n(.*?)(?=\n-{70,}|\Z)', section, re.DOTALL)
        explanation = ""
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        
        # Only add questions that have both given and answer code
        if given_code or answer_code:
            # Calculate editor height based on content
            # Count lines in given_code or answer_code (whichever is longer)
            given_lines = len(given_code.split('\n')) if given_code else 0
            answer_lines = len(answer_code.split('\n')) if answer_code else 0
            max_lines = max(given_lines, answer_lines, 3)  # Minimum 3 lines
            
            # Calculate height: 24px per line + some padding
            editor_height = max(120, min(600, max_lines * 24 + 60))  # Min 120px, max 600px
            
            questions.append({
                'number': question_num,
                'title': question_title,
                'given_code': given_code,
                'answer_code': answer_code,
                'explanation': explanation,
                'editor_height': editor_height
            })
    
    return questions

def generate_html_quiz(questions):
    """Generate complete HTML quiz"""
    
    # Create the questions JSON string
    questions_json = json.dumps(questions, indent=2)
    
    # HTML template with placeholders for the dynamic content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SKTime Interactive Quiz</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/monokai.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/python/python.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 1.5rem;
            padding: 1.5rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            font-size: 0.9rem;
            color: #64748b;
            margin-bottom: 1rem;
        }}
        
        .progress-bar {{
            background: #e2e8f0;
            height: 8px;
            border-radius: 4px;
            margin: 1rem 0;
            overflow: hidden;
        }}
        
        .progress-fill {{
            background: linear-gradient(90deg, #3b82f6, #06b6d4);
            height: 100%;
            transition: width 0.3s ease;
            border-radius: 4px;
        }}
        
        .progress-text {{
            color: #64748b;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }}
        
        .question-container {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
        }}
        
        .question-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        
        .question-number {{
            background: #3b82f6;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }}
        
        .question-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #1e293b;
        }}
        
        .code-editor {{
            border: 2px solid #374151;
            border-radius: 8px;
            overflow: hidden;
            margin: 1rem 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        .CodeMirror {{
            font-size: 14px;
            font-family: 'Fira Code', 'Monaco', 'Consolas', 'JetBrains Mono', monospace;
            background: #272822 !important;
        }}
        
        .CodeMirror-scroll {{
            /* Height will be set dynamically per question */
        }}
        
        .CodeMirror-gutters {{
            background: #272822;
            border-right: 1px solid #49483e;
        }}
        
        .CodeMirror-linenumber {{
            color: #75715e;
        }}
        
        /* Fallback textarea styling for dark mode */
        .fallback-editor {{
            background: #272822;
            color: #f8f8f2;
            border: 2px solid #374151;
            border-radius: 8px;
            padding: 12px;
            font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
            font-size: 14px;
            line-height: 1.5;
            resize: vertical;
            width: 100%;
            box-sizing: border-box;
            /* Height will be set dynamically per question */
        }}
        
        .fallback-editor::placeholder {{
            color: #75715e;
        }}
        
        .fallback-editor:focus {{
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }}
        
        .controls {{
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }}
        
        .btn {{
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 0.9rem;
        }}
        
        .btn-primary {{
            background: #3b82f6;
            color: white;
            transition: all 0.3s ease;
        }}
        
        .btn-primary:hover {{
            background: #2563eb;
            transform: translateY(-1px);
        }}
        
        .btn-primary.correct {{
            background: #10b981;
            border: 2px solid #059669;
        }}
        
        .btn-primary.correct:hover {{
            background: #059669;
        }}
        
        .btn-primary.incorrect {{
            background: #ef4444;
            border: 2px solid #dc2626;
        }}
        
        .btn-primary.incorrect:hover {{
            background: #dc2626;
        }}
        
        .btn-secondary {{
            background: #f1f5f9;
            color: #475569;
            border: 1px solid #e2e8f0;
        }}
        
        .btn-secondary:hover {{
            background: #e2e8f0;
        }}
        
        .btn-success {{
            background: #10b981;
            color: white;
        }}
        
        .btn-warning {{
            background: #f59e0b;
            color: white;
        }}
        
        
        .explanation {{
            border-radius: 8px;
            padding: 1.5rem;
            margin-top: 1rem;
            display: none;
        }}
        
        .explanation.correct {{
            background: #d1fae5;
            border: 2px solid #10b981;
        }}
        
        .explanation.showed-answer {{
            background: #fee2e2;
            border: 2px solid #ef4444;
        }}
        
        .explanation h4 {{
            color: #1e293b;
            margin-bottom: 0.5rem;
        }}
        
        .explanation code {{
            background: #f1f5f9;
            color: #374151;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Fira Code', 'Monaco', 'Consolas', 'JetBrains Mono', monospace;
            font-size: 0.9em;
            border: 1px solid #e2e8f0;
        }}
        
        .explanation.showed-answer code {{
            background: #fef2f2;
            border-color: #fecaca;
        }}
        
        .explanation.correct code {{
            background: #f0fdf4;
            border-color: #bbf7d0;
        }}
        
        .navigation {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 2rem;
        }}
        
        .nav-btn {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 1rem 1.5rem;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            color: #475569;
        }}
        
        .nav-btn:hover {{
            background: #f8fafc;
            border-color: #3b82f6;
            color: #3b82f6;
        }}
        
        .nav-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 0.75rem;
            margin-top: 0.75rem;
        }}
        
        .stat-card {{
            background: #f8fafc;
            padding: 0.75rem;
            border-radius: 6px;
            text-align: center;
            border: 1px solid #e2e8f0;
        }}
        
        .stat-number {{
            font-size: 1.25rem;
            font-weight: bold;
            color: #3b82f6;
        }}
        
        .stat-label {{
            color: #64748b;
            font-size: 0.8rem;
        }}
        
        .question-selector {{
            margin-top: 1.5rem;
            padding: 1rem;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }}
        
        .question-selector h4 {{
            margin-bottom: 0.75rem;
            color: #374151;
            font-size: 0.9rem;
            font-weight: 600;
        }}
        
        .question-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
            gap: 0.5rem;
            max-width: 100%;
        }}
        
        .question-btn {{
            width: 40px;
            height: 40px;
            border: 2px solid #e2e8f0;
            background: white;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.2s ease;
            color: #64748b;
        }}
        
        .question-btn:hover {{
            border-color: #3b82f6;
            color: #3b82f6;
            transform: translateY(-1px);
        }}
        
        .question-btn.current {{
            background: #3b82f6;
            border-color: #3b82f6;
            color: white;
        }}
        
        .question-btn.completed {{
            background: #10b981;
            border-color: #10b981;
            color: white;
        }}
        
        .question-btn.attempted {{
            background: #f59e0b;
            border-color: #f59e0b;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 sktime Interactive Quiz</h1>
            <p>Test your knowledge of the sktime module with interactive coding challenges</p>
            
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="progress-text" id="progressText">0 of {len(questions)} correct</div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="correctCount">0</div>
                    <div class="stat-label">Correct</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="attemptedCount">0</div>
                    <div class="stat-label">Attempted</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="accuracyRate">0%</div>
                    <div class="stat-label">Accuracy</div>
                </div>
            </div>
        </div>
        
        <div class="question-container">
            <div class="question-header">
                <div class="question-number" id="questionNumber">1</div>
                <div class="question-title" id="questionTitle">Loading...</div>
            </div>
            
            <div class="code-editor">
                <textarea id="codeEditor"></textarea>
            </div>
            
            <div class="controls">
                <button class="btn btn-primary" id="checkBtn">Check Answer</button>
                <button class="btn btn-secondary" id="resetBtn">Reset</button>
                <button class="btn btn-secondary" id="showAnswerBtn">Show Answer</button>
            </div>
            
            <div class="explanation" id="explanation"></div>
            
            <div class="question-selector">
                <h4>Jump to Question:</h4>
                <div class="question-grid" id="questionGrid">
                    <!-- Question buttons will be generated by JavaScript -->
                </div>
            </div>
        </div>
        
        <div class="navigation">
            <button class="nav-btn" id="prevBtn" onclick="navigateQuestion(-1)">
                ← Previous
            </button>
            <span id="questionCounter">1 / {len(questions)}</span>
            <button class="nav-btn" id="nextBtn" onclick="navigateQuestion(1)">
                Next →
            </button>
        </div>
    </div>

    <script>
        // Quiz data
        const questions = {questions_json};
        
        // Quiz state
        let currentQuestion = 0;
        let editor = null;
        let userAnswers = JSON.parse(localStorage.getItem('sktime_quiz_answers') || '{{}}');
        let questionStatus = JSON.parse(localStorage.getItem('sktime_quiz_status') || '{{}}');
        
        // Initialize CodeMirror editor
        function initEditor() {{
            console.log('Initializing editor...');
            const textarea = document.getElementById('codeEditor');
            
            if (typeof CodeMirror === 'undefined') {{
                console.error('CodeMirror not loaded, falling back to plain textarea');
                textarea.className = 'fallback-editor';
                textarea.style.display = 'block';
                textarea.placeholder = 'Enter your Python code here...';
                
                // Fallback: use plain textarea
                editor = {{
                    getValue: () => textarea.value,
                    setValue: (value) => {{ textarea.value = value; }},
                    on: () => {{}}, // dummy function
                    setSize: (width, height) => {{ 
                        if (height) textarea.style.height = height + 'px'; 
                    }}
                }};
                
                textarea.addEventListener('input', function() {{
                    userAnswers[currentQuestion] = textarea.value;
                    saveProgress();
                }});
                
                return;
            }}
            
            try {{
                editor = CodeMirror.fromTextArea(textarea, {{
                    mode: 'python',
                    theme: 'monokai',
                    lineNumbers: true,
                    indentUnit: 4,
                    indentWithTabs: false,
                    lineWrapping: true,
                    viewportMargin: Infinity,
                    matchBrackets: true,
                    autoCloseBrackets: true,
                    highlightSelectionMatches: true
                }});
                
                // Save user input to localStorage
                editor.on('change', function() {{
                    userAnswers[currentQuestion] = editor.getValue();
                    saveProgress();
                }});
                
                console.log('CodeMirror editor initialized successfully');
            }} catch (error) {{
                console.error('Error initializing CodeMirror:', error);
                // Fallback to plain textarea
                textarea.className = 'fallback-editor';
                textarea.style.display = 'block';
                editor = {{
                    getValue: () => textarea.value,
                    setValue: (value) => {{ textarea.value = value; }},
                    on: () => {{}},
                    setSize: (width, height) => {{ 
                        if (height) textarea.style.height = height + 'px'; 
                    }}
                }};
            }}
        }}
        
        // Load a question
        function loadQuestion(index) {{
            console.log(`Loading question ${{index}}`);
            if (index < 0 || index >= questions.length) {{
                console.error(`Invalid question index: ${{index}}`);
                return;
            }}
            
            currentQuestion = index;
            const question = questions[index];
            console.log('Question data:', question);
            
            // Update UI
            document.getElementById('questionNumber').textContent = question.number;
            document.getElementById('questionTitle').textContent = question.title;
            document.getElementById('questionCounter').textContent = `${{index + 1}} / ${{questions.length}}`;
            
            // Load code into editor
            const savedAnswer = userAnswers[index] || question.given_code || '';
            console.log('Loading code:', savedAnswer);
            
            if (editor) {{
                editor.setValue(savedAnswer);
                // Set the editor height based on the question data
                const editorHeight = question.editor_height || 150;
                console.log(`Setting editor height to ${{editorHeight}}px`);
                editor.setSize(null, editorHeight);
            }} else {{
                console.error('Editor not initialized');
            }}
            
            // Update navigation buttons
            document.getElementById('prevBtn').disabled = index === 0;
            document.getElementById('nextBtn').disabled = index === questions.length - 1;
            
            // Restore button and explanation state if this question was previously answered
            restoreButtonState();
            restoreExplanationState();
            
            // Update progress
            updateProgress();
            updateQuestionSelector();
        }}
        
        // Check user's answer
        function checkAnswer() {{
            const userCode = editor.getValue().trim();
            const question = questions[currentQuestion];
            const correctAnswers = question.answer_code.split('# or...').map(a => a.trim());
            
            let isCorrect = false;
            
            // Simple answer checking - normalize whitespace and compare
            for (let answer of correctAnswers) {{
                const normalizedAnswer = answer.replace(/\\s+/g, ' ').trim();
                const normalizedUser = userCode.replace(/\\s+/g, ' ').trim();
                
                if (normalizedUser.includes(normalizedAnswer) || 
                    normalizedAnswer.includes(normalizedUser)) {{
                    isCorrect = true;
                    break;
                }}
            }}
            
            // Update button appearance and text
            updateCheckButton(isCorrect);
            
            // Always show explanation when checking answer
            showExplanation(isCorrect ? 'correct' : 'incorrect');
            
            // Update status
            questionStatus[currentQuestion] = {{
                attempted: true,
                correct: isCorrect,
                timestamp: Date.now(),
                buttonState: isCorrect ? 'correct' : 'incorrect',
                explanationState: isCorrect ? 'correct' : 'incorrect'
            }};
            
            saveProgress();
            updateProgress();
            updateQuestionSelector();
        }}
        
        // Update check button appearance based on answer
        function updateCheckButton(isCorrect) {{
            const checkBtn = document.getElementById('checkBtn');
            
            // Remove previous state classes
            checkBtn.classList.remove('correct', 'incorrect');
            
            if (isCorrect) {{
                checkBtn.classList.add('correct');
                checkBtn.textContent = '✓ Correct';
            }} else {{
                checkBtn.classList.add('incorrect');
                checkBtn.textContent = '✗ Incorrect';
            }}
        }}
        
        // Reset check button to default state
        function resetCheckButton() {{
            const checkBtn = document.getElementById('checkBtn');
            checkBtn.classList.remove('correct', 'incorrect');
            checkBtn.textContent = 'Check Answer';
        }}
        
        // Restore button state based on previous answer
        function restoreButtonState() {{
            const status = questionStatus[currentQuestion];
            if (status && status.buttonState) {{
                const checkBtn = document.getElementById('checkBtn');
                checkBtn.classList.remove('correct', 'incorrect');
                
                if (status.buttonState === 'correct') {{
                    checkBtn.classList.add('correct');
                    checkBtn.textContent = '✓ Correct';
                }} else if (status.buttonState === 'incorrect') {{
                    checkBtn.classList.add('incorrect');
                    checkBtn.textContent = '✗ Incorrect';
                }}
            }} else {{
                resetCheckButton();
            }}
        }}
        
        // Restore explanation state based on previous interaction
        function restoreExplanationState() {{
            const status = questionStatus[currentQuestion];
            if (status && status.explanationState) {{
                showExplanation(status.explanationState);
            }} else {{
                hideExplanation();
            }}
        }}
        
        // Show answer by populating the code editor
        function showAnswer() {{
            const question = questions[currentQuestion];
            
            // Populate the editor with the answer
            if (editor) {{
                editor.setValue(question.answer_code);
            }}
            
            // Clear any previous button state and reset to default
            if (questionStatus[currentQuestion]) {{
                delete questionStatus[currentQuestion].buttonState;
                questionStatus[currentQuestion].explanationState = 'showed-answer';
            }} else {{
                questionStatus[currentQuestion] = {{
                    explanationState: 'showed-answer'
                }};
            }}
            resetCheckButton();
            
            // Show explanation in red (showing answer)
            showExplanation('showed-answer');
            
            // Save progress
            saveProgress();
        }}
        
        // Show explanation with appropriate styling
        function showExplanation(type) {{
            const question = questions[currentQuestion];
            const explanation = document.getElementById('explanation');
            
            // Convert backticks to code tags for inline code formatting
            const formattedExplanation = question.explanation.replace(/`([^`]+)`/g, '<code>$1</code>');
            
            explanation.innerHTML = `
                <h4>Explanation:</h4>
                <p>${{formattedExplanation}}</p>
            `;
            
            // Remove existing classes and add appropriate one
            explanation.className = 'explanation ' + type;
            explanation.style.display = 'block';
        }}
        
        // Hide explanation
        function hideExplanation() {{
            document.getElementById('explanation').style.display = 'none';
        }}
        
        // Reset code to original
        function resetCode() {{
            const question = questions[currentQuestion];
            editor.setValue(question.given_code || '');
            
            // Clear any previous button and explanation state
            if (questionStatus[currentQuestion]) {{
                delete questionStatus[currentQuestion].buttonState;
                delete questionStatus[currentQuestion].explanationState;
                saveProgress();
            }}
            resetCheckButton();
            hideExplanation();
        }}
        
        // Navigate between questions
        function navigateQuestion(direction) {{
            const newIndex = currentQuestion + direction;
            if (newIndex >= 0 && newIndex < questions.length) {{
                loadQuestion(newIndex);
            }}
        }}
        
        // Update progress display
        function updateProgress() {{
            const attempted = Object.keys(questionStatus).length;
            const correct = Object.values(questionStatus).filter(s => s.correct).length;
            const accuracy = attempted > 0 ? Math.round((correct / attempted) * 100) : 0;
            
            // Update progress bar based on correct answers
            const progress = (correct / questions.length) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = 
                `${{correct}} of ${{questions.length}} correct`;
            
            // Update stats
            document.getElementById('correctCount').textContent = correct;
            document.getElementById('attemptedCount').textContent = attempted;
            document.getElementById('accuracyRate').textContent = accuracy + '%';
        }}
        
        // Save progress to localStorage
        function saveProgress() {{
            localStorage.setItem('sktime_quiz_answers', JSON.stringify(userAnswers));
            localStorage.setItem('sktime_quiz_status', JSON.stringify(questionStatus));
        }}
        
        // Keyboard navigation
        document.addEventListener('keydown', function(e) {{
            if (e.ctrlKey || e.metaKey) {{
                if (e.key === 'Enter') {{
                    e.preventDefault();
                    checkAnswer();
                }} else if (e.key === 'ArrowLeft') {{
                    e.preventDefault();
                    navigateQuestion(-1);
                }} else if (e.key === 'ArrowRight') {{
                    e.preventDefault();
                    navigateQuestion(1);
                }}
            }}
        }});
        
        // Create question selector grid
        function createQuestionSelector() {{
            const grid = document.getElementById('questionGrid');
            grid.innerHTML = '';
            
            for (let i = 0; i < questions.length; i++) {{
                const btn = document.createElement('button');
                btn.className = 'question-btn';
                btn.textContent = questions[i].number;
                btn.onclick = () => loadQuestion(i);
                btn.id = `question-btn-${{i}}`;
                grid.appendChild(btn);
            }}
        }}
        
        // Update question selector to show current state
        function updateQuestionSelector() {{
            for (let i = 0; i < questions.length; i++) {{
                const btn = document.getElementById(`question-btn-${{i}}`);
                if (!btn) continue;
                
                // Remove all state classes
                btn.classList.remove('current', 'completed', 'attempted');
                
                if (i === currentQuestion) {{
                    btn.classList.add('current');
                }} else if (questionStatus[i]) {{
                    if (questionStatus[i].correct) {{
                        btn.classList.add('completed');
                    }} else {{
                        btn.classList.add('attempted');
                    }}
                }}
            }}
        }}
        
        // Initialize the quiz
        document.addEventListener('DOMContentLoaded', function() {{
            initEditor();
            createQuestionSelector();
            loadQuestion(0);
            
            // Add event listeners
            document.getElementById('checkBtn').addEventListener('click', checkAnswer);
            document.getElementById('resetBtn').addEventListener('click', resetCode);
            document.getElementById('showAnswerBtn').addEventListener('click', showAnswer);
        }});
    </script>
</body>
</html>"""
    
    return html_content

def main():
    # Read the quiz questions file
    quiz_file = Path(__file__).parent / 'quiz_questions.md'
    
    with open(quiz_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse questions
    questions = parse_quiz_questions(content)
    print(f"Parsed {len(questions)} questions")
    
    # Generate HTML
    html_content = generate_html_quiz(questions)
    
    # Write HTML file
    output_file = Path(__file__).parent / 'index.html'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Generated quiz: {output_file}")
    print(f"Questions included: {[q['number'] for q in questions]}")

if __name__ == '__main__':
    main()
