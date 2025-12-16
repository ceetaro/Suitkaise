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
    // Page Content Storage
    // Pre-loaded pages are stored here (instant navigation)
    // Lazy-loaded pages will be fetched when requested
    // ============================================
    
    // Pages that are pre-loaded (lightweight, instant)
    const preloadedPages = {
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
        `,
        
        // ============================================
        // Processing Module Pages
        // ============================================
        'processing': `
            <div class="module-bar" data-module="processing">
                <span class="module-bar-title">suitkaise.processing</span>
                <nav class="module-bar-nav">
                    <a href="#processing" class="module-bar-link active" data-page="processing">how to use</a>
                    <a href="#processing-how-it-works" class="module-bar-link" data-page="processing-how-it-works">how it works</a>
                    <a href="#processing-videos" class="module-bar-link" data-page="processing-videos">videos</a>
                    <a href="#processing-tests" class="module-bar-link" data-page="processing-tests">tests</a>
                    <a href="#processing-examples" class="module-bar-link" data-page="processing-examples">examples</a>
                    <a href="#processing-why" class="module-bar-link" data-page="processing-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how to use</h1>
                <p>Processing module - how to use content coming soon...</p>
            </section>
        `,
        'processing-how-it-works': `
            <div class="module-bar" data-module="processing">
                <span class="module-bar-title">suitkaise.processing</span>
                <nav class="module-bar-nav">
                    <a href="#processing" class="module-bar-link" data-page="processing">how to use</a>
                    <a href="#processing-how-it-works" class="module-bar-link active" data-page="processing-how-it-works">how it works</a>
                    <a href="#processing-videos" class="module-bar-link" data-page="processing-videos">videos</a>
                    <a href="#processing-tests" class="module-bar-link" data-page="processing-tests">tests</a>
                    <a href="#processing-examples" class="module-bar-link" data-page="processing-examples">examples</a>
                    <a href="#processing-why" class="module-bar-link" data-page="processing-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how it works</h1>
                <p>Processing module - how it works content coming soon...</p>
            </section>
        `,
        // processing-videos and processing-tests are lazy-loaded
        'processing-examples': `
            <div class="module-bar" data-module="processing">
                <span class="module-bar-title">suitkaise.processing</span>
                <nav class="module-bar-nav">
                    <a href="#processing" class="module-bar-link" data-page="processing">how to use</a>
                    <a href="#processing-how-it-works" class="module-bar-link" data-page="processing-how-it-works">how it works</a>
                    <a href="#processing-videos" class="module-bar-link" data-page="processing-videos">videos</a>
                    <a href="#processing-tests" class="module-bar-link" data-page="processing-tests">tests</a>
                    <a href="#processing-examples" class="module-bar-link active" data-page="processing-examples">examples</a>
                    <a href="#processing-why" class="module-bar-link" data-page="processing-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>examples</h1>
                <p>Processing module - examples content coming soon...</p>
            </section>
        `,
        'processing-why': `
            <div class="module-bar" data-module="processing">
                <span class="module-bar-title">suitkaise.processing</span>
                <nav class="module-bar-nav">
                    <a href="#processing" class="module-bar-link" data-page="processing">how to use</a>
                    <a href="#processing-how-it-works" class="module-bar-link" data-page="processing-how-it-works">how it works</a>
                    <a href="#processing-videos" class="module-bar-link" data-page="processing-videos">videos</a>
                    <a href="#processing-tests" class="module-bar-link" data-page="processing-tests">tests</a>
                    <a href="#processing-examples" class="module-bar-link" data-page="processing-examples">examples</a>
                    <a href="#processing-why" class="module-bar-link active" data-page="processing-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>why</h1>
                <p>Processing module - why content coming soon...</p>
            </section>
        `,
        
        // ============================================
        // Cerial Module Pages
        // ============================================
        'cerial': `
            <div class="module-bar" data-module="cerial">
                <span class="module-bar-title">suitkaise.cerial</span>
                <nav class="module-bar-nav">
                    <a href="#cerial" class="module-bar-link active" data-page="cerial">how to use</a>
                    <a href="#cerial-how-it-works" class="module-bar-link" data-page="cerial-how-it-works">how it works</a>
                    <a href="#cerial-videos" class="module-bar-link" data-page="cerial-videos">videos</a>
                    <a href="#cerial-tests" class="module-bar-link" data-page="cerial-tests">tests</a>
                    <a href="#cerial-examples" class="module-bar-link" data-page="cerial-examples">examples</a>
                    <a href="#cerial-why" class="module-bar-link" data-page="cerial-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how to use</h1>
                <p>Cerial module - how to use content coming soon...</p>
            </section>
        `,
        'cerial-how-it-works': `
            <div class="module-bar" data-module="cerial">
                <span class="module-bar-title">suitkaise.cerial</span>
                <nav class="module-bar-nav">
                    <a href="#cerial" class="module-bar-link" data-page="cerial">how to use</a>
                    <a href="#cerial-how-it-works" class="module-bar-link active" data-page="cerial-how-it-works">how it works</a>
                    <a href="#cerial-videos" class="module-bar-link" data-page="cerial-videos">videos</a>
                    <a href="#cerial-tests" class="module-bar-link" data-page="cerial-tests">tests</a>
                    <a href="#cerial-examples" class="module-bar-link" data-page="cerial-examples">examples</a>
                    <a href="#cerial-why" class="module-bar-link" data-page="cerial-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how it works</h1>
                <p>Cerial module - how it works content coming soon...</p>
            </section>
        `,
        // cerial-videos and cerial-tests are lazy-loaded
        'cerial-examples': `
            <div class="module-bar" data-module="cerial">
                <span class="module-bar-title">suitkaise.cerial</span>
                <nav class="module-bar-nav">
                    <a href="#cerial" class="module-bar-link" data-page="cerial">how to use</a>
                    <a href="#cerial-how-it-works" class="module-bar-link" data-page="cerial-how-it-works">how it works</a>
                    <a href="#cerial-videos" class="module-bar-link" data-page="cerial-videos">videos</a>
                    <a href="#cerial-tests" class="module-bar-link" data-page="cerial-tests">tests</a>
                    <a href="#cerial-examples" class="module-bar-link active" data-page="cerial-examples">examples</a>
                    <a href="#cerial-why" class="module-bar-link" data-page="cerial-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>examples</h1>
                <p>Cerial module - examples content coming soon...</p>
            </section>
        `,
        'cerial-why': `
            <div class="module-bar" data-module="cerial">
                <span class="module-bar-title">suitkaise.cerial</span>
                <nav class="module-bar-nav">
                    <a href="#cerial" class="module-bar-link" data-page="cerial">how to use</a>
                    <a href="#cerial-how-it-works" class="module-bar-link" data-page="cerial-how-it-works">how it works</a>
                    <a href="#cerial-videos" class="module-bar-link" data-page="cerial-videos">videos</a>
                    <a href="#cerial-tests" class="module-bar-link" data-page="cerial-tests">tests</a>
                    <a href="#cerial-examples" class="module-bar-link" data-page="cerial-examples">examples</a>
                    <a href="#cerial-why" class="module-bar-link active" data-page="cerial-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>why</h1>
                <p>Cerial module - why content coming soon...</p>
            </section>
        `,
        
        // ============================================
        // Sktime Module Pages
        // ============================================
        'sktime': `
            <div class="module-bar" data-module="sktime">
                <span class="module-bar-title">suitkaise.sktime</span>
                <nav class="module-bar-nav">
                    <a href="#sktime" class="module-bar-link active" data-page="sktime">how to use</a>
                    <a href="#sktime-how-it-works" class="module-bar-link" data-page="sktime-how-it-works">how it works</a>
                    <a href="#sktime-videos" class="module-bar-link" data-page="sktime-videos">videos</a>
                    <a href="#sktime-tests" class="module-bar-link" data-page="sktime-tests">tests</a>
                    <a href="#sktime-examples" class="module-bar-link" data-page="sktime-examples">examples</a>
                    <a href="#sktime-why" class="module-bar-link" data-page="sktime-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how to use</h1>
                <p>Sktime module - how to use content coming soon...</p>
            </section>
        `,
        'sktime-how-it-works': `
            <div class="module-bar" data-module="sktime">
                <span class="module-bar-title">suitkaise.sktime</span>
                <nav class="module-bar-nav">
                    <a href="#sktime" class="module-bar-link" data-page="sktime">how to use</a>
                    <a href="#sktime-how-it-works" class="module-bar-link active" data-page="sktime-how-it-works">how it works</a>
                    <a href="#sktime-videos" class="module-bar-link" data-page="sktime-videos">videos</a>
                    <a href="#sktime-tests" class="module-bar-link" data-page="sktime-tests">tests</a>
                    <a href="#sktime-examples" class="module-bar-link" data-page="sktime-examples">examples</a>
                    <a href="#sktime-why" class="module-bar-link" data-page="sktime-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how it works</h1>
                <p>Sktime module - how it works content coming soon...</p>
            </section>
        `,
        // sktime-videos and sktime-tests are lazy-loaded
        'sktime-examples': `
            <div class="module-bar" data-module="sktime">
                <span class="module-bar-title">suitkaise.sktime</span>
                <nav class="module-bar-nav">
                    <a href="#sktime" class="module-bar-link" data-page="sktime">how to use</a>
                    <a href="#sktime-how-it-works" class="module-bar-link" data-page="sktime-how-it-works">how it works</a>
                    <a href="#sktime-videos" class="module-bar-link" data-page="sktime-videos">videos</a>
                    <a href="#sktime-tests" class="module-bar-link" data-page="sktime-tests">tests</a>
                    <a href="#sktime-examples" class="module-bar-link active" data-page="sktime-examples">examples</a>
                    <a href="#sktime-why" class="module-bar-link" data-page="sktime-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>examples</h1>
                <p>Sktime module - examples content coming soon...</p>
            </section>
        `,
        'sktime-why': `
            <div class="module-bar" data-module="sktime">
                <span class="module-bar-title">suitkaise.sktime</span>
                <nav class="module-bar-nav">
                    <a href="#sktime" class="module-bar-link" data-page="sktime">how to use</a>
                    <a href="#sktime-how-it-works" class="module-bar-link" data-page="sktime-how-it-works">how it works</a>
                    <a href="#sktime-videos" class="module-bar-link" data-page="sktime-videos">videos</a>
                    <a href="#sktime-tests" class="module-bar-link" data-page="sktime-tests">tests</a>
                    <a href="#sktime-examples" class="module-bar-link" data-page="sktime-examples">examples</a>
                    <a href="#sktime-why" class="module-bar-link active" data-page="sktime-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>why</h1>
                <p>Sktime module - why content coming soon...</p>
            </section>
        `,
        
        // ============================================
        // Skpath Module Pages
        // ============================================
        'skpath': `
            <div class="module-bar" data-module="skpath">
                <span class="module-bar-title">suitkaise.skpath</span>
                <nav class="module-bar-nav">
                    <a href="#skpath" class="module-bar-link active" data-page="skpath">how to use</a>
                    <a href="#skpath-how-it-works" class="module-bar-link" data-page="skpath-how-it-works">how it works</a>
                    <a href="#skpath-videos" class="module-bar-link" data-page="skpath-videos">videos</a>
                    <a href="#skpath-tests" class="module-bar-link" data-page="skpath-tests">tests</a>
                    <a href="#skpath-examples" class="module-bar-link" data-page="skpath-examples">examples</a>
                    <a href="#skpath-why" class="module-bar-link" data-page="skpath-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how to use</h1>
                <p>Skpath module - how to use content coming soon...</p>
            </section>
        `,
        'skpath-how-it-works': `
            <div class="module-bar" data-module="skpath">
                <span class="module-bar-title">suitkaise.skpath</span>
                <nav class="module-bar-nav">
                    <a href="#skpath" class="module-bar-link" data-page="skpath">how to use</a>
                    <a href="#skpath-how-it-works" class="module-bar-link active" data-page="skpath-how-it-works">how it works</a>
                    <a href="#skpath-videos" class="module-bar-link" data-page="skpath-videos">videos</a>
                    <a href="#skpath-tests" class="module-bar-link" data-page="skpath-tests">tests</a>
                    <a href="#skpath-examples" class="module-bar-link" data-page="skpath-examples">examples</a>
                    <a href="#skpath-why" class="module-bar-link" data-page="skpath-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how it works</h1>
                <p>Skpath module - how it works content coming soon...</p>
            </section>
        `,
        // skpath-videos and skpath-tests are lazy-loaded
        'skpath-examples': `
            <div class="module-bar" data-module="skpath">
                <span class="module-bar-title">suitkaise.skpath</span>
                <nav class="module-bar-nav">
                    <a href="#skpath" class="module-bar-link" data-page="skpath">how to use</a>
                    <a href="#skpath-how-it-works" class="module-bar-link" data-page="skpath-how-it-works">how it works</a>
                    <a href="#skpath-videos" class="module-bar-link" data-page="skpath-videos">videos</a>
                    <a href="#skpath-tests" class="module-bar-link" data-page="skpath-tests">tests</a>
                    <a href="#skpath-examples" class="module-bar-link active" data-page="skpath-examples">examples</a>
                    <a href="#skpath-why" class="module-bar-link" data-page="skpath-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>examples</h1>
                <p>Skpath module - examples content coming soon...</p>
            </section>
        `,
        'skpath-why': `
            <div class="module-bar" data-module="skpath">
                <span class="module-bar-title">suitkaise.skpath</span>
                <nav class="module-bar-nav">
                    <a href="#skpath" class="module-bar-link" data-page="skpath">how to use</a>
                    <a href="#skpath-how-it-works" class="module-bar-link" data-page="skpath-how-it-works">how it works</a>
                    <a href="#skpath-videos" class="module-bar-link" data-page="skpath-videos">videos</a>
                    <a href="#skpath-tests" class="module-bar-link" data-page="skpath-tests">tests</a>
                    <a href="#skpath-examples" class="module-bar-link" data-page="skpath-examples">examples</a>
                    <a href="#skpath-why" class="module-bar-link active" data-page="skpath-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>why</h1>
                <p>Skpath module - why content coming soon...</p>
            </section>
        `,
        
        // ============================================
        // Circuit Module Pages
        // ============================================
        'circuit': `
            <div class="module-bar" data-module="circuit">
                <span class="module-bar-title">suitkaise.circuit</span>
                <nav class="module-bar-nav">
                    <a href="#circuit" class="module-bar-link active" data-page="circuit">how to use</a>
                    <a href="#circuit-how-it-works" class="module-bar-link" data-page="circuit-how-it-works">how it works</a>
                    <a href="#circuit-videos" class="module-bar-link" data-page="circuit-videos">videos</a>
                    <a href="#circuit-tests" class="module-bar-link" data-page="circuit-tests">tests</a>
                    <a href="#circuit-examples" class="module-bar-link" data-page="circuit-examples">examples</a>
                    <a href="#circuit-why" class="module-bar-link" data-page="circuit-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how to use</h1>
                <p>Circuit module - how to use content coming soon...</p>
            </section>
        `,
        'circuit-how-it-works': `
            <div class="module-bar" data-module="circuit">
                <span class="module-bar-title">suitkaise.circuit</span>
                <nav class="module-bar-nav">
                    <a href="#circuit" class="module-bar-link" data-page="circuit">how to use</a>
                    <a href="#circuit-how-it-works" class="module-bar-link active" data-page="circuit-how-it-works">how it works</a>
                    <a href="#circuit-videos" class="module-bar-link" data-page="circuit-videos">videos</a>
                    <a href="#circuit-tests" class="module-bar-link" data-page="circuit-tests">tests</a>
                    <a href="#circuit-examples" class="module-bar-link" data-page="circuit-examples">examples</a>
                    <a href="#circuit-why" class="module-bar-link" data-page="circuit-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>how it works</h1>
                <p>Circuit module - how it works content coming soon...</p>
            </section>
        `,
        // circuit-videos and circuit-tests are lazy-loaded
        'circuit-examples': `
            <div class="module-bar" data-module="circuit">
                <span class="module-bar-title">suitkaise.circuit</span>
                <nav class="module-bar-nav">
                    <a href="#circuit" class="module-bar-link" data-page="circuit">how to use</a>
                    <a href="#circuit-how-it-works" class="module-bar-link" data-page="circuit-how-it-works">how it works</a>
                    <a href="#circuit-videos" class="module-bar-link" data-page="circuit-videos">videos</a>
                    <a href="#circuit-tests" class="module-bar-link" data-page="circuit-tests">tests</a>
                    <a href="#circuit-examples" class="module-bar-link active" data-page="circuit-examples">examples</a>
                    <a href="#circuit-why" class="module-bar-link" data-page="circuit-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>examples</h1>
                <p>Circuit module - examples content coming soon...</p>
            </section>
        `,
        'circuit-why': `
            <div class="module-bar" data-module="circuit">
                <span class="module-bar-title">suitkaise.circuit</span>
                <nav class="module-bar-nav">
                    <a href="#circuit" class="module-bar-link" data-page="circuit">how to use</a>
                    <a href="#circuit-how-it-works" class="module-bar-link" data-page="circuit-how-it-works">how it works</a>
                    <a href="#circuit-videos" class="module-bar-link" data-page="circuit-videos">videos</a>
                    <a href="#circuit-tests" class="module-bar-link" data-page="circuit-tests">tests</a>
                    <a href="#circuit-examples" class="module-bar-link" data-page="circuit-examples">examples</a>
                    <a href="#circuit-why" class="module-bar-link active" data-page="circuit-why">why</a>
                </nav>
            </div>
            <section class="module-page">
                <h1>why</h1>
                <p>Circuit module - why content coming soon...</p>
            </section>
        `
    };
    
    // Cache for lazy-loaded pages (once loaded, stored here for instant access)
    const loadedPages = {};
    
    // Registry of pages that need lazy loading
    // These pages will show the loading animation while content loads
    const lazyPages = {
        // Processing
        'processing-videos': async () => await loadModulePage('processing', 'videos'),
        'processing-tests': async () => await loadModulePage('processing', 'tests'),
        
        // Cerial
        'cerial-videos': async () => await loadModulePage('cerial', 'videos'),
        'cerial-tests': async () => await loadModulePage('cerial', 'tests'),
        
        // Sktime
        'sktime-videos': async () => await loadModulePage('sktime', 'videos'),
        'sktime-tests': async () => await loadModulePage('sktime', 'tests'),
        
        // Skpath
        'skpath-videos': async () => await loadModulePage('skpath', 'videos'),
        'skpath-tests': async () => await loadModulePage('skpath', 'tests'),
        
        // Circuit
        'circuit-videos': async () => await loadModulePage('circuit', 'videos'),
        'circuit-tests': async () => await loadModulePage('circuit', 'tests'),
    };
    
    // Loader function for module pages
    // Fetches HTML content from static files
    async function loadModulePage(moduleName, subPage) {
        try {
            const response = await fetch(`pages/${moduleName}-${subPage}.html`);
            if (!response.ok) {
                throw new Error(`Failed to load: ${response.status}`);
            }
            return await response.text();
        } catch (error) {
            console.error(`Error loading ${moduleName}-${subPage}:`, error);
            // Return fallback content on error
            return `
                <div class="module-bar" data-module="${moduleName}">
                    <span class="module-bar-title">suitkaise.${moduleName}</span>
                    <nav class="module-bar-nav">
                        <a href="#${moduleName}" class="module-bar-link" data-page="${moduleName}">how to use</a>
                        <a href="#${moduleName}-how-it-works" class="module-bar-link" data-page="${moduleName}-how-it-works">how it works</a>
                        <a href="#${moduleName}-videos" class="module-bar-link ${subPage === 'videos' ? 'active' : ''}" data-page="${moduleName}-videos">videos</a>
                        <a href="#${moduleName}-tests" class="module-bar-link ${subPage === 'tests' ? 'active' : ''}" data-page="${moduleName}-tests">tests</a>
                        <a href="#${moduleName}-examples" class="module-bar-link" data-page="${moduleName}-examples">examples</a>
                        <a href="#${moduleName}-why" class="module-bar-link" data-page="${moduleName}-why">why</a>
                    </nav>
                </div>
                <section class="module-page">
                    <h1>${subPage}</h1>
                    <p>Content loading failed. Please try again.</p>
                </section>
            `;
        }
    }
    
    // Check if a page is available (pre-loaded or cached)
    function isPageReady(pageName) {
        return preloadedPages[pageName] || loadedPages[pageName];
    }
    
    // Get page content (from pre-loaded, cache, or load it)
    async function getPageContent(pageName) {
        // Check pre-loaded pages first
        if (preloadedPages[pageName]) {
            return preloadedPages[pageName];
        }
        
        // Check if already lazy-loaded and cached
        if (loadedPages[pageName]) {
            return loadedPages[pageName];
        }
        
        // Need to lazy load
        if (lazyPages[pageName]) {
            const content = await lazyPages[pageName]();
            loadedPages[pageName] = content; // Cache it
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
        if (!isReady && lazyPages[pageName]) {
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
        if (hash !== currentPage && (preloadedPages[hash] || lazyPages[hash])) {
            navigateTo(hash);
        }
    });

    // Hide loading screen on initial load
    stopLoadingAnimation();
    
    // Check URL hash on initial load and navigate to that page
    (async function handleInitialHash() {
        const initialHash = window.location.hash.slice(1);
        
        if (initialHash && (preloadedPages[initialHash] || lazyPages[initialHash])) {
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
