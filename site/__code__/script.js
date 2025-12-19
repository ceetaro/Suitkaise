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

    // ============================================
    // Page Content Storage
    // Core pages are inline (instant)
    // Module pages are fetched at startup
    // Heavy pages (videos/tests) are lazy-loaded on demand
    // ============================================
    
    // Core pages that are always inline (small, essential)
    const corePages = {
        home: document.getElementById('pageContent').innerHTML,
        about: `
            <section class="page-section">
                <div class="page-header">
                    <h1>About Suitkaise</h1>
                </div>
                <div class="page-body">
                    <p>About page content coming soon...</p>
                </div>
            </section>
        `,
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
    
    async function hashPassword(password) {
        const encoder = new TextEncoder();
        const data = encoder.encode(password.toLowerCase().trim());
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    
    function setupPasswordPage() {
        const passwordInput = document.getElementById('passwordInput');
        
        if (passwordInput) {
            passwordInput.addEventListener('keydown', async (e) => {
                if (e.key === 'Enter') {
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

    async function navigateTo(pageName, force = false) {
        if (!force && pageName === currentPage) return;
        
        // Check if page content is already available
        const isReady = isPageReady(pageName);
        
        // Only show loading animation if we need to load content
        if (!isReady && (lazyPages[pageName] || modulePagesList.includes(pageName))) {
            startLoadingAnimation();
        }
        
        // Get the page content (instant if pre-loaded, async if lazy)
        const content = await getPageContent(pageName);
        
        if (content) {
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
            
            // Scroll to top
            window.scrollTo(0, 0);
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
        }
        
        // Setup module bar links if present
        setupModuleBarLinks();
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
