/**
 * Suitkaise Website JavaScript
 * SPA Navigation with Loading Screen Animation
 */

document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // Loading Screen Animation
    // Cycles through briefcase images
    // ============================================
    
    const loadingScreen = document.getElementById('loadingScreen');
    const loadingImg = document.getElementById('loadingImg');
    
    const loadingImages = [
        { src: '../__assets__/briefcase-laptop-closed.png', class: '' },
        { src: '../__assets__/briefcase-laptop-half-open.png', class: 'half-open' },
        { src: '../__assets__/briefcase-laptop-fully-open.png', class: 'fully-open' }
    ];
    
    let loadingFrame = 0;
    let loadingInterval = null;

    // Flag to track if we're waiting for animation to finish
    let loadingComplete = false;
    
    function stopLoadingAnimation() {
        // Mark that content is ready
        loadingComplete = true;
        
        // If animation isn't running (instant page), hide immediately
        if (!loadingInterval) {
            loadingScreen.classList.add('hidden');
            return;
        }
        
        // Otherwise, let the animation finish its current cycle
        // The interval handler will check loadingComplete and hide when at frame 0
    }
    
    function startLoadingAnimation() {
        loadingFrame = 0;
        loadingComplete = false;
        loadingImg.src = loadingImages[0].src;
        loadingImg.className = 'loading-img';
        loadingScreen.classList.remove('hidden');
        
        // Clear any existing interval
        if (loadingInterval) {
            clearInterval(loadingInterval);
        }
        
        loadingInterval = setInterval(() => {
            loadingFrame = (loadingFrame + 1) % loadingImages.length;
            const frame = loadingImages[loadingFrame];
            loadingImg.src = frame.src;
            loadingImg.className = 'loading-img ' + frame.class;
            
            // If content is ready and we're back at the start of the loop, hide
            if (loadingComplete && loadingFrame === 0) {
                clearInterval(loadingInterval);
                loadingInterval = null;
                loadingScreen.classList.add('hidden');
            }
        }, 250); // Change image every 250ms
    }

    // Preload loading images for smooth animation
    loadingImages.forEach(img => {
        const preload = new Image();
        preload.src = img.src;
    });

    // ============================================
    // Decorator Line Styling
    // Makes entire decorator lines white
    // ============================================
    
    function styleDecoratorLines() {
        // Find all code blocks
        const codeBlocks = document.querySelectorAll('.module-page pre code');
        
        codeBlocks.forEach(codeBlock => {
            // Split content into lines by looking at the HTML structure
            const html = codeBlock.innerHTML;
            const lines = html.split('\n');
            
            // Check each line for decorators and mark entire line
            const processedLines = lines.map(line => {
                // Check if line contains a decorator token
                if (line.includes('token decorator') || line.includes('class="decorator"')) {
                    // Wrap the entire line content in a decorator-line span
                    return `<span class="decorator-line-wrapper">${line}</span>`;
                }
                return line;
            });
            
            codeBlock.innerHTML = processedLines.join('\n');
        });
    }
    
    function styleLineCountComments() {
        // Find all comment tokens in code blocks
        const comments = document.querySelectorAll('.module-page pre code .token.comment');
        
        comments.forEach(comment => {
            const text = comment.textContent;
            // Match "# N" pattern (e.g., "# 1", "# 2", etc.)
            if (/^#\s*\d+$/.test(text.trim())) {
                comment.classList.add('line-count');
            }
        });
    }

    // Global state for API highlight toggle
    let apiHighlightEnabled = true;
    
    function toggleAPIHighlight() {
        apiHighlightEnabled = !apiHighlightEnabled;
        
        // Update module bar title
        const moduleBarTitle = document.querySelector('.module-bar-title');
        if (moduleBarTitle) {
            if (apiHighlightEnabled) {
                moduleBarTitle.classList.add('highlight-active');
            } else {
                moduleBarTitle.classList.remove('highlight-active');
            }
        }
        
        // Update module page content
        const modulePage = document.querySelector('.module-page, .about-page');
        if (modulePage) {
            if (apiHighlightEnabled) {
                modulePage.classList.add('highlight-active');
            } else {
                modulePage.classList.remove('highlight-active');
            }
        }
    }
    
    function setupModuleBarToggle() {
        const moduleBarTitle = document.querySelector('.module-bar-title');
        if (moduleBarTitle) {
            // Set initial state
            if (apiHighlightEnabled) {
                moduleBarTitle.classList.add('highlight-active');
            }
            
            // Add click listener
            moduleBarTitle.addEventListener('click', toggleAPIHighlight);
        }
        
        // Set initial state on module page
        const modulePage = document.querySelector('.module-page, .about-page');
        if (modulePage && apiHighlightEnabled) {
            modulePage.classList.add('highlight-active');
        }
    }

    function styleAPIHighlights() {
        // API identifiers to highlight
        const apiModules = new Set(['suitkaise', 'sktime', 'skpath', 'circuit', 'cerial', 'processing', 'docs']);
        const apiClasses = new Set(['SKPath', 'Timer', 'TimeThis', 'Yawn', 'Circuit', 'Process', 'CustomRoot', 'AnyPath', 'Permission']);
        // Note: 'time' and 'sleep' are NOT included here because they conflict with time.time() and time.sleep()
        // They still get highlighted as part of sktime.time() chains since 'sktime' is in apiModules
        const apiMethods = new Set(['timethis', 'autopath', 'elapsed', 'get_stats', 'get_statistics']);
        
        // Overrides: properties that should highlight word.property.chain patterns
        // These only activate if their associated decorator is found in the code block
        const overrideConfig = {
            'timer': '@sktime.timethis'  // timer property only highlights if @sktime.timethis decorator exists
        };
        
        // Find all code blocks
        const codeBlocks = document.querySelectorAll('.module-page pre code, .about-page pre code');
        
        codeBlocks.forEach(codeBlock => {
            // Track variables assigned to API objects in this block
            const apiVariables = new Set();
            
            // Get the text content to analyze for variable assignments
            const textContent = codeBlock.textContent;
            
            // Determine which overrides are active based on decorators found in code block
            const activeOverrides = new Set();
            for (const [property, requiredDecorator] of Object.entries(overrideConfig)) {
                if (textContent.includes(requiredDecorator)) {
                    activeOverrides.add(property);
                }
            }
            
            // Find variable assignments like: varname = sktime.Timer()
            const assignmentPatterns = [
                /(\w+)\s*=\s*(?:sktime|skpath|circuit|cerial|processing)\.\w+/g,
                /(\w+)\s*=\s*(?:Timer|TimeThis|Yawn|SKPath|Circuit|Process|CustomRoot|AnyPath|Permission)\s*\(/g,
                /with\s+(?:sktime|skpath|circuit|cerial|processing)\.\w+[^:]*\s+as\s+(\w+)/g,
            ];
            
            assignmentPatterns.forEach(pattern => {
                let match;
                while ((match = pattern.exec(textContent)) !== null) {
                    if (match[1]) apiVariables.add(match[1]);
                }
            });
            
            // Note: We don't add function names to apiVariables just because they use .timer
            // The word before .timer (like my_function) is NOT an API identifier
            // Instead, we handle this in the merge pass by working backwards from 'timer'
            
            // Walk through all text nodes and wrap API identifiers
            const walker = document.createTreeWalker(
                codeBlock,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            const nodesToProcess = [];
            let node;
            while (node = walker.nextNode()) {
                // Skip if inside a comment span
                let parent = node.parentElement;
                let isComment = false;
                while (parent && parent !== codeBlock) {
                    if (parent.classList && parent.classList.contains('comment')) {
                        isComment = true;
                        break;
                    }
                    parent = parent.parentElement;
                }
                if (!isComment && node.textContent.trim()) {
                    nodesToProcess.push(node);
                }
            }
            
            nodesToProcess.forEach(textNode => {
                const text = textNode.textContent;
                
                // Build regex pattern for all API identifiers
                const allIdentifiers = [
                    ...apiModules,
                    ...apiClasses, 
                    ...apiMethods,
                    ...apiVariables,
                    ...activeOverrides  // Add active override properties (like 'timer') as identifiers
                ];
                
                // Check if this text contains any API identifiers
                let hasMatch = false;
                for (const id of allIdentifiers) {
                    if (text.includes(id)) {
                        hasMatch = true;
                        break;
                    }
                }
                // Also check for @ decorator
                if (text.includes('@')) hasMatch = true;
                // Also check for active override patterns (e.g., "timer" only if @sktime.timethis was found)
                for (const id of activeOverrides) {
                    if (text.toLowerCase().includes(id)) {
                        hasMatch = true;
                        break;
                    }
                }
                
                if (!hasMatch) return;
                
                // Create pattern to match identifiers
                const identifierPattern = allIdentifiers
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                
                // Build overrides pattern for active overrides only
                const overridesPattern = [...activeOverrides]
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                
                // Match patterns:
                // 1. Decorators: @identifier.method()
                // 2. Module.something chains: sktime.Timer(), skpath.get_project_root()
                // 3. Standalone classes: SKPath(), Timer()
                // 4. Variables with chains: t.mean, timer.stdev, circ.flowing
                // 5. Override patterns: word.timer.chain... (1 word before, all words after connected by dots)
                let regexPattern = `(@(?:${identifierPattern})(?:\\.\\w+)*(?:\\(\\))?)|` +  // decorators with empty ()
                    `\\b(${identifierPattern})(?:\\.\\w+)*(\\(\\))?`;  // identifiers with chains and optional ()
                
                // Add override pattern only if there are active overrides
                if (activeOverrides.size > 0) {
                    regexPattern = `(@(?:${identifierPattern})(?:\\.\\w+)*(?:\\(\\))?)|` +  // decorators with empty ()
                        `(\\b\\w+)\\.(${overridesPattern})(?:\\.\\w+)*(\\(\\))?|` +  // override: word.timer.chain...()
                        `\\b(${identifierPattern})(?:\\.\\w+)*(\\(\\))?`;  // identifiers with chains and optional ()
                }
                
                const regex = new RegExp(regexPattern, 'gi');
                
                const parts = [];
                let lastIndex = 0;
                let match;
                
                while ((match = regex.exec(text)) !== null) {
                    // Add text before match
                    if (match.index > lastIndex) {
                        parts.push(document.createTextNode(text.slice(lastIndex, match.index)));
                    }
                    
                    // Create highlighted span for match
                    const span = document.createElement('span');
                    span.className = 'api-highlight';
                    span.textContent = match[0];
                    parts.push(span);
                    
                    lastIndex = regex.lastIndex;
                }
                
                // Add remaining text
                if (lastIndex < text.length) {
                    parts.push(document.createTextNode(text.slice(lastIndex)));
                }
                
                // Replace text node with parts if we found matches
                if (parts.length > 0 && lastIndex > 0) {
                    const parent = textNode.parentNode;
                    parts.forEach(part => parent.insertBefore(part, textNode));
                    parent.removeChild(textNode);
                }
            });
            
            // Second pass: extend api-highlight to include adjacent "()" 
            // This handles cases where Prism split the parens into separate tokens
            const highlights = codeBlock.querySelectorAll('.api-highlight');
            highlights.forEach(highlight => {
                let nextSibling = highlight.nextSibling;
                
                // Skip whitespace text nodes
                while (nextSibling && nextSibling.nodeType === Node.TEXT_NODE && !nextSibling.textContent.trim()) {
                    nextSibling = nextSibling.nextSibling;
                }
                
                // Check if next element is "(" or "()"
                if (nextSibling) {
                    let textToAdd = '';
                    let nodesToRemove = [];
                    
                    // Handle text node with "(" or "()"
                    if (nextSibling.nodeType === Node.TEXT_NODE) {
                        const text = nextSibling.textContent;
                        if (text.startsWith('()')) {
                            textToAdd = '()';
                            if (text === '()') {
                                nodesToRemove.push(nextSibling);
                            } else {
                                nextSibling.textContent = text.slice(2);
                            }
                        } else if (text.startsWith('(')) {
                            // Look for closing )
                            if (text === '(') {
                                const afterOpen = nextSibling.nextSibling;
                                if (afterOpen && afterOpen.nodeType === Node.TEXT_NODE && afterOpen.textContent.startsWith(')')) {
                                    textToAdd = '()';
                                    nodesToRemove.push(nextSibling);
                                    if (afterOpen.textContent === ')') {
                                        nodesToRemove.push(afterOpen);
                                    } else {
                                        afterOpen.textContent = afterOpen.textContent.slice(1);
                                    }
                                }
                            }
                        }
                    }
                    // Handle span element containing "(" or "()" (Prism punctuation token)
                    else if (nextSibling.nodeType === Node.ELEMENT_NODE) {
                        const text = nextSibling.textContent;
                        if (text === '()' || text === '(') {
                            if (text === '()') {
                                textToAdd = '()';
                                nodesToRemove.push(nextSibling);
                            } else if (text === '(') {
                                // Look for closing ) in next sibling
                                const afterOpen = nextSibling.nextSibling;
                                if (afterOpen) {
                                    const afterText = afterOpen.textContent;
                                    if (afterText === ')' || afterText.startsWith(')')) {
                                        textToAdd = '()';
                                        nodesToRemove.push(nextSibling);
                                        if (afterText === ')') {
                                            nodesToRemove.push(afterOpen);
                                        } else if (afterOpen.nodeType === Node.TEXT_NODE) {
                                            afterOpen.textContent = afterText.slice(1);
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // Extend the highlight
                    if (textToAdd) {
                        highlight.textContent += textToAdd;
                        nodesToRemove.forEach(n => n.parentNode.removeChild(n));
                    }
                }
            });
            
            // Third pass: merge api-highlight chains connected by dots
            // This handles cases like my_function.timer.mean where Prism splits them
            // Only merges if the chain contains 'timer' (when activeOverrides has 'timer')
            if (activeOverrides.has('timer')) {
                let merged = true;
                while (merged) {
                    merged = false;
                    const currentHighlights = codeBlock.querySelectorAll('.api-highlight');
                    for (const highlight of currentHighlights) {
                        let nextNode = highlight.nextSibling;
                        
                        // Check if next is a dot, and if what comes after contains 'timer' or 'timethis'
                        // This allows merging my_function + . + timer, or @sktime + . + timethis
                        let shouldProcess = false;
                        const highlightText = highlight.textContent.toLowerCase();
                        const timerKeywords = ['timer', 'timethis'];
                        
                        const containsTimerKeyword = (text) => timerKeywords.some(kw => text.includes(kw));
                        
                        if (containsTimerKeyword(highlightText)) {
                            // This highlight contains timer/timethis, process it
                            shouldProcess = true;
                        } else {
                            // Check if what comes after the dot contains timer/timethis
                            let dotNode = nextNode;
                            if (dotNode) {
                                let isDot = (dotNode.nodeType === Node.TEXT_NODE && dotNode.textContent.startsWith('.')) ||
                                           (dotNode.nodeType === Node.ELEMENT_NODE && dotNode.textContent === '.');
                                if (isDot) {
                                    let afterDot = dotNode.nodeType === Node.TEXT_NODE && dotNode.textContent.length > 1 
                                        ? null  // dot and word in same node, check the text
                                        : dotNode.nextSibling;
                                    
                                    // Check if after dot contains timer/timethis
                                    if (dotNode.nodeType === Node.TEXT_NODE && containsTimerKeyword(dotNode.textContent.toLowerCase())) {
                                        shouldProcess = true;
                                    } else if (afterDot && afterDot.textContent && containsTimerKeyword(afterDot.textContent.toLowerCase())) {
                                        shouldProcess = true;
                                    } else if (afterDot && afterDot.classList && afterDot.classList.contains('api-highlight') &&
                                               containsTimerKeyword(afterDot.textContent.toLowerCase())) {
                                        shouldProcess = true;
                                    }
                                }
                            }
                            
                            // Also check if this highlight is part of an existing timer chain
                            if (!shouldProcess) {
                                let prev = highlight.previousSibling;
                                while (prev) {
                                    if (prev.classList && prev.classList.contains('api-highlight') && 
                                        containsTimerKeyword(prev.textContent.toLowerCase())) {
                                        shouldProcess = true;
                                        break;
                                    }
                                    prev = prev.previousSibling;
                                }
                            }
                        }
                        
                        if (!shouldProcess) continue;
                        
                        // Check for pattern: highlight -> "." -> (highlight or word)
                        if (nextNode) {
                            // Check if next is a dot (text node or punctuation span)
                            let isDot = false;
                            let dotNode = null;
                            if (nextNode.nodeType === Node.TEXT_NODE && nextNode.textContent.startsWith('.')) {
                                isDot = true;
                                dotNode = nextNode;
                            } else if (nextNode.nodeType === Node.ELEMENT_NODE && nextNode.textContent === '.') {
                                isDot = true;
                                dotNode = nextNode;
                            }
                            
                            if (isDot) {
                                let afterDot = dotNode.nextSibling;
                                
                                // Handle case where dot and next word are in same text node
                                if (dotNode.nodeType === Node.TEXT_NODE && dotNode.textContent.length > 1) {
                                    const restAfterDot = dotNode.textContent.slice(1);
                                    // Only match alphanumeric + underscore for identifiers
                                    const wordMatch = restAfterDot.match(/^([a-zA-Z_][a-zA-Z0-9_]*)(.*)/);
                                    if (wordMatch) {
                                        highlight.textContent += '.' + wordMatch[1];
                                        if (wordMatch[2]) {
                                            dotNode.textContent = wordMatch[2];
                                        } else {
                                            dotNode.parentNode.removeChild(dotNode);
                                        }
                                        merged = true;
                                        break;
                                    }
                                }
                                
                                if (afterDot && afterDot.classList && afterDot.classList.contains('api-highlight')) {
                                    // Merge: highlight + "." + highlight
                                    highlight.textContent += '.' + afterDot.textContent;
                                    dotNode.parentNode.removeChild(dotNode);
                                    afterDot.parentNode.removeChild(afterDot);
                                    merged = true;
                                    break;
                                } else if (afterDot && afterDot.nodeType === Node.TEXT_NODE && /^[a-zA-Z_]/.test(afterDot.textContent)) {
                                    // Absorb the identifier (alphanumeric + underscore)
                                    const wordMatch = afterDot.textContent.match(/^([a-zA-Z_][a-zA-Z0-9_]*)(.*)/s);
                                    if (wordMatch) {
                                        const word = wordMatch[1];
                                        const rest = wordMatch[2];
                                        highlight.textContent += '.' + word;
                                        dotNode.parentNode.removeChild(dotNode);
                                        if (rest) {
                                            afterDot.textContent = rest;
                                        } else {
                                            afterDot.parentNode.removeChild(afterDot);
                                        }
                                        merged = true;
                                        break;
                                    }
                                } else if (afterDot && afterDot.nodeType === Node.ELEMENT_NODE && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(afterDot.textContent)) {
                                    // Absorb identifier from element (like a Prism token)
                                    highlight.textContent += '.' + afterDot.textContent;
                                    dotNode.parentNode.removeChild(dotNode);
                                    afterDot.parentNode.removeChild(afterDot);
                                    merged = true;
                                    break;
                                }
                            }
                        }
                    }
                }
                
                // Fourth pass: work BACKWARDS from 'timer' highlights to absorb word.timer patterns
                // This handles my_function.timer where my_function is not an API identifier
                merged = true;
                while (merged) {
                    merged = false;
                    const timerHighlights = codeBlock.querySelectorAll('.api-highlight');
                    for (const highlight of timerHighlights) {
                        const highlightText = highlight.textContent.toLowerCase();
                        // Only process if this starts with 'timer' (not already merged with something before)
                        if (!highlightText.startsWith('timer')) continue;
                        
                        let prevNode = highlight.previousSibling;
                        
                        // Check for pattern: word -> "." -> timer
                        if (prevNode) {
                            let isDot = false;
                            let dotNode = null;
                            
                            if (prevNode.nodeType === Node.TEXT_NODE && prevNode.textContent === '.') {
                                isDot = true;
                                dotNode = prevNode;
                            } else if (prevNode.nodeType === Node.ELEMENT_NODE && prevNode.textContent === '.') {
                                isDot = true;
                                dotNode = prevNode;
                            } else if (prevNode.nodeType === Node.TEXT_NODE && prevNode.textContent.endsWith('.')) {
                                // Dot is at end of text node
                                isDot = true;
                                dotNode = prevNode;
                            }
                            
                            if (isDot) {
                                let beforeDot = dotNode === prevNode && dotNode.textContent === '.' 
                                    ? dotNode.previousSibling 
                                    : null;
                                
                                // Handle case where dot is at end of text node with word before it
                                if (dotNode.nodeType === Node.TEXT_NODE && dotNode.textContent.endsWith('.') && dotNode.textContent.length > 1) {
                                    const textBeforeDot = dotNode.textContent.slice(0, -1);
                                    const wordMatch = textBeforeDot.match(/([a-zA-Z_][a-zA-Z0-9_]*)$/);
                                    if (wordMatch) {
                                        const word = wordMatch[1];
                                        const rest = textBeforeDot.slice(0, -word.length);
                                        highlight.textContent = word + '.' + highlight.textContent;
                                        if (rest) {
                                            dotNode.textContent = rest;
                                        } else {
                                            dotNode.parentNode.removeChild(dotNode);
                                        }
                                        merged = true;
                                        break;
                                    }
                                }
                                
                                if (beforeDot && beforeDot.nodeType === Node.TEXT_NODE && /[a-zA-Z_][a-zA-Z0-9_]*$/.test(beforeDot.textContent)) {
                                    // Absorb the identifier before the dot
                                    const wordMatch = beforeDot.textContent.match(/([a-zA-Z_][a-zA-Z0-9_]*)$/);
                                    if (wordMatch) {
                                        const word = wordMatch[0];
                                        const rest = beforeDot.textContent.slice(0, -word.length);
                                        highlight.textContent = word + '.' + highlight.textContent;
                                        dotNode.parentNode.removeChild(dotNode);
                                        if (rest) {
                                            beforeDot.textContent = rest;
                                        } else {
                                            beforeDot.parentNode.removeChild(beforeDot);
                                        }
                                        merged = true;
                                        break;
                                    }
                                } else if (beforeDot && beforeDot.nodeType === Node.ELEMENT_NODE && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(beforeDot.textContent)) {
                                    // Absorb identifier from element (like a Prism token)
                                    highlight.textContent = beforeDot.textContent + '.' + highlight.textContent;
                                    dotNode.parentNode.removeChild(dotNode);
                                    beforeDot.parentNode.removeChild(beforeDot);
                                    merged = true;
                                    break;
                                }
                            }
                        }
                    }
                }
            }
            
            // Fifth pass: merge ALL api-highlight chains with following dot chains
            // This handles cases like circ.broken, circ.short() where circ is an API variable
            let generalMerged = true;
            while (generalMerged) {
                generalMerged = false;
                const allHighlights = codeBlock.querySelectorAll('.api-highlight');
                for (const highlight of allHighlights) {
                    let nextNode = highlight.nextSibling;
                    
                    if (nextNode) {
                        // Check if next is a dot
                        let isDot = false;
                        let dotNode = null;
                        if (nextNode.nodeType === Node.TEXT_NODE && nextNode.textContent.startsWith('.')) {
                            isDot = true;
                            dotNode = nextNode;
                        } else if (nextNode.nodeType === Node.ELEMENT_NODE && nextNode.textContent === '.') {
                            isDot = true;
                            dotNode = nextNode;
                        }
                        
                        if (isDot) {
                            let afterDot = dotNode.nextSibling;
                            
                            // Handle case where dot and next word are in same text node
                            if (dotNode.nodeType === Node.TEXT_NODE && dotNode.textContent.length > 1) {
                                const restAfterDot = dotNode.textContent.slice(1);
                                const wordMatch = restAfterDot.match(/^([a-zA-Z_][a-zA-Z0-9_]*)(.*)/);
                                if (wordMatch) {
                                    highlight.textContent += '.' + wordMatch[1];
                                    if (wordMatch[2]) {
                                        dotNode.textContent = wordMatch[2];
                                    } else {
                                        dotNode.parentNode.removeChild(dotNode);
                                    }
                                    generalMerged = true;
                                    break;
                                }
                            }
                            
                            // Merge with another api-highlight
                            if (afterDot && afterDot.classList && afterDot.classList.contains('api-highlight')) {
                                highlight.textContent += '.' + afterDot.textContent;
                                dotNode.parentNode.removeChild(dotNode);
                                afterDot.parentNode.removeChild(afterDot);
                                generalMerged = true;
                                break;
                            } 
                            // Absorb word from text node
                            else if (afterDot && afterDot.nodeType === Node.TEXT_NODE && /^[a-zA-Z_]/.test(afterDot.textContent)) {
                                const wordMatch = afterDot.textContent.match(/^([a-zA-Z_][a-zA-Z0-9_]*)(.*)/s);
                                if (wordMatch) {
                                    const word = wordMatch[1];
                                    const rest = wordMatch[2];
                                    highlight.textContent += '.' + word;
                                    dotNode.parentNode.removeChild(dotNode);
                                    if (rest) {
                                        afterDot.textContent = rest;
                                    } else {
                                        afterDot.parentNode.removeChild(afterDot);
                                    }
                                    generalMerged = true;
                                    break;
                                }
                            }
                            // Absorb word from element (like a Prism token)
                            else if (afterDot && afterDot.nodeType === Node.ELEMENT_NODE && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(afterDot.textContent)) {
                                highlight.textContent += '.' + afterDot.textContent;
                                dotNode.parentNode.removeChild(dotNode);
                                afterDot.parentNode.removeChild(afterDot);
                                generalMerged = true;
                                break;
                            }
                        }
                    }
                }
            }
        });
    }

    // ============================================
    // Page Content Storage
    // Core pages are inline (instant)
    // Module pages are fetched at startup
    // Heavy pages (videos/tests) are lazy-loaded on demand
    // ============================================
    
    // Core pages that are always inline (small, essential)
    const corePages = {
        home: document.getElementById('pageContent').innerHTML,
        donate: `
            <section class="page-section">
                <div class="page-header">
                    <h1>Support Suitkaise</h1>
                </div>
                <div class="page-body">
                    <p>Donate page content coming soon...</p>
                </div>
            </section>
        `,
        error: `
            <section class="error-page">
                <a href="#home" class="error-briefcase" id="errorBriefcase" data-page="home">
                    <img src="../__assets__/briefcase-laptop-closed.png" alt="Back to Home" class="error-briefcase-img" id="errorBriefcaseImg">
                    <span class="error-back-text">Back to Home</span>
                </a>
                <h1 class="error-title">ERROR</h1>
                <p class="error-message">An error has occurred. This might have been a loading error, or this page may not exist.</p>
            </section>
        `,
        password: `
            <section class="password-page">
                <div class="password-briefcase">
                    <img src="../__assets__/briefcase-laptop-closed.png" alt="Suitkaise" class="password-briefcase-img" id="passwordBriefcaseImg">
                </div>
                <p class="password-message">This site is not yet publicly accessible. Enter the password to access the site.</p>
                <div class="password-input-container">
                    <input type="password" class="password-input" id="passwordInput" placeholder="Enter password...">
                </div>
            </section>
        `
    };
    
    // Module pages to fetch at startup (stored in pages/ folder)
    const modulePagesList = [
        // Site pages
        'about',
        // Processing
        'processing', 'processing-how-it-works', 'processing-examples', 'processing-why',
        // Cerial
        'cerial', 'cerial-how-it-works', 'cerial-examples', 'cerial-why',
        // Sktime
        'sktime', 'sktime-how-it-works', 'sktime-examples', 'sktime-why',
        // Skpath
        'skpath', 'skpath-how-it-works', 'skpath-examples', 'skpath-why',
        // Circuit
        'circuit', 'circuit-how-it-works', 'circuit-examples', 'circuit-why'
    ];
    
    // Cache for all fetched pages (module pages loaded at startup, lazy pages loaded on demand)
    const fetchedPages = {};
    
    // Fetch a single page from the pages folder
    async function fetchPage(pageName) {
        try {
            const response = await fetch(`pages/${pageName}.html`);
            if (!response.ok) {
                throw new Error(`Failed to load ${pageName}: ${response.status}`);
            }
            return await response.text();
        } catch (error) {
            console.error(`Error loading ${pageName}:`, error);
            return null;
        }
    }
    
    // Fetch all module pages at startup
    async function preloadModulePages() {
        const fetchPromises = modulePagesList.map(async (pageName) => {
            const content = await fetchPage(pageName);
            if (content) {
                fetchedPages[pageName] = content;
            }
        });
        
        await Promise.all(fetchPromises);
        console.log(`Preloaded ${Object.keys(fetchedPages).length} module pages`);
    }
    
    // Flag to track if initial preload is complete
    let initialPreloadComplete = false;
    
    // Start preloading module pages immediately
    const preloadPromise = preloadModulePages().then(() => {
        initialPreloadComplete = true;
    });
    
    // Registry of pages that need lazy loading (heavy content like videos/tests)
    // These pages will show the loading animation while content loads
    const lazyPages = {
        // Processing
        'processing-videos': async () => await fetchPage('processing-videos'),
        'processing-tests': async () => await fetchPage('processing-tests'),
        
        // Cerial
        'cerial-videos': async () => await fetchPage('cerial-videos'),
        'cerial-tests': async () => await fetchPage('cerial-tests'),
        
        // Sktime
        'sktime-videos': async () => await fetchPage('sktime-videos'),
        'sktime-tests': async () => await fetchPage('sktime-tests'),
        
        // Skpath
        'skpath-videos': async () => await fetchPage('skpath-videos'),
        'skpath-tests': async () => await fetchPage('skpath-tests'),
        
        // Circuit
        'circuit-videos': async () => await fetchPage('circuit-videos'),
        'circuit-tests': async () => await fetchPage('circuit-tests'),
    };
    
    // Check if a page is available (core, preloaded module, or cached lazy page)
    function isPageReady(pageName) {
        return corePages[pageName] || fetchedPages[pageName];
    }
    
    // Check if a page exists at all
    function pageExists(pageName) {
        return corePages[pageName] || fetchedPages[pageName] || lazyPages[pageName] || modulePagesList.includes(pageName);
    }
    
    // Get page content (from core, fetched, or lazy load it)
    async function getPageContent(pageName) {
        // Check core pages first (always available)
        if (corePages[pageName]) {
            return corePages[pageName];
        }
        
        // Check if already fetched (module pages or cached lazy pages)
        if (fetchedPages[pageName]) {
            return fetchedPages[pageName];
        }
        
        // Need to lazy load
        if (lazyPages[pageName]) {
            const content = await lazyPages[pageName]();
            if (content) {
                fetchedPages[pageName] = content; // Cache it
            }
            return content;
        }
        
        // Module page that hasn't loaded yet - try to fetch it
        if (modulePagesList.includes(pageName)) {
            const content = await fetchPage(pageName);
            if (content) {
                fetchedPages[pageName] = content;
            }
            return content;
        }
        
        // Page doesn't exist
        return null;
    }
    
    // ============================================
    // Password Page Functionality
    // ============================================
    
    // SHA-256 hash (password is not visible in code)
    const PASSWORD_HASH = '360b845c061f5bd1bb34217b1d4fb53d814730194407e00d7a21d80e9db8088e';
    
    // Pure JavaScript SHA-256 implementation (works in all contexts, including file://)
    function sha256(message) {
        // Convert string to bytes
        const encoder = new TextEncoder();
        const msgBytes = encoder.encode(message);
        
        // Constants
        const K = [
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
        ];
        
        // Initial hash values
        let H0 = 0x6a09e667, H1 = 0xbb67ae85, H2 = 0x3c6ef372, H3 = 0xa54ff53a;
        let H4 = 0x510e527f, H5 = 0x9b05688c, H6 = 0x1f83d9ab, H7 = 0x5be0cd19;
        
        // Helper functions
        const rotr = (n, x) => (x >>> n) | (x << (32 - n));
        const ch = (x, y, z) => (x & y) ^ (~x & z);
        const maj = (x, y, z) => (x & y) ^ (x & z) ^ (y & z);
        const sigma0 = x => rotr(2, x) ^ rotr(13, x) ^ rotr(22, x);
        const sigma1 = x => rotr(6, x) ^ rotr(11, x) ^ rotr(25, x);
        const gamma0 = x => rotr(7, x) ^ rotr(18, x) ^ (x >>> 3);
        const gamma1 = x => rotr(17, x) ^ rotr(19, x) ^ (x >>> 10);
        
        // Pre-processing: create padded message
        const msgLen = msgBytes.length;
        const bitLen = msgLen * 8;
        
        // Calculate padded length (must be multiple of 64 bytes / 512 bits)
        // Need: msgLen + 1 (0x80) + padding + 8 (length) = multiple of 64
        const totalLen = Math.ceil((msgLen + 9) / 64) * 64;
        const padded = new Uint8Array(totalLen);
        padded.set(msgBytes);
        padded[msgLen] = 0x80;
        
        // Append length in bits as 64-bit big-endian (we only use lower 32 bits for simplicity)
        const lenView = new DataView(padded.buffer);
        lenView.setUint32(totalLen - 4, bitLen, false);
        
        // Process each 64-byte (512-bit) chunk
        for (let chunkStart = 0; chunkStart < totalLen; chunkStart += 64) {
            const W = new Uint32Array(64);
            
            // Break chunk into sixteen 32-bit big-endian words
            for (let t = 0; t < 16; t++) {
                const offset = chunkStart + t * 4;
                W[t] = (padded[offset] << 24) | (padded[offset + 1] << 16) | 
                       (padded[offset + 2] << 8) | padded[offset + 3];
            }
            
            // Extend to 64 words
            for (let t = 16; t < 64; t++) {
                W[t] = (gamma1(W[t - 2]) + W[t - 7] + gamma0(W[t - 15]) + W[t - 16]) >>> 0;
            }
            
            // Initialize working variables
            let a = H0, b = H1, c = H2, d = H3, e = H4, f = H5, g = H6, h = H7;
            
            // Main loop
            for (let t = 0; t < 64; t++) {
                const T1 = (h + sigma1(e) + ch(e, f, g) + K[t] + W[t]) >>> 0;
                const T2 = (sigma0(a) + maj(a, b, c)) >>> 0;
                h = g; g = f; f = e;
                e = (d + T1) >>> 0;
                d = c; c = b; b = a;
                a = (T1 + T2) >>> 0;
            }
            
            // Add to hash
            H0 = (H0 + a) >>> 0; H1 = (H1 + b) >>> 0;
            H2 = (H2 + c) >>> 0; H3 = (H3 + d) >>> 0;
            H4 = (H4 + e) >>> 0; H5 = (H5 + f) >>> 0;
            H6 = (H6 + g) >>> 0; H7 = (H7 + h) >>> 0;
        }
        
        // Convert to hex string
        const toHex = n => n.toString(16).padStart(8, '0');
        return toHex(H0) + toHex(H1) + toHex(H2) + toHex(H3) + 
               toHex(H4) + toHex(H5) + toHex(H6) + toHex(H7);
    }
    
    async function hashPassword(password) {
        const processed = password.toLowerCase().trim();
        
        // Try Web Crypto API first (faster, but requires secure context)
        if (typeof crypto !== 'undefined' && crypto.subtle) {
            try {
                const encoder = new TextEncoder();
                const data = encoder.encode(processed);
                const hashBuffer = await crypto.subtle.digest('SHA-256', data);
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            } catch (e) {
                // Fall through to pure JS implementation
            }
        }
        
        // Fallback to pure JavaScript implementation
        return sha256(processed);
    }
    
    function setupPasswordPage() {
        const passwordInput = document.getElementById('passwordInput');
        
        if (passwordInput) {
            passwordInput.addEventListener('keydown', async (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    
                    try {
                        const inputHash = await hashPassword(passwordInput.value);
                        if (inputHash === PASSWORD_HASH) {
                            // Correct password - store in session and go to home
                            sessionStorage.setItem('suitkaise_authenticated', 'true');
                            navigateTo('home');
                        } else {
                            // Incorrect password - shake the input
                            passwordInput.classList.add('shake');
                            passwordInput.value = '';
                            setTimeout(() => {
                                passwordInput.classList.remove('shake');
                            }, 400);
                        }
                    } catch (error) {
                        console.error('Password check failed:', error);
                        // Still shake on error to indicate failure
                        passwordInput.classList.add('shake');
                        passwordInput.value = '';
                        setTimeout(() => {
                            passwordInput.classList.remove('shake');
                        }, 400);
                    }
                }
            });
            
            // Focus the input
            passwordInput.focus();
        }
    }
    
    // ============================================
    // Error Page Briefcase Hover
    // ============================================
    
    function setupErrorPageHover() {
        const errorBriefcase = document.getElementById('errorBriefcase');
        const errorBriefcaseImg = document.getElementById('errorBriefcaseImg');
        const errorBackText = errorBriefcase?.querySelector('.error-back-text');
        
        if (errorBriefcase && errorBriefcaseImg) {
            const closedImg = '../__assets__/briefcase-laptop-closed.png';
            const halfOpenImg = '../__assets__/briefcase-laptop-half-open.png';
            
            errorBriefcase.addEventListener('mouseenter', () => {
                errorBriefcaseImg.src = halfOpenImg;
                errorBriefcaseImg.classList.add('half-open');
                if (errorBackText) {
                    errorBackText.classList.add('visible');
                }
            });
            
            errorBriefcase.addEventListener('mouseleave', () => {
                // Hide text instantly
                if (errorBackText) {
                    errorBackText.classList.remove('visible');
                }
                // Change image back
                errorBriefcaseImg.src = closedImg;
                errorBriefcaseImg.classList.remove('half-open');
            });
            
            errorBriefcase.addEventListener('click', (e) => {
                e.preventDefault();
                navigateTo('home');
            });
        }
    }

    // ============================================
    // SPA Navigation
    // ============================================
    
    const pageContent = document.getElementById('pageContent');
    const navBar = document.querySelector('.nav-bar');
    let currentPage = 'home';
    
    // Pages that should hide the nav bar
    const noNavPages = ['password', 'error'];
    
    // Module names for scroll position memory
    const moduleNames = ['skpath', 'sktime', 'circuit', 'cerial', 'processing'];
    
    // Store scroll positions per module
    const moduleScrollPositions = {};
    
    // Extract module name from page name
    function getModuleName(pageName) {
        for (const mod of moduleNames) {
            if (pageName === mod || pageName.startsWith(mod + '-')) {
                return mod;
            }
        }
        return null;
    }

    async function navigateTo(pageName, force = false) {
        if (!force && pageName === currentPage) return;
        
        // Save scroll position for current module before navigating
        const currentModule = getModuleName(currentPage);
        if (currentModule) {
            moduleScrollPositions[currentModule] = window.scrollY;
        }
        
        // Check if page content is already available
        const isReady = isPageReady(pageName);
        
        // Only show loading animation if we need to load content
        if (!isReady && (lazyPages[pageName] || modulePagesList.includes(pageName))) {
            startLoadingAnimation();
        }
        
        // Get the page content (instant if pre-loaded, async if lazy)
        const content = await getPageContent(pageName);
        
        if (content) {
            // Cleanup scroll opacity from previous page
            cleanupScrollOpacity();
            
            // Update content
            pageContent.innerHTML = content;
            currentPage = pageName;
            
            // Show/hide nav bar based on page
            if (noNavPages.includes(pageName)) {
                navBar.classList.add('hidden');
                pageContent.classList.add('no-nav');
            } else {
                navBar.classList.remove('hidden');
                pageContent.classList.remove('no-nav');
            }
            
            // Update URL hash
            window.location.hash = pageName === 'home' ? '' : pageName;
            
            // Restore scroll position if navigating within same module, otherwise scroll to top
            const newModule = getModuleName(pageName);
            if (newModule && newModule === currentModule && moduleScrollPositions[newModule] !== undefined) {
                window.scrollTo(0, moduleScrollPositions[newModule]);
            } else {
                window.scrollTo(0, 0);
            }
        }
        
        // Hide loading screen (if it was shown)
        stopLoadingAnimation();
        
        // Setup page-specific functionality
        if (pageName === 'error') {
            setupErrorPageHover();
        } else if (pageName === 'password') {
            setupPasswordPage();
        } else if (pageName === 'home') {
            setupFadeInAnimations();
        }
        
        // Run syntax highlighting on code blocks
        if (typeof Prism !== 'undefined') {
            Prism.highlightAll();
            styleDecoratorLines();
            styleLineCountComments();
            styleAPIHighlights();
        }
        
        // Setup module bar links if present
        setupModuleBarLinks();
        
        // Setup module bar title toggle for API highlighting
        setupModuleBarToggle();
        
        // Setup scroll-based opacity for module pages
        setupScrollOpacity();
    }
    
    // ============================================
    // Module Bar Link Handler
    // ============================================
    
    function setupModuleBarLinks() {
        const moduleBarLinks = document.querySelectorAll('.module-bar-link');
        moduleBarLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const pageName = link.dataset.page;
                navigateTo(pageName);
            });
        });
    }

    // Handle nav link clicks
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const pageName = link.dataset.page;
            navigateTo(pageName);
        });
    });

    // Handle browser back/forward
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.slice(1) || 'home';
        if (hash !== currentPage && pageExists(hash)) {
            navigateTo(hash);
        }
    });

    // Hide loading screen on initial load
    stopLoadingAnimation();
    
    // Check URL hash on initial load and navigate to that page
    (async function handleInitialHash() {
        const initialHash = window.location.hash.slice(1);
        
        if (initialHash && pageExists(initialHash)) {
            // Force navigate to the page specified in the URL hash
            currentPage = ''; // Reset so navigateTo doesn't skip
            await navigateTo(initialHash, true);
        } else {
            // On home page, setup fade-in animations
            setupFadeInAnimations();
        }
    })();
    
    // ============================================
    // Section-based Scroll Effects for Module Pages
    // Groups content into logical sections and highlights the active one
    // ============================================
    
    function setupScrollOpacity() {
        const modulePage = document.querySelector('.module-page, .about-page, .why-page');
        if (!modulePage) return;
        
        // Group elements into logical sections:
        // - h2 starts a major section (includes everything until next h2)
        // - h3/h4/h5 starts a subsection within the current major section
        // - Code blocks (pre) are part of their parent section
        // - Text/lists belong to the most recent header
        
        const allElements = Array.from(modulePage.querySelectorAll('h1, h2, h3, h4, h5, h6, p, li, pre, details, hr'));
        if (allElements.length === 0) return;
        
        const sections = [];
        let currentSection = null;
        
        // Helper to check if current section only has headers (no content yet)
        function sectionHasOnlyHeaders(section) {
            if (!section) return false;
            return section.elements.every(el => /^h[1-6]$/i.test(el.tagName));
        }
        
        allElements.forEach(el => {
            const tagName = el.tagName.toLowerCase();
            
            // Skip li elements inside details (they're part of the details group)
            if (tagName === 'li' && el.closest('details')) return;
            
            // Headers (h2-h6)
            if (/^h[2-6]$/.test(tagName)) {
                // If current section only has headers, add this header to it
                // This groups consecutive headers together
                if (sectionHasOnlyHeaders(currentSection)) {
                    currentSection.elements.push(el);
                } else {
                    // Current section has content, so save it and start new
                    if (currentSection && currentSection.elements.length > 0) {
                        sections.push(currentSection);
                    }
                    currentSection = { 
                        elements: [el]
                    };
                }
            }
            // hr creates a visual break - save current section
            else if (tagName === 'hr') {
                if (currentSection && currentSection.elements.length > 0) {
                    sections.push(currentSection);
                }
                currentSection = null;
            }
            // Everything else (p, li, pre, details, h1) belongs to current section
            else {
                if (!currentSection) {
                    currentSection = { elements: [] };
                }
                currentSection.elements.push(el);
            }
        });
        
        // Don't forget the last section
        if (currentSection && currentSection.elements.length > 0) {
            sections.push(currentSection);
        }
        
        // Debug: log sections
        console.log(`Found ${sections.length} sections:`, sections.map(s => ({
            firstElement: s.elements[0]?.tagName + ': ' + s.elements[0]?.textContent?.slice(0, 30),
            elementCount: s.elements.length
        })));
        
        function updateSections() {
            const viewportHeight = window.innerHeight;
            const navHeight = 80;
            const contentTop = navHeight;
            const contentBottom = viewportHeight;
            const contentHeight = contentBottom - contentTop;
            
            // Define the "safe zone" - middle 70% (exclude top/bottom 15%)
            const safeZoneTop = contentTop + contentHeight * 0.15;
            const safeZoneBottom = contentTop + contentHeight * 0.85;
            
            // Calculate visibility info for each section
            const sectionInfo = sections.map((section, index) => {
                if (section.elements.length === 0) {
                    return { index, isFullyVisible: false, isInSafeZone: false, isVisible: false };
                }
                
                // Get bounding box of entire section (first to last element)
                const firstEl = section.elements[0];
                const lastEl = section.elements[section.elements.length - 1];
                const firstRect = firstEl.getBoundingClientRect();
                const lastRect = lastEl.getBoundingClientRect();
                
                const sectionTop = firstRect.top;
                const sectionBottom = lastRect.bottom;
                
                // Is section at least partially visible?
                const isVisible = sectionBottom > contentTop && sectionTop < contentBottom;
                
                // Is section fully visible (entirely within viewport)?
                const isFullyVisible = sectionTop >= contentTop && sectionBottom <= contentBottom;
                
                // Is section in the safe zone (not in top/bottom 15%)?
                // Section is in safe zone if its bounds are within the middle 70%
                const isInSafeZone = sectionTop >= safeZoneTop && sectionBottom <= safeZoneBottom;
                
                return { index, isFullyVisible, isInSafeZone, isVisible };
            });
            
            // Determine which sections should be highlighted
            const activeIndices = new Set();
            
            // Rule 1: Any section fully visible AND in safe zone is highlighted
            sectionInfo.forEach(info => {
                if (info.isFullyVisible && info.isInSafeZone) {
                    activeIndices.add(info.index);
                }
            });
            
            // Rule 2: First section is always highlighted if visible,
            // UNLESS another section (index > 0) is highlighted
            const firstSectionInfo = sectionInfo[0];
            const hasOtherHighlighted = [...activeIndices].some(idx => idx > 0);
            
            if (firstSectionInfo && firstSectionInfo.isVisible && !hasOtherHighlighted) {
                activeIndices.add(0);
            }
            
            // If nothing is highlighted, highlight the most visible section
            if (activeIndices.size === 0) {
                let bestIndex = -1;
                let bestVisibility = 0;
                
                sectionInfo.forEach(info => {
                    if (info.isVisible) {
                        // Calculate how much of section is visible
                        const section = sections[info.index];
                        const firstRect = section.elements[0].getBoundingClientRect();
                        const lastRect = section.elements[section.elements.length - 1].getBoundingClientRect();
                        const visibleTop = Math.max(firstRect.top, contentTop);
                        const visibleBottom = Math.min(lastRect.bottom, contentBottom);
                        const visibleHeight = Math.max(0, visibleBottom - visibleTop);
                        
                        if (visibleHeight > bestVisibility) {
                            bestVisibility = visibleHeight;
                            bestIndex = info.index;
                        }
                    }
                });
                
                if (bestIndex >= 0) {
                    activeIndices.add(bestIndex);
                }
            }
            
            // Rule 3: Connect first section to second section
            // If either is highlighted, both are highlighted
            if (sections.length >= 2) {
                if (activeIndices.has(0) || activeIndices.has(1)) {
                    if (sectionInfo[0]?.isVisible) activeIndices.add(0);
                    if (sectionInfo[1]?.isVisible) activeIndices.add(1);
                }
            }
            
            // Rule 4: Connect last section to second-to-last section
            // If either is highlighted, both are highlighted
            const lastIdx = sections.length - 1;
            const secondLastIdx = sections.length - 2;
            if (sections.length >= 2 && secondLastIdx >= 0) {
                if (activeIndices.has(lastIdx) || activeIndices.has(secondLastIdx)) {
                    if (sectionInfo[lastIdx]?.isVisible) activeIndices.add(lastIdx);
                    if (sectionInfo[secondLastIdx]?.isVisible) activeIndices.add(secondLastIdx);
                }
            }
            
            // Apply styles based on active sections
            sections.forEach((section, index) => {
                const isActive = activeIndices.has(index);
                
                section.elements.forEach(el => {
                    if (isActive) {
                        el.style.opacity = 1;
                    } else {
                        el.style.opacity = 0.3;
                    }
                });
            });
        }
        
        // Update on scroll
        let ticking = false;
        function onScroll() {
            if (!ticking) {
                requestAnimationFrame(() => {
                    updateSections();
                    ticking = false;
                });
                ticking = true;
            }
        }
        
        // Initial update
        updateSections();
        
        // Listen for scroll
        window.addEventListener('scroll', onScroll, { passive: true });
        
        // Store cleanup function for when navigating away
        modulePage._scrollOpacityCleanup = () => {
            window.removeEventListener('scroll', onScroll);
        };
    }
    
    // Cleanup scroll opacity when navigating to a new page
    function cleanupScrollOpacity() {
        const modulePage = document.querySelector('.module-page, .about-page, .why-page');
        if (modulePage && modulePage._scrollOpacityCleanup) {
            modulePage._scrollOpacityCleanup();
        }
    }
    
    // ============================================
    // Fade-in Animation on Scroll
    // ============================================
    
    function setupFadeInAnimations() {
        const fadeElements = document.querySelectorAll('.module-row .module-text, .module-row .module-image');
        
        if (fadeElements.length === 0) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const element = entry.target;
                    
                    // 1/10 chance for flicker effect on images
                    if (element.classList.contains('module-image') && Math.random() < 0.1) {
                        element.classList.add('flicker');
                    } else {
                        element.classList.add('visible');
                    }
                    
                    // Stop observing once animated
                    observer.unobserve(element);
                }
            });
        }, {
            threshold: 0.2, // Trigger when 20% visible
            rootMargin: '0px 0px -50px 0px' // Slightly before fully in view
        });
        
        fadeElements.forEach(el => observer.observe(el));
    }
    
    // Run on initial load
    setupFadeInAnimations();

    // ============================================
    // Sidebar Toggle Functionality
    // ============================================
    
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');

    function openSidebar() {
        sidebar.classList.add('open');
        sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    sidebarToggle.addEventListener('click', openSidebar);
    sidebarCloseBtn.addEventListener('click', closeSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);

    // Close sidebar when a sidebar link is clicked
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    sidebarItems.forEach(item => {
        item.addEventListener('click', closeSidebar);
    });

    // Close sidebar on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });

    // ============================================
    // Home Button Hover Effect
    // ============================================
    
    const homeBtn = document.getElementById('homeBtn');
    const homeIcon = document.getElementById('homeIcon');
    
    const closedImage = '../__assets__/briefcase-laptop-closed.png';
    const openImage = '../__assets__/briefcase-laptop-fully-open.png';

    const preloadImage = new Image();
    preloadImage.src = openImage;

    homeBtn.addEventListener('mouseenter', () => {
        homeIcon.src = openImage;
        homeIcon.classList.add('open');
    });

    homeBtn.addEventListener('mouseleave', () => {
        homeIcon.src = closedImage;
        homeIcon.classList.remove('open');
    });
});
