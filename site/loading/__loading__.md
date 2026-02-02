/*

LOADING SCREEN DOCUMENTATION

The loading screen displays while heavy content is being fetched from the server.

*/

# How It Works

## 1. Page Types

There are two types of pages:

### Pre-loaded Pages (Instant)
- Bundled in the initial JavaScript
- No loading animation needed
- Examples: home, about, how-to-use, how-it-works, examples, why

### Lazy-loaded Pages (Fetch Required)
- Stored as separate HTML files in __code__/pages/
- Loading animation displays while fetching
- Examples: videos, tests (for all modules)

## 2. Loading Animation Behavior

When navigating to a lazy-loaded page:

1. User clicks a link (e.g., "videos")
2. Loading screen appears immediately
3. Blocks all clicks/input while displayed (pointer-events: all, cursor: wait)
4. Animation cycles: closed → half-open → fully-open briefcase (250ms per frame)
5. Meanwhile, JavaScript fetches the HTML content from pages/{module}-{subpage}.html
6. Once content is fetched, animation completes its current loop
7. When animation returns to frame 0 (closed briefcase), loading screen hides
8. Page content is displayed

## 3. Animation Images

same bkg color as home page.

switches through these images:

briefcase-laptop-closed.png
briefcase-laptop-half-open.png
briefcase-laptop-fully-open.png

the size of the 2 open images needs to be adjusted similar to the one on the nav bar home button.

## 4. Caching

Once a lazy-loaded page is fetched, it's cached in memory.
Subsequent visits to the same page are instant (no loading animation).

## 5. File Structure

__code__/
├── index.html
├── styles.css
├── script.js
└── pages/
    ├── processing-videos.html
    ├── processing-tests.html
    ├── cucumber-videos.html
    ├── cucumber-tests.html
    ├── sktime-videos.html
    ├── sktime-tests.html
    ├── skpath-videos.html
    ├── skpath-tests.html
    ├── circuit-videos.html
    └── circuit-tests.html

## 6. Adding New Lazy Pages

To make a page lazy-loaded:

1. Create the HTML file in __code__/pages/{module}-{subpage}.html
2. Add entry to lazyPages object in script.js:
   '{module}-{subpage}': async () => await loadModulePage('{module}', '{subpage}')
3. Remove the page from preloadedPages if it exists there

## 7. Testing

Note: Lazy loading requires a web server. Opening index.html directly (file://) won't work.

Run a local server:
- Python: python -m http.server 8000
- Node: npx serve
- VS Code: Live Server extension

Then navigate to http://localhost:8000
