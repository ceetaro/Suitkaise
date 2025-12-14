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

    function startLoadingAnimation() {
        loadingFrame = 0;
        loadingImg.src = loadingImages[0].src;
        loadingImg.className = 'loading-img';
        loadingScreen.classList.remove('hidden');
        
        loadingInterval = setInterval(() => {
            loadingFrame = (loadingFrame + 1) % loadingImages.length;
            const frame = loadingImages[loadingFrame];
            loadingImg.src = frame.src;
            loadingImg.className = 'loading-img ' + frame.class;
        }, 250); // Change image every 250ms
    }

    function stopLoadingAnimation() {
        if (loadingInterval) {
            clearInterval(loadingInterval);
            loadingInterval = null;
        }
        loadingScreen.classList.add('hidden');
    }

    // Preload loading images for smooth animation
    loadingImages.forEach(img => {
        const preload = new Image();
        preload.src = img.src;
    });

    // ============================================
    // Page Content Storage
    // Store page HTML for SPA navigation
    // ============================================
    
    const pages = {
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

    function navigateTo(pageName) {
        if (pageName === currentPage) return;
        
        // Show loading screen
        startLoadingAnimation();
        
        // Simulate network delay for effect (remove in production or adjust)
        setTimeout(() => {
            // Update content
            if (pages[pageName]) {
                pageContent.innerHTML = pages[pageName];
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
            
            // Hide loading screen
            stopLoadingAnimation();
            
            // Setup page-specific functionality
            if (pageName === 'error') {
                setupErrorPageHover();
            } else if (pageName === 'password') {
                setupPasswordPage();
            } else if (pageName === 'home') {
                setupFadeInAnimations();
            }
        }, 750); // Show loading for at least 750ms
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
        if (hash !== currentPage && pages[hash]) {
            navigateTo(hash);
        }
    });

    // Hide loading screen on initial load
    stopLoadingAnimation();
    
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
