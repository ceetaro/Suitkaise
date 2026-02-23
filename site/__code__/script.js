/**
 * Suitkaise Website JavaScript
 * SPA Navigation with Loading Screen Animation
 */

document.addEventListener('DOMContentLoaded', () => {
    const assetBasePath = window.location.pathname.includes('/__code__/')
        ? '../__assets__'
        : '__assets__';
    const assetPath = (filename) => `${assetBasePath}/${filename}`;

    // Normalize asset image paths for both serve modes:
    // - site root: /__code__/index.html (needs ../__assets__/...)
    // - __code__ root: / (needs __assets__/...)
    document.querySelectorAll('img[src*="__assets__/"]').forEach((img) => {
        const rawSrc = img.getAttribute('src') || '';
        const fileName = rawSrc.split('/').pop();
        if (fileName) {
            img.src = assetPath(fileName);
        }
    });

    // ============================================
    // Loading Screen Animation
    // Cycles through briefcase images
    // ============================================
    
    const loadingScreen = document.getElementById('loadingScreen');
    const loadingFrames = [
        document.getElementById('loadingFrame0'),
        document.getElementById('loadingFrame1'),
        document.getElementById('loadingFrame2')
    ];
    
    let loadingComplete = false;
    let animationId = 0;
    
    function showLoadingFrame(idx) {
        for (let i = 0; i < loadingFrames.length; i++) {
            loadingFrames[i].style.display = i === idx ? '' : 'none';
        }
    }
    
    function hideLoadingScreen() {
        loadingScreen.style.opacity = '';
        loadingScreen.style.visibility = '';
        loadingScreen.style.transition = '';
        loadingScreen.classList.add('hidden');
        showLoadingFrame(0);
    }
    
    function stopLoadingAnimation() {
        loadingComplete = true;
        if (animationId === 0) {
            hideLoadingScreen();
        }
    }
    
    function startLoadingAnimation() {
        loadingComplete = false;
        const id = ++animationId;
        
        showLoadingFrame(0);
        loadingScreen.style.transition = 'none';
        loadingScreen.offsetHeight;
        loadingScreen.classList.remove('hidden');
        loadingScreen.style.opacity = '1';
        loadingScreen.style.visibility = 'visible';
        
        setTimeout(() => {
            if (id !== animationId) return;
            showLoadingFrame(1);
        }, 250);
        
        setTimeout(() => {
            if (id !== animationId) return;
            showLoadingFrame(2);
        }, 500);
        
        setTimeout(() => {
            if (id !== animationId) return;
            if (loadingComplete) {
                hideLoadingScreen();
            } else {
                const waitId = setInterval(() => {
                    if (id !== animationId) { clearInterval(waitId); return; }
                    if (loadingComplete) {
                        clearInterval(waitId);
                        hideLoadingScreen();
                    }
                }, 50);
            }
        }, 750);
    }

    // ============================================
    // Decorator Line Styling
    // Makes entire decorator lines white
    // ============================================
    
    function styleDecoratorLines() {
        // Find all code blocks
        const codeBlocks = document.querySelectorAll('.module-page pre code, .about-page pre code, .why-page pre code');
        
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
        // Disabled: numeric line comments should not receive special highlight.
    }
    
    function styleCalloutLabels() {
        const textContainers = document.querySelectorAll(
            '.module-page p, .module-page li, .about-page p, .about-page li, .why-page p, .why-page li'
        );
        
        textContainers.forEach(el => {
            // Prevent double-wrapping on repeated navigation/highlight passes.
            if (el.querySelector('.callout-label')) return;
            
            // Find first non-empty text node at the start of the element.
            let firstTextNode = null;
            for (const child of el.childNodes) {
                if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
                    firstTextNode = child;
                    break;
                }
                // If element starts with non-text content, don't force a rewrite.
                if (child.nodeType === Node.ELEMENT_NODE) {
                    return;
                }
            }
            if (!firstTextNode) return;
            
            const text = firstTextNode.textContent;
            const colonIndex = text.indexOf(':');
            if (colonIndex <= 0) return;
            const labelText = text.slice(0, colonIndex).trim();
            if (!labelText) return;
            const lowerLabel = labelText.toLowerCase();
            if (lowerLabel === 'pros' || lowerLabel === 'cons') return;
            
            // Smart callouts: if a line starts with a short phrase (<= 8 words)
            // followed by ":", emphasize the label.
            const wordCount = labelText.split(/\s+/).filter(Boolean).length;
            if (wordCount === 0 || wordCount > 8) return;
            const after = text.slice(colonIndex + 1);
            // If ":" is the last non-whitespace character, do not style.
            if (!after.trim()) return;
            
            const label = document.createElement('strong');
            label.className = 'callout-label';
            label.textContent = `${labelText}:`;
            
            const afterText = after.replace(/^\s*/, '');
            const fragment = document.createDocumentFragment();
            fragment.appendChild(label);
            fragment.appendChild(document.createTextNode(` ${afterText}`));
            
            el.replaceChild(fragment, firstTextNode);
        });
    }

    function normalizeSignatureLabelParagraphs() {
        const labels = new Set(['Arguments', 'Returns', 'Raises', 'Parameters', 'Attributes']);
        const paragraphs = document.querySelectorAll('.module-page p, .about-page p, .why-page p');

        paragraphs.forEach(p => {
            // Skip if this paragraph is already a standalone label.
            if (p.children.length === 1 && p.firstElementChild?.tagName === 'STRONG' && p.textContent.trim()) {
                return;
            }

            // Find first text node at paragraph start.
            let firstText = null;
            for (const child of p.childNodes) {
                if (child.nodeType === Node.TEXT_NODE) {
                    if (child.textContent.trim()) {
                        firstText = child;
                        break;
                    }
                    continue;
                }
                // Starts with non-text content; not our pattern.
                return;
            }
            if (!firstText) return;

            const text = firstText.textContent.replace(/^\s+/, '');
            const labelMatch = text.match(/^([A-Za-z]+)\s+/);
            if (!labelMatch) return;
            const label = labelMatch[1];
            if (!labels.has(label)) return;

            // Require a ":" somewhere in the paragraph for "X <code>...: ..."
            if (!p.textContent.includes(':')) return;

            // Split at first whitespace after label in the leading text node.
            firstText.textContent = text.slice(label.length).replace(/^\s+/, '');

            const labelP = document.createElement('p');
            const strong = document.createElement('strong');
            strong.textContent = label;
            labelP.appendChild(strong);

            p.parentNode?.insertBefore(labelP, p);
        });
    }

    function styleWithWithoutLineCounts() {
        const containers = document.querySelectorAll(
            '.module-page p, .module-page details summary, .about-page p, .about-page details summary, .why-page p, .why-page details summary'
        );

        containers.forEach(el => {
            if (el.querySelector('.line-count-number')) return;

            const normalizedText = el.textContent.replace(/\s+/g, ' ').trim().toLowerCase();
            if (!normalizedText.includes('lines')) return;
            if (!/\b(with|without)\b/.test(normalizedText)) return;

            // Primary pattern in docs: "With/Without <code>x</code> - <em>92 lines</em>"
            const emBlocks = el.querySelectorAll('em');
            let styledFromEm = false;
            emBlocks.forEach(em => {
                if (em.closest('pre, code')) return;
                const match = em.textContent.match(/^\s*(\d+\+?)\s+lines\b/i);
                if (!match) return;

                const numberSpan = document.createElement('span');
                numberSpan.className = 'line-count-number';
                numberSpan.textContent = `${match[1]} lines`;

                em.textContent = '';
                em.appendChild(numberSpan);
                styledFromEm = true;
            });
            if (styledFromEm) {
                el.classList.add('line-count-row');
                return;
            }

            // Fallback for plain text: "... - 92 lines"
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
                acceptNode(node) {
                    if (!node.textContent || !node.textContent.trim()) return NodeFilter.FILTER_REJECT;
                    const parent = node.parentElement;
                    if (!parent) return NodeFilter.FILTER_REJECT;
                    if (parent.closest('pre, code, .line-count-number')) return NodeFilter.FILTER_REJECT;
                    return NodeFilter.FILTER_ACCEPT;
                }
            });

            const nodesToPatch = [];
            let currentNode = walker.nextNode();
            while (currentNode) {
                if (/-\s*\d+\+?\s+lines\b/i.test(currentNode.textContent)) {
                    nodesToPatch.push(currentNode);
                }
                currentNode = walker.nextNode();
            }

            nodesToPatch.forEach(node => {
                const text = node.textContent;
                const match = text.match(/-\s*(\d+\+?)\s+lines\b/i);
                if (!match || match.index === undefined) return;

                const prefix = text.slice(0, match.index);
                const suffix = text.slice(match.index + match[0].length);
                const fragment = document.createDocumentFragment();

                if (prefix) fragment.appendChild(document.createTextNode(prefix));
                fragment.appendChild(document.createTextNode('- '));

                const numberSpan = document.createElement('span');
                numberSpan.className = 'line-count-number';
                numberSpan.textContent = `${match[1]} lines`;
                fragment.appendChild(numberSpan);
                if (suffix) fragment.appendChild(document.createTextNode(suffix));

                node.parentNode?.replaceChild(fragment, node);
            });

            if (nodesToPatch.length > 0) {
                el.classList.add('line-count-row');
            }
        });
    }

    function compactProsConsSpacing() {
        const paragraphs = document.querySelectorAll('.module-page p, .about-page p, .why-page p');

        paragraphs.forEach((p) => {
            const text = p.textContent.trim();
            const isProsCons = /^(Pros|Cons):\s+/i.test(text);
            if (!isProsCons) return;

            p.classList.add('pros-cons-line');

            // Label-only styling: color just "Pros:" / "Cons:" (not whole line).
            if (!p.querySelector('.pros-cons-label')) {
                let firstTextNode = null;
                for (const child of p.childNodes) {
                    if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
                        firstTextNode = child;
                        break;
                    }
                    if (child.nodeType === Node.ELEMENT_NODE) {
                        break;
                    }
                }

                if (firstTextNode) {
                    const labelMatch = firstTextNode.textContent.match(/^\s*(Pros|Cons):\s*/i);
                    if (labelMatch && labelMatch.index !== undefined) {
                        const fullMatch = labelMatch[0];
                        const labelOnly = labelMatch[1];
                        const rest = firstTextNode.textContent.slice(fullMatch.length);

                        const fragment = document.createDocumentFragment();
                        const labelSpan = document.createElement('span');
                        labelSpan.className = 'pros-cons-label';
                        labelSpan.textContent = `${labelOnly}:`;
                        fragment.appendChild(labelSpan);
                        if (rest.length > 0) {
                            fragment.appendChild(document.createTextNode(` ${rest.replace(/^\s+/, '')}`));
                        }
                        firstTextNode.parentNode?.replaceChild(fragment, firstTextNode);
                    }
                }
            }

            const prev = p.previousElementSibling;
            if (prev && prev.tagName === 'P') {
                prev.classList.add('before-pros-cons');
            }
        });
    }

    // Global state for API highlight toggle
    let apiHighlightEnabled = true;
    const API_FLICKER_BASE_CHANCE = 0.03;
    const SKAPI_PLACEHOLDER_PATTERN = /__SKAPI_(?:TOKEN|AUTO)_(\d+)__/g;
    const NOT_API_PLACEHOLDER_PATTERN = /__NOT_API_(\d+)__/g;
    const skapiManualTokenMap = new Map();
    const notApiTokenMap = new Map();
    function isWithoutComparisonContext(node) {
        const details = node?.closest?.('details');
        if (!details) return false;
        const summary = details.querySelector(':scope > summary');
        if (!summary) return false;
        const text = (summary.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
        return text.startsWith('without ');
    }
    const KNOWN_SKAPI_TOKENS = Array.from(new Set([
        // modules
        'suitkaise', 'timing', 'paths', 'circuits', 'cucumber', 'processing', 'sk', 'docs',
        // classes / errors
        'Skpath', 'AnyPath', 'CustomRoot', 'PathDetectionError', 'NotAFileError',
        'Sktimer', 'TimeThis', 'Circuit', 'BreakingCircuit',
        'SerializationError', 'DeserializationError',
        'Skprocess', 'Pool', 'Share', 'Pipe', 'ProcessTimers',
        'ProcessError', 'PreRunError', 'RunError', 'PostRunError', 'OnFinishError',
        'ResultError', 'ErrorHandlerError', 'ProcessTimeoutError', 'ResultTimeoutError',
        'AsyncSkfunction', 'SkModifierError', 'FunctionTimeoutError',
        // functions / helpers
        'timethis', 'clear_global_timers', 'autopath',
        'get_project_root', 'set_custom_root', 'get_custom_root', 'clear_custom_root',
        'get_caller_path', 'get_current_dir', 'get_cwd', 'get_module_path', 'get_id',
        'get_project_paths', 'get_project_structure', 'get_formatted_project_tree',
        'is_valid_filename', 'streamline_path', 'streamline_path_quick',
        'serialize', 'serialize_ir', 'deserialize_ir', 'deserialize', 'reconnect_all',
        'ir_to_jsonable', 'ir_to_json', 'to_jsonable', 'to_json',
        'autoreconnect', 'Reconnector', 'sk', 'blocking',
        // NOTE:
        // Keep auto-tagging conservative. Generic member/property names (result, run,
        // error, times, etc.) are intentionally excluded here and handled by the
        // context-aware highlighter below to avoid false positives in local variables.
        'asynced', 'background', 'rate_limit',
        'has_blocking_calls', 'blocking_calls',
        // Skprocess lifecycle dunders
        '__prerun__', '__run__', '__postrun__', '__onfinish__', '__result__', '__error__',
    ]));

    function autoTagKnownAPIInCode() {
        const scope = document.querySelector('.module-page, .about-page, .why-page, .home-page');
        if (!scope) return;

        const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const tokenPattern = KNOWN_SKAPI_TOKENS
            .slice()
            .sort((a, b) => b.length - a.length)
            .map(escapeRegex)
            .join('|');
        if (!tokenPattern) return;
        const tokenRegex = new RegExp(`\\b(${tokenPattern})\\b`, 'g');

        const codeEls = scope.querySelectorAll('code');
        codeEls.forEach((codeEl) => {
            if (codeEl.classList.contains('language-text')) return;
            if (codeEl.closest('suitkaise-api')) return;
            if (codeEl.closest('not-api')) return;
            if (isWithoutComparisonContext(codeEl)) return;

            const walker = document.createTreeWalker(codeEl, NodeFilter.SHOW_TEXT, null, false);
            const textNodes = [];
            let node;
            while ((node = walker.nextNode())) {
                const parent = node.parentElement;
                if (!parent) continue;
                if (parent.closest('suitkaise-api')) continue;
                if (parent.closest('not-api')) continue;
                if (!node.textContent || !node.textContent.trim()) continue;
                textNodes.push(node);
            }

            textNodes.forEach((textNode) => {
                const text = textNode.textContent;
                tokenRegex.lastIndex = 0;
                if (!tokenRegex.test(text)) return;
                tokenRegex.lastIndex = 0;

                const frag = document.createDocumentFragment();
                let lastIndex = 0;
                let match;
                while ((match = tokenRegex.exec(text)) !== null) {
                    if (match.index > 0 && text[match.index - 1] === '.') {
                        const before = text.slice(0, match.index - 1);
                        const prevWord = before.match(/(\w+)$/);
                        if (prevWord && !KNOWN_SKAPI_TOKENS.includes(prevWord[1])) {
                            continue;
                        }
                    }
                    if (match.index > lastIndex) {
                        frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
                    }
                    const tag = document.createElement('suitkaise-api');
                    tag.setAttribute('data-auto', '');
                    tag.textContent = match[1];
                    frag.appendChild(tag);
                    lastIndex = tokenRegex.lastIndex;
                }
                if (lastIndex < text.length) {
                    frag.appendChild(document.createTextNode(text.slice(lastIndex)));
                }

                textNode.parentNode?.replaceChild(frag, textNode);
            });
        });
    }

    function preprocessManualAPITags() {
        skapiManualTokenMap.clear();
        let tokenIndex = 0;
        const isHowItWorksPage = /\-how-it-works\b/.test(window.location.hash || '');
        const genericInternalMethodTokens = new Set([
            'start', 'stop', 'pause', 'resume', 'lap', 'discard'
        ]);

        notApiTokenMap.clear();
        let notApiIndex = 0;
        const notApiTags = document.querySelectorAll('not-api');
        notApiTags.forEach((tag) => {
            const text = tag.textContent || '';
            const placeholder = `__NOT_API_${notApiIndex++}__`;
            notApiTokenMap.set(placeholder, text);
            tag.replaceWith(document.createTextNode(placeholder));
        });

        const manualTags = document.querySelectorAll('suitkaise-api');
        manualTags.forEach((tag) => {
            const tokenText = (tag.textContent || '').trim();
            if (!tokenText) {
                tag.remove();
                return;
            }

            // In explicit "Without ..." comparison blocks, keep raw text unhighlighted.
            if (isWithoutComparisonContext(tag)) {
                tag.replaceWith(document.createTextNode(tokenText));
                return;
            }

            // In fenced code blocks, Prism would strip unknown tags. Replace with
            // a stable placeholder, then restore to .api-highlight after highlighting.
            // Exception: language-text blocks aren't processed by Prism or
            // styleAPIHighlights, so convert directly to a span there.
            const closestCode = tag.closest('pre code');
            if (closestCode) {
                // In "*-how-it-works" pages, keep internal implementation calls like
                // `sess.start()` plain (they are implementation details, not API docs).
                if (
                    isHowItWorksPage &&
                    closestCode.classList.contains('language-python') &&
                    genericInternalMethodTokens.has(tokenText)
                ) {
                    tag.replaceWith(document.createTextNode(tokenText));
                    return;
                }
                if (closestCode.classList.contains('language-text')) {
                    const span = document.createElement('span');
                    span.className = 'api-highlight api-highlight-manual';
                    span.textContent = tokenText;
                    tag.replaceWith(span);
                    return;
                }
                const isAuto = tag.hasAttribute('data-auto');
                const prefix = isAuto ? '__SKAPI_AUTO_' : '__SKAPI_TOKEN_';
                const placeholder = `${prefix}${tokenIndex++}__`;
                skapiManualTokenMap.set(placeholder, tokenText);
                tag.replaceWith(document.createTextNode(placeholder));
                return;
            }

            // Outside fenced blocks, convert directly to highlighted span.
            const span = document.createElement('span');
            span.className = 'api-highlight api-highlight-manual';
            span.textContent = tokenText;
            tag.replaceWith(span);
        });
    }

    function getAPIFlickerChance() {
        // Temporary debug override:
        // - URL: ?apiFlickerDebug=1
        // - localStorage: apiFlickerDebug = "1" (or "true")
        const params = new URLSearchParams(window.location.search);
        const urlDebug = params.get('apiFlickerDebug');
        const storageDebug = localStorage.getItem('apiFlickerDebug');
        const debugEnabled =
            urlDebug === '1' || urlDebug === 'true' ||
            storageDebug === '1' || storageDebug === 'true';
        return debugEnabled ? 1 : API_FLICKER_BASE_CHANCE;
    }

    function triggerAPIFlickerOnActivate() {
        const modulePage = document.querySelector('.module-page, .about-page, .why-page, .home-page');
        if (!modulePage || !modulePage.classList.contains('highlight-active')) return;

        const apiTokens = Array.from(modulePage.querySelectorAll('.api-highlight'));
        if (apiTokens.length === 0) return;
        // Exact behavior: each API token independently gets a 3% flicker chance on toggle-on.
        // Debug mode can temporarily force this to 100% via getAPIFlickerChance().
        modulePage.querySelectorAll('.api-highlight.api-flicker').forEach((el) => {
            el.classList.remove('api-flicker');
        });
        void modulePage.offsetWidth;
        const flickerChance = getAPIFlickerChance();
        apiTokens.forEach((el) => {
            if (Math.random() < flickerChance) {
                el.classList.add('api-flicker');
                el.addEventListener('animationend', () => {
                    el.classList.remove('api-flicker');
                }, { once: true });
            }
        });
    }
    
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
        const modulePage = document.querySelector('.module-page, .about-page, .why-page, .home-page');
        if (modulePage) {
            if (apiHighlightEnabled) {
                modulePage.classList.add('highlight-active');
                triggerAPIFlickerOnActivate();
            } else {
                modulePage.classList.remove('highlight-active');
                // Ensure no flicker animation can continue while highlight is off.
                modulePage.querySelectorAll('.api-highlight.api-flicker').forEach((el) => {
                    el.classList.remove('api-flicker');
                });
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
        const modulePage = document.querySelector('.module-page, .about-page, .why-page, .home-page');
        if (modulePage && apiHighlightEnabled) {
            modulePage.classList.add('highlight-active');
        }
    }

    function styleAPIHighlights() {
        // API identifiers to highlight
        const apiModules = new Set([
            'suitkaise',
            'timing',
            'paths',
            'circuits',
            'cucumber',
            'processing',
            'sk',
            'docs',
        ]);
        const apiClasses = new Set([
            // paths
            'Skpath', 'AnyPath', 'CustomRoot', 'PathDetectionError',
            'NotAFileError',
            // timing
            'Sktimer', 'TimeThis',
            // circuits
            'Circuit', 'BreakingCircuit',
            // cucumber
            'Reconnector', 'SerializationError', 'DeserializationError',
            // processing
            'Skprocess', 'Pool', 'Share', 'Pipe', 'ProcessTimers',
            'ProcessError', 'PreRunError', 'RunError', 'PostRunError', 'OnFinishError',
            'ResultError', 'ErrorHandlerError', 'ProcessTimeoutError', 'ResultTimeoutError',
            // sk
            'AsyncSkfunction', 'SkModifierError', 'FunctionTimeoutError',
        ]);
        // Keep ambiguous names ('time', 'sleep') out of standalone highlighting
        // to avoid false positives with Python stdlib usage. They still highlight
        // in module chains (e.g. timing.time()) because module names are tracked.
        const apiMethods = new Set([
            // timing
            'elapsed', 'timethis', 'clear_global_timers',
            // paths
            'autopath', 'get_project_root', 'set_custom_root', 'get_custom_root', 'clear_custom_root',
            'get_caller_path', 'get_current_dir', 'get_cwd', 'get_module_path', 'get_id',
            'get_project_paths', 'get_project_structure', 'get_formatted_project_tree',
            'is_valid_filename', 'streamline_path', 'streamline_path_quick',
            // cucumber
            'serialize', 'serialize_ir', 'deserialize_ir', 'deserialize', 'reconnect_all',
            'ir_to_jsonable', 'ir_to_json', 'to_jsonable', 'to_json',
            // processing
            'autoreconnect',
            // Skprocess lifecycle methods
            '__prerun__', '__run__', '__postrun__', '__onfinish__', '__result__', '__error__',
            // sk
            'sk', 'blocking',
        ]);
        // Members that often appear after API roots in docs/examples.
        // We do not highlight these as standalone identifiers to avoid
        // generic-word false positives; they are used for smarter root
        // detection and chain propagation only.
        const apiMembers = new Set([
            // timing / Sktimer
            'start', 'stop', 'lap', 'pause', 'resume', 'discard', 'add_time', 'reset',
            'set_max_times', 'most_recent', 'total_time', 'mean', 'stdev', 'variance',
            'times', 'num_times', 'percentile',
            // processing / Pool / Skprocess
            'map', 'imap', 'unordered_map', 'unordered_imap', 'star',
            'wait', 'result', 'tell', 'listen', 'kill', 'process_config',
            'runs', 'join_in', 'lives', 'timeouts', 'prerun', 'run', 'postrun', 'onfinish', 'error',
            // circuits
            'short', 'trip', 'reset_backoff', 'broken', 'times_shorted', 'total_trips',
            'current_sleep_time', 'num_shorts_to_trip',
            // sk / wrapped functions
            'asynced', 'retry', 'timeout', 'background', 'rate_limit', 'has_blocking_calls',
            'blocking_calls', 'timer',
            // cucumber / reconnector
            'reconnect',
            // paths / skpath-ish usage
            'ap', 'rp', 'id', 'root', 'parent',
        ]);
        
        // Overrides: properties that should highlight word.property.chain patterns
        // These only activate if their associated decorator is found in the code block
        const overrideConfig = {
            'timer': '@timing.timethis'  // timer property only highlights if @timing.timethis decorator exists
        };
        
        // Find all code elements (inline + block). Inline code needs API highlighting too.
        const codeBlocks = document.querySelectorAll('.module-page code, .about-page code, .why-page code, .home-page code');
        
        codeBlocks.forEach(codeBlock => {
            // Plain text blocks (tracebacks, logs, ASCII diagrams) should not get API highlight.
            if (codeBlock.classList.contains('language-text')) {
                return;
            }
            if (isWithoutComparisonContext(codeBlock)) {
                return;
            }

            // Manual API overrides:
            // - data-skapi-extra="token1,token2"  -> force-add highlightable API tokens
            // - data-skapi-ignore="token1,token2" -> suppress tokens for this scope
            // - data-skapi-roots="token1,token2"  -> allow anyRoot.token.chain highlighting
            // Attributes can be set on <code>, enclosing <pre>, or page <section>.
            const preEl = codeBlock.closest('pre');
            const pageSection = codeBlock.closest('.module-page, .about-page, .why-page, .home-page');
            const readSkapiSet = (attrName) => {
                const raw =
                    codeBlock.getAttribute(attrName) ||
                    preEl?.getAttribute(attrName) ||
                    pageSection?.getAttribute(attrName) ||
                    '';
                return new Set(
                    raw
                        .split(',')
                        .map(s => s.trim())
                        .filter(Boolean)
                );
            };
            const manualApiExtra = readSkapiSet('data-skapi-extra');
            const manualApiIgnore = readSkapiSet('data-skapi-ignore');
            const manualChainRoots = readSkapiSet('data-skapi-roots');
            const manualOnlyAttr =
                codeBlock.getAttribute('data-skapi-manual-only') ||
                preEl?.getAttribute('data-skapi-manual-only') ||
                pageSection?.getAttribute('data-skapi-manual-only') ||
                '';
            const manualOnly = /^(1|true|yes|on)$/i.test(manualOnlyAttr.trim());

            // Track variables assigned to API objects in this block
            const apiVariables = new Set();
            // API variables discovered from explicit syntax (imports/assignments/inheritance).
            // Used to prevent inferred-root cleanup from unwrapping real API vars.
            const explicitApiVariables = new Set();
            // Roots inferred from member-chain usage (no import/assignment context)
            // should only be highlighted when actually connected to a chain.
            const inferredApiRoots = new Set();
            
            // Get the text content to analyze for variable assignments.
            // <suitkaise-api> tags have been replaced with __SKAPI_TOKEN_n__ (manual)
            // or __SKAPI_AUTO_n__ (auto) placeholders by preprocessManualAPITags().
            // Restore them so patterns like `share = Share(` match correctly.
            let textContent = codeBlock.textContent;
            for (const [placeholder, original] of skapiManualTokenMap) {
                while (textContent.includes(placeholder)) {
                    textContent = textContent.replace(placeholder, original);
                }
            }
            for (const [placeholder, original] of notApiTokenMap) {
                while (textContent.includes(placeholder)) {
                    textContent = textContent.replace(placeholder, original);
                }
            }
            
            // Determine which overrides are active based on decorators found in code block
            const activeOverrides = new Set();
            for (const [property, requiredDecorator] of Object.entries(overrideConfig)) {
                if (textContent.includes(requiredDecorator)) {
                    activeOverrides.add(property);
                }
            }
            
            // Build dynamic patterns from our API sets
            const classesPattern = [...apiClasses].join('|');
            const methodsPattern = [...apiMethods].join('|');
            const membersPattern = [...apiMembers].join('|');
            const modulesPattern = [...apiModules].join('|');
            
            // Detect imported aliases and imported API names, e.g.:
            //   import suitkaise as sks
            //   from suitkaise import timing as tm, Sktimer
            //   from suitkaise.paths import Skpath as P
            const importAsPattern = /\bimport\s+suitkaise\s+as\s+(\w+)/g;
            let importMatch;
            while ((importMatch = importAsPattern.exec(textContent)) !== null) {
                apiVariables.add(importMatch[1]);
                explicitApiVariables.add(importMatch[1]);
            }
            
            const fromSuitkaiseImportPattern = /\bfrom\s+suitkaise(?:\.\w+)?\s+import\s+([^\n#]+)/g;
            while ((importMatch = fromSuitkaiseImportPattern.exec(textContent)) !== null) {
                const rawImports = importMatch[1].split(',');
                rawImports.forEach(part => {
                    const trimmed = part.trim();
                    if (!trimmed) return;
                    const aliasMatch = trimmed.match(/^(\w+)\s+as\s+(\w+)$/);
                    const importedName = aliasMatch ? aliasMatch[1] : trimmed;
                    const localName = aliasMatch ? aliasMatch[2] : importedName;
                    if (apiModules.has(importedName) || apiClasses.has(importedName) || apiMethods.has(importedName)) {
                        apiVariables.add(localName);
                        explicitApiVariables.add(localName);
                    }
                });
            }
            
            // Infer API roots from member-chain usage when imports/assignments
            // are not present in the snippet. Example:
            //   pool.star().unordered_map.timeout(...)
            const rootInferenceMembers = new Set([
                // high-signal processing chains
                'map', 'imap', 'unordered_map', 'unordered_imap', 'star',
                // high-signal sk/timing chains
                'asynced', 'background', 'timethis',
                // high-signal module-specific helpers
                'autopath', 'serialize_ir', 'reconnect_all',
                // high-signal timer/circuit properties
                'percentile', 'num_times', 'most_recent',
                'total_trips', 'times_shorted', 'current_sleep_time', 'reset_backoff',
            ]);
            const ambiguousInferenceMembers = new Set([
                // useful, but can be generic in arbitrary code
                'broken', 'result', 'wait', 'start', 'stop', 'mean', 'stdev', 'variance', 'timer',
            ]);
            const memberChainPattern = /\b([A-Za-z_]\w*)((?:\.[A-Za-z_]\w*)+)\s*(?:\(|$)/g;
            const instanceKeywords = new Set(['self', 'cls']);
            let chainMatch;
            while ((chainMatch = memberChainPattern.exec(textContent)) !== null) {
                const root = chainMatch[1];
                if (instanceKeywords.has(root)) continue;
                const segments = chainMatch[2]
                    .split('.')
                    .filter(Boolean);
                const hasStrongSignal = segments.some(segment => rootInferenceMembers.has(segment));
                const hasAmbiguousSignal = segments.some(segment => ambiguousInferenceMembers.has(segment));
                const rootLooksApiLike = /(?:pool|process|proc|timer|timing|circ|circuit|breaker|share|pipe|worker|future)/i.test(root);
                if (hasStrongSignal || (hasAmbiguousSignal && rootLooksApiLike)) {
                    apiVariables.add(root);
                    inferredApiRoots.add(root);
                }
            }
            
            // Detect user classes that inherit from API classes, e.g.:
            //   class Doubler(Skprocess):
            //   class MyWorker(processing.Skprocess):
            //   class MyProc(BaseSkprocessAlias):
            const apiDerivedClasses = new Set();
            const classInheritancePattern = /\bclass\s+(\w+)\s*\(([^)]*)\)\s*:/g;
            let classMatch;
            while ((classMatch = classInheritancePattern.exec(textContent)) !== null) {
                const className = classMatch[1];
                const baseList = classMatch[2];
                const bases = baseList.split(',').map(base => base.trim()).filter(Boolean);
                
                let inheritsFromApi = false;
                for (const base of bases) {
                    // Strip simple generic syntax (e.g., Base[T]) for matching.
                    const noGenerics = base.replace(/\[.*$/, '');
                    const parts = noGenerics.split('.');
                    const first = parts[0];
                    const last = parts[parts.length - 1];
                    
                    if (
                        apiClasses.has(noGenerics) || apiClasses.has(last) ||
                        apiVariables.has(noGenerics) || apiVariables.has(last) ||
                        apiModules.has(first)
                    ) {
                        inheritsFromApi = true;
                        break;
                    }
                }
                
                if (inheritsFromApi) {
                    apiDerivedClasses.add(className);
                    // Treat subclasses of API types as API roots for chain highlighting.
                    apiVariables.add(className);
                    explicitApiVariables.add(className);
                }
            }
            
            const knownClassesPattern = [...apiClasses, ...apiDerivedClasses].join('|');
            
            // Find variable assignments iteratively. Chain calls like
            // elapsed = timer.stop() require timer to be detected first,
            // so we loop until no new variables are discovered.
            let prevApiVarSize;
            do {
                prevApiVarSize = apiVariables.size;
                const knownWithRoots = [...apiModules, ...apiVariables]
                    .filter(Boolean)
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .sort((a, b) => b.length - a.length)
                    .join('|');
                const assignmentPatterns = [
                    new RegExp(`(?<!\\.)\\b(\\w+)\\s*=\\s*(?:${knownWithRoots})\\.\\w+`, 'g'),
                    new RegExp(`(?<!\\.)\\b(\\w+)\\s*:\\s*[\\w\\[\\],\\s|]+\\s*=\\s*(?:${knownWithRoots})\\.\\w+`, 'g'),
                    new RegExp(`(?<!\\.)\\b(\\w+)\\s*=\\s*(?:${knownClassesPattern})\\s*\\(`, 'g'),
                    new RegExp(`(?<!\\.)\\b(\\w+)\\s*:\\s*[\\w\\[\\],\\s|]+\\s*=\\s*(?:${knownClassesPattern})\\s*\\(`, 'g'),
                    new RegExp(`(?<!\\.)\\b(\\w+)\\s*=\\s*(?:${methodsPattern})\\s*\\(`, 'g'),
                    ...(knownWithRoots ? [new RegExp(`with\\s+(?:${knownWithRoots})\\.\\w+[^:]*\\s+as\\s+(\\w+)`, 'g')] : []),
                    new RegExp(`with\\s+(?:${knownClassesPattern}|${methodsPattern})[^:]*\\s+as\\s+(\\w+)`, 'g'),
                ];
                
                assignmentPatterns.forEach(pattern => {
                    let match;
                    while ((match = pattern.exec(textContent)) !== null) {
                        if (match[1] && !instanceKeywords.has(match[1])) {
                            apiVariables.add(match[1]);
                            explicitApiVariables.add(match[1]);
                        }
                    }
                });
            } while (apiVariables.size > prevApiVarSize);
            if (apiVariables.size > 0) console.debug('[SK-API] apiVariables:', [...apiVariables], 'textContent sample:', textContent.slice(0, 200));
            
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
                // Skip if inside a comment or string span
                let parent = node.parentElement;
                let isCommentOrString = false;
                while (parent && parent !== codeBlock) {
                    if (parent.classList && (parent.classList.contains('comment') || parent.classList.contains('string'))) {
                        isCommentOrString = true;
                        break;
                    }
                    parent = parent.parentElement;
                }
                const hasPlaceholder = node.textContent && (node.textContent.includes('__SKAPI_TOKEN_') || node.textContent.includes('__SKAPI_AUTO_') || node.textContent.includes('__NOT_API_'));
                if (((!isCommentOrString && node.textContent.trim()) || hasPlaceholder)) {
                    nodesToProcess.push(node);
                }
            }
            
            // === PASS 1: Restore placeholders ===
            // Manual tags (__SKAPI_TOKEN_) always highlight (even in strings/comments).
            // Auto tags (__SKAPI_AUTO_) revert to plain text inside comments/strings.
            nodesToProcess.forEach(textNode => {
                const text = textNode.textContent;
                if (text && (text.includes('__SKAPI_TOKEN_') || text.includes('__SKAPI_AUTO_'))) {
                    SKAPI_PLACEHOLDER_PATTERN.lastIndex = 0;
                    if (SKAPI_PLACEHOLDER_PATTERN.test(text)) {
                        let inCommentOrString = false;
                        let ancestor = textNode.parentElement;
                        while (ancestor && ancestor !== codeBlock) {
                            if (ancestor.classList && (ancestor.classList.contains('comment') || ancestor.classList.contains('string'))) {
                                inCommentOrString = true;
                                break;
                            }
                            ancestor = ancestor.parentElement;
                        }
                        SKAPI_PLACEHOLDER_PATTERN.lastIndex = 0;
                        const parts = [];
                        let lastIdx = 0;
                        let m;
                        while ((m = SKAPI_PLACEHOLDER_PATTERN.exec(text)) !== null) {
                            const matchStart = m.index;
                            const fullMatch = m[0];
                            if (matchStart > lastIdx) {
                                parts.push(document.createTextNode(text.slice(lastIdx, matchStart)));
                            }
                            const replacementText = skapiManualTokenMap.get(fullMatch) || fullMatch;
                            const isAuto = fullMatch.startsWith('__SKAPI_AUTO_');
                            if (isAuto && inCommentOrString) {
                                parts.push(document.createTextNode(replacementText));
                            } else {
                                const span = document.createElement('span');
                                span.className = 'api-highlight api-highlight-manual';
                                span.textContent = replacementText;
                                parts.push(span);
                            }
                            lastIdx = matchStart + fullMatch.length;
                        }
                        if (lastIdx < text.length) {
                            parts.push(document.createTextNode(text.slice(lastIdx)));
                        }
                        const parent = textNode.parentNode;
                        if (parent && parts.length > 0) {
                            parts.forEach(part => parent.insertBefore(part, textNode));
                            parent.removeChild(textNode);
                        }
                    }
                }
            });
            
            // === PASS 2: Auto-highlight API identifiers ===
            // Re-walk the DOM so text nodes created during placeholder restoration
            // (e.g. "timer " split from " __SKAPI_AUTO_1__\n\ntimer ") are included.
            if (!manualOnly) {
                const autoWalker = document.createTreeWalker(
                    codeBlock,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                const autoNodesToProcess = [];
                let autoNode;
                while (autoNode = autoWalker.nextNode()) {
                    let parent = autoNode.parentElement;
                    let skip = false;
                    while (parent && parent !== codeBlock) {
                        if (parent.classList && (
                            parent.classList.contains('comment') ||
                            parent.classList.contains('string') ||
                            parent.classList.contains('api-highlight') ||
                            parent.classList.contains('api-highlight-manual')
                        )) {
                            skip = true;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    if (!skip && autoNode.textContent.trim()) {
                        autoNodesToProcess.push(autoNode);
                    }
                }
                
                const allIdentifiers = [
                    ...apiModules,
                    ...apiClasses, 
                    ...apiDerivedClasses,
                    ...apiMethods,
                    ...apiVariables,
                    ...activeOverrides,
                    ...manualApiExtra,
                ].filter(id => !manualApiIgnore.has(id));
                const alwaysChainRoots = [
                    'process_config',
                    ...manualChainRoots
                ].filter(id => !manualApiIgnore.has(id));
                
                const identifierPattern = allIdentifiers
                    .sort((a, b) => b.length - a.length)
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                const chainSegmentPattern = [
                    ...apiMembers,
                    ...apiMethods,
                    ...apiClasses,
                    ...apiModules,
                    ...apiDerivedClasses,
                    ...activeOverrides,
                    ...manualApiExtra,
                ]
                    .filter(id => !manualApiIgnore.has(id))
                    .sort((a, b) => b.length - a.length)
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                const variablePattern = [...apiVariables]
                    .sort((a, b) => b.length - a.length)
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                const overridesPattern = [...activeOverrides]
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                const alwaysChainRootsPattern = alwaysChainRoots
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                
                let regexPattern = `(@(?:${identifierPattern})(?:\\.(?:${chainSegmentPattern}))*(?:\\(\\))?)|` +
                    `\\b(${identifierPattern})\\b(?:\\.(?:${chainSegmentPattern}))*(\\(\\))?`;
                if (alwaysChainRootsPattern) {
                    regexPattern += `|(\\b\\w+)\\.(${alwaysChainRootsPattern})(?:\\.(?:${chainSegmentPattern}))*(\\(\\))?`;
                }
                if (variablePattern) {
                    regexPattern += `|\\b(${variablePattern})\\b(?:\\.(?:${chainSegmentPattern}))+((?:\\(\\))?)`;
                }
                if (activeOverrides.size > 0) {
                    regexPattern = `(@(?:${identifierPattern})(?:\\.(?:${chainSegmentPattern}))*(?:\\(\\))?)|` +
                        `(\\b\\w+)\\.(${overridesPattern})(?:\\.(?:${chainSegmentPattern}))*(\\(\\))?|` +
                        `\\b(${identifierPattern})\\b(?:\\.(?:${chainSegmentPattern}))*(\\(\\))?`;
                    if (alwaysChainRootsPattern) {
                        regexPattern += `|(\\b\\w+)\\.(${alwaysChainRootsPattern})(?:\\.(?:${chainSegmentPattern}))*(\\(\\))?`;
                    }
                    if (variablePattern) {
                        regexPattern += `|\\b(${variablePattern})\\b(?:\\.(?:${chainSegmentPattern}))+((?:\\(\\))?)`;
                    }
                }
                const regex = new RegExp(regexPattern, 'g');
                
                autoNodesToProcess.forEach(textNode => {
                    const text = textNode.textContent;
                    
                    let hasMatch = false;
                    for (const id of allIdentifiers) {
                        if (text.includes(id)) {
                            hasMatch = true;
                            break;
                        }
                    }
                    if (!hasMatch && apiVariables.size > 0) {
                        for (const variable of apiVariables) {
                            if (text.includes(variable + '.')) {
                                hasMatch = true;
                                break;
                            }
                        }
                    }
                    if (text.includes('@')) hasMatch = true;
                    for (const id of activeOverrides) {
                        if (text.toLowerCase().includes(id)) {
                            hasMatch = true;
                            break;
                        }
                    }
                    if (!hasMatch) {
                        for (const root of alwaysChainRoots) {
                            if (text.includes(`.${root}`) || text.startsWith(`${root}.`) || text.includes(` ${root}.`)) {
                                hasMatch = true;
                                break;
                            }
                        }
                    }
                    
                    if (!hasMatch) return;
                    
                    regex.lastIndex = 0;
                    const parts = [];
                    let lastIndex = 0;
                    let match;
                    
                    while ((match = regex.exec(text)) !== null) {
                        const matchedText = match[0];
                        const matchStart = match.index;
                        const matchEnd = matchStart + matchedText.length;
                        
                        let nextIdx = matchEnd;
                        while (nextIdx < text.length && /\s/.test(text[nextIdx])) nextIdx++;
                        const hasEqualsAfter = nextIdx < text.length && text[nextIdx] === '=';
                        if (hasEqualsAfter) {
                            let prevIdx = matchStart - 1;
                            while (prevIdx >= 0 && /\s/.test(text[prevIdx])) prevIdx--;
                            const prevChar = prevIdx >= 0 ? text[prevIdx] : '';
                            if (prevChar === '(' || prevChar === ',') {
                                lastIndex = regex.lastIndex;
                                continue;
                            }
                        }
                        
                        if (match.index > lastIndex) {
                            parts.push(document.createTextNode(text.slice(lastIndex, match.index)));
                        }
                        
                        const span = document.createElement('span');
                        span.className = 'api-highlight';
                        span.textContent = match[0];
                        parts.push(span);
                        
                        lastIndex = regex.lastIndex;
                    }
                    
                    if (lastIndex < text.length) {
                        parts.push(document.createTextNode(text.slice(lastIndex)));
                    }
                    
                    if (parts.length > 0 && lastIndex > 0) {
                        const parent = textNode.parentNode;
                        parts.forEach(part => parent.insertBefore(part, textNode));
                        parent.removeChild(textNode);
                    }
                });
            }
            
            // Second pass: extend api-highlight to include adjacent "()"
            // This handles cases where Prism split parens into separate tokens.
            const absorbAdjacentCallParens = (highlight) => {
                let nextSibling = highlight.nextSibling;
                while (nextSibling && nextSibling.nodeType === Node.TEXT_NODE && !nextSibling.textContent.trim()) {
                    nextSibling = nextSibling.nextSibling;
                }
                if (!nextSibling) return false;

                let textToAdd = '';
                const nodesToRemove = [];

                if (nextSibling.nodeType === Node.TEXT_NODE) {
                    const text = nextSibling.textContent;
                    if (text.startsWith('()')) {
                        textToAdd = '()';
                        if (text === '()') {
                            nodesToRemove.push(nextSibling);
                        } else {
                            nextSibling.textContent = text.slice(2);
                        }
                    } else if (text === '(') {
                        let afterOpen = nextSibling.nextSibling;
                        while (afterOpen && afterOpen.nodeType === Node.TEXT_NODE && !afterOpen.textContent.trim()) {
                            afterOpen = afterOpen.nextSibling;
                        }
                        if (afterOpen) {
                            const afterText = afterOpen.textContent || '';
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
                } else if (nextSibling.nodeType === Node.ELEMENT_NODE) {
                    const text = nextSibling.textContent;
                    if (text === '()') {
                        textToAdd = '()';
                        nodesToRemove.push(nextSibling);
                    } else if (text === '(') {
                        let afterOpen = nextSibling.nextSibling;
                        while (afterOpen && afterOpen.nodeType === Node.TEXT_NODE && !afterOpen.textContent.trim()) {
                            afterOpen = afterOpen.nextSibling;
                        }
                        if (afterOpen) {
                            const afterText = afterOpen.textContent || '';
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

                if (!textToAdd) return false;
                highlight.textContent += textToAdd;
                nodesToRemove.forEach(n => n.parentNode && n.parentNode.removeChild(n));
                return true;
            };

            const absorbAdjacentApiPrefix = (highlight) => {
                let prevSibling = highlight.previousSibling;
                while (prevSibling && prevSibling.nodeType === Node.TEXT_NODE && !prevSibling.textContent.trim()) {
                    prevSibling = prevSibling.previousSibling;
                }
                if (!prevSibling) return false;

                let prefixChar = '';
                if (prevSibling.nodeType === Node.TEXT_NODE) {
                    const text = prevSibling.textContent;
                    if (text.endsWith('@') || text.endsWith('.')) {
                        prefixChar = text.slice(-1);
                        const remaining = text.slice(0, -1);
                        if (remaining.length > 0) {
                            prevSibling.textContent = remaining;
                        } else if (prevSibling.parentNode) {
                            prevSibling.parentNode.removeChild(prevSibling);
                        }
                    }
                } else if (prevSibling.nodeType === Node.ELEMENT_NODE) {
                    const text = (prevSibling.textContent || '').trim();
                    if (text === '@' || text === '.') {
                        prefixChar = text;
                        if (prevSibling.parentNode) prevSibling.parentNode.removeChild(prevSibling);
                    }
                }

                if (!prefixChar) return false;
                highlight.textContent = prefixChar + highlight.textContent;
                return true;
            };

            const mergeAdjacentApiDotChains = () => {
                let mergedAny = false;
                let keepMerging = true;
                while (keepMerging) {
                    keepMerging = false;
                    const highlights = Array.from(codeBlock.querySelectorAll('.api-highlight'));
                    for (const left of highlights) {
                        let dotNode = left.nextSibling;
                        while (dotNode && dotNode.nodeType === Node.TEXT_NODE && !dotNode.textContent.trim()) {
                            dotNode = dotNode.nextSibling;
                        }
                        if (!dotNode) continue;

                        const isDotNode =
                            (dotNode.nodeType === Node.TEXT_NODE && dotNode.textContent === '.') ||
                            (dotNode.nodeType === Node.ELEMENT_NODE && dotNode.textContent === '.');
                        if (!isDotNode) continue;

                        let right = dotNode.nextSibling;
                        while (right && right.nodeType === Node.TEXT_NODE && !right.textContent.trim()) {
                            right = right.nextSibling;
                        }
                        if (!right || !(right.nodeType === Node.ELEMENT_NODE && right.classList.contains('api-highlight'))) continue;

                        left.textContent += '.' + right.textContent;
                        if (dotNode.parentNode) dotNode.parentNode.removeChild(dotNode);
                        if (right.parentNode) right.parentNode.removeChild(right);
                        absorbAdjacentCallParens(left);
                        keepMerging = true;
                        mergedAny = true;
                        break;
                    }
                }
                return mergedAny;
            };

            let punctuationChanged = true;
            while (punctuationChanged) {
                punctuationChanged = false;
                codeBlock.querySelectorAll('.api-highlight').forEach((highlight) => {
                    if (absorbAdjacentApiPrefix(highlight)) punctuationChanged = true;
                    if (absorbAdjacentCallParens(highlight)) punctuationChanged = true;
                });
                if (mergeAdjacentApiDotChains()) punctuationChanged = true;
            }

            // Highlight call parens for API calls WITH arguments.
            // After the punctuation pass, any api-highlight that already ends
            // with "()" was a no-arg call and is complete.  For the rest, check
            // if the next token is "(" (with args), absorb it, then find and
            // highlight the matching ")".
            codeBlock.querySelectorAll('.api-highlight').forEach(highlight => {
                if (highlight.textContent.endsWith('()')) return;

                let needsCloseParen = highlight.textContent.endsWith('(');

                if (!needsCloseParen) {
                    let next = highlight.nextSibling;
                    while (next && next.nodeType === Node.TEXT_NODE && !next.textContent.trim()) {
                        next = next.nextSibling;
                    }
                    if (!next) return;

                    // Detect opening paren in the next node (text or Prism element).
                    if (next.nodeType === Node.TEXT_NODE && next.textContent.startsWith('(')) {
                        highlight.textContent += '(';
                        if (next.textContent.length === 1) {
                            next.parentNode.removeChild(next);
                        } else {
                            next.textContent = next.textContent.slice(1);
                        }
                        needsCloseParen = true;
                    } else if (next.nodeType === Node.ELEMENT_NODE && (next.textContent || '') === '(') {
                        highlight.textContent += '(';
                        next.parentNode.removeChild(next);
                        needsCloseParen = true;
                    }
                }
                if (!needsCloseParen) return;

                // Walk forward through siblings to find the matching ")".
                let depth = 1;
                let node = highlight.nextSibling;
                while (node && depth > 0) {
                    const txt = node.textContent || '';
                    for (let ci = 0; ci < txt.length; ci++) {
                        if (txt[ci] === '(') depth++;
                        else if (txt[ci] === ')') {
                            depth--;
                            if (depth === 0) {
                                // Highlight this closing paren.
                                if (node.nodeType === Node.TEXT_NODE) {
                                    const before = txt.slice(0, ci);
                                    const after = txt.slice(ci + 1);
                                    const parent = node.parentNode;
                                    if (before) parent.insertBefore(document.createTextNode(before), node);
                                    const closeSpan = document.createElement('span');
                                    closeSpan.className = 'api-highlight';
                                    closeSpan.textContent = ')';
                                    parent.insertBefore(closeSpan, node);
                                    if (after) parent.insertBefore(document.createTextNode(after), node);
                                    parent.removeChild(node);
                                } else if (node.nodeType === Node.ELEMENT_NODE && txt === ')') {
                                    const closeSpan = document.createElement('span');
                                    closeSpan.className = 'api-highlight';
                                    closeSpan.textContent = ')';
                                    node.parentNode.insertBefore(closeSpan, node);
                                    node.parentNode.removeChild(node);
                                }
                                node = null;
                                break;
                            }
                        }
                    }
                    if (node) node = node.nextSibling;
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

            // Re-run paren absorption after chain merges, since merges can create
            // new trailing-call opportunities (e.g. root.method + () tokens).
            codeBlock.querySelectorAll('.api-highlight').forEach(absorbAdjacentCallParens);
            
            // Sixth pass: for inferred roots (like `pool`), keep highlight only
            // when connected to a chain (root.member...). If not chained, unwrap.
            if (inferredApiRoots.size > 0) {
                const inferredHighlights = codeBlock.querySelectorAll('.api-highlight');
                inferredHighlights.forEach(highlight => {
                    const text = highlight.textContent;
                    if (!inferredApiRoots.has(text)) return;
                    if (explicitApiVariables.has(text)) return;
                    // If already part of a merged chain, keep it.
                    if (text.includes('.')) return;
                    
                    let prev = highlight.previousSibling;
                    let next = highlight.nextSibling;
                    
                    // Skip whitespace text nodes.
                    while (prev && prev.nodeType === Node.TEXT_NODE && !prev.textContent.trim()) {
                        prev = prev.previousSibling;
                    }
                    while (next && next.nodeType === Node.TEXT_NODE && !next.textContent.trim()) {
                        next = next.nextSibling;
                    }
                    
                    const prevIsDot = prev && (
                        (prev.nodeType === Node.TEXT_NODE && prev.textContent.endsWith('.')) ||
                        (prev.nodeType === Node.ELEMENT_NODE && prev.textContent === '.')
                    );
                    const nextIsDot = next && (
                        (next.nodeType === Node.TEXT_NODE && next.textContent.startsWith('.')) ||
                        (next.nodeType === Node.ELEMENT_NODE && next.textContent === '.')
                    );
                    
                    if (prevIsDot || nextIsDot) return;
                    
                    // Unwrap the span to plain text.
                    const parent = highlight.parentNode;
                    if (parent) {
                        parent.replaceChild(document.createTextNode(text), highlight);
                    }
                });
            }

            // Final: restore NOT_API placeholders to plain text.
            if (notApiTokenMap.size > 0) {
                const finalWalker = document.createTreeWalker(codeBlock, NodeFilter.SHOW_TEXT, null, false);
                const finalNodes = [];
                let fn;
                while (fn = finalWalker.nextNode()) {
                    if (fn.textContent && fn.textContent.includes('__NOT_API_')) {
                        finalNodes.push(fn);
                    }
                }
                finalNodes.forEach(textNode => {
                    NOT_API_PLACEHOLDER_PATTERN.lastIndex = 0;
                    textNode.textContent = textNode.textContent.replace(NOT_API_PLACEHOLDER_PATTERN, (match) => {
                        return notApiTokenMap.get(match) || match;
                    });
                });
            }
        });
    }

    function tagInlineCodeVariants() {
        const codeEls = document.querySelectorAll('.module-page code, .about-page code, .why-page code, .home-page code');
        codeEls.forEach((codeEl) => {
            // Skip fenced/code-block content; inline rules only.
            if (codeEl.closest('pre')) return;

            codeEl.classList.add('inline-code');
            codeEl.classList.remove('inline-code-suitkaise');

            if (/\bsuitkaise\b/i.test(codeEl.textContent || '')) {
                codeEl.classList.add('inline-code-suitkaise');
            }
        });
    }

    function transformBenchmarkTables() {
        const parseBenchmarkUs = (value) => {
            if (!value) return null;
            const trimmed = value.trim();
            if (!trimmed || trimmed.toLowerCase() === 'fail') return null;
            const match = trimmed.match(/-?\d+(?:\.\d+)?/);
            if (!match) return null;
            const parsed = Number.parseFloat(match[0]);
            return Number.isFinite(parsed) ? parsed : null;
        };

        const benchmarkPres = document.querySelectorAll('pre[data-benchmark-table]');
        benchmarkPres.forEach(pre => {
            // Skip if already transformed.
            if (pre.dataset.benchmarkTransformed === 'true') return;
            const code = pre.querySelector('code');
            if (!code) return;

            const raw = code.textContent || '';
            const lines = raw
                .split('\n')
                .map(line => line.trimEnd());

            const cleaned = lines.filter(line => {
                const trimmed = line.trim();
                if (!trimmed) return false;
                if (/^─+$/.test(trimmed)) return false;
                if (trimmed.includes('Supported Types Compatibility Benchmarks')) return false;
                return true;
            });

            const headerIndex = cleaned.findIndex(line => /^Type\s{2,}/.test(line.trim()));
            if (headerIndex === -1) return;

            const headers = cleaned[headerIndex].trim().split(/\s{2,}/);
            const dataLines = cleaned.slice(headerIndex + 1);
            if (headers.length < 2 || dataLines.length === 0) return;

            const wrap = document.createElement('div');
            wrap.className = 'benchmark-table-wrap';

            const table = document.createElement('table');
            table.className = 'benchmark-table';

            const thead = document.createElement('thead');
            const headRow = document.createElement('tr');
            headers.forEach(header => {
                const th = document.createElement('th');
                th.textContent = header;
                headRow.appendChild(th);
            });
            thead.appendChild(headRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            dataLines.forEach(line => {
                const cols = line.trim().split(/\s{2,}/);
                if (cols.length < 2) return;
                while (cols.length < headers.length) cols.push('');
                
                // Find fastest numeric benchmark in this row (excluding type col).
                const numericValues = cols.slice(1, headers.length).map(parseBenchmarkUs);
                let fastestCol = -1;
                let fastestValue = Number.POSITIVE_INFINITY;
                numericValues.forEach((num, idx) => {
                    if (num !== null && num < fastestValue) {
                        fastestValue = num;
                        fastestCol = idx + 1; // offset because first column is type
                    }
                });

                const tr = document.createElement('tr');
                cols.slice(0, headers.length).forEach((value, idx) => {
                    const td = document.createElement('td');
                    if (idx === 0) {
                        const typeCode = document.createElement('code');
                        typeCode.textContent = value;
                        td.appendChild(typeCode);
                    } else {
                        td.textContent = value;
                        if (value.trim().toLowerCase() === 'fail') {
                            td.classList.add('benchmark-fail');
                        } else if (idx === fastestCol) {
                            td.classList.add('benchmark-fastest');
                        }
                    }
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });

            table.appendChild(tbody);
            wrap.appendChild(table);

            pre.dataset.benchmarkTransformed = 'true';
            pre.replaceWith(wrap);
        });
    }

    let mermaidInitialized = false;
    async function renderMermaidDiagrams() {
        if (typeof mermaid === 'undefined') return;
        if (!mermaidInitialized) {
            mermaid.initialize({
                startOnLoad: false,
                theme: 'base',
                securityLevel: 'loose',
                fontFamily: 'Inter, system-ui, sans-serif',
                flowchart: {
                    useMaxWidth: false,
                    htmlLabels: true,
                    curve: 'basis',
                    nodeSpacing: 38,
                    rankSpacing: 52,
                    wrappingWidth: 180
                },
                themeVariables: {
                    background: '#090d0b',
                    primaryColor: '#0f1f15',
                    primaryBorderColor: '#2f7c4a',
                    primaryTextColor: '#bfffd3',
                    secondaryColor: '#0f1a13',
                    secondaryBorderColor: '#2f7c4a',
                    tertiaryColor: '#0b1410',
                    tertiaryBorderColor: '#2f7c4a',
                    lineColor: '#6de995',
                    textColor: '#c6f8d7',
                    nodeTextColor: '#c6f8d7',
                    clusterBkg: '#0c1611',
                    clusterBorder: '#2f7c4a',
                    edgeLabelBackground: '#09130f',
                    mainBkg: '#0f1f15',
                    fontSize: '16px'
                }
            });
            mermaidInitialized = true;
        }

        const nodes = Array.from(document.querySelectorAll('pre.mermaid, div.mermaid'))
            .filter((el) => !el.dataset.mermaidRendered);
        if (!nodes.length) return;

        nodes.forEach((el) => {
            el.dataset.mermaidRendered = 'true';
        });

        try {
            await mermaid.run({ nodes });
        } catch (error) {
            console.error('Mermaid render failed:', error);
        }
    }

    // ============================================
    // Page Content Storage
    // Core pages are inline (instant)
    // Module pages are fetched at startup
    // Heavy pages (videos) are lazy-loaded on demand
    // ============================================
    
    // Core pages that are always inline (small, essential)
    const corePages = {
        error: `
            <section class="error-page">
                <a href="#home" class="error-briefcase" id="errorBriefcase" data-page="home">
                    <img src="${assetPath('briefcase-laptop-closed.png')}" alt="Back to Home" class="error-briefcase-img" id="errorBriefcaseImg">
                    <span class="error-back-text">Back to Home</span>
                </a>
                <h1 class="error-title">ERROR</h1>
                <p class="error-message">An error has occurred. This might have been a loading error, or this page may not exist.</p>
            </section>
        `,
        password: `
            <section class="password-page">
                <div class="password-briefcase">
                    <img src="${assetPath('briefcase-laptop-closed.png')}" alt="Suitkaise" class="password-briefcase-img" id="passwordBriefcaseImg">
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
        'home', 'about', 'quick-start', 'feedback', 'technical-info', 'donate',
        // Processing
        'processing', 'processing-quick-start', 'processing-how-it-works', 'processing-examples', 'processing-why', 'processing-learn',
        // Cucumber
        'cucumber', 'cucumber-quick-start', 'cucumber-how-it-works', 'cucumber-why', 'cucumber-supported-types', 'cucumber-performance', 'cucumber-worst-possible-object', 'cucumber-learn',
        // Timing
        'timing', 'timing-quick-start', 'timing-how-it-works', 'timing-examples', 'timing-why', 'timing-learn',
        // Paths
        'paths', 'paths-quick-start', 'paths-how-it-works', 'paths-examples', 'paths-why', 'paths-learn',
        // Sk
        'sk', 'sk-quick-start', 'sk-how-it-works', 'sk-examples', 'sk-blocking-calls', 'sk-why', 'sk-learn',
        // Circuits
        'circuits', 'circuits-quick-start', 'circuits-how-it-works', 'circuits-examples', 'circuits-why', 'circuits-learn'
    ];
    
    // Cache for all fetched pages (module pages loaded at startup, lazy pages loaded on demand)
    const fetchedPages = {};
    
    // Fetch a single page from the pages folder
    async function fetchPage(pageName) {
        try {
            const cacheBust = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
            const response = await fetch(`pages/${pageName}.html?cb=${cacheBust}`, { cache: 'no-store' });
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
    
    // Registry of pages that need lazy loading (heavy content like videos)
    // These pages will show the loading animation while content loads
    const lazyPages = {
        // Processing
        'processing-videos': async () => await fetchPage('processing-videos'),
        
        // Cucumber
        'cucumber-videos': async () => await fetchPage('cucumber-videos'),
        
        // Timing
        'timing-videos': async () => await fetchPage('timing-videos'),
        
        // Paths
        'paths-videos': async () => await fetchPage('paths-videos'),

        // Sk
        'sk-videos': async () => await fetchPage('sk-videos'),
        
        // Circuits
        'circuits-videos': async () => await fetchPage('circuits-videos'),
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

    function renderInlineMarkdown(text) {
        const escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        return escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
    }

    function renderSimpleMarkdownToHtml(markdownText) {
        const lines = markdownText.split('\n');
        const html = [];

        let inCodeBlock = false;
        let codeLang = '';
        let codeLines = [];
        let paragraphLines = [];
        let listItems = [];

        const flushParagraph = () => {
            if (paragraphLines.length === 0) return;
            const joined = paragraphLines.join(' ').trim();
            if (joined) {
                html.push(`<p>${renderInlineMarkdown(joined)}</p>`);
            }
            paragraphLines = [];
        };

        const flushList = () => {
            if (listItems.length === 0) return;
            html.push('<ul>');
            listItems.forEach(item => {
                html.push(`    <li>${renderInlineMarkdown(item)}</li>`);
            });
            html.push('</ul>');
            listItems = [];
        };

        const flushCode = () => {
            const codeText = codeLines.join('\n')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            const langClass = codeLang ? ` class="language-${codeLang}"` : '';
            html.push(`<pre><code${langClass}>${codeText}</code></pre>`);
            codeLines = [];
            codeLang = '';
        };

        for (const rawLine of lines) {
            const line = rawLine.replace(/\r$/, '');

            if (line.trim().startsWith('```')) {
                if (inCodeBlock) {
                    flushCode();
                    inCodeBlock = false;
                } else {
                    flushParagraph();
                    flushList();
                    inCodeBlock = true;
                    codeLang = line.trim().slice(3).trim();
                }
                continue;
            }

            if (inCodeBlock) {
                codeLines.push(line);
                continue;
            }

            const headingMatch = line.match(/^(#{2,6})\s+(.*)$/);
            if (headingMatch) {
                flushParagraph();
                flushList();
                const level = headingMatch[1].length;
                html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2].trim())}</h${level}>`);
                continue;
            }

            const listMatch = line.match(/^\s*-\s+(.*)$/);
            if (listMatch) {
                flushParagraph();
                listItems.push(listMatch[1].trim());
                continue;
            }

            if (!line.trim()) {
                flushParagraph();
                flushList();
                continue;
            }

            paragraphLines.push(line.trim());
        }

        if (inCodeBlock) {
            flushCode();
        }
        flushParagraph();
        flushList();

        return html.join('\n');
    }

    async function hydrateCucumberHowItWorksIfEmpty(pageName) {
        // No-op: cucumber-how-it-works.html is now fully static; no fallback hydration needed.
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
            const closedImg = assetPath('briefcase-laptop-closed.png');
            const halfOpenImg = assetPath('briefcase-laptop-half-open.png');
            
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
    const noFooterPages = ['password', 'error'];

    const footerHTML = `
        <footer class="site-footer">
            <div class="footer-social-row">
                <a href="https://www.instagram.com/__suitkaise__?igsh=NTc4MTIwNjQ2YQ%3D%3D&utm_source=qr" target="_blank" rel="noopener" class="social-link" title="Instagram">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>
                </a>
                <a href="https://discord.com/channels/1475285390800715948/1475285393678143611" target="_blank" rel="noopener" class="social-link" title="Discord">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/></svg>
                </a>
                <a href="https://www.youtube.com/channel/UCeoybqa6wA3I9P0YksjtRQg" target="_blank" rel="noopener" class="social-link" title="YouTube">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19.13C5.12 19.56 12 19.56 12 19.56s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.43z"/><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"/></svg>
                </a>
                <a href="https://www.reddit.com/r/suitkaise" target="_blank" rel="noopener" class="social-link" title="Reddit">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/></svg>
                </a>
                <a href="#" class="social-link disabled" title="Twitter / X (coming soon)">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                </a>
                <a href="#" class="social-link disabled" title="TikTok (coming soon)">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1v-3.5a6.37 6.37 0 0 0-.79-.05A6.34 6.34 0 0 0 3.15 15.2a6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V8.73a8.19 8.19 0 0 0 4.76 1.52V6.69h-1z"/></svg>
                </a>
                <a href="https://github.com/ceetaro/Suitkaise" target="_blank" rel="noopener" class="social-link" title="GitHub">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
                </a>
                <button class="social-link copy-email-btn" title="Copy email address" data-email="suitkaise@suitkaise.info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                </button>
            </div>
            <div class="footer-feedback-row">
                <a href="#feedback" class="nav-link footer-feedback-link" data-page="feedback">Feedback &amp; Suggestions</a>
            </div>
            <div class="footer-copyright">
                <p>&copy; 2025-2026 Casey Eddings &middot; Apache License 2.0</p>
            </div>
        </footer>
    `;
    
    // Module names for scroll position memory
    const moduleNames = ['sk', 'paths', 'timing', 'circuits', 'cucumber', 'processing'];
    
    // Store scroll positions per page (persisted across refreshes via sessionStorage)
    function getScrollPositions() {
        try {
            return JSON.parse(sessionStorage.getItem('sk_scrollPositions') || '{}');
        } catch { return {}; }
    }
    function saveScrollPosition(page, y) {
        const positions = getScrollPositions();
        positions[page] = y;
        sessionStorage.setItem('sk_scrollPositions', JSON.stringify(positions));
    }
    function getSavedScrollPosition(page) {
        return getScrollPositions()[page];
    }
    
    // Extract module name from page name
    function getModuleName(pageName) {
        for (const mod of moduleNames) {
            if (pageName === mod || pageName.startsWith(mod + '-')) {
                return mod;
            }
        }
        return null;
    }

    var showcaseCallbacks = {};

    // WPO showcase state (declared early so navigateTo can call cleanupWPO)
    var wpoTimers = [];
    var wpoSnowRAF = null;
    var wpoCountRAF = null;
    var wpoPowerupRAF = null;
    var wpoOutroHandler = null;

    function cleanupWPO() {
        wpoTimers.forEach(clearTimeout);
        wpoTimers = [];
        if (wpoSnowRAF) { cancelAnimationFrame(wpoSnowRAF); wpoSnowRAF = null; }
        if (wpoCountRAF) { cancelAnimationFrame(wpoCountRAF); wpoCountRAF = null; }
        if (wpoPowerupRAF) { cancelAnimationFrame(wpoPowerupRAF); wpoPowerupRAF = null; }
    }

    // Showcase state
    var cuke2Timers = [];
    var sh1Timers = [];
    var sh1CounterInterval = null;
    var sk1Timers = [];
    var tm1Timers = [];
    var pt1Timers = [];
    var pt2Timers = [];
    var ci1Timers = [];

    function cleanupCuke2() {
        cuke2Timers.forEach(clearTimeout);
        cuke2Timers = [];
    }

    function cleanupSh1() {
        sh1Timers.forEach(clearTimeout);
        sh1Timers = [];
        if (sh1CounterInterval) { clearInterval(sh1CounterInterval); sh1CounterInterval = null; }
    }

    function cleanupSk1() {
        sk1Timers.forEach(clearTimeout);
        sk1Timers = [];
    }

    function cleanupTm1() {
        tm1Timers.forEach(clearTimeout);
        tm1Timers = [];
    }

    function cleanupPt1() {
        pt1Timers.forEach(clearTimeout);
        pt1Timers = [];
    }

    function cleanupPt2() {
        pt2Timers.forEach(clearTimeout);
        pt2Timers = [];
    }

    function cleanupCi1() {
        ci1Timers.forEach(clearTimeout);
        ci1Timers = [];
    }

    async function navigateTo(pageName, force = false) {
        if (!force && pageName === currentPage) return;
        
        // Save scroll position for current page before navigating
        if (currentPage) {
            saveScrollPosition(currentPage, window.scrollY);
        }

        cleanupWPO();
        cleanupCuke2();
        cleanupSh1();
        cleanupSk1();
        cleanupTm1();
        cleanupPt1();
        cleanupPt2();
        cleanupCi1();
        
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

            // Normalize asset paths for dynamically loaded images
            pageContent.querySelectorAll('img[src*="__assets__/"]').forEach((img) => {
                const fileName = (img.getAttribute('src') || '').split('/').pop();
                if (fileName) img.src = assetPath(fileName);
            });
            
            // Inject footer on non-excluded pages
            if (!noFooterPages.includes(pageName)) {
                pageContent.insertAdjacentHTML('beforeend', footerHTML);
            }
            
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
            
            // Restore scroll position if page was visited before, otherwise start at top
            const savedScroll = getSavedScrollPosition(pageName);
            if (savedScroll !== undefined) {
                window.scrollTo(0, savedScroll);
            } else {
                window.scrollTo(0, 0);
            }

            // Fallback: hydrate known empty generated pages from pseudo-markdown source.
            await hydrateCucumberHowItWorksIfEmpty(pageName);
        }
        
        // Hide loading screen (if it was shown)
        stopLoadingAnimation();
        
        // Setup page-specific functionality
        if (pageName === 'error') {
            setupErrorPageHover();
        } else if (pageName === 'password') {
            setupPasswordPage();
        } else if (pageName === 'home') {
            await loadShowcases();
            setupFadeInAnimations();
            setupWPOShowcase();
            setupProcessingShowcase();
            setupCucumber2Showcase();
            setupShare1Showcase();
            setupSk1Showcase();
            setupTiming1Showcase();
            setupPaths1Showcase();
            setupPaths2Showcase();
            setupCircuits1Showcase();
            setupShowcaseCarousel();
            pulseQuickStart();
        }

        // If summary title already labels the dropdown, remove duplicated first heading.
        normalizeDropdownHeadingDupes();
        
        // Deterministically tag known API tokens across the current page.
        autoTagKnownAPIInCode();
        // Convert manual <suitkaise-api> tags before Prism tokenization.
        preprocessManualAPITags();
        await renderMermaidDiagrams();

        // Run syntax highlighting on code blocks
        if (typeof Prism !== 'undefined') {
            Prism.highlightAll();
            styleDecoratorLines();
            styleLineCountComments();
            styleAPIHighlights();
        }
        tagInlineCodeVariants();

        // Normalize collapsed signature labels:
        // "Arguments <code>x</code>: ..." -> "<strong>Arguments</strong>" + next line.
        normalizeSignatureLabelParagraphs();
        
        // Emphasize callout prefixes like "Note:" and "Important:".
        styleCalloutLabels();

        // Bold just the numeric part in "With/Without X - N lines".
        styleWithWithoutLineCounts();

        // Tighten spacing around "Pros:" / "Cons:" blocks.
        compactProsConsSpacing();
        
        // Convert large benchmark pre blocks to custom HTML tables
        transformBenchmarkTables();
        
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

    function normalizeDropdownHeadingDupes() {
        const normalize = (value) =>
            (value || '')
                .replace(/[`"'“”‘’]/g, '')
                .replace(/\s+/g, ' ')
                .trim()
                .toLowerCase();

        const detailsEls = document.querySelectorAll('.module-page details, .about-page details, .why-page details');
        detailsEls.forEach((details) => {
            const summary = details.querySelector(':scope > summary');
            if (!summary) return;

            const summaryText = normalize(summary.textContent);
            if (!summaryText) return;

            const contentRoot = details.querySelector(':scope > .dropdown-content') || details;
            const firstContentChild = Array.from(contentRoot.children).find((el) => el.tagName !== 'SUMMARY');
            if (!firstContentChild) return;

            if (!/^H[1-4]$/.test(firstContentChild.tagName)) return;

            const headingText = normalize(firstContentChild.textContent);
            if (headingText === summaryText) {
                // Preserve full heading element so summary-specific heading CSS hooks
                // (including arrow styling for h2 summaries) keep working.
                summary.innerHTML = firstContentChild.outerHTML;
                if (firstContentChild.tagName === 'H2') {
                    summary.classList.add('dropdown-title-h2');
                } else {
                    summary.classList.remove('dropdown-title-h2');
                }
                firstContentChild.remove();
            }
        });
    }

    // Handle nav link clicks (event delegation for dynamic content like footer)
    document.addEventListener('click', (e) => {
        const link = e.target.closest('.nav-link');
        if (link && link.dataset.page) {
            e.preventDefault();
            navigateTo(link.dataset.page);
        }

        const copyBtn = e.target.closest('.copy-email-btn');
        if (copyBtn) {
            e.preventDefault();
            const email = copyBtn.dataset.email;
            navigator.clipboard.writeText(email).then(() => {
                const toast = document.createElement('div');
                toast.className = 'copy-toast';
                toast.textContent = 'Email copied';
                document.body.appendChild(toast);
                requestAnimationFrame(() => toast.classList.add('show'));
                setTimeout(() => {
                    toast.classList.remove('show');
                    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
                }, 1800);
            });
        }
    });

    // Handle browser back/forward
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.slice(1) || 'home';
        if (hash !== currentPage && pageExists(hash)) {
            navigateTo(hash);
        }
    });

    // Save scroll position before unload (refresh / tab close)
    window.addEventListener('beforeunload', () => {
        if (currentPage) {
            saveScrollPosition(currentPage, window.scrollY);
        }
    });

    // Hide loading screen on initial load
    stopLoadingAnimation();
    
    // Check URL hash on initial load and navigate to that page
    (async function handleInitialHash() {
        const initialHash = window.location.hash.slice(1) || 'home';
        currentPage = '';
        await navigateTo(initialHash, true);
    })();
    
    // ============================================
    // Section-based Scroll Effects for Module Pages
    // Groups content into logical sections and highlights the active one
    // ============================================
    
    function setupScrollOpacity() {
        const modulePage = document.querySelector('.module-page, .about-page, .why-page');
        if (!modulePage) return;
        
        // Collect dropdown elements separately - they have their own opacity logic
        const dropdownElements = Array.from(modulePage.querySelectorAll('details'));
        
        // Group elements into logical sections:
        // - h2 starts a major section (includes everything until next h2)
        // - h3/h4/h5 starts a subsection within the current major section
        // - Code blocks (pre) are part of their parent section
        // - Text/lists belong to the most recent header
        // - Dropdowns are handled separately (not part of sections)
        
        // Select elements for sections, excluding content inside details
        // Use :scope > * for pages with dropdowns to avoid nested content issues
        const hasDropdowns = dropdownElements.length > 0;
        let allElements;
        if (hasDropdowns) {
            // Get direct children only, excluding details (handled separately)
            allElements = Array.from(modulePage.querySelectorAll(':scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6, :scope > p, :scope > ul, :scope > ol, :scope > pre, :scope > table, :scope > hr'));
        } else {
            allElements = Array.from(modulePage.querySelectorAll('h1, h2, h3, h4, h5, h6, p, li, pre, table, hr'));
        }
        if (allElements.length === 0 && dropdownElements.length === 0) return;
        
        const sections = [];
        let currentSection = null;
        
        // Helper to check if current section only has headers (no content yet)
        function sectionHasOnlyHeaders(section) {
            if (!section) return false;
            return section.elements.every(el => /^h[1-6]$/i.test(el.tagName));
        }
        
        allElements.forEach(el => {
            const tagName = el.tagName.toLowerCase();
            
            // Skip li elements inside details (they're part of the details, handled separately)
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
            // Everything else (p, li, pre, h1, ul, ol) belongs to current section
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
            
            // Handle dropdowns with viewport-based activation.
            // Each dropdown determines its own active state from its position
            // in the viewport rather than relying on top-level sections (which
            // can be sparse or absent on dropdown-heavy pages like examples).
            dropdownElements.forEach(details => {
                const summary = details.querySelector(':scope > summary');
                if (!summary) {
                    details.style.opacity = 1;
                    return;
                }

                details.style.opacity = 1;

                if (!details.open) {
                    const summaryRect = summary.getBoundingClientRect();
                    const summaryCenterY = (summaryRect.top + summaryRect.bottom) / 2;
                    const isVisible = summaryRect.bottom > contentTop && summaryRect.top < contentBottom;
                    const isActive = isVisible && summaryCenterY >= safeZoneTop && summaryCenterY <= safeZoneBottom;
                    summary.style.opacity = isActive ? 1 : 0.3;
                    return;
                }

                // Open dropdown: use the center of the *visible* portion so
                // tall dropdowns that span beyond the viewport still activate.
                const detailsRect = details.getBoundingClientRect();
                const visibleTop = Math.max(detailsRect.top, contentTop);
                const visibleBottom = Math.min(detailsRect.bottom, contentBottom);
                const isVisible = visibleBottom > visibleTop;
                const visibleCenterY = (visibleTop + visibleBottom) / 2;
                const isActive = isVisible && visibleCenterY >= safeZoneTop && visibleCenterY <= safeZoneBottom;
                const opacity = isActive ? 1 : 0.3;

                summary.style.opacity = opacity;
                // Apply opacity to direct children only (not the wrapper itself)
                // to avoid compounding on nested elements like tables.
                Array.from(details.children).forEach(child => {
                    if (child.tagName === 'SUMMARY') return;
                    child.style.opacity = opacity;
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
        
        // Listen for details toggle events (dropdowns expanding/collapsing)
        const detailsElements = modulePage.querySelectorAll('details');
        const detailsToggleHandlers = [];
        detailsElements.forEach(details => {
            const summary = details.querySelector(':scope > summary');
            if (!summary) return;

            const capturePreToggleTop = (e) => {
                // Only capture keyboard toggles that can change details state.
                if (e && e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return;
                details._preToggleSummaryTop = summary.getBoundingClientRect().top;
            };

            const onDetailsToggle = () => {
                const beforeTop = details._preToggleSummaryTop;
                requestAnimationFrame(() => {
                    updateSections();
                    if (typeof beforeTop === 'number') {
                        const afterTop = summary.getBoundingClientRect().top;
                        const delta = afterTop - beforeTop;
                        if (Math.abs(delta) > 1) {
                            window.scrollBy(0, delta);
                        }
                        details._preToggleSummaryTop = undefined;
                    }
                });
            };

            summary.addEventListener('mousedown', capturePreToggleTop);
            summary.addEventListener('keydown', capturePreToggleTop);
            details.addEventListener('toggle', onDetailsToggle);
            detailsToggleHandlers.push({ details, summary, capturePreToggleTop, onDetailsToggle });
        });
        
        // Store cleanup function for when navigating away
        modulePage._scrollOpacityCleanup = () => {
            window.removeEventListener('scroll', onScroll);
            detailsToggleHandlers.forEach(({ details, summary, capturePreToggleTop, onDetailsToggle }) => {
                summary.removeEventListener('mousedown', capturePreToggleTop);
                summary.removeEventListener('keydown', capturePreToggleTop);
                details.removeEventListener('toggle', onDetailsToggle);
            });
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
    
    // ============================================
    // WPO Showcase (Cucumber Boss Battle)
    // ============================================

    function setupWPOShowcase() {
        const showcase = document.getElementById('wpoShowcase');
        if (!showcase) return;

        const stage       = document.getElementById('wpoStage');
        const overlay     = document.getElementById('wpoOverlay');
        const intro       = document.getElementById('wpoIntro');
        const intro2      = document.getElementById('wpoIntro2');
        const intro3      = document.getElementById('wpoIntro3');
        const blackScreen = document.getElementById('wpoBlackScreen');
        const title       = document.getElementById('wpoTitle');
        const zoomWrap    = document.getElementById('wpoZoomWrap');
        const monster     = document.getElementById('wpoMonster');
        const subtitle    = document.getElementById('wpoSubtitle');
        const phrases     = document.getElementById('wpoPhrases');
        const codeScroll  = document.getElementById('wpoCodeScroll');
        const challenge   = document.getElementById('wpoChallenge');
        const chal0       = document.getElementById('wpoChal0');
        const chal1       = document.getElementById('wpoChal1');
        const chal2       = document.getElementById('wpoChal2');
        const chal3       = document.getElementById('wpoChal3');
        const chal4       = document.getElementById('wpoChal4');
        const chal5       = document.getElementById('wpoChal5');
        const codeType    = document.getElementById('wpoCodeType');
        const codeTypeTxt = document.getElementById('wpoCodeTypeText');
        const suitcase    = document.getElementById('wpoSuitcase');
        const suitcaseImg = document.getElementById('wpoSuitcaseImg');
        const ssj         = document.getElementById('wpoSSJ');
        const powerupCanvas = document.getElementById('wpoPowerupCanvas');
        const battle      = document.getElementById('wpoBattle');
        const video       = document.getElementById('wpoVideo');
        const snow        = document.getElementById('wpoSnow');
        const stageSnow   = document.getElementById('wpoStageSnow');
        const countContainer = document.getElementById('wpoCountContainer');
        const result      = document.getElementById('wpoResult');
        const resultLine2 = document.getElementById('wpoResultLine2');
        const replayBtn   = document.getElementById('wpoReplay');

        if (!monster || !video) return;

        var videoSource = video.querySelector('source');
        if (videoSource) {
            var vf = (videoSource.getAttribute('src') || '').split('/').pop();
            if (vf) { videoSource.src = assetPath(vf); video.load(); }
        }

        function reset() {
            cleanupWPO();
            overlay.className = 'wpo-stage-overlay';
            overlay.style.opacity = '';
            blackScreen.className = 'wpo-black-screen';
            blackScreen.style.display = '';
            intro.classList.remove('visible');
            if (intro2) intro2.classList.remove('visible');
            if (intro3) intro3.classList.remove('visible');
            title.classList.remove('visible');
            monster.classList.remove('visible', 'faded', 'very-dim', 'powering-up', 'brightening', 'full');
            zoomWrap.classList.remove('zoomed-out', 'zoomed-character');
            zoomWrap.style.transformOrigin = '';
            zoomWrap.style.transform = '';
            subtitle.classList.remove('visible');
            if (phrases) phrases.querySelectorAll('.wpo-phrase').forEach(function(p) { p.classList.remove('pop'); });
            if (codeScroll) codeScroll.classList.remove('active');
            var absorbEl = document.getElementById('wpoAbsorbContainer');
            if (absorbEl) absorbEl.remove();
            challenge.classList.remove('active');
            [chal0, chal1, chal2, chal3, chal4, chal5].forEach(function(c) { if (c) c.classList.remove('shown'); });
            codeType.classList.remove('active', 'fading');
            codeTypeTxt.innerHTML = '';
            codeTypeTxt.classList.remove('done');
            suitcase.classList.remove('active');
            suitcaseImg.src = '../__assets__/briefcase-laptop-closed.png';
            suitcaseImg.classList.remove('lowered');
            suitcaseImg.style.opacity = '';
            ssj.classList.remove('active', 'intensifying');
            battle.classList.remove('active', 'split');
            battle.style.opacity = '';
            if (wpoOutroHandler) {
                video.removeEventListener('ended', wpoOutroHandler);
                wpoOutroHandler = null;
            }
            video.pause();
            video.currentTime = 0;
            video.style.opacity = '';
            countContainer.innerHTML = '';
            stage.style.display = '';
            stage.style.opacity = '';
            stage.style.transition = '';
            stage.style.position = '';
            stage.style.top = '';
            stage.style.left = '';
            stage.style.width = '';
            stage.style.height = '';
            stage.style.zIndex = '';
            battle.style.transition = '';
            var ctx = snow.getContext('2d');
            if (ctx) ctx.clearRect(0, 0, snow.width, snow.height);
            var stgCtx = stageSnow.getContext('2d');
            if (stgCtx) stgCtx.clearRect(0, 0, stageSnow.width, stageSnow.height);
            stageSnow.style.opacity = '';
            stageSnow.style.transition = '';
            stopPowerup();
            result.classList.remove('active');
            result.style.display = '';
            var resultNum = document.getElementById('wpoResultNum');
            if (resultNum) resultNum.textContent = '';
            var prePart = document.getElementById('wpoResultPre');
            var postPart = document.getElementById('wpoResultPost');
            if (prePart) prePart.classList.remove('visible');
            if (postPart) postPart.classList.remove('visible');
            if (resultLine2) resultLine2.classList.remove('visible');
            replayBtn.classList.remove('visible');
        }

        function typeCode(segments, cb) {
            var segIdx = 0, charIdx = 0;
            var html = '';
            function next() {
                if (segIdx >= segments.length) {
                    codeTypeTxt.classList.add('done');
                    if (cb) cb();
                    return;
                }
                var seg = segments[segIdx];
                var ch = seg.text[charIdx];
                if (seg.api) {
                    var built = seg.text.substring(0, charIdx + 1);
                    codeTypeTxt.innerHTML = html + '<span class="wpo-type-api">' + built + '</span>';
                } else {
                    html += ch;
                    codeTypeTxt.innerHTML = html;
                }
                charIdx++;
                if (charIdx >= seg.text.length) {
                    if (seg.api) html += '<span class="wpo-type-api">' + seg.text + '</span>';
                    segIdx++;
                    charIdx = 0;
                }
                var delay = ch === '\n' ? 300 : 35;
                wpoTimers.push(setTimeout(next, delay));
            }
            next();
        }

        function runCount(durationMs, onDone) {
            var counterEl = document.createElement('span');
            counterEl.className = 'wpo-count-num';
            counterEl.textContent = '0';
            countContainer.appendChild(counterEl);

            var startTime = performance.now();
            var lastShown = 0;

            function tick(now) {
                var elapsed = now - startTime;
                var progress = Math.min(elapsed / durationMs, 1);
                var num = Math.max(1, Math.ceil(progress * 1000));
                if (num !== lastShown) {
                    counterEl.textContent = num >= 1000 ? '1,000' : String(num);
                    lastShown = num;
                }
                if (progress < 1) {
                    wpoCountRAF = requestAnimationFrame(tick);
                } else {
                    if (onDone) onDone();
                }
            }
            wpoCountRAF = requestAnimationFrame(tick);
        }

        function startPowerup(canvas) {
            if (wpoPowerupRAF) { cancelAnimationFrame(wpoPowerupRAF); wpoPowerupRAF = null; }
            var ctx = canvas.getContext('2d');
            if (!ctx) return;
            var dpr = window.devicePixelRatio || 1;
            canvas.width = canvas.offsetWidth * dpr;
            canvas.height = canvas.offsetHeight * dpr;
            ctx.scale(dpr, dpr);
            var w = canvas.offsetWidth;
            var h = canvas.offsetHeight;
            var startTime = performance.now();
            var cx = w * 0.5;
            var baseY = h * 0.92;

            var particles = [];
            for (var i = 0; i < 200; i++) {
                particles.push({
                    x: cx + (Math.random() - 0.5) * w * 0.12,
                    y: baseY + Math.random() * 20,
                    vx: (Math.random() - 0.5) * 0.6,
                    vy: -(Math.random() * 1.5 + 0.3),
                    r: Math.random() * 2.5 + 0.5,
                    life: 0,
                    maxLife: 3000 + Math.random() * 4000,
                    delay: Math.random() * 8000,
                    hue: 140 + Math.random() * 30
                });
            }

            var sparks = [];
            for (var j = 0; j < 40; j++) {
                var angle = Math.random() * Math.PI * 0.8 + Math.PI * 0.1;
                sparks.push({
                    x: cx, y: baseY,
                    vx: Math.cos(angle) * (Math.random() * 2 + 0.8) * (Math.random() < 0.5 ? 1 : -1),
                    vy: -Math.sin(angle) * (Math.random() * 2.5 + 1),
                    r: Math.random() * 1.8 + 0.4,
                    life: 0,
                    maxLife: 1500 + Math.random() * 2000,
                    delay: 2000 + Math.random() * 8000,
                    hue: 130 + Math.random() * 40
                });
            }

            function draw(now) {
                var elapsed = now - startTime;
                var intensity = Math.min(elapsed / 10000, 1);
                ctx.clearRect(0, 0, w, h);

                var glowR = w * 0.08 + intensity * w * 0.06;
                var glowAlpha = 0.1 + intensity * 0.2;
                var grd = ctx.createRadialGradient(cx, baseY, 0, cx, baseY, glowR);
                grd.addColorStop(0, 'rgba(109, 233, 149, ' + glowAlpha + ')');
                grd.addColorStop(0.5, 'rgba(109, 233, 149, ' + (glowAlpha * 0.3) + ')');
                grd.addColorStop(1, 'transparent');
                ctx.fillStyle = grd;
                ctx.fillRect(cx - glowR, baseY - glowR, glowR * 2, glowR * 2);

                for (var p = 0; p < particles.length; p++) {
                    var pt = particles[p];
                    if (elapsed < pt.delay) continue;
                    var age = elapsed - pt.delay;
                    if (age > pt.maxLife) {
                        pt.x = cx + (Math.random() - 0.5) * w * (0.12 + intensity * 0.08);
                        pt.y = baseY + Math.random() * 20;
                        pt.vx = (Math.random() - 0.5) * (0.6 + intensity * 0.4);
                        pt.vy = -(Math.random() * (1.5 + intensity * 1.5) + 0.3);
                        pt.delay = elapsed;
                        pt.maxLife = 2500 + Math.random() * 3000;
                        continue;
                    }
                    var prog = age / pt.maxLife;
                    var px = pt.x + pt.vx * age * 0.02 + Math.sin(age * 0.003 + p) * 3;
                    var py = pt.y + pt.vy * age * 0.025;
                    var alpha = prog < 0.15 ? prog / 0.15 : (1 - prog) * 0.9;
                    alpha *= (0.4 + intensity * 0.6);
                    ctx.beginPath();
                    ctx.arc(px, py, pt.r * (0.8 + intensity * 0.5), 0, Math.PI * 2);
                    ctx.fillStyle = 'hsla(' + pt.hue + ', 80%, 65%, ' + alpha + ')';
                    ctx.fill();
                }

                for (var s = 0; s < sparks.length; s++) {
                    var sp = sparks[s];
                    if (elapsed < sp.delay) continue;
                    var sAge = elapsed - sp.delay;
                    if (sAge > sp.maxLife) {
                        var sAngle = Math.random() * Math.PI * 0.8 + Math.PI * 0.1;
                        sp.x = cx + (Math.random() - 0.5) * w * 0.06;
                        sp.y = baseY;
                        sp.vx = Math.cos(sAngle) * (Math.random() * 2 + 0.8) * (Math.random() < 0.5 ? 1 : -1);
                        sp.vy = -Math.sin(sAngle) * (Math.random() * (2.5 + intensity * 2) + 1);
                        sp.delay = elapsed;
                        sp.maxLife = 1200 + Math.random() * 1500;
                        continue;
                    }
                    var sProg = sAge / sp.maxLife;
                    var sx = sp.x + sp.vx * sAge * 0.04;
                    var sy = sp.y + sp.vy * sAge * 0.04 + 0.001 * sAge;
                    var sAlpha = (1 - sProg) * (0.5 + intensity * 0.5);
                    ctx.beginPath();
                    ctx.arc(sx, sy, sp.r, 0, Math.PI * 2);
                    ctx.fillStyle = 'hsla(' + sp.hue + ', 90%, 75%, ' + sAlpha + ')';
                    ctx.fill();
                    if (sProg < 0.5) {
                        ctx.beginPath();
                        ctx.moveTo(sx, sy);
                        ctx.lineTo(sx - sp.vx * 4, sy - sp.vy * 4);
                        ctx.strokeStyle = 'hsla(' + sp.hue + ', 80%, 65%, ' + (sAlpha * 0.3) + ')';
                        ctx.lineWidth = sp.r * 0.6;
                        ctx.stroke();
                    }
                }

                wpoPowerupRAF = requestAnimationFrame(draw);
            }
            wpoPowerupRAF = requestAnimationFrame(draw);
        }

        function stopPowerup(fadeMs) {
            if (!fadeMs) {
                if (wpoPowerupRAF) { cancelAnimationFrame(wpoPowerupRAF); wpoPowerupRAF = null; }
                if (powerupCanvas) {
                    var ctx = powerupCanvas.getContext('2d');
                    if (ctx) ctx.clearRect(0, 0, powerupCanvas.width, powerupCanvas.height);
                    powerupCanvas.style.opacity = '';
                    powerupCanvas.style.transition = '';
                }
                return;
            }
            if (powerupCanvas) {
                powerupCanvas.style.transition = 'opacity ' + fadeMs + 'ms ease-out';
                powerupCanvas.style.opacity = '0';
            }
            wpoTimers.push(setTimeout(function() {
                if (wpoPowerupRAF) { cancelAnimationFrame(wpoPowerupRAF); wpoPowerupRAF = null; }
                if (powerupCanvas) {
                    var ctx = powerupCanvas.getContext('2d');
                    if (ctx) ctx.clearRect(0, 0, powerupCanvas.width, powerupCanvas.height);
                    powerupCanvas.style.opacity = '';
                    powerupCanvas.style.transition = '';
                }
            }, fadeMs + 100));
        }

        function startBattle() {
            // Stage becomes the left panel — same image, no duplicate
            stage.style.position = 'absolute';
            stage.style.top = '0';
            stage.style.left = '0';
            stage.style.width = '100%';
            stage.style.height = '75vh';
            stage.style.zIndex = '5';

            // Show the battle container (for the right panel only)
            battle.classList.add('active');

            // Animate both in the same frame — stage shrinks left, video expands right
            requestAnimationFrame(function() {
                requestAnimationFrame(function() {
                    stage.style.transition = 'width 2.5s cubic-bezier(0.25, 0.1, 0.25, 1)';
                    stage.style.width = '50%';
                    battle.classList.add('split');
                });
            });

            // Start video immediately
            video.play();
            video.style.opacity = '0.9';

            // Count 1-1000 (starts 1.5s into video)
            wpoTimers.push(setTimeout(function() {
                runCount(26000, function() {});
            }, 1500));

            // After video finishes, fade everything out and show result
            wpoOutroHandler = function beginOutro() {
                stage.style.transition = 'opacity 2s ease';
                stage.style.opacity = '0';
                battle.style.transition = 'opacity 2s ease';
                battle.style.opacity = '0';

                wpoTimers.push(setTimeout(function() {
                    stage.style.display = 'none';
                    stage.style.position = '';
                    stage.style.top = '';
                    stage.style.left = '';
                    stage.style.width = '';
                    stage.style.height = '';
                    stage.style.zIndex = '';
                    stage.style.overflow = '';
                    stage.style.transition = '';
                    stage.style.opacity = '';
                    battle.classList.remove('active', 'split');
                    battle.style.opacity = '';
                    battle.style.transition = '';
                    video.pause();

                    // Set the result number text
                    var resultNum = document.getElementById('wpoResultNum');
                    if (resultNum) resultNum.textContent = '1,000';

                    // Show result screen
                    result.classList.add('active');

                    var prePart = document.getElementById('wpoResultPre');
                    var postPart = document.getElementById('wpoResultPost');
                    requestAnimationFrame(function() {
                        if (prePart) prePart.classList.add('visible');
                        if (postPart) postPart.classList.add('visible');
                    });

                    wpoTimers.push(setTimeout(function() {
                        if (resultLine2) resultLine2.classList.add('visible');
                    }, 2500));

                    wpoTimers.push(setTimeout(function() {
                        replayBtn.classList.add('visible');
                    }, 4000));
                }, 2200));
            }
            video.addEventListener('ended', wpoOutroHandler, { once: true });
        }

        function runAbsorption() {
            var old = document.getElementById('wpoAbsorbContainer');
            if (old) old.remove();

            var container = document.createElement('div');
            container.id = 'wpoAbsorbContainer';
            container.style.cssText = 'position:absolute;inset:0;z-index:6;overflow:hidden;pointer-events:none;';
            stage.appendChild(container);

            var w = container.offsetWidth;
            var h = container.offsetHeight;
            var tx = w * 0.42;
            var ty = h * 0.25;

            var types = [
                'int','float','str','bool','bytes','None',
                'list','tuple','set','frozenset','dict',
                'datetime.datetime','datetime.date','datetime.time',
                'datetime.timedelta','datetime.timezone',
                'decimal.Decimal','fractions.Fraction','uuid.UUID',
                'pathlib.Path','pathlib.PurePath','pathlib.PosixPath',
                'FunctionType','functools.partial','MethodType',
                'staticmethod','classmethod','type','property',
                'logging.Logger','logging.StreamHandler',
                'logging.FileHandler','logging.Formatter',
                'threading.Lock','threading.RLock','threading.Semaphore',
                'threading.BoundedSemaphore','threading.Barrier',
                'threading.Condition','threading.Event','threading.Thread',
                'io.TextIOBase','io.StringIO','io.BytesIO','io.FileIO',
                'tempfile.NamedTemporaryFile',
                'queue.Queue','multiprocessing.Queue',
                'multiprocessing.Event','multiprocessing.SharedMemory',
                're.Pattern','re.Match',
                'sqlite3.Connection','sqlite3.Cursor',
                'contextvars.ContextVar','contextvars.Token',
                'requests.Session','socket.socket',
                'psycopg2.Connection','pymysql.Connection',
                'pymongo.MongoClient','redis.Redis',
                'sqlalchemy.Engine','cassandra.Cluster',
                'elasticsearch.Elasticsearch','neo4j.Driver',
                'influxdb_client.InfluxDBClient','pyodbc.Connection',
                'clickhouse_driver.Client','duckdb.Connection',
                'snowflake.Connection','oracledb.Connection',
                'Iterator','range','enumerate','zip',
                'mmap.mmap','memoryview',
                'ThreadPoolExecutor','ProcessPoolExecutor',
                'threading.local','types.CodeType','types.FrameType',
                'GeneratorType','CoroutineType','AsyncGeneratorType',
                'weakref.ref','WeakValueDictionary','WeakKeyDictionary',
                'enum.Enum','enum.EnumMeta',
                'subprocess.Popen','subprocess.CompletedProcess',
                'asyncio.Task','asyncio.Future',
                'types.ModuleType','collections.namedtuple',
                'typing.NamedTuple','typing.TypedDict'
            ];

            for (var s = types.length - 1; s > 0; s--) {
                var r = Math.floor(Math.random() * (s + 1));
                var tmp = types[s]; types[s] = types[r]; types[r] = tmp;
            }

            var numTypes = types.length;
            var stagger = Math.floor(5500 / numTypes);
            var occupied = [];
            var charW = 9;
            var lineH = 22;
            var pad = 6;

            function overlaps(x, y, tw, th) {
                for (var o = 0; o < occupied.length; o++) {
                    var r = occupied[o];
                    if (x < r.x + r.w + pad && x + tw + pad > r.x &&
                        y < r.y + r.h + pad && y + th + pad > r.y) return true;
                }
                return false;
            }

            function findSpot(tw, th) {
                var minX = w * 0.03, maxX = w * 0.95 - tw;
                var minY = h * 0.03, maxY = h * 0.95 - th;
                for (var attempt = 0; attempt < 60; attempt++) {
                    var cx = minX + Math.random() * (maxX - minX);
                    var cy = minY + Math.random() * (maxY - minY);
                    if (!overlaps(cx, cy, tw, th)) return { x: cx, y: cy };
                }
                return { x: minX + Math.random() * (maxX - minX),
                         y: minY + Math.random() * (maxY - minY) };
            }

            for (var i = 0; i < numTypes; i++) {
                (function(idx) {
                    var delay = idx * stagger;
                    wpoTimers.push(setTimeout(function() {
                        var text = types[idx];
                        var elW = text.length * charW;
                        var elH = lineH;
                        var spot = findSpot(elW, elH);
                        var ex = spot.x, ey = spot.y;

                        var rect = { x: ex, y: ey, w: elW, h: elH };
                        occupied.push(rect);

                        var el = document.createElement('span');
                        el.textContent = text;
                        el.style.cssText =
                            'position:absolute;left:' + ex + 'px;top:' + ey + 'px;' +
                            'font-weight:700;font-size:1.1rem;' +
                            'color:rgba(109,233,149,0.9);' +
                            'text-shadow:0 0 15px rgba(109,233,149,0.4);' +
                            'white-space:nowrap;pointer-events:none;letter-spacing:0.03em;';
                        container.appendChild(el);

                        wpoTimers.push(setTimeout(function() {
                            var oi = occupied.indexOf(rect);
                            if (oi !== -1) occupied.splice(oi, 1);

                            var dx = tx - ex;
                            var dy = ty - ey;
                            el.animate([
                                { transform: 'translate(0,0) scale(1,1)', opacity: 1, offset: 0 },
                                { transform: 'translate(' + (dx * 0.2) + 'px,' + (dy * 0.2) + 'px) scale(0.8,0.55)', opacity: 0.5, offset: 0.3 },
                                { transform: 'translate(' + (dx * 0.6) + 'px,' + (dy * 0.6) + 'px) scale(0.4,0.1)', opacity: 0.1, offset: 0.65 },
                                { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(0.05,0.01)', opacity: 0, offset: 1 }
                            ], { duration: 1200, easing: 'ease-in', fill: 'forwards' })
                            .onfinish = function() { if (el.parentNode) el.remove(); };
                        }, 1500));
                    }, delay));
                })(i);
            }

            wpoTimers.push(setTimeout(function() {
                if (container.parentNode) container.remove();
            }, 9500));
        }

        function runSequence() {
            reset();
            var t = 0;

            // Step 1: Black screen (set by reset — blackScreen is opaque)

            // Step 2: First intro line — then fade out
            wpoTimers.push(setTimeout(function() {
                intro.classList.add('visible');
            }, t += 1500));

            wpoTimers.push(setTimeout(function() {
                intro.classList.remove('visible');
            }, t += 3000));

            // Step 3: Second intro line
            wpoTimers.push(setTimeout(function() {
                if (intro2) intro2.classList.add('visible');
            }, t += 1200));

            wpoTimers.push(setTimeout(function() {
                if (intro2) intro2.classList.remove('visible');
            }, t += 3000));

            // Step 3b: Third intro line
            wpoTimers.push(setTimeout(function() {
                if (intro3) intro3.classList.add('visible');
            }, t += 1200));

            wpoTimers.push(setTimeout(function() {
                if (intro3) intro3.classList.remove('visible');
            }, t += 3000));

            // Step 4: Fade in monster and zoom out simultaneously
            wpoTimers.push(setTimeout(function() {
                monster.classList.add('visible');
                blackScreen.classList.add('hidden');
                zoomWrap.classList.add('zoomed-out');
            }, t += 600));

            // Step 6: Title appears
            wpoTimers.push(setTimeout(function() {
                title.classList.add('visible');
            }, t += 3500));

            wpoTimers.push(setTimeout(function() {
                subtitle.classList.add('visible');
            }, t += 1000));

            // Steps 7-9: Code and phrases absorbed by monster (7s)
            wpoTimers.push(setTimeout(function() {
                title.classList.remove('visible');
                subtitle.classList.remove('visible');
                overlay.classList.add('dim');
                monster.classList.add('faded');
                blackScreen.style.display = 'none';
                runAbsorption();
            }, t += 2000));

            // Step 10: Fade to black after 7s absorption
            wpoTimers.push(setTimeout(function() {
                monster.classList.remove('faded');
                monster.classList.add('very-dim');
                overlay.classList.remove('dim');
                overlay.classList.add('very-dark');
            }, t += 7500));

            // "All of those types added to one single object."
            wpoTimers.push(setTimeout(function() {
                challenge.classList.add('active');
                chal0.classList.add('shown');
            }, t += 2000));

            wpoTimers.push(setTimeout(function() {
                challenge.classList.remove('active');
                chal0.classList.remove('shown');
            }, t += 3500));

            // Steps 11-13: "X can't handle it"
            wpoTimers.push(setTimeout(function() {
                challenge.classList.add('active');
                wpoTimers.push(setTimeout(function() { chal1.classList.add('shown'); }, 400));
                wpoTimers.push(setTimeout(function() { chal2.classList.add('shown'); }, 2000));
                wpoTimers.push(setTimeout(function() { chal3.classList.add('shown'); }, 3600));

                // Step 14: Fade out "can't handle it" text to black
                wpoTimers.push(setTimeout(function() {
                    challenge.classList.remove('active');
                    [chal1, chal2, chal3].forEach(function(c) { if (c) c.classList.remove('shown'); });
                }, 9200));

                // Step 15: Fade in "But with cucumber?" on black screen
                wpoTimers.push(setTimeout(function() {
                    challenge.classList.add('active');
                    chal4.classList.add('shown');
                }, 10400));

                // Fade out cucumber line
                wpoTimers.push(setTimeout(function() {
                    challenge.classList.remove('active');
                    chal4.classList.remove('shown');
                }, 13400));
            }, t += 2000));

            // Step 16: Suitcase opens in center, then moves down
            wpoTimers.push(setTimeout(function() {
                [chal0, chal1, chal2, chal3, chal4, chal5].forEach(function(c) { if (c) c.classList.remove('shown'); });

                suitcase.classList.add('active');
                wpoTimers.push(setTimeout(function() {
                    suitcaseImg.src = '../__assets__/briefcase-laptop-half-open.png';
                }, 200));
                wpoTimers.push(setTimeout(function() {
                    suitcaseImg.src = '../__assets__/briefcase-laptop-fully-open.png';
                }, 400));
                wpoTimers.push(setTimeout(function() {
                    suitcaseImg.classList.add('lowered');
                }, 800));
            }, t += 14000));

            // Step 17: Typing animation on black screen
            wpoTimers.push(setTimeout(function() {
                codeType.classList.add('active');
                typeCode([
                    {text: 'from suitkaise import '},
                    {text: 'cucumber', api: true},
                    {text: '\n\n'},
                    {text: 'cucumber', api: true},
                    {text: '.serialize(WorstPossibleObject)'}
                ], function() {
                    // Step 18: Typing done — hold so it's readable
                    wpoTimers.push(setTimeout(function() {
                        codeType.classList.add('fading');
                        suitcase.classList.remove('active');
                    }, 2500));

                    wpoTimers.push(setTimeout(function() {
                        codeType.classList.remove('active', 'fading');
                        suitcaseImg.classList.remove('lowered');
                    }, 4000));

                    // Step 19-20: After black pause, character-focused gradient + canvas powerup
                    wpoTimers.push(setTimeout(function() {
                        overlay.classList.remove('very-dark');
                        overlay.classList.add('character-focus');
                        monster.classList.remove('very-dim');
                        monster.classList.add('powering-up');

                        powerupCanvas.style.opacity = '0';
                        powerupCanvas.style.transition = 'none';
                        startPowerup(powerupCanvas);
                        requestAnimationFrame(function() {
                            requestAnimationFrame(function() {
                                powerupCanvas.style.transition = 'opacity 3s ease-in';
                                powerupCanvas.style.opacity = '1';
                            });
                        });

                        // Intensify
                        wpoTimers.push(setTimeout(function() {
                            monster.classList.remove('powering-up');
                            monster.classList.add('brightening');
                        }, 4000));

                        // Step 21: Full power — fade out focus gradient smoothly
                        wpoTimers.push(setTimeout(function() {
                            monster.classList.remove('brightening');
                            monster.classList.add('full');
                            overlay.classList.add('widening');
                        }, 7000));

                        wpoTimers.push(setTimeout(function() {
                            stopPowerup(2000);
                        }, 9000));

                        wpoTimers.push(setTimeout(function() {
                            overlay.classList.remove('character-focus', 'widening');
                            overlay.classList.add('clear');
                        }, 11000));

                        // "Let the battle begin."
                        wpoTimers.push(setTimeout(function() {
                            challenge.classList.add('active');
                            chal5.classList.add('shown');
                        }, 12000));

                        wpoTimers.push(setTimeout(function() {
                            challenge.classList.remove('active');
                            chal5.classList.remove('shown');
                        }, 16000));

                        // Transition to battle
                        wpoTimers.push(setTimeout(function() {
                            startBattle();
                        }, 17000));
                    }, 5500));
                });
            }, t += 2000));
        }

        replayBtn.addEventListener('click', runSequence);

        showcaseCallbacks['cucumber-1'] = {
            start: runSequence,
            stop: reset
        };
    }

    function startBlizzard(canvas) {
        if (wpoSnowRAF) { cancelAnimationFrame(wpoSnowRAF); wpoSnowRAF = null; }
        var ctx = canvas.getContext('2d');
        if (!ctx) return;
        var dpr = window.devicePixelRatio || 1;
        canvas.width = canvas.offsetWidth * dpr;
        canvas.height = canvas.offsetHeight * dpr;
        ctx.scale(dpr, dpr);
        var w = canvas.offsetWidth;
        var h = canvas.offsetHeight;
        var startTime = performance.now();

        var gustWind = 0, gustTarget = 0, nextGust = 2000;

        var flakes = [];
        for (var i = 0; i < 900; i++) {
            flakes.push({
                x: Math.random() * (w + 80) - 40,
                y: Math.random() * h * 2 - h,
                r: Math.random() * 3.5 + 0.3,
                speed: Math.random() * 5 + 1.5,
                drift: Math.random() * 2 - 1,
                wobble: Math.random() * Math.PI * 2,
                wobbleSpd: Math.random() * 0.05 + 0.01,
                opacity: Math.random() * 0.7 + 0.15
            });
        }

        var streaks = [];
        for (var j = 0; j < 140; j++) {
            streaks.push({
                x: Math.random() * (w + 200) - 100,
                y: Math.random() * h * 2 - h,
                len: Math.random() * 28 + 8,
                speed: Math.random() * 14 + 6,
                windMult: Math.random() * 1.6 + 0.6,
                opacity: Math.random() * 0.16 + 0.04
            });
        }

        function draw() {
            var now = performance.now();
            var elapsed = (now - startTime) / 1000;
            var ramp = Math.min(elapsed / 3, 1);

            if (now > nextGust) {
                gustTarget = (Math.random() * 14 - 3) * ramp;
                nextGust = now + 1200 + Math.random() * 2500;
            }
            gustWind += (gustTarget - gustWind) * 0.025;
            var wind = (3 + gustWind) * ramp;

            ctx.clearRect(0, 0, w, h);

            if (ramp > 0.5) {
                ctx.fillStyle = 'rgba(190,205,230,' + ((ramp - 0.5) * 0.1) + ')';
                ctx.fillRect(0, 0, w, h);
            }

            for (var i = 0; i < flakes.length; i++) {
                var f = flakes[i];
                f.y += f.speed * ramp;
                f.x += (wind + f.drift + Math.sin(f.wobble) * 0.9) * ramp;
                f.wobble += f.wobbleSpd;
                if (f.y > h + 15) { f.y = -15; f.x = Math.random() * w; }
                if (f.x > w + 40) f.x = -40;
                if (f.x < -40) f.x = w + 40;
                ctx.beginPath();
                ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(220,235,255,' + (f.opacity * ramp) + ')';
                ctx.fill();
            }

            for (var j = 0; j < streaks.length; j++) {
                var s = streaks[j];
                var ss = s.speed * ramp;
                var sw = wind * s.windMult;
                s.y += ss;
                s.x += sw;
                if (s.y > h + 40) { s.y = -40; s.x = Math.random() * w; }
                if (s.x > w + 60) s.x = -60;
                if (s.x < -60) s.x = w + 60;
                var a = Math.atan2(ss, sw);
                ctx.beginPath();
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(s.x + Math.cos(a) * s.len, s.y + Math.sin(a) * s.len);
                ctx.strokeStyle = 'rgba(200,218,255,' + (s.opacity * ramp) + ')';
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            wpoSnowRAF = requestAnimationFrame(draw);
        }
        draw();
    }

    // ============================================
    // Processing Showcase (Code Comparison)
    // ============================================

    var procTimers = [];

    function cleanupProcessing() {
        procTimers.forEach(function(id) { clearTimeout(id); });
        procTimers = [];
    }

    function setupProcessingShowcase() {
        var showcase = document.getElementById('procShowcase');
        if (!showcase) return;

        var intro     = document.getElementById('procIntro');
        var scenario  = document.getElementById('procScenario');
        var battle    = document.getElementById('procBattle');
        var codeLeft  = document.getElementById('procCodeLeft');
        var codeRight = document.getElementById('procCodeRight');

        var reqs = [];
        for (var i = 0; i < 7; i++) {
            reqs.push(document.getElementById('procReq' + i));
        }

        var leftCode = [
            {t:'cm', v:'# comments and whitespace excluded from line count\n'},
            {t:'kw', v:'from'}, ' ', {t:'api-hl', v:'suitkaise.processing'}, ' ', {t:'kw', v:'import'}, ' Skprocess, autoreconnect\n',
            {t:'kw', v:'import'}, ' psycopg2\n',
            '\n',
            {t:'dc', v:'@autoreconnect'}, '(', {t:'op', v:'**'}, '{', {t:'st', v:'"psycopg2.Connection"'}, ': {', {t:'st', v:'"*"'}, ': ', {t:'st', v:'"password"'}, '}})\n',
            {t:'kw', v:'class'}, ' ', {t:'fn', v:'DatabaseWorker'}, '(Skprocess):\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'__init__'}, '(', {t:'bi', v:'self'}, ', db_connection):\n',
            '        ', {t:'bi', v:'self'}, '.db = db_connection\n',
            '        ', {t:'bi', v:'self'}, '.process_config.lives = ', {t:'nr', v:'3'}, '\n',
            '        ', {t:'bi', v:'self'}, '.process_config.timeouts.run = ', {t:'nr', v:'30.0'}, '\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'__prerun__'}, '(', {t:'bi', v:'self'}, '):\n',
            '        msg = ', {t:'bi', v:'self'}, '.listen(timeout=', {t:'nr', v:'0.1'}, ')\n',
            '        ', {t:'bi', v:'self'}, '.query = msg ', {t:'kw', v:'if'}, ' msg ', {t:'kw', v:'else'}, ' ', {t:'kw', v:'None'}, '\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'__run__'}, '(', {t:'bi', v:'self'}, '):\n',
            '        ', {t:'kw', v:'if'}, ' ', {t:'kw', v:'not'}, ' ', {t:'bi', v:'self'}, '.query:\n',
            '            ', {t:'kw', v:'return'}, '\n',
            '        cursor = ', {t:'bi', v:'self'}, '.db.cursor()\n',
            '        cursor.execute(', {t:'bi', v:'self'}, '.query[', {t:'st', v:"'sql'"}, '], ', {t:'bi', v:'self'}, '.query.get(', {t:'st', v:"'params'"}, '))\n',
            '        ', {t:'bi', v:'self'}, '.results = cursor.fetchall()\n',
            '        cursor.close()\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'__postrun__'}, '(', {t:'bi', v:'self'}, '):\n',
            '        ', {t:'kw', v:'if'}, ' ', {t:'bi', v:'self'}, '.query:\n',
            '            ', {t:'kw', v:'if'}, ' ', {t:'kw', v:'not'}, ' ', {t:'bi', v:'self'}, '.results:\n',
            '                ', {t:'bi', v:'self'}, '.tell({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'error'"}, ', ', {t:'st', v:"'data'"}, ': ', {t:'kw', v:'None'}, '})\n',
            '            ', {t:'kw', v:'else'}, ':\n',
            '                ', {t:'bi', v:'self'}, '.tell({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'ok'"}, ', ', {t:'st', v:"'data'"}, ': ', {t:'bi', v:'self'}, '.results})\n',
            '        ', {t:'kw', v:'else'}, ':\n',
            '            ', {t:'bi', v:'self'}, '.tell({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'no query'"}, ', ', {t:'st', v:"'data'"}, ': ', {t:'kw', v:'None'}, '})\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'__onfinish__'}, '(', {t:'bi', v:'self'}, '):\n',
            '        ', {t:'bi', v:'self'}, '.db.close()\n',
            '\n',
            {t:'cm', v:'# usage'}, '\n',
            'db = psycopg2.connect(host=', {t:'st', v:"'localhost'"}, ', database=', {t:'st', v:"'mydb'"}, ', password=', {t:'st', v:"'secret'"}, ')\n',
            'worker = DatabaseWorker(db)\n',
            'worker.start()\n',
            '\n',
            'queries = [\n',
            '    {', {t:'st', v:"'sql'"}, ': ', {t:'st', v:"'SELECT * FROM users WHERE id = %s'"}, ', ', {t:'st', v:"'params'"}, ': (', {t:'nr', v:'123'}, ',)},\n',
            '    {', {t:'st', v:"'sql'"}, ': ', {t:'st', v:"'SELECT * FROM users WHERE id = %s'"}, ', ', {t:'st', v:"'params'"}, ': (', {t:'nr', v:'456'}, ',)},\n',
            '    {', {t:'st', v:"'sql'"}, ': ', {t:'st', v:"'SELECT * FROM users WHERE id = %s'"}, ', ', {t:'st', v:"'params'"}, ': (', {t:'nr', v:'789'}, ',)},\n',
            ']\n',
            'results = []\n',
            '\n',
            {t:'kw', v:'for'}, ' query ', {t:'kw', v:'in'}, ' queries:\n',
            '    worker.tell(query)\n',
            '    result = worker.listen(timeout=', {t:'nr', v:'30'}, ')\n',
            '    results.append(result)\n',
            '\n',
            'worker.stop()\n',
            'worker.wait()\n',
            {t:'fn', v:'print'}, '(', {t:'kw', v:'f'}, {t:'st', v:'"Avg query time: {worker.__run__.timer.mean:.3f}s"'}, ')\n'
        ];

        var rightCode = [
            {t:'cm', v:'# comments and whitespace excluded from line count\n'},
            {t:'kw', v:'import'}, ' multiprocessing\n',
            {t:'kw', v:'import'}, ' signal\n',
            {t:'kw', v:'import'}, ' time\n',
            {t:'kw', v:'import'}, ' psycopg2\n',
            {t:'kw', v:'from'}, ' multiprocessing ', {t:'kw', v:'import'}, ' Queue, Event, Value\n',
            {t:'kw', v:'from'}, ' ctypes ', {t:'kw', v:'import'}, ' c_double\n',
            '\n',
            {t:'kw', v:'class'}, ' ', {t:'fn', v:'DatabaseWorker'}, '(multiprocessing.Process):\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'__init__'}, '(', {t:'bi', v:'self'}, ', task_queue, result_queue, stats_lock,\n',
            '                 total_time, query_count, stop_event, db_config):\n',
            '        ', {t:'fn', v:'super'}, '().', {t:'fn', v:'__init__'}, '()\n',
            '        ', {t:'bi', v:'self'}, '.task_queue = task_queue\n',
            '        ', {t:'bi', v:'self'}, '.result_queue = result_queue\n',
            '        ', {t:'bi', v:'self'}, '.stats_lock = stats_lock\n',
            '        ', {t:'bi', v:'self'}, '.total_time = total_time\n',
            '        ', {t:'bi', v:'self'}, '.query_count = query_count\n',
            '        ', {t:'bi', v:'self'}, '.stop_event = stop_event\n',
            '        ', {t:'bi', v:'self'}, '.db_config = db_config\n',
            '        ', {t:'bi', v:'self'}, '.timeout = ', {t:'nr', v:'30'}, '\n',
            '        ', {t:'bi', v:'self'}, '.max_retries = ', {t:'nr', v:'3'}, '\n',
            '        ', {t:'bi', v:'self'}, '.conn = ', {t:'kw', v:'None'}, '\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'_connect'}, '(', {t:'bi', v:'self'}, '):\n',
            '        ', {t:'kw', v:'for'}, ' attempt ', {t:'kw', v:'in'}, ' ', {t:'fn', v:'range'}, '(', {t:'bi', v:'self'}, '.max_retries):\n',
            '            ', {t:'kw', v:'try'}, ':\n',
            '                ', {t:'bi', v:'self'}, '.conn = psycopg2.connect(', {t:'op', v:'**'}, {t:'bi', v:'self'}, '.db_config)\n',
            '                ', {t:'kw', v:'return'}, '\n',
            '            ', {t:'kw', v:'except'}, ' psycopg2.OperationalError:\n',
            '                ', {t:'kw', v:'if'}, ' attempt == ', {t:'bi', v:'self'}, '.max_retries - ', {t:'nr', v:'1'}, ':\n',
            '                    ', {t:'kw', v:'raise'}, '\n',
            '                time.sleep(', {t:'nr', v:'2'}, ' ', {t:'op', v:'**'}, ' attempt)\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'_timeout_handler'}, '(', {t:'bi', v:'self'}, ', signum, frame):\n',
            '        ', {t:'kw', v:'raise'}, ' ', {t:'fn', v:'TimeoutError'}, '(', {t:'st', v:'"Query timed out"'}, ')\n',
            '\n',
            '    ', {t:'kw', v:'def'}, ' ', {t:'fn', v:'run'}, '(', {t:'bi', v:'self'}, '):\n',
            '        ', {t:'bi', v:'self'}, '._connect()\n',
            '        signal.signal(signal.SIGALRM, ', {t:'bi', v:'self'}, '._timeout_handler)\n',
            '        ', {t:'kw', v:'try'}, ':\n',
            '            ', {t:'kw', v:'while'}, ' ', {t:'kw', v:'not'}, ' ', {t:'bi', v:'self'}, '.stop_event.is_set():\n',
            '                ', {t:'kw', v:'try'}, ':\n',
            '                    query_params = ', {t:'bi', v:'self'}, '.task_queue.get(timeout=', {t:'nr', v:'0.1'}, ')\n',
            '                ', {t:'kw', v:'except'}, ':\n',
            '                    ', {t:'bi', v:'self'}, '.result_queue.put({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'no query'"}, ', ', {t:'st', v:"'data'"}, ': ', {t:'kw', v:'None'}, '})\n',
            '                    ', {t:'kw', v:'continue'}, '\n',
            '                start = time.time()\n',
            '                signal.alarm(', {t:'bi', v:'self'}, '.timeout)\n',
            '                ', {t:'kw', v:'try'}, ':\n',
            '                    cursor = ', {t:'bi', v:'self'}, '.conn.cursor()\n',
            '                    cursor.execute(query_params[', {t:'st', v:"'sql'"}, '], query_params.get(', {t:'st', v:"'params'"}, '))\n',
            '                    results = cursor.fetchall()\n',
            '                    cursor.close()\n',
            '                    signal.alarm(', {t:'nr', v:'0'}, ')\n',
            '                    elapsed = time.time() - start\n',
            '                    ', {t:'kw', v:'with'}, ' ', {t:'bi', v:'self'}, '.stats_lock:\n',
            '                        ', {t:'bi', v:'self'}, '.total_time.value += elapsed\n',
            '                        ', {t:'bi', v:'self'}, '.query_count.value += ', {t:'nr', v:'1'}, '\n',
            '                    ', {t:'kw', v:'if'}, ' ', {t:'kw', v:'not'}, ' results:\n',
            '                        ', {t:'bi', v:'self'}, '.result_queue.put({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'error'"}, ', ', {t:'st', v:"'data'"}, ': ', {t:'kw', v:'None'}, '})\n',
            '                    ', {t:'kw', v:'else'}, ':\n',
            '                        ', {t:'bi', v:'self'}, '.result_queue.put({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'ok'"}, ', ', {t:'st', v:"'data'"}, ': results})\n',
            '                ', {t:'kw', v:'except'}, ' ', {t:'fn', v:'TimeoutError'}, ':\n',
            '                    signal.alarm(', {t:'nr', v:'0'}, ')\n',
            '                    ', {t:'bi', v:'self'}, '.result_queue.put({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'error'"}, ', ', {t:'st', v:"'error'"}, ': ', {t:'st', v:"'timeout'"}, '})\n',
            '                ', {t:'kw', v:'except'}, ' ', {t:'fn', v:'Exception'}, ' ', {t:'kw', v:'as'}, ' e:\n',
            '                    signal.alarm(', {t:'nr', v:'0'}, ')\n',
            '                    ', {t:'bi', v:'self'}, '.result_queue.put({', {t:'st', v:"'status'"}, ': ', {t:'st', v:"'error'"}, ', ', {t:'st', v:"'error'"}, ': ', {t:'fn', v:'str'}, '(e)})\n',
            '        ', {t:'kw', v:'finally'}, ':\n',
            '            ', {t:'kw', v:'if'}, ' ', {t:'bi', v:'self'}, '.conn:\n',
            '                ', {t:'bi', v:'self'}, '.conn.close()\n',
            '\n',
            {t:'cm', v:'# usage'}, '\n',
            'db_config = {', {t:'st', v:"'host'"}, ': ', {t:'st', v:"'localhost'"}, ', ', {t:'st', v:"'database'"}, ': ', {t:'st', v:"'mydb'"}, ', ', {t:'st', v:"'password'"}, ': ', {t:'st', v:"'secret'"}, '}\n',
            'manager = multiprocessing.Manager()\n',
            'task_queue = Queue()\n',
            'result_queue = Queue()\n',
            'stats_lock = manager.Lock()\n',
            'total_time = Value(c_double, ', {t:'nr', v:'0.0'}, ')\n',
            'query_count = Value(', {t:'st', v:"'i'"}, ', ', {t:'nr', v:'0'}, ')\n',
            'stop_event = Event()\n',
            '\n',
            'worker = DatabaseWorker(\n',
            '    task_queue, result_queue, stats_lock, total_time,\n',
            '    query_count, stop_event, db_config,\n',
            '    timeout=', {t:'nr', v:'30'}, ', max_retries=', {t:'nr', v:'3'}, '\n',
            ')\n',
            'worker.start()\n',
            '\n',
            'queries = [\n',
            '    {', {t:'st', v:"'sql'"}, ': ', {t:'st', v:"'SELECT * FROM users WHERE id = %s'"}, ', ', {t:'st', v:"'params'"}, ': (', {t:'nr', v:'123'}, ',)},\n',
            '    {', {t:'st', v:"'sql'"}, ': ', {t:'st', v:"'SELECT * FROM users WHERE id = %s'"}, ', ', {t:'st', v:"'params'"}, ': (', {t:'nr', v:'456'}, ',)},\n',
            '    {', {t:'st', v:"'sql'"}, ': ', {t:'st', v:"'SELECT * FROM users WHERE id = %s'"}, ', ', {t:'st', v:"'params'"}, ': (', {t:'nr', v:'789'}, ',)},\n',
            ']\n',
            'results = []\n',
            '\n',
            {t:'kw', v:'for'}, ' query ', {t:'kw', v:'in'}, ' queries:\n',
            '    task_queue.put(query)\n',
            '    result = result_queue.get(timeout=', {t:'nr', v:'30'}, ')\n',
            '    results.append(result)\n',
            '\n',
            'stop_event.set()\n',
            'worker.join()\n',
            '\n',
            {t:'kw', v:'if'}, ' query_count.value > ', {t:'nr', v:'0'}, ':\n',
            '    avg_time = total_time.value / query_count.value\n',
            '    ', {t:'fn', v:'print'}, '(', {t:'kw', v:'f'}, {t:'st', v:'"Avg query time: {avg_time:.3f}s"'}, ')\n'
        ];

        function tokenToHtml(tok) {
            if (typeof tok === 'string') return escHtml(tok);
            return '<span class="' + tok.t + '">' + escHtml(tok.v) + '</span>';
        }

        function escHtml(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function flattenToText(tokens) {
            var s = '';
            for (var i = 0; i < tokens.length; i++) {
                s += (typeof tokens[i] === 'string') ? tokens[i] : tokens[i].v;
            }
            return s;
        }

        var leftText = flattenToText(leftCode);
        var rightText = flattenToText(rightCode);
        var leftTotal = leftText.length;
        var rightTotal = rightText.length;

        var msPerChar = 10;
        var totalDuration = rightTotal * msPerChar;

        function renderPartial(tokens, charCount) {
            var html = '';
            var remaining = charCount;
            for (var i = 0; i < tokens.length && remaining > 0; i++) {
                var tok = tokens[i];
                var txt = (typeof tok === 'string') ? tok : tok.v;
                if (txt.length <= remaining) {
                    html += tokenToHtml(tok);
                    remaining -= txt.length;
                } else {
                    var partial = txt.substring(0, remaining);
                    if (typeof tok === 'string') {
                        html += escHtml(partial);
                    } else {
                        html += '<span class="' + tok.t + '">' + escHtml(partial) + '</span>';
                    }
                    remaining = 0;
                }
            }
            return html;
        }

        var procTypingRAF = null;
        var prevBtn = document.getElementById('procPrev');
        var nextBtn = document.getElementById('procNext');
        var curStep = -1;
        var stepping = false;
        var maxStep = 1;

        function resetAllState() {
            cleanupProcessing();
            if (procTypingRAF) { cancelAnimationFrame(procTypingRAF); procTypingRAF = null; }
            intro.classList.remove('active');
            scenario.classList.remove('visible');
            reqs.forEach(function(r) { if (r) r.classList.remove('shown'); });
            battle.classList.remove('active');
            codeLeft.innerHTML = '';
            codeRight.innerHTML = '';
            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            procTimers.push(setTimeout(fn, delay));
        }

        function updateNav() {
            if (prevBtn) prevBtn.disabled = curStep <= 0;
            if (nextBtn) nextBtn.disabled = curStep >= maxStep;
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupProcessing();
            if (procTypingRAF) { cancelAnimationFrame(procTypingRAF); procTypingRAF = null; }

            // Hide all scenes
            intro.classList.remove('active');
            battle.classList.remove('active');

            curStep = step;
            var d = 0;

            switch (step) {
                case 0: // Intro — scenario + requirements
                    scenario.classList.remove('visible');
                    reqs.forEach(function(r) { if (r) r.classList.remove('shown'); });

            intro.classList.add('active');

                    sched(function() { scenario.classList.add('visible'); }, d += 300);

            reqs.forEach(function(req, idx) {
                        sched(function() {
                    if (req) req.classList.add('shown');
                        }, d += 500);
                    });

                    sched(function() { stepping = false; }, d += 300);
                    break;

                case 1: // Code battle — side-by-side typing
                    codeLeft.innerHTML = '';
                    codeRight.innerHTML = '';

                battle.classList.add('active');

                    sched(function() {
                    var startTime = performance.now();
                    var charsPerMs = 1 / msPerChar;

                    function tick(now) {
                        var elapsed = now - startTime;
                        var chars = Math.floor(elapsed * charsPerMs);
                        var leftChars = Math.min(chars, leftTotal);
                        var rightChars = Math.min(chars, rightTotal);

                        codeLeft.innerHTML = renderPartial(leftCode, leftChars);
                        codeRight.innerHTML = renderPartial(rightCode, rightChars);

                        if (leftChars < leftTotal) {
                            codeLeft.parentElement.scrollTop = codeLeft.parentElement.scrollHeight;
                        }
                        if (rightChars < rightTotal) {
                            codeRight.parentElement.scrollTop = codeRight.parentElement.scrollHeight;
                        }

                        if (elapsed < totalDuration) {
                            procTypingRAF = requestAnimationFrame(tick);
                            } else {
                                stepping = false;
                        }
                    }
                    procTypingRAF = requestAnimationFrame(tick);
                    }, d += 600);
                    break;

                default:
                    stepping = false;
                    break;
            }
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (stepping || curStep >= maxStep) return;
                enterStep(curStep + 1);
                updateNav();
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (stepping || curStep <= 0) return;
                enterStep(curStep - 1);
                updateNav();
            });
        }

        showcaseCallbacks['processing-1'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    // ============================================
    // Cucumber-2 Showcase (Reconnector / Suitcase)
    // ============================================

    function setupCucumber2Showcase() {
        var showcase = document.getElementById('cuke2Showcase');
        if (!showcase) return;

        var prevBtn     = document.getElementById('cuke2Prev');
        var nextBtn     = document.getElementById('cuke2Next');

        var probPhase   = document.getElementById('cuke2Problem');
        var probText1   = document.getElementById('cuke2ProbText1');
        var probCode    = document.getElementById('cuke2ProbCode');
        var probError   = document.getElementById('cuke2Error');
        var probText2   = document.getElementById('cuke2ProbText2');

        var packPhase   = document.getElementById('cuke2Packing');
        var packText1   = document.getElementById('cuke2PackText1');
        var packText2   = document.getElementById('cuke2PackText2');
        var caseArea    = document.getElementById('cuke2CaseArea');
        var caseImg     = document.getElementById('cuke2CaseImg');
        var tagsWrap    = document.getElementById('cuke2Tags');
        var secNote     = document.getElementById('cuke2SecurityNote');
        var labelWrap   = document.getElementById('cuke2LabelWrap');
        var labelExplain = document.getElementById('cuke2LabelExplain');

        var crossPhase  = document.getElementById('cuke2Crossing');
        var travelCase  = document.getElementById('cuke2TravelCase');
        var crossText   = document.getElementById('cuke2CrossText');

        var flavPhase   = document.getElementById('cuke2Flavors');
        var lazyDiv     = document.getElementById('cuke2Lazy');
        var lazyCode    = document.getElementById('cuke2LazyCode');
        var authDiv     = document.getElementById('cuke2Auth');
        var authCode    = document.getElementById('cuke2AuthCode');
        var allDiv      = document.getElementById('cuke2All');
        var allCode     = document.getElementById('cuke2AllCode');

        var punchPhase  = document.getElementById('cuke2Punchline');
        var punchText1  = document.getElementById('cuke2PunchText1');
        var punchCode   = document.getElementById('cuke2PunchCode');
        var punchNote   = document.getElementById('cuke2PunchNote');
        var tagline     = document.getElementById('cuke2Tagline');
        var replayBtn   = document.getElementById('cuke2Replay');

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function tok(tokens) {
            var html = '';
            for (var i = 0; i < tokens.length; i++) {
                var t = tokens[i];
                if (typeof t === 'string') { html += esc(t); }
                else { html += '<span class="' + t.c + '">' + esc(t.v) + '</span>'; }
            }
            return html;
        }

        var probTokens = tok([
            {c:'fn', v:'conn'}, ' = psycopg2.', {c:'fn', v:'connect'}, '(\n',
            '    host=', {c:'st', v:'"db.prod"'}, ',\n',
            '    database=', {c:'st', v:'"users"'}, ',\n',
            '    password=', {c:'st', v:'"secret"'}, '\n',
            ')\n',
            '\n',
            {c:'fn', v:'worker'}, ' = ', {c:'fn', v:'MyWorker'}, '(conn)\n',
            'worker.', {c:'fn', v:'start'}, '()'
        ]);

        var lazyTokens = tok([
            'conn = sqlite3.', {c:'fn', v:'connect'}, '(', {c:'st', v:'"app.db"'}, ')\n',
            'data = ', {c:'api-hl', v:'cucumber'}, '.', {c:'fn', v:'serialize'}, '(conn)\n',
            '\n',
            'restored = ', {c:'api-hl', v:'cucumber'}, '.', {c:'fn', v:'deserialize'}, '(data)\n',
            {c:'glow', v:'restored.execute("SELECT * FROM users")'}, '\n',
            {c:'cm', v:'# just use it — auto-reconnects'}
        ]);

        var authTokens = tok([
            'conn = psycopg2.', {c:'fn', v:'connect'}, '(\n',
            '    host=', {c:'st', v:'"db.prod"'}, ',\n',
            '    password=', {c:'st', v:'"secret"'}, '\n',
            ')\n',
            'data = ', {c:'api-hl', v:'cucumber'}, '.', {c:'fn', v:'serialize'}, '(conn)\n',
            '\n',
            'restored = ', {c:'api-hl', v:'cucumber'}, '.', {c:'fn', v:'deserialize'}, '(data)\n',
            {c:'glow', v:'live = restored.reconnect(auth="secret")'}
        ]);

        var allTokens = tok([
            {c:'kw', v:'class'}, ' ', {c:'fn', v:'Pipeline'}, ':\n',
            '  ', {c:'kw', v:'def'}, ' ', {c:'fn', v:'__init__'}, '(', {c:'bi', v:'self'}, '):\n',
            '    ', {c:'bi', v:'self'}, '.db = psycopg2.', {c:'fn', v:'connect'}, '(', {c:'op', v:'...'}, ')\n',
            '    ', {c:'bi', v:'self'}, '.cache = redis.', {c:'fn', v:'Redis'}, '(', {c:'op', v:'...'}, ')\n',
            '\n',
            {c:'api-hl', v:'cucumber'}, '.', {c:'glow', v:'reconnect_all'}, '(\n',
            '  pipeline, ', {c:'op', v:'**'}, '{\n',
            '    ', {c:'st', v:'"psycopg2.Connection"'}, ':\n',
            '      {', {c:'st', v:'"*"'}, ': ', {c:'st', v:'"db_pass"'}, '},\n',
            '    ', {c:'st', v:'"redis.Redis"'}, ':\n',
            '      {', {c:'st', v:'"*"'}, ': ', {c:'st', v:'"redis_pass"'}, '}\n',
            '})'
        ]);

        var punchTokens = tok([
            {c:'dc', v:'@autoreconnect'}, '(', {c:'op', v:'**'}, '{', {c:'st', v:'"psycopg2.Connection"'}, ': {', {c:'st', v:'"*"'}, ': ', {c:'st', v:'"secret"'}, '}})\n',
            {c:'kw', v:'class'}, ' ', {c:'fn', v:'Worker'}, '(Skprocess):\n',
            '\n',
            '    ', {c:'kw', v:'def'}, ' ', {c:'fn', v:'__init__'}, '(', {c:'bi', v:'self'}, ', db_connection):\n',
            '        ', {c:'bi', v:'self'}, '.db = db_connection\n',
            '\n',
            '    ', {c:'kw', v:'def'}, ' ', {c:'fn', v:'__run__'}, '(', {c:'bi', v:'self'}, '):\n',
            '        ', {c:'bi', v:'self'}, '.db.', {c:'fn', v:'execute'}, '(', {c:'op', v:'...'}, ')  ', {c:'cm', v:'# already reconnected'}
        ]);

        var tags = tagsWrap ? tagsWrap.querySelectorAll('.cuke2-tag') : [];
        var allPhases = [probPhase, packPhase, crossPhase, flavPhase, punchPhase];

        var curStep = -1;
        var stepping = false;

        function hideAllPhases() {
            allPhases.forEach(function(p) { if (p) p.classList.remove('active'); });
        }

        function resetAllState() {
            cleanupCuke2();
            hideAllPhases();

            [probText1, probText2, probCode, probError, packText1, packText2,
             crossText, punchText1, punchCode, punchNote, labelExplain].forEach(function(el) {
                if (el) el.classList.remove('visible');
            });

            if (caseArea) caseArea.classList.remove('visible', 'compact');
            if (tagsWrap) tagsWrap.classList.remove('collapsed');
            tags.forEach(function(t) { t.classList.remove('visible', 'packed'); });
            if (secNote) secNote.classList.remove('visible');
            if (labelWrap) labelWrap.classList.remove('visible');

            if (travelCase) {
                travelCase.classList.remove('visible', 'arrived');
            }

            [lazyDiv, authDiv, allDiv].forEach(function(f) {
                if (f) f.classList.remove('visible');
            });

            if (lazyCode) lazyCode.innerHTML = '';
            if (authCode) authCode.innerHTML = '';
            if (allCode) allCode.innerHTML = '';
            if (probCode) probCode.innerHTML = '';
            if (punchCode) punchCode.innerHTML = '';

            if (tagline) tagline.classList.remove('visible');
            if (replayBtn) replayBtn.classList.remove('visible');

            function resetCaseImg(img) {
                if (img) img.src = img.src.replace(/briefcase-laptop-[^.]+\.png/, 'briefcase-laptop-closed.png');
            }
            resetCaseImg(caseImg);

            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            cuke2Timers.push(setTimeout(fn, delay));
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupCuke2();
            hideAllPhases();
            curStep = step;

            var d = 0;

            switch (step) {
                case 0: // The Problem
                    probPhase.classList.add('active');
                    probCode.innerHTML = probTokens;

                    sched(function() { probText1.classList.add('visible'); }, d += 300);

                    sched(function() {
                        probCode.classList.add('visible');
                    }, d += 1200);

                    sched(function() {
                        probError.classList.add('visible');
                    }, d += 2500);

                    sched(function() {
                        probText2.classList.add('visible');
                        stepping = false;
                    }, d += 1200);
                    break;

                case 1: // Suitcase packing + reconnector label (one scene)
                    // Reset sub-element state so re-entering works
                    if (caseArea) caseArea.classList.remove('visible', 'compact');
                    if (tagsWrap) tagsWrap.classList.remove('collapsed');
                    tags.forEach(function(t) { t.classList.remove('visible', 'packed'); });
                    if (secNote) secNote.classList.remove('visible');
                    if (labelWrap) labelWrap.classList.remove('visible');
                    if (labelExplain) labelExplain.classList.remove('visible');
                    if (packText1) packText1.classList.remove('visible');
                    if (packText2) packText2.classList.remove('visible');
                    (function() {
                        var baseSrc = (caseImg.getAttribute('src') || '').replace(/briefcase-laptop-[^.]+\.png/, '');
                        caseImg.src = baseSrc + 'briefcase-laptop-closed.png';
                    })();

                    packPhase.classList.add('active');
                    sched(function() { packText1.classList.add('visible'); }, d += 300);
                    sched(function() {
                        caseArea.classList.add('visible');
                    }, d += 1200);
                    sched(function() {
                        var baseSrc = (caseImg.getAttribute('src') || '').replace(/briefcase-laptop-[^.]+\.png/, '');
                        caseImg.src = baseSrc + 'briefcase-laptop-half-open.png';
                    }, d += 250);
                    sched(function() {
                        var baseSrc = (caseImg.getAttribute('src') || '').replace(/briefcase-laptop-[^.]+\.png/, '');
                        caseImg.src = baseSrc + 'briefcase-laptop-fully-open.png';
                        packText1.classList.remove('visible');
                        packText2.classList.add('visible');
                    }, d += 250);

                    for (var i = 0; i < tags.length; i++) {
                        (function(tag) {
                            sched(function() { tag.classList.add('visible'); }, d += 600);
                        })(tags[i]);
                    }

                    sched(function() {
                        secNote.classList.add('visible');
                    }, d += 1000);

                    // Tags fly into the suitcase
                    sched(function() {
                        secNote.classList.remove('visible');
                        packText2.classList.remove('visible');
                        for (var j = 0; j < tags.length; j++) {
                            (function(tag, idx) {
                                sched(function() { tag.classList.add('packed'); }, idx * 100);
                            })(tags[j], j);
                        }
                    }, d += 1800);

                    // Collapse tags + compact suitcase, then close
                    sched(function() {
                        tagsWrap.classList.add('collapsed');
                        caseArea.classList.add('compact');
                        var baseSrc = (caseImg.getAttribute('src') || '').replace(/briefcase-laptop-[^.]+\.png/, '');
                        caseImg.src = baseSrc + 'briefcase-laptop-half-open.png';
                    }, d += 700);

                    sched(function() {
                        var baseSrc = (caseImg.getAttribute('src') || '').replace(/briefcase-laptop-[^.]+\.png/, '');
                        caseImg.src = baseSrc + 'briefcase-laptop-closed.png';
                    }, d += 400);

                    // Reconnector label appears below the closed suitcase
                    sched(function() {
                        labelWrap.classList.add('visible');
                    }, d += 600);

                    sched(function() {
                        labelExplain.classList.add('visible');
                        stepping = false;
                    }, d += 800);
                    break;

                case 2: // Crossing the boundary
                    crossPhase.classList.add('active');
                    sched(function() {
                        travelCase.classList.add('visible');
                    }, d += 300);
                    sched(function() {
                        travelCase.classList.add('arrived');
                    }, d += 500);
                    sched(function() {
                        crossText.classList.add('visible');
                        stepping = false;
                    }, d += 2400);
                    break;

                case 3: // Three flavors side by side
                    flavPhase.classList.add('active');
                    lazyCode.innerHTML = lazyTokens;
                    authCode.innerHTML = authTokens;
                    allCode.innerHTML = allTokens;

                    sched(function() { lazyDiv.classList.add('visible'); }, d += 200);
                    sched(function() { authDiv.classList.add('visible'); }, d += 250);
                    sched(function() {
                        allDiv.classList.add('visible');
                        stepping = false;
                    }, d += 250);
                    break;

                case 4: // Punchline
                    punchPhase.classList.add('active');
                    punchCode.innerHTML = punchTokens;
                    sched(function() { punchText1.classList.add('visible'); }, d += 200);
                    sched(function() {
                        punchCode.classList.add('visible');
                    }, d += 600);
                    sched(function() { punchNote.classList.add('visible'); }, d += 800);
                    sched(function() {
                        tagline.classList.add('visible');
                    }, d += 1000);
                    sched(function() {
                        replayBtn.classList.add('visible');
                        stepping = false;
                    }, d += 1200);
                    break;

                default:
                    stepping = false;
                    break;
            }
        }

        var maxStep = 4;

        function updateNav() {
            if (prevBtn) prevBtn.disabled = curStep <= 0;
            if (nextBtn) nextBtn.disabled = curStep >= maxStep;
        }

        function advance() {
            if (stepping) return;
            if (curStep >= maxStep) return;
            enterStep(curStep + 1);
            updateNav();
        }

        function goBack() {
            if (stepping) return;
            if (curStep <= 0) return;
            enterStep(curStep - 1);
            updateNav();
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                advance();
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                goBack();
            });
        }

        if (replayBtn) {
            replayBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                resetAllState();
                updateNav();
                setTimeout(function() { enterStep(0); updateNav(); }, 200);
            });
        }

        showcaseCallbacks['cucumber-2'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    function setupShare1Showcase() {
        var showcase = document.getElementById('sh1Showcase');
        if (!showcase) return;

        var prevBtn     = document.getElementById('sh1Prev');
        var nextBtn     = document.getElementById('sh1Next');

        var setupPhase  = document.getElementById('sh1Setup');
        var setupCode   = document.getElementById('sh1SetupCode');
        var expandNote  = document.getElementById('sh1ExpandNote');

        var revealPhase = document.getElementById('sh1Reveal');
        var revealText  = document.getElementById('sh1RevealText');
        var diagram     = document.getElementById('sh1Diagram');
        var shareNode   = document.getElementById('sh1ShareNode');
        var proc1       = document.getElementById('sh1Proc1');
        var proc2       = document.getElementById('sh1Proc2');
        var proc3       = document.getElementById('sh1Proc3');
        var proc4       = document.getElementById('sh1Proc4');
        var line1       = document.getElementById('sh1Line1');
        var line2       = document.getElementById('sh1Line2');
        var line3       = document.getElementById('sh1Line3');
        var line4       = document.getElementById('sh1Line4');
        var counterEl   = document.getElementById('sh1Counter');
        var resultsEl   = document.getElementById('sh1Results');
        var revealSub   = document.getElementById('sh1RevealSub');
        var kicker      = document.getElementById('sh1Kicker');

        var compPhase   = document.getElementById('sh1Compare');
        var panelGood   = document.getElementById('sh1PanelGood');
        var panelBad    = document.getElementById('sh1PanelBad');
        var goodCode    = document.getElementById('sh1GoodCode');
        var badCode     = document.getElementById('sh1BadCode');

        var punchPhase  = document.getElementById('sh1Punchline');
        var punchTitle  = document.getElementById('sh1PunchTitle');
        var punchCode   = document.getElementById('sh1PunchCode');
        var tagline     = document.getElementById('sh1Tagline');
        var replayBtn   = document.getElementById('sh1Replay');

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function tok(tokens) {
            var html = '';
            for (var i = 0; i < tokens.length; i++) {
                var t = tokens[i];
                if (typeof t === 'string') { html += esc(t); }
                else { html += '<span class="' + t.c + '">' + esc(t.v) + '</span>'; }
            }
            return html;
        }

        var typed = function(inner) {
            return '<span class="sh1-typed">' + inner + '</span>';
        };
        var hl = function(v) {
            return '<span class="api-hl">' + esc(v) + '</span>';
        };
        var sharePrefix = typed(hl('share') + '.');

        var unifiedHTML = ''
            + '<span class="cm">' + esc('# here\'s some simple python code') + '</span>\n'
            + typed(hl('share') + ' = ' + hl('Share') + '()\n') + '\n'
            + sharePrefix + 'counter = <span class="nr">0</span>\n'
            + sharePrefix + 'results = []\n'
            + sharePrefix + 'log = logging.<span class="fn">' + esc('getLogger') + '</span>(<span class="st">' + esc('"worker"') + '</span>)\n'
            + '\n'
            + '<span class="kw">def</span> <span class="fn">double</span>(item):\n'
            + '    result = item * <span class="nr">2</span>\n'
            + '    ' + sharePrefix + 'results.<span class="fn">append</span>(result)\n'
            + '    ' + sharePrefix + 'counter += <span class="nr">1</span>\n'
            + '    ' + sharePrefix + 'log.<span class="fn">info</span>(<span class="st">' + esc('f"done: {result}"') + '</span>)';

        var goodTokens = tok([
            {c:'kw', v:'from'}, ' suitkaise ', {c:'kw', v:'import'}, ' ', {c:'api-hl', v:'Share'}, ', ', {c:'api-hl', v:'Pool'}, '\n',
            '\n',
            {c:'api-hl', v:'share'}, ' = ', {c:'fn', v:'Share'}, '()\n',
            {c:'api-hl', v:'share'}, '.counter = ', {c:'nr', v:'0'}, '\n',
            {c:'api-hl', v:'share'}, '.results = []\n',
            {c:'api-hl', v:'share'}, '.log = logging.', {c:'fn', v:'getLogger'}, '(', {c:'st', v:'"worker"'}, ')\n',
            '\n',
            {c:'kw', v:'def'}, ' ', {c:'fn', v:'process'}, '(item):\n',
            '    result = item * ', {c:'nr', v:'2'}, '\n',
            '    ', {c:'api-hl', v:'share'}, '.results.', {c:'fn', v:'append'}, '(result)\n',
            '    ', {c:'api-hl', v:'share'}, '.counter += ', {c:'nr', v:'1'}, '\n',
            '    ', {c:'api-hl', v:'share'}, '.log.', {c:'fn', v:'info'}, '(', {c:'st', v:'f"done: {result}"'}, ')\n',
            '\n',
            'pool = ', {c:'api-hl', v:'Pool'}, '(workers=', {c:'nr', v:'4'}, ')\n',
            'pool.', {c:'fn', v:'star'}, '().', {c:'fn', v:'map'}, '(process, [(x, share) ', {c:'kw', v:'for'}, ' x ', {c:'kw', v:'in'}, ' ', {c:'fn', v:'range'}, '(', {c:'nr', v:'4'}, ')])'
        ]);

        var badTokens = tok([
            {c:'kw', v:'from'}, ' multiprocessing ', {c:'kw', v:'import'}, ' Process, Manager\n',
            '\n',
            'manager = ', {c:'fn', v:'Manager'}, '()\n',
            'counter = manager.', {c:'fn', v:'Value'}, '(', {c:'st', v:"'i'"}, ', ', {c:'nr', v:'0'}, ')\n',
            'lock = manager.', {c:'fn', v:'Lock'}, '()\n',
            'results = manager.', {c:'fn', v:'list'}, '()\n',
            {c:'bad', v:'# no logger support ✗'}, '\n',
            '\n',
            {c:'kw', v:'def'}, ' ', {c:'fn', v:'process'}, '(item):\n',
            '    result = item * ', {c:'nr', v:'2'}, '\n',
            '    results.', {c:'fn', v:'append'}, '(result)\n',
            '    ', {c:'kw', v:'with'}, ' lock:\n',
            '        counter.value += ', {c:'nr', v:'1'}, '\n',
            '    ', {c:'bad', v:"# can't share logger ✗"}, '\n',
            '\n',
            'workers = []\n',
            {c:'kw', v:'for'}, ' i ', {c:'kw', v:'in'}, ' ', {c:'fn', v:'range'}, '(', {c:'nr', v:'4'}, '):\n',
            '    p = ', {c:'fn', v:'Process'}, '(target=process, args=(i,))\n',
            '    p.', {c:'fn', v:'start'}, '()\n',
            '    workers.', {c:'fn', v:'append'}, '(p)\n',
            {c:'kw', v:'for'}, ' p ', {c:'kw', v:'in'}, ' workers:\n',
            '    p.', {c:'fn', v:'join'}, '()'
        ]);

        var punchTokens = tok([
            {c:'api-hl', v:'share'}, ' = ', {c:'fn', v:'Share'}, '()\n',
            {c:'api-hl', v:'share'}, '.anything = anything\n',
            {c:'cm', v:"# that's it."}
        ]);

        var allPhases = [setupPhase, revealPhase, compPhase, punchPhase];
        var procs = [proc1, proc2, proc3, proc4];
        var lines = [line1, line2, line3, line4];

        var curStep = -1;
        var stepping = false;

        function hideAllPhases() {
            allPhases.forEach(function(p) { if (p) p.classList.remove('active'); });
        }

        function resetAllState() {
            cleanupSh1();
            hideAllPhases();

            [revealText, revealSub, kicker, punchTitle, punchCode, tagline].forEach(function(el) {
                if (el) el.classList.remove('visible');
            });

            if (setupCode) {
                setupCode.innerHTML = '';
                setupCode.classList.remove('visible');
                setupCode.querySelectorAll('.sh1-typed').forEach(function(el) { el.classList.remove('visible'); });
            }
            if (expandNote) expandNote.classList.remove('visible');
            if (diagram) diagram.classList.remove('visible');
            if (shareNode) shareNode.classList.remove('visible', 'receiving');
            procs.forEach(function(p) { if (p) p.classList.remove('visible', 'sending'); });
            lines.forEach(function(l) { if (l) l.classList.remove('active'); });

            if (counterEl) counterEl.textContent = '0';
            if (resultsEl) resultsEl.textContent = '';

            if (panelGood) panelGood.classList.remove('visible');
            if (panelBad) panelBad.classList.remove('visible');
            if (goodCode) goodCode.innerHTML = '';
            if (badCode) badCode.innerHTML = '';
            if (punchCode) punchCode.innerHTML = '';

            if (tagline) tagline.classList.remove('visible');
            if (replayBtn) replayBtn.classList.remove('visible');

            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            sh1Timers.push(setTimeout(fn, delay));
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupSh1();
            hideAllPhases();
            curStep = step;

            var d = 0;

            switch (step) {
                case 0: // Plain code (typed spans hidden)
                    setupPhase.classList.add('active');
                    setupCode.innerHTML = unifiedHTML;
                    setupCode.querySelectorAll('.sh1-typed').forEach(function(el) { el.classList.remove('visible'); });
                    if (expandNote) expandNote.classList.remove('visible');

                    sched(function() {
                        setupCode.classList.add('visible');
                        stepping = false;
                    }, d += 400);
                    break;

                case 1: // Type in Share — same phase, animate typed spans
                    setupPhase.classList.add('active');
                    setupCode.classList.add('visible');

                    var typedEls = setupCode.querySelectorAll('.sh1-typed');
                    typedEls.forEach(function(el, i) {
                        sched(function() { el.classList.add('visible'); }, d += 150);
                    });

                    sched(function() {
                        if (expandNote) expandNote.classList.add('visible');
                        stepping = false;
                    }, d += 500);
                    break;

                case 2: // The Reveal — processes appear, send data to Share
                    revealPhase.classList.add('active');
                    sched(function() { revealText.classList.add('visible'); }, d += 300);

                    sched(function() { diagram.classList.add('visible'); }, d += 600);
                    sched(function() { shareNode.classList.add('visible'); }, d += 400);

                    // Processes pop up one by one
                    for (var i = 0; i < procs.length; i++) {
                        (function(proc) {
                            sched(function() { proc.classList.add('visible'); }, d += 300);
                        })(procs[i]);
                    }

                    d += 500;

                    // Each process sends its result to Share in order
                    var sendResults = [2, 4, 6, 8];
                    for (var si = 0; si < 4; si++) {
                        (function(idx, result) {
                            // Light up line + process glow
                            sched(function() {
                                procs[idx].classList.add('sending');
                                lines[idx].classList.add('active');
                            }, d);

                            // Update Share values
                            sched(function() {
                                shareNode.classList.add('receiving');
                                if (counterEl) counterEl.textContent = String(idx + 1);
                                if (resultsEl) {
                                    var arr = sendResults.slice(0, idx + 1);
                                    resultsEl.textContent = arr.join(', ');
                                }
                            }, d += 400);

                            // Clear glow
                            sched(function() {
                                procs[idx].classList.remove('sending');
                                lines[idx].classList.remove('active');
                                shareNode.classList.remove('receiving');
                            }, d += 400);
                        })(si, sendResults[si]);
                    }

                    sched(function() { revealSub.classList.add('visible'); }, d += 300);

                    sched(function() {
                        kicker.classList.add('visible');
                        stepping = false;
                    }, d += 1200);
                    break;

                case 3: // Comparison
                    compPhase.classList.add('active');
                    goodCode.innerHTML = goodTokens;
                    badCode.innerHTML = badTokens;

                    sched(function() { panelGood.classList.add('visible'); }, d += 200);
                    sched(function() {
                        panelBad.classList.add('visible');
                        stepping = false;
                    }, d += 350);
                    break;

                case 4: // Punchline
                    punchPhase.classList.add('active');
                    punchCode.innerHTML = punchTokens;

                    sched(function() { punchTitle.classList.add('visible'); }, d += 200);
                    sched(function() { punchCode.classList.add('visible'); }, d += 600);
                    sched(function() { tagline.classList.add('visible'); }, d += 1000);
                    sched(function() {
                        replayBtn.classList.add('visible');
                        stepping = false;
                    }, d += 1200);
                    break;

                default:
                    stepping = false;
                    break;
            }
        }

        var maxStep = 4;

        function updateNav() {
            if (prevBtn) prevBtn.disabled = curStep <= 0;
            if (nextBtn) nextBtn.disabled = curStep >= maxStep;
        }

        function advance() {
            if (stepping) return;
            if (curStep >= maxStep) return;
            enterStep(curStep + 1);
            updateNav();
        }

        function goBack() {
            if (stepping) return;
            if (curStep <= 0) return;
            enterStep(curStep - 1);
            updateNav();
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                advance();
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                goBack();
            });
        }

        if (replayBtn) {
            replayBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                resetAllState();
                updateNav();
                setTimeout(function() { enterStep(0); updateNav(); }, 200);
            });
        }

        showcaseCallbacks['share-1'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    // ============================================
    // SK-1 Showcase (The Swiss Army Knife)
    // ============================================

    function setupSk1Showcase() {
        var showcase = document.getElementById('sk1Showcase');
        if (!showcase) return;

        var prevBtn    = document.getElementById('sk1Prev');
        var nextBtn    = document.getElementById('sk1Next');

        var introPhase  = document.getElementById('sk1Intro');
        var sk1Title    = document.getElementById('sk1Title');
        var sk1Col1     = document.getElementById('sk1Collapse');
        var sk1Col2     = document.getElementById('sk1Collapse2');
        var introCode   = document.getElementById('sk1IntroCode');
        var introNote   = document.getElementById('sk1IntroNote');

        var modPhase   = document.getElementById('sk1Modifiers');
        var modTitle   = document.getElementById('sk1ModTitle');
        var mods = [];
        for (var mi = 0; mi < 5; mi++) mods.push(document.getElementById('sk1Mod' + mi));

        var demoPhase     = document.getElementById('sk1Demo');
        var demoTitle     = document.getElementById('sk1DemoTitle');
        var demoAsync     = document.getElementById('sk1DemoAsync');
        var demoAsyncCode = document.getElementById('sk1DemoAsyncCode');
        var demoBg        = document.getElementById('sk1DemoBg');
        var demoBgCode    = document.getElementById('sk1DemoBgCode');
        var demoNote      = document.getElementById('sk1DemoNote');

        var chainPhase = document.getElementById('sk1Chain');
        var chainLabel = document.getElementById('sk1ChainLabel');
        var chainCode  = document.getElementById('sk1ChainCode');
        var chainNote  = document.getElementById('sk1ChainNote');

        var punchPhase = document.getElementById('sk1Punchline');
        var punchTitle = document.getElementById('sk1PunchTitle');
        var punchCode  = document.getElementById('sk1PunchCode');
        var tagline    = document.getElementById('sk1Tagline');
        var replayBtn  = document.getElementById('sk1Replay');

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function tok(tokens) {
            var html = '';
            for (var i = 0; i < tokens.length; i++) {
                var t = tokens[i];
                if (typeof t === 'string') { html += esc(t); }
                else { html += '<span class="' + t.c + '">' + esc(t.v) + '</span>'; }
            }
            return html;
        }

        var introTokens = tok([
            {c:'kw', v:'from'}, ' suitkaise ', {c:'kw', v:'import'}, ' ', {c:'dc', v:'sk'}, '\n',
            '\n',
            {c:'dc', v:'@sk'}, '\n',
            {c:'kw', v:'def'}, ' ', {c:'fn', v:'fetch_data'}, '(url):\n',
            '    ', {c:'kw', v:'return'}, ' requests.', {c:'fn', v:'get'}, '(url).', {c:'fn', v:'json'}, '()\n',
            '\n',
            {c:'cm', v:'# works exactly like before'}, '\n',
            'data = ', {c:'fn', v:'fetch_data'}, '(', {c:'st', v:'"https://api.example.com"'}, ')'
        ]);

        var asyncDemoTokens = tok([
            {c:'cm', v:'# your sync function'}, '\n',
            {c:'dc', v:'@sk'}, '\n',
            {c:'kw', v:'def'}, ' ', {c:'fn', v:'fetch_data'}, '(url):\n',
            '    ', {c:'kw', v:'return'}, ' requests.', {c:'fn', v:'get'}, '(url).', {c:'fn', v:'json'}, '()\n',
            '\n',
            {c:'cm', v:'# now it\'s async'}, '\n',
            'data = ', {c:'kw', v:'await'}, ' ', {c:'fn', v:'fetch_data'}, '.', {c:'api-hl', v:'asynced'}, '()(', {c:'st', v:'"url"'}, ')'
        ]);

        var bgDemoTokens = tok([
            {c:'cm', v:'# fire and forget'}, '\n',
            'future = ', {c:'fn', v:'fetch_data'}, '.', {c:'api-hl', v:'background'}, '()(', {c:'st', v:'"url"'}, ')\n',
            '\n',
            {c:'cm', v:'# do other work...'}, '\n',
            {c:'fn', v:'process_other_stuff'}, '()\n',
            '\n',
            {c:'cm', v:'# get the result when ready'}, '\n',
            'data = future.', {c:'fn', v:'result'}, '()'
        ]);

        var chainTokens = tok([
            {c:'cm', v:'# retry 3 times, 5s timeout per attempt, throttled'}, '\n',
            'data = ', {c:'fn', v:'fetch_data'}, '\n',
            '    .', {c:'api-hl', v:'retry'}, '(', {c:'nr', v:'3'}, ')\n',
            '    .', {c:'api-hl', v:'timeout'}, '(', {c:'nr', v:'5.0'}, ')\n',
            '    .', {c:'api-hl', v:'rate_limit'}, '(', {c:'nr', v:'2'}, ')\n',
            '(', {c:'st', v:'"https://api.example.com"'}, ')\n',
            '\n',
            {c:'cm', v:'# same thing, different order — identical behavior'}, '\n',
            'data = ', {c:'fn', v:'fetch_data'}, '.', {c:'api-hl', v:'timeout'}, '(', {c:'nr', v:'5.0'}, ').', {c:'api-hl', v:'retry'}, '(', {c:'nr', v:'3'}, ')(', {c:'st', v:'"url"'}, ')'
        ]);

        var punchTokens = tok([
            {c:'dc', v:'@sk'}, '\n',
            {c:'kw', v:'def'}, ' ', {c:'fn', v:'anything'}, '(...):\n',
            '    ...\n',
            '\n',
            {c:'cm', v:"# that's it. you're done."}
        ]);

        var allPhases = [introPhase, modPhase, demoPhase, chainPhase, punchPhase];

        var curStep = -1;
        var stepping = false;
        var maxStep = 4;

        function hideAllPhases() {
            allPhases.forEach(function(p) { if (p) p.classList.remove('active'); });
        }

        function resetAllState() {
            cleanupSk1();
            hideAllPhases();

            if (sk1Title) sk1Title.classList.remove('visible');
            if (sk1Col1) sk1Col1.classList.remove('hidden');
            if (sk1Col2) sk1Col2.classList.remove('hidden');
            if (introCode) { introCode.innerHTML = ''; introCode.classList.remove('visible'); }
            if (introNote) introNote.classList.remove('visible');

            if (modTitle) modTitle.classList.remove('visible');
            mods.forEach(function(m) { if (m) m.classList.remove('visible', 'highlight'); });

            if (demoTitle) demoTitle.classList.remove('visible');
            if (demoAsync) demoAsync.classList.remove('visible');
            if (demoAsyncCode) { demoAsyncCode.innerHTML = ''; demoAsyncCode.classList.remove('visible'); }
            if (demoBg) demoBg.classList.remove('visible');
            if (demoBgCode) { demoBgCode.innerHTML = ''; demoBgCode.classList.remove('visible'); }
            if (demoNote) demoNote.classList.remove('visible');

            if (chainLabel) chainLabel.classList.remove('visible');
            if (chainCode) { chainCode.innerHTML = ''; chainCode.classList.remove('visible'); }
            if (chainNote) chainNote.classList.remove('visible');

            if (punchTitle) punchTitle.classList.remove('visible');
            if (punchCode) { punchCode.innerHTML = ''; punchCode.classList.remove('visible'); }
            if (tagline) tagline.classList.remove('visible');
            if (replayBtn) replayBtn.classList.remove('visible');

            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            sk1Timers.push(setTimeout(fn, delay));
        }

        function updateNav() {
            if (prevBtn) prevBtn.disabled = curStep <= 0;
            if (nextBtn) nextBtn.disabled = curStep >= maxStep;
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupSk1();
            hideAllPhases();
            curStep = step;

            var d = 0;

            switch (step) {
                case 0: // The decorator
                    introPhase.classList.add('active');
                    introCode.innerHTML = introTokens;

                    sched(function() { sk1Title.classList.add('visible'); }, d += 300);

                    sched(function() {
                        sk1Col1.classList.add('hidden');
                        sk1Col2.classList.add('hidden');
                    }, d += 2000);

                    sched(function() { introCode.classList.add('visible'); }, d += 800);
                    sched(function() {
                        introNote.classList.add('visible');
                        stepping = false;
                    }, d += 800);
                    break;

                case 1: // Modifiers one by one
                    modPhase.classList.add('active');
                    sched(function() { modTitle.classList.add('visible'); }, d += 300);

                    mods.forEach(function(mod, idx) {
                        sched(function() { if (mod) mod.classList.add('visible'); }, d += 300);
                    });

                    sched(function() { stepping = false; }, d += 300);
                    break;

                case 2: // asynced & background demo
                    demoPhase.classList.add('active');
                    demoAsyncCode.innerHTML = asyncDemoTokens;
                    demoBgCode.innerHTML = bgDemoTokens;

                    sched(function() { demoTitle.classList.add('visible'); }, d += 300);
                    sched(function() {
                        demoAsync.classList.add('visible');
                        demoAsyncCode.classList.add('visible');
                    }, d += 500);
                    sched(function() {
                        demoBg.classList.add('visible');
                        demoBgCode.classList.add('visible');
                    }, d += 600);
                    sched(function() {
                        demoNote.classList.add('visible');
                        stepping = false;
                    }, d += 800);
                    break;

                case 3: // Chain
                    chainPhase.classList.add('active');
                    chainCode.innerHTML = chainTokens;

                    sched(function() { chainLabel.classList.add('visible'); }, d += 300);
                    sched(function() { chainCode.classList.add('visible'); }, d += 500);
                    sched(function() {
                        chainNote.classList.add('visible');
                        stepping = false;
                    }, d += 800);
                    break;

                case 4: // Punchline
                    punchPhase.classList.add('active');
                    punchCode.innerHTML = punchTokens;

                    sched(function() { punchTitle.classList.add('visible'); }, d += 300);
                    sched(function() { punchCode.classList.add('visible'); }, d += 600);
                    sched(function() { tagline.classList.add('visible'); }, d += 800);
                    sched(function() {
                        replayBtn.classList.add('visible');
                        stepping = false;
                    }, d += 1000);
                    break;

                default:
                    stepping = false;
                    break;
            }
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (stepping || curStep >= maxStep) return;
                enterStep(curStep + 1);
                updateNav();
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (stepping || curStep <= 0) return;
                enterStep(curStep - 1);
                updateNav();
            });
        }

        if (replayBtn) {
            replayBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                resetAllState();
                updateNav();
                setTimeout(function() { enterStep(0); updateNav(); }, 200);
            });
        }

        showcaseCallbacks['sk-1'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    // ============================================
    // Timing-1 Showcase
    // ============================================

    function setupTiming1Showcase() {
        var showcase = document.getElementById('tm1Showcase');
        if (!showcase) return;

        var prevBtn = document.getElementById('tm1Prev');
        var nextBtn = document.getElementById('tm1Next');

        var beforePhase = document.getElementById('tm1Before');
        var beforeTitle = document.getElementById('tm1BeforeTitle');
        var beforeCode = document.getElementById('tm1BeforeCode');
        var beforeCount = document.getElementById('tm1BeforeCount');

        var afterPhase = document.getElementById('tm1After');
        var afterTitle = document.getElementById('tm1AfterTitle');
        var afterCode = document.getElementById('tm1AfterCode');
        var afterNote = document.getElementById('tm1AfterNote');

        var statsPhase = document.getElementById('tm1Stats');
        var statsTitle = document.getElementById('tm1StatsTitle');
        var statsGrid = document.getElementById('tm1StatsGrid');
        var stats = statsGrid ? statsGrid.querySelectorAll('.tm1-stat') : [];
        var statsNote = document.getElementById('tm1StatsNote');

        var punchPhase = document.getElementById('tm1Punchline');
        var punchTitle = document.getElementById('tm1PunchTitle');
        var punchCode = document.getElementById('tm1PunchCode');
        var panelDec = document.getElementById('tm1PanelDec');
        var panelCtx = document.getElementById('tm1PanelCtx');
        var ctxCode = document.getElementById('tm1CtxCode');
        var tagline = document.getElementById('tm1Tagline');
        var replayBtn = document.getElementById('tm1Replay');

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function tok(tokens) {
            var html = '';
            for (var i = 0; i < tokens.length; i++) {
                var t = tokens[i];
                if (typeof t === 'string') { html += esc(t); }
                else { html += '<span class="' + t.c + '">' + esc(t.v) + '</span>'; }
            }
            return html;
        }

        var beforeTokens = tok([
            {c:'kw',v:'import'}, ' ', {c:'fn',v:'time'}, '\n',
            {c:'kw',v:'import'}, ' ', {c:'fn',v:'statistics'}, '\n\n',
            {c:'fn',v:'times'}, ' = []\n\n',
            {c:'kw',v:'def'}, ' ', {c:'fn',v:'do_work'}, '():\n',
            '    ', {c:'cm',v:'# ... your code ...'}, '\n',
            '    ', {c:'kw',v:'pass'}, '\n\n',
            {c:'kw',v:'for'}, ' i ', {c:'kw',v:'in'}, ' ', {c:'bi',v:'range'}, '(', {c:'nr',v:'100'}, '):\n',
            '    start = time.perf_counter()\n',
            '    do_work()\n',
            '    end = time.perf_counter()\n',
            '    times.append(end - start)\n\n',
            'mean = statistics.mean(times)\n',
            'median = statistics.median(times)\n',
            'stdev = statistics.stdev(times)\n',
            'sorted_t = ', {c:'bi',v:'sorted'}, '(times)\n',
            'p95 = sorted_t[', {c:'bi',v:'int'}, '(', {c:'nr',v:'0.95'}, ' * ', {c:'bi',v:'len'}, '(sorted_t))]'
        ]);

        var afterTokens = tok([
            {c:'kw',v:'from'}, ' ', {c:'fn',v:'suitkaise.timing'}, ' ', {c:'kw',v:'import'}, ' ', {c:'dc',v:'timethis'}, '\n\n',
            {c:'api-hl',v:'@timethis()'}, '\n',
            {c:'kw',v:'def'}, ' ', {c:'fn',v:'do_work'}, '():\n',
            '    ', {c:'cm',v:'# ... your code ...'}, '\n',
            '    ', {c:'kw',v:'pass'}, '\n\n',
            {c:'kw',v:'for'}, ' i ', {c:'kw',v:'in'}, ' ', {c:'bi',v:'range'}, '(', {c:'nr',v:'100'}, '):\n',
            '    do_work()'
        ]);

        var punchTokens = tok([
            {c:'api-hl',v:'@timethis()'}, '\n',
            {c:'kw',v:'def'}, ' ', {c:'fn',v:'anything'}, '():\n',
            '    ...\n\n',
            'anything.', {c:'dc',v:'timer'}, '.', {c:'dc',v:'mean'}, '\n',
            'anything.', {c:'dc',v:'timer'}, '.', {c:'dc',v:'median'}, '\n',
            'anything.', {c:'dc',v:'timer'}, '.', {c:'dc',v:'percentile'}, '(', {c:'nr',v:'99'}, ')'
        ]);

        var ctxTokens = tok([
            {c:'kw',v:'with'}, ' ', {c:'api-hl',v:'TimeThis()'}, ' ', {c:'kw',v:'as'}, ' timer:\n',
            '    ', {c:'cm',v:'# anything here gets timed'}, '\n',
            '    ...\n\n',
            'timer.', {c:'dc',v:'mean'}, '\n',
            'timer.', {c:'dc',v:'stdev'}, '\n',
            'timer.', {c:'dc',v:'percentile'}, '(', {c:'nr',v:'95'}, ')'
        ]);

        var allPhases = [beforePhase, afterPhase, statsPhase, punchPhase];
        var curStep = -1;
        var stepping = false;
        var maxStep = 3;

        function hideAllPhases() {
            allPhases.forEach(function(p) { if (p) p.classList.remove('active'); });
        }

        function resetAllState() {
            cleanupTm1();
            hideAllPhases();

            [beforeTitle, beforeCode, beforeCount,
             afterTitle, afterCode, afterNote,
             statsTitle, statsNote,
             punchTitle, punchCode, ctxCode, panelDec, panelCtx, tagline].forEach(function(el) {
                if (el) { el.classList.remove('visible'); }
            });

            stats.forEach(function(s) { s.classList.remove('visible'); });
            if (replayBtn) replayBtn.classList.remove('visible');

            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            tm1Timers.push(setTimeout(fn, delay));
        }

        function updateNav() {
            if (prevBtn) prevBtn.disabled = (curStep <= 0);
            if (nextBtn) nextBtn.disabled = (curStep >= maxStep);
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupTm1();
            hideAllPhases();
            curStep = step;
            updateNav();

            switch (step) {
                case 0:
                    beforePhase.classList.add('active');
                    beforeCode.innerHTML = beforeTokens;
                    sched(function() { beforeTitle.classList.add('visible'); }, 100);
                    sched(function() { beforeCode.classList.add('visible'); }, 500);
                    sched(function() { beforeCount.classList.add('visible'); stepping = false; }, 1200);
                    break;

                case 1:
                    afterPhase.classList.add('active');
                    afterCode.innerHTML = afterTokens;
                    sched(function() { afterTitle.classList.add('visible'); }, 100);
                    sched(function() { afterCode.classList.add('visible'); }, 500);
                    sched(function() { afterNote.classList.add('visible'); stepping = false; }, 1200);
                    break;

                case 2:
                    statsPhase.classList.add('active');
                    sched(function() { statsTitle.classList.add('visible'); }, 100);
                    var d = 500;
                    for (var i = 0; i < stats.length; i++) {
                        (function(idx, delay) {
                            sched(function() { stats[idx].classList.add('visible'); }, delay);
                        })(i, d);
                        d += 120;
                    }
                    sched(function() { statsNote.classList.add('visible'); stepping = false; }, d + 400);
                    break;

                case 3:
                    punchPhase.classList.add('active');
                    punchCode.innerHTML = punchTokens;
                    ctxCode.innerHTML = ctxTokens;
                    sched(function() { punchTitle.classList.add('visible'); }, 100);
                    sched(function() { panelDec.classList.add('visible'); punchCode.classList.add('visible'); }, 500);
                    sched(function() { panelCtx.classList.add('visible'); ctxCode.classList.add('visible'); }, 900);
                    sched(function() { tagline.classList.add('visible'); }, 1500);
                    sched(function() { replayBtn.classList.add('visible'); stepping = false; }, 2000);
                    break;
            }
        }

        if (nextBtn) nextBtn.addEventListener('click', function() {
            if (curStep < maxStep) enterStep(curStep + 1);
        });
        if (prevBtn) prevBtn.addEventListener('click', function() {
            if (curStep > 0) enterStep(curStep - 1);
        });
        if (replayBtn) replayBtn.addEventListener('click', function() {
            resetAllState();
            setTimeout(function() { enterStep(0); updateNav(); }, 200);
        });

        showcaseCallbacks['timing-1'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    // ============================================
    // Paths-1 Showcase
    // ============================================

    function setupPaths1Showcase() {
        var showcase = document.getElementById('pt1Showcase');
        if (!showcase) return;

        var prevBtn = document.getElementById('pt1Prev');
        var nextBtn = document.getElementById('pt1Next');

        var probPhase = document.getElementById('pt1Problem');
        var probTitle = document.getElementById('pt1ProbTitle');
        var cardMac = document.getElementById('pt1CardMac');
        var cardWin = document.getElementById('pt1CardWin');
        var cardLinux = document.getElementById('pt1CardLinux');
        var compare = document.getElementById('pt1Compare');
        var probCards = [cardMac, cardWin, cardLinux];

        var fixPhase = document.getElementById('pt1Fix');
        var fixTitle = document.getElementById('pt1FixTitle');
        var fixCardMac = document.getElementById('pt1FixCardMac');
        var fixCardWin = document.getElementById('pt1FixCardWin');
        var fixCardLinux = document.getElementById('pt1FixCardLinux');
        var fixCompare = document.getElementById('pt1FixCompare');
        var fixCards = [fixCardMac, fixCardWin, fixCardLinux];

        var punchPhase = document.getElementById('pt1Punchline');
        var punchTitle = document.getElementById('pt1PunchTitle');
        var punchCode = document.getElementById('pt1PunchCode');
        var tagline = document.getElementById('pt1Tagline');
        var replayBtn = document.getElementById('pt1Replay');

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function tok(tokens) {
            var html = '';
            for (var i = 0; i < tokens.length; i++) {
                var t = tokens[i];
                if (typeof t === 'string') { html += esc(t); }
                else { html += '<span class="' + t.c + '">' + esc(t.v) + '</span>'; }
            }
            return html;
        }

        var punchTokens = tok([
            {c:'kw',v:'from'}, ' ', {c:'fn',v:'suitkaise.paths'}, ' ', {c:'kw',v:'import'}, ' ', {c:'api-hl',v:'Skpath'}, '\n\n',
            'path = ', {c:'api-hl',v:'Skpath'}, '(', {c:'st',v:'"config/settings.yaml"'}, ')\n\n',
            'path.', {c:'dc',v:'rp'}, '        ', {c:'cm',v:'# same on every machine'}, '\n',
            'path.', {c:'dc',v:'ap'}, '        ', {c:'cm',v:'# absolute, always forward slashes'}, '\n',
            'path.', {c:'dc',v:'platform'}, '  ', {c:'cm',v:'# native OS separators'}
        ]);

        var allPhases = [probPhase, fixPhase, punchPhase];
        var curStep = -1;
        var stepping = false;
        var maxStep = 2;

        function hideAllPhases() {
            allPhases.forEach(function(p) { if (p) p.classList.remove('active'); });
        }

        function resetAllState() {
            cleanupPt1();
            hideAllPhases();

            [probTitle, compare, fixTitle, fixCompare,
             punchTitle, punchCode, tagline].forEach(function(el) {
                if (el) el.classList.remove('visible');
            });

            probCards.forEach(function(c) { if (c) c.classList.remove('visible', 'glow-fail'); });
            fixCards.forEach(function(c) { if (c) c.classList.remove('visible', 'glow-pass'); });

            if (replayBtn) replayBtn.classList.remove('visible');

            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            pt1Timers.push(setTimeout(fn, delay));
        }

        function updateNav() {
            if (prevBtn) prevBtn.disabled = (curStep <= 0);
            if (nextBtn) nextBtn.disabled = (curStep >= maxStep);
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupPt1();
            hideAllPhases();
            curStep = step;
            updateNav();

            var d = 0;

            switch (step) {
                case 0:
                    probPhase.classList.add('active');
                    sched(function() { probTitle.classList.add('visible'); }, 100);
                    sched(function() { cardMac.classList.add('visible'); }, d += 400);
                    sched(function() { cardWin.classList.add('visible'); }, d += 400);
                    sched(function() { cardLinux.classList.add('visible'); }, d += 400);
                    sched(function() {
                        probCards.forEach(function(c) { c.classList.add('glow-fail'); });
                        compare.classList.add('visible');
                        stepping = false;
                    }, d += 600);
                    break;

                case 1:
                    fixPhase.classList.add('active');
                    sched(function() { fixTitle.classList.add('visible'); }, 100);
                    sched(function() { fixCardMac.classList.add('visible'); }, d += 400);
                    sched(function() { fixCardWin.classList.add('visible'); }, d += 400);
                    sched(function() { fixCardLinux.classList.add('visible'); }, d += 400);
                    sched(function() {
                        fixCards.forEach(function(c) { c.classList.add('glow-pass'); });
                        fixCompare.classList.add('visible');
                        stepping = false;
                    }, d += 600);
                    break;

                case 2:
                    punchPhase.classList.add('active');
                    punchCode.innerHTML = punchTokens;
                    sched(function() { punchTitle.classList.add('visible'); }, 100);
                    sched(function() { punchCode.classList.add('visible'); }, 600);
                    sched(function() { tagline.classList.add('visible'); }, 1200);
                    sched(function() { replayBtn.classList.add('visible'); stepping = false; }, 1800);
                    break;
            }
        }

        if (nextBtn) nextBtn.addEventListener('click', function() {
            if (curStep < maxStep) enterStep(curStep + 1);
        });
        if (prevBtn) prevBtn.addEventListener('click', function() {
            if (curStep > 0) enterStep(curStep - 1);
        });
        if (replayBtn) replayBtn.addEventListener('click', function() {
            resetAllState();
            setTimeout(function() { enterStep(0); updateNav(); }, 200);
        });

        showcaseCallbacks['paths-1'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    // ============================================
    // Paths-2 Showcase (@autopath)
    // ============================================

    function setupPaths2Showcase() {
        var showcase = document.getElementById('pt2Showcase');
        if (!showcase) return;

        var prevBtn = document.getElementById('pt2Prev');
        var nextBtn = document.getElementById('pt2Next');

        var probPhase = document.getElementById('pt2Problem');
        var probTitle = document.getElementById('pt2ProbTitle');
        var callers = [
            document.getElementById('pt2Caller0'),
            document.getElementById('pt2Caller1')
        ];
        var probLabel = document.getElementById('pt2ProbLabel');
        var probCode = document.getElementById('pt2ProbCode');

        var fixPhase = document.getElementById('pt2Fix');
        var fixTitle = document.getElementById('pt2FixTitle');
        var fixCode = document.getElementById('pt2FixCode');
        var flow = document.getElementById('pt2Flow');
        var flowInputs = [
            document.getElementById('pt2In0'),
            document.getElementById('pt2In1'),
            document.getElementById('pt2In2')
        ];
        var arrow1 = document.getElementById('pt2Arrow1');
        var middle = document.getElementById('pt2Middle');
        var arrow2 = document.getElementById('pt2Arrow2');
        var flowOut = document.getElementById('pt2FlowOut');
        var flowCheck = flowOut ? flowOut.querySelector('.pt2-flow-check') : null;
        var fixNote = document.getElementById('pt2FixNote');

        var punchPhase = document.getElementById('pt2Punchline');
        var punchTitle = document.getElementById('pt2PunchTitle');
        var punchCode = document.getElementById('pt2PunchCode');
        var tagline = document.getElementById('pt2Tagline');
        var replayBtn = document.getElementById('pt2Replay');

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function tok(tokens) {
            var html = '';
            for (var i = 0; i < tokens.length; i++) {
                var t = tokens[i];
                if (typeof t === 'string') { html += esc(t); }
                else { html += '<span class="' + t.c + '">' + esc(t.v) + '</span>'; }
            }
            return html;
        }

        var probTokens = tok([
            {c:'kw',v:'def'}, ' ', {c:'fn',v:'process_file'}, '(path):\n',
            '    ', {c:'kw',v:'if'}, ' ', {c:'bi',v:'isinstance'}, '(path, Path):\n',
            '        path = ', {c:'bi',v:'str'}, '(path)\n',
            '    ', {c:'kw',v:'if'}, ' ', {c:'kw',v:'not'}, ' ', {c:'bi',v:'isinstance'}, '(path, ', {c:'bi',v:'str'}, '):\n',
            '        ', {c:'kw',v:'raise'}, ' TypeError(...)\n',
            '    path = os.path.normpath(path)\n',
            '    ', {c:'cm',v:'# ... finally use it'},
        ]);

        var fixTokens = tok([
            {c:'api-hl',v:'@autopath()'}, '\n',
            {c:'kw',v:'def'}, ' ', {c:'fn',v:'process_file'}, '(path: ', {c:'bi',v:'str'}, '):\n',
            '    ', {c:'cm',v:'# path is always a str, no matter what was passed.'}
        ]);

        var punchTokens = tok([
            {c:'kw',v:'from'}, ' ', {c:'fn',v:'suitkaise.paths'}, ' ', {c:'kw',v:'import'}, ' ', {c:'api-hl',v:'autopath'}, '\n\n',
            {c:'api-hl',v:'@autopath()'}, '\n',
            {c:'kw',v:'def'}, ' ', {c:'fn',v:'anything'}, '(path: ', {c:'bi',v:'str'}, '):\n',
            '    ...  ', {c:'cm',v:'# all paths that get passed become strings'}
        ]);

        var allPhases = [probPhase, fixPhase, punchPhase];
        var curStep = -1;
        var stepping = false;
        var maxStep = 2;

        function hideAllPhases() {
            allPhases.forEach(function(p) { if (p) p.classList.remove('active'); });
        }

        function resetAllState() {
            cleanupPt2();
            hideAllPhases();

            [probTitle, probLabel, probCode, fixTitle, fixCode, fixNote,
             punchTitle, punchCode, tagline].forEach(function(el) {
                if (el) el.classList.remove('visible');
            });

            callers.forEach(function(c) { if (c) c.classList.remove('visible'); });
            flowInputs.forEach(function(fi) { if (fi) fi.classList.remove('visible'); });
            if (flow) flow.classList.remove('visible');
            if (arrow1) arrow1.classList.remove('visible');
            if (middle) middle.classList.remove('visible');
            if (arrow2) arrow2.classList.remove('visible');
            if (flowOut) flowOut.classList.remove('visible', 'glow');
            if (flowCheck) flowCheck.classList.remove('visible');
            if (replayBtn) replayBtn.classList.remove('visible');

            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            pt2Timers.push(setTimeout(fn, delay));
        }

        function updateNav() {
            if (prevBtn) prevBtn.disabled = (curStep <= 0);
            if (nextBtn) nextBtn.disabled = (curStep >= maxStep);
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupPt2();
            hideAllPhases();
            curStep = step;
            updateNav();

            var d = 0;

            switch (step) {
                case 0:
                    probPhase.classList.add('active');
                    probCode.innerHTML = probTokens;
                    sched(function() { probTitle.classList.add('visible'); }, 100);
                    sched(function() { callers[0].classList.add('visible'); }, d += 400);
                    sched(function() { callers[1].classList.add('visible'); }, d += 300);
                    sched(function() { probLabel.classList.add('visible'); }, d += 400);
                    sched(function() { probCode.classList.add('visible'); stepping = false; }, d += 400);
                    break;

                case 1:
                    fixPhase.classList.add('active');
                    fixCode.innerHTML = fixTokens;
                    sched(function() { fixTitle.classList.add('visible'); }, 100);
                    sched(function() { fixCode.classList.add('visible'); }, d += 500);
                    sched(function() { flow.classList.add('visible'); }, d += 500);
                    sched(function() { flowInputs[0].classList.add('visible'); }, d += 300);
                    sched(function() { flowInputs[1].classList.add('visible'); }, d += 250);
                    sched(function() { flowInputs[2].classList.add('visible'); }, d += 250);
                    sched(function() { arrow1.classList.add('visible'); }, d += 300);
                    sched(function() { middle.classList.add('visible'); }, d += 350);
                    sched(function() { arrow2.classList.add('visible'); }, d += 300);
                    sched(function() { flowOut.classList.add('visible'); }, d += 350);
                    sched(function() {
                        flowOut.classList.add('glow');
                        flowCheck.classList.add('visible');
                    }, d += 400);
                    sched(function() { fixNote.classList.add('visible'); stepping = false; }, d += 500);
                    break;

                case 2:
                    punchPhase.classList.add('active');
                    punchCode.innerHTML = punchTokens;
                    sched(function() { punchTitle.classList.add('visible'); }, 100);
                    sched(function() { punchCode.classList.add('visible'); }, 600);
                    sched(function() { tagline.classList.add('visible'); }, 1200);
                    sched(function() { replayBtn.classList.add('visible'); stepping = false; }, 1800);
                    break;
            }
        }

        if (nextBtn) nextBtn.addEventListener('click', function() {
            if (curStep < maxStep) enterStep(curStep + 1);
        });
        if (prevBtn) prevBtn.addEventListener('click', function() {
            if (curStep > 0) enterStep(curStep - 1);
        });
        if (replayBtn) replayBtn.addEventListener('click', function() {
            resetAllState();
            setTimeout(function() { enterStep(0); updateNav(); }, 200);
        });

        showcaseCallbacks['paths-2'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    // ============================================
    // Circuits-1 Showcase
    // ============================================

    function setupCircuits1Showcase() {
        var showcase = document.getElementById('ci1Showcase');
        if (!showcase) return;

        var prevBtn = document.getElementById('ci1Prev');
        var nextBtn = document.getElementById('ci1Next');

        var beforePhase = document.getElementById('ci1Before');
        var beforeTitle = document.getElementById('ci1BeforeTitle');
        var beforeCode = document.getElementById('ci1BeforeCode');
        var beforeNote = document.getElementById('ci1BeforeNote');

        var afterPhase = document.getElementById('ci1After');
        var afterTitle = document.getElementById('ci1AfterTitle');
        var afterCode = document.getElementById('ci1AfterCode');
        var ladder = document.getElementById('ci1Ladder');
        var bars = [];
        for (var b = 0; b < 6; b++) {
            bars.push(document.getElementById('ci1Bar' + b));
        }
        var afterNote = document.getElementById('ci1AfterNote');

        var coordPhase = document.getElementById('ci1Coord');
        var coordTitle = document.getElementById('ci1CoordTitle');
        var workers = [];
        for (var w = 0; w < 4; w++) {
            workers.push(document.getElementById('ci1W' + w));
        }
        var coordEvent = document.getElementById('ci1Event');
        var coordNote = document.getElementById('ci1CoordNote');

        var punchPhase = document.getElementById('ci1Punchline');
        var punchTitle = document.getElementById('ci1PunchTitle');
        var punchCode = document.getElementById('ci1PunchCode');
        var tagline = document.getElementById('ci1Tagline');
        var replayBtn = document.getElementById('ci1Replay');

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function tok(tokens) {
            var html = '';
            for (var i = 0; i < tokens.length; i++) {
                var t = tokens[i];
                if (typeof t === 'string') { html += esc(t); }
                else { html += '<span class="' + t.c + '">' + esc(t.v) + '</span>'; }
            }
            return html;
        }

        var beforeTokens = tok([
            {c:'kw',v:'import'}, ' time, random\n\n',
            {c:'nr',v:'max_retries'}, ' = ', {c:'nr',v:'5'}, '\n',
            {c:'nr',v:'base_delay'}, ' = ', {c:'nr',v:'1.0'}, '\n',
            {c:'nr',v:'max_delay'}, ' = ', {c:'nr',v:'30.0'}, '\n\n',
            {c:'kw',v:'for'}, ' attempt ', {c:'kw',v:'in'}, ' ', {c:'bi',v:'range'}, '(max_retries):\n',
            '    ', {c:'kw',v:'try'}, ':\n',
            '        result = ', {c:'fn',v:'call_service'}, '()\n',
            '        ', {c:'kw',v:'break'}, '\n',
            '    ', {c:'kw',v:'except'}, ' ServiceError:\n',
            '        ', {c:'kw',v:'if'}, ' attempt == max_retries - ', {c:'nr',v:'1'}, ':\n',
            '            ', {c:'kw',v:'raise'}, '\n',
            '        delay = ', {c:'bi',v:'min'}, '(base_delay * (', {c:'nr',v:'2'}, ' ** attempt), max_delay)\n',
            '        jitter = random.', {c:'fn',v:'uniform'}, '(', {c:'nr',v:'0'}, ', delay * ', {c:'nr',v:'0.1'}, ')\n',
            '        time.', {c:'fn',v:'sleep'}, '(delay + jitter)',
        ]);

        var afterTokens = tok([
            {c:'kw',v:'from'}, ' ', {c:'fn',v:'suitkaise'}, ' ', {c:'kw',v:'import'}, ' ', {c:'api-hl',v:'Circuit'}, '\n\n',
            'circuit = ', {c:'api-hl',v:'Circuit'}, '(\n',
            '    num_shorts_to_trip=', {c:'nr',v:'5'}, ',\n',
            '    sleep_time_after_trip=', {c:'nr',v:'1.0'}, ',\n',
            '    backoff_factor=', {c:'nr',v:'2.0'}, ',\n',
            '    max_sleep_time=', {c:'nr',v:'30.0'}, ',\n',
            '    jitter=', {c:'nr',v:'0.1'}, '\n',
            ')\n\n',
            {c:'kw',v:'while'}, ' ', {c:'bi',v:'True'}, ':\n',
            '    ', {c:'kw',v:'try'}, ':\n',
            '        result = ', {c:'fn',v:'call_service'}, '()\n',
            '        ', {c:'kw',v:'break'}, '\n',
            '    ', {c:'kw',v:'except'}, ' ServiceError:\n',
            '        circuit.', {c:'api-hl',v:'short'}, '()  ', {c:'cm',v:'# handles everything'},
        ]);

        var punchTokens = tok([
            {c:'kw',v:'from'}, ' ', {c:'fn',v:'suitkaise'}, ' ', {c:'kw',v:'import'}, ' ', {c:'api-hl',v:'Circuit'}, ', ', {c:'api-hl',v:'BreakingCircuit'}, '\n\n',
            {c:'cm',v:'# auto-reset: backoff + retry'}, '\n',
            'circuit = ', {c:'api-hl',v:'Circuit'}, '(num_shorts_to_trip=', {c:'nr',v:'5'}, ', ...)\n',
            'circuit.', {c:'api-hl',v:'short'}, '()   ', {c:'cm',v:'# count failures, auto-sleep'}, '\n',
            'circuit.', {c:'api-hl',v:'trip'}, '()    ', {c:'cm',v:'# skip counter, trip now'}, '\n\n',
            {c:'cm',v:'# manual-reset: coordinated shutdown'}, '\n',
            'breaker = ', {c:'api-hl',v:'BreakingCircuit'}, '(num_shorts_to_trip=', {c:'nr',v:'1'}, ')\n',
            'breaker.', {c:'api-hl',v:'broken'}, '     ', {c:'cm',v:'# all workers check this'},
        ]);

        var allPhases = [beforePhase, afterPhase, coordPhase, punchPhase];
        var curStep = -1;
        var stepping = false;
        var maxStep = 3;

        function hideAllPhases() {
            allPhases.forEach(function(p) { if (p) p.classList.remove('active'); });
        }

        function resetAllState() {
            cleanupCi1();
            hideAllPhases();

            [beforeTitle, beforeCode, beforeNote, afterTitle, afterCode,
             ladder, afterNote, coordTitle, coordEvent, coordNote,
             punchTitle, punchCode, tagline].forEach(function(el) {
                if (el) el.classList.remove('visible');
            });

            bars.forEach(function(bar) { if (bar) bar.classList.remove('visible'); });

            workers.forEach(function(wk) {
                if (wk) {
                    wk.classList.remove('visible', 'running', 'error', 'stopped');
                    var status = wk.querySelector('.ci1-worker-status');
                    if (status) {
                        status.textContent = 'running';
                        status.className = 'ci1-worker-status ci1-status-running';
                    }
                }
            });

            if (replayBtn) replayBtn.classList.remove('visible');

            curStep = -1;
            stepping = false;
        }

        function sched(fn, delay) {
            ci1Timers.push(setTimeout(fn, delay));
        }

        function updateNav() {
            if (prevBtn) prevBtn.disabled = (curStep <= 0);
            if (nextBtn) nextBtn.disabled = (curStep >= maxStep);
        }

        function enterStep(step) {
            if (stepping) return;
            stepping = true;
            cleanupCi1();
            hideAllPhases();
            curStep = step;
            updateNav();

            var d = 0;

            switch (step) {
                case 0:
                    beforePhase.classList.add('active');
                    beforeCode.innerHTML = beforeTokens;
                    sched(function() { beforeTitle.classList.add('visible'); }, 100);
                    sched(function() { beforeCode.classList.add('visible'); }, d += 500);
                    sched(function() { beforeNote.classList.add('visible'); stepping = false; }, d += 800);
                    break;

                case 1:
                    afterPhase.classList.add('active');
                    afterCode.innerHTML = afterTokens;
                    sched(function() { afterTitle.classList.add('visible'); }, 100);
                    sched(function() { afterCode.classList.add('visible'); }, d += 500);
                    sched(function() { ladder.classList.add('visible'); }, d += 600);
                    for (var i = 0; i < bars.length; i++) {
                        (function(idx) {
                            sched(function() { bars[idx].classList.add('visible'); }, d += 120);
                        })(i);
                    }
                    sched(function() { afterNote.classList.add('visible'); stepping = false; }, d += 400);
                    break;

                case 2:
                    coordPhase.classList.add('active');
                    sched(function() { coordTitle.classList.add('visible'); }, 100);
                    d = 300;
                    for (var j = 0; j < workers.length; j++) {
                        (function(idx) {
                            sched(function() {
                                workers[idx].classList.add('visible');
                                sched(function() { workers[idx].classList.add('running'); }, 150);
                            }, d += 200);
                        })(j);
                    }

                    sched(function() {
                        // Worker 3 (index 2) hits error
                        var errWorker = workers[2];
                        errWorker.classList.remove('running');
                        errWorker.classList.add('error');
                        var errStatus = errWorker.querySelector('.ci1-worker-status');
                        if (errStatus) {
                            errStatus.textContent = 'FATAL ERROR';
                        }
                    }, d += 1400);

                    sched(function() { coordEvent.classList.add('visible'); }, d += 600);

                    // Cascade: other workers stop one by one
                    var stopOrder = [1, 0, 3]; // workers 2,1,4 stop after worker 3
                    for (var k = 0; k < stopOrder.length; k++) {
                        (function(idx) {
                            sched(function() {
                                var wk = workers[idx];
                                wk.classList.remove('running');
                                wk.classList.add('stopped');
                                var st = wk.querySelector('.ci1-worker-status');
                                if (st) st.textContent = '.broken → stop';
                            }, d += 350);
                        })(stopOrder[k]);
                    }

                    sched(function() { coordNote.classList.add('visible'); stepping = false; }, d += 600);
                    break;

                case 3:
                    punchPhase.classList.add('active');
                    punchCode.innerHTML = punchTokens;
                    sched(function() { punchTitle.classList.add('visible'); }, 100);
                    sched(function() { punchCode.classList.add('visible'); }, 600);
                    sched(function() { tagline.classList.add('visible'); }, 1200);
                    sched(function() { replayBtn.classList.add('visible'); stepping = false; }, 1800);
                    break;
            }
        }

        if (nextBtn) nextBtn.addEventListener('click', function() {
            if (curStep < maxStep) enterStep(curStep + 1);
        });
        if (prevBtn) prevBtn.addEventListener('click', function() {
            if (curStep > 0) enterStep(curStep - 1);
        });
        if (replayBtn) replayBtn.addEventListener('click', function() {
            resetAllState();
            setTimeout(function() { enterStep(0); updateNav(); }, 200);
        });

        showcaseCallbacks['circuits-1'] = {
            start: function() { resetAllState(); setTimeout(function() { enterStep(0); updateNav(); }, 200); },
            stop: function() { resetAllState(); }
        };
    }

    function pulseQuickStart() {
        if (sessionStorage.getItem('qs_pulsed')) return;
        const btn = document.getElementById('navQuickStart');
        if (!btn) return;
        sessionStorage.setItem('qs_pulsed', '1');
        btn.classList.add('pulse');
        btn.addEventListener('animationend', () => btn.classList.remove('pulse'), { once: true });
    }

    async function loadShowcases() {
        const slides = document.querySelectorAll('.carousel-slide[data-showcase]');
        const promises = Array.from(slides).map(async (slide) => {
            const name = slide.dataset.showcase;
            const contentDiv = slide.querySelector('.slide-content');
            if (!name || !contentDiv) return;
            try {
                const cb = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
                const resp = await fetch(`pages/showcases/${name}.html?cb=${cb}`, { cache: 'no-store' });
                if (resp.ok) {
                    contentDiv.innerHTML = await resp.text();
                    contentDiv.querySelectorAll('img[src*="__assets__/"]').forEach((img) => {
                        const fileName = (img.getAttribute('src') || '').split('/').pop();
                        if (fileName) img.src = assetPath(fileName);
                    });
                }
            } catch (e) {
                console.warn(`Failed to load showcase ${name}:`, e);
            }
        });
        await Promise.all(promises);
    }

    function setupShowcaseCarousel() {
        const track = document.querySelector('.carousel-track');
        if (!track) return;

        const slides = Array.from(track.querySelectorAll('.carousel-slide'));
        const prevBtn = document.querySelector('.carousel-prev');
        const nextBtn = document.querySelector('.carousel-next');
        const tabsContainer = document.querySelector('.carousel-tabs');
        if (!slides.length) return;

        let current = -1;

        tabsContainer.innerHTML = '';
        slides.forEach((slide, i) => {
            const tab = document.createElement('button');
            tab.className = 'carousel-tab' + (i === 0 ? ' active' : '');
            tab.textContent = slide.dataset.label || slide.dataset.showcase || `Slide ${i + 1}`;
            tab.addEventListener('click', () => goTo(i));
            tabsContainer.appendChild(tab);
        });

        function goTo(index) {
            var prev = current;
            current = Math.max(0, Math.min(index, slides.length - 1));
            track.style.transform = `translateX(-${current * 100}%)`;
            prevBtn.disabled = current === 0;
            nextBtn.disabled = current === slides.length - 1;
            tabsContainer.querySelectorAll('.carousel-tab').forEach((t, i) => {
                t.classList.toggle('active', i === current);
            });
            sessionStorage.setItem('showcase_slide', String(current));

            // Stop previous showcase, start current one
            if (prev !== current || prev === undefined) {
                var prevName = slides[prev] && slides[prev].dataset.showcase;
                var curName = slides[current] && slides[current].dataset.showcase;
                if (prevName && showcaseCallbacks[prevName]) {
                    showcaseCallbacks[prevName].stop();
                }
                if (curName && showcaseCallbacks[curName]) {
                    showcaseCallbacks[curName].start();
                }
            }
        }

        prevBtn.addEventListener('click', () => goTo(current - 1));
        nextBtn.addEventListener('click', () => goTo(current + 1));

        var saved = parseInt(sessionStorage.getItem('showcase_slide'), 10);
        goTo(!isNaN(saved) && saved >= 0 && saved < slides.length ? saved : 0);
    }

    function setupFadeInAnimations() {
        const fadeElements = document.querySelectorAll('.fade-in');
        
        if (fadeElements.length === 0) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.15,
            rootMargin: '0px 0px -40px 0px'
        });
        
        fadeElements.forEach(el => observer.observe(el));
    }
    
    // Run on initial load
    setupShowcaseCarousel();
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
    
    const closedImage = assetPath('briefcase-laptop-closed.png');
    const openImage = assetPath('briefcase-laptop-fully-open.png');

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
