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
    const loadingImg = document.getElementById('loadingImg');
    
    const loadingImages = [
        { src: assetPath('briefcase-laptop-closed.png'), class: '' },
        { src: assetPath('briefcase-laptop-half-open.png'), class: 'half-open' },
        { src: assetPath('briefcase-laptop-fully-open.png'), class: 'fully-open' }
    ];
    
    let loadingFrame = 0;
    let loadingInterval = null;
    let loadingDelayTimeout = null;
    let loadingComplete = false;
    
    function hideLoadingScreen() {
        loadingScreen.style.transition = '';
        loadingScreen.classList.add('hidden');
    }
    
    function stopLoadingAnimation() {
        loadingComplete = true;
        
        if (!loadingInterval && !loadingDelayTimeout) {
            hideLoadingScreen();
            return;
        }
    }
    
    function startLoadingAnimation() {
        loadingFrame = 0;
        loadingComplete = false;
        loadingImg.src = loadingImages[0].src;
        loadingImg.className = 'loading-img';
        
        loadingScreen.style.transition = 'none';
        loadingScreen.classList.remove('hidden');
        
        if (loadingInterval) {
            clearInterval(loadingInterval);
            loadingInterval = null;
        }
        if (loadingDelayTimeout) {
            clearTimeout(loadingDelayTimeout);
            loadingDelayTimeout = null;
        }
        
        // Hold on the closed briefcase before cycling, matching the natural
        // pause the user sees on a full page refresh (where the static HTML
        // image is visible while resources load).  If content arrives during
        // this window we skip the cycling animation entirely.
        loadingDelayTimeout = setTimeout(() => {
            loadingDelayTimeout = null;
            
            if (loadingComplete) {
                hideLoadingScreen();
                return;
            }
            
            loadingInterval = setInterval(() => {
                loadingFrame = (loadingFrame + 1) % loadingImages.length;
                const frame = loadingImages[loadingFrame];
                loadingImg.src = frame.src;
                loadingImg.className = 'loading-img ' + frame.class;
                
                if (loadingComplete && loadingFrame === 0) {
                    clearInterval(loadingInterval);
                    loadingInterval = null;
                    hideLoadingScreen();
                }
            }, 250);
        }, 400);
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
    const SKAPI_PLACEHOLDER_PATTERN = /__SKAPI_TOKEN_(\d+)__/g;
    const skapiManualTokenMap = new Map();
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
        'elapsed', 'timethis', 'clear_global_timers', 'autopath',
        'get_project_root', 'set_custom_root', 'get_custom_root', 'clear_custom_root',
        'get_caller_path', 'get_current_dir', 'get_cwd', 'get_module_path', 'get_id',
        'get_project_paths', 'get_project_structure', 'get_formatted_project_tree',
        'is_valid_filename', 'streamline_path', 'streamline_path_quick',
        'serialize', 'serialize_ir', 'deserialize_ir', 'deserialize', 'reconnect_all',
        'ir_to_jsonable', 'ir_to_json', 'to_jsonable', 'to_json',
        'autoreconnect', 'sk', 'blocking',
        // NOTE:
        // Keep auto-tagging conservative. Generic member/property names (result, run,
        // error, times, etc.) are intentionally excluded here and handled by the
        // context-aware highlighter below to avoid false positives in local variables.
        'asynced', 'retry', 'timeout', 'background', 'rate_limit',
        'has_blocking_calls', 'blocking_calls',
        // Skprocess lifecycle dunders
        '__prerun__', '__run__', '__postrun__', '__onfinish__', '__result__', '__error__',
    ]));

    function autoTagKnownAPIInCode() {
        const scope = document.querySelector('.module-page, .about-page, .why-page');
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
            if (isWithoutComparisonContext(codeEl)) return;

            const walker = document.createTreeWalker(codeEl, NodeFilter.SHOW_TEXT, null, false);
            const textNodes = [];
            let node;
            while ((node = walker.nextNode())) {
                const parent = node.parentElement;
                if (!parent) continue;
                if (parent.closest('suitkaise-api')) continue;
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
                    if (match.index > lastIndex) {
                        frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
                    }
                    const tag = document.createElement('suitkaise-api');
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
            if (tag.closest('pre code')) {
                const placeholder = `__SKAPI_TOKEN_${tokenIndex++}__`;
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
        const modulePage = document.querySelector('.module-page, .about-page, .why-page');
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
        const modulePage = document.querySelector('.module-page, .about-page, .why-page');
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
        const modulePage = document.querySelector('.module-page, .about-page, .why-page');
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
            'SerializationError', 'DeserializationError',
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
            // paths / skpath-ish usage
            'id', 'root', 'parent',
        ]);
        
        // Overrides: properties that should highlight word.property.chain patterns
        // These only activate if their associated decorator is found in the code block
        const overrideConfig = {
            'timer': '@timing.timethis'  // timer property only highlights if @timing.timethis decorator exists
        };
        
        // Find all code elements (inline + block). Inline code needs API highlighting too.
        const codeBlocks = document.querySelectorAll('.module-page code, .about-page code, .why-page code');
        
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
            const pageSection = codeBlock.closest('.module-page, .about-page, .why-page');
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
            // Roots inferred from member-chain usage (no import/assignment context)
            // should only be highlighted when actually connected to a chain.
            const inferredApiRoots = new Set();
            
            // Get the text content to analyze for variable assignments
            const textContent = codeBlock.textContent;
            
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
                'asynced', 'background', 'retry', 'timethis',
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
            let chainMatch;
            while ((chainMatch = memberChainPattern.exec(textContent)) !== null) {
                const root = chainMatch[1];
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
                }
            }
            
            const knownClassesPattern = [...apiClasses, ...apiDerivedClasses].join('|');
            
            // Find variable assignments like: varname = timing.Sktimer()
            const assignmentPatterns = [
                new RegExp(`(\\w+)\\s*=\\s*(?:${modulesPattern})\\.\\w+`, 'g'),
                new RegExp(`(\\w+)\\s*:\\s*[\\w\\[\\],\\s|]+\\s*=\\s*(?:${modulesPattern})\\.\\w+`, 'g'),
                new RegExp(`(\\w+)\\s*=\\s*(?:${knownClassesPattern})\\s*\\(`, 'g'),
                new RegExp(`(\\w+)\\s*:\\s*[\\w\\[\\],\\s|]+\\s*=\\s*(?:${knownClassesPattern})\\s*\\(`, 'g'),
                new RegExp(`(\\w+)\\s*=\\s*(?:${methodsPattern})\\s*\\(`, 'g'),
                new RegExp(`with\\s+(?:${modulesPattern}|\\w+)\\.\\w+[^:]*\\s+as\\s+(\\w+)`, 'g'),
                new RegExp(`with\\s+(?:${knownClassesPattern}|${methodsPattern})[^:]*\\s+as\\s+(\\w+)`, 'g'),
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
                const hasManualPlaceholder = node.textContent && node.textContent.includes('__SKAPI_TOKEN_');
                if (((!isComment && node.textContent.trim()) || hasManualPlaceholder)) {
                    nodesToProcess.push(node);
                }
            }
            
            nodesToProcess.forEach(textNode => {
                const text = textNode.textContent;

                // Manual placeholders (from <suitkaise-api> in code blocks):
                // convert "__SKAPI_TOKEN_n__" back into forced api-highlight spans.
                // If inside a comment span (from Prism), restore as plain text instead.
                if (text && text.includes('__SKAPI_TOKEN_')) {
                    let inComment = false;
                    let ancestor = textNode.parentElement;
                    while (ancestor && ancestor !== codeBlock) {
                        if (ancestor.classList && (ancestor.classList.contains('comment') || ancestor.classList.contains('string'))) {
                            inComment = true;
                            break;
                        }
                        ancestor = ancestor.parentElement;
                    }
                    SKAPI_PLACEHOLDER_PATTERN.lastIndex = 0;
                    if (SKAPI_PLACEHOLDER_PATTERN.test(text)) {
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
                            if (inComment) {
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
                            return;
                        }
                    }
                }
                if (manualOnly) return;
                
                // Build regex pattern for all API identifiers
                const allIdentifiers = [
                    ...apiModules,
                    ...apiClasses, 
                    ...apiDerivedClasses,
                    ...apiMethods,
                    ...apiVariables,
                    ...activeOverrides, // Add active override properties (like 'timer') as identifiers
                    ...manualApiExtra,  // Manual forced API tokens for this scope
                ].filter(id => !manualApiIgnore.has(id));
                // Always-on chain roots that should match after any identifier.
                // Example: self.process_config.runs
                const alwaysChainRoots = [
                    'process_config',
                    ...manualChainRoots
                ].filter(id => !manualApiIgnore.has(id));
                
                // Check if this text contains any API identifiers
                let hasMatch = false;
                for (const id of allIdentifiers) {
                    if (text.includes(id)) {
                        hasMatch = true;
                        break;
                    }
                }
                // Check for inferred API roots only when used as chains (e.g., pool.star)
                if (!hasMatch && apiVariables.size > 0) {
                    for (const variable of apiVariables) {
                        if (text.includes(variable + '.')) {
                            hasMatch = true;
                            break;
                        }
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
                // Ensure always-on chain roots can trigger matching.
                if (!hasMatch) {
                    for (const root of alwaysChainRoots) {
                        if (text.includes(`.${root}`) || text.startsWith(`${root}.`) || text.includes(` ${root}.`)) {
                            hasMatch = true;
                            break;
                        }
                    }
                }
                
                if (!hasMatch) return;
                
                // Create pattern to match identifiers
                const identifierPattern = allIdentifiers
                    .sort((a, b) => b.length - a.length)
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                
                // Only allow chain segments that we know are part of Suitkaise API.
                // This guards against over-highlighting arbitrary properties/methods.
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
                
                // Build overrides pattern for active overrides only
                const overridesPattern = [...activeOverrides]
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                
                const alwaysChainRootsPattern = alwaysChainRoots
                    .map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
                    .join('|');
                
                // Match patterns:
                // 1. Decorators: @identifier.method()
                // 2. Module.something chains: timing.Sktimer(), paths.get_project_root()
                // 3. Standalone classes/functions: Skpath(), timethis()
                // 4. Variables with chains: t.mean, timer.stdev, circ.flowing
                // 5. Override patterns: word.timer.chain... / word.process_config.chain...
                let regexPattern = `(@(?:${identifierPattern})(?:\\.(?:${chainSegmentPattern}))*(?:\\(\\))?)|` +
                    `\\b(${identifierPattern})\\b(?:\\.(?:${chainSegmentPattern}))*(\\(\\))?`;
                if (alwaysChainRootsPattern) {
                    regexPattern += `|(\\b\\w+)\\.(${alwaysChainRootsPattern})(?:\\.(?:${chainSegmentPattern}))*(\\(\\))?`;
                }
                
                // Inferred variables (like pool, timer, breaker) only highlight when
                // connected to known API chain segments.
                if (variablePattern) {
                    regexPattern += `|\\b(${variablePattern})\\b(?:\\.(?:${chainSegmentPattern}))+((?:\\(\\))?)`;
                }
                
                // Add override pattern only if there are active overrides
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
                
                // Case-sensitive matching prevents lowercase `sk` from
                // consuming the `Sk` prefix in class names (e.g. Skprocess).
                const regex = new RegExp(regexPattern, 'g');
                
                const parts = [];
                let lastIndex = 0;
                let match;
                
                while ((match = regex.exec(text)) !== null) {
                    const matchedText = match[0];
                    const matchStart = match.index;
                    const matchEnd = matchStart + matchedText.length;
                    
                    // Skip keyword-argument names inside calls:
                    // e.g. connect(host=..., database=...) -> do not highlight host/database.
                    // Heuristic: token is immediately followed by "=" and appears after
                    // "(" or "," (ignoring whitespace) in the same expression.
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
        });
    }

    function tagInlineCodeVariants() {
        const codeEls = document.querySelectorAll('.module-page code, .about-page code, .why-page code');
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

    // ============================================
    // Page Content Storage
    // Core pages are inline (instant)
    // Module pages are fetched at startup
    // Heavy pages (videos) are lazy-loaded on demand
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
        'about',
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
    
    // Module names for scroll position memory
    const moduleNames = ['sk', 'paths', 'timing', 'circuits', 'cucumber', 'processing'];
    
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
            setupFadeInAnimations();
        }

        // If summary title already labels the dropdown, remove duplicated first heading.
        normalizeDropdownHeadingDupes();
        
        // Deterministically tag known API tokens across the current page.
        autoTagKnownAPIInCode();
        // Convert manual <suitkaise-api> tags before Prism tokenization.
        preprocessManualAPITags();

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
                const contentRoot = details.querySelector(':scope > .dropdown-content') || details;
                if (contentRoot !== details) {
                    contentRoot.style.opacity = opacity;
                }
                // Set opacity only on direct children to avoid compounding on
                // nested elements like table > tr > td (0.3^3 ≈ invisible).
                // CSS opacity visually propagates to descendants automatically.
                Array.from(contentRoot.children).forEach(child => {
                    if (child !== summary) {
                        child.style.opacity = opacity;
                    }
                });
                Array.from(details.children).forEach(child => {
                    if (child !== summary && child !== contentRoot) {
                        child.style.opacity = opacity;
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
