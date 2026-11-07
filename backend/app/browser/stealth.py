"""Anti-detection scripts injected into every browser page.

Hides Playwright automation markers that websites use to detect bots:
- navigator.webdriver flag
- navigator.plugins count
- Chrome runtime object
- Permission API inconsistencies
- Canvas/WebGL fingerprint noise
"""

STEALTH_SCRIPT = """
// Hide webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => false });

// Fake plugins array (real browsers have several)
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// Set realistic languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

// Fake Chrome runtime (missing in headless)
window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };

// Fix permissions API (headless returns inconsistent results)
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) =>
    params.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : origQuery(params);

// Canvas fingerprint noise — adds tiny random pixel variations
const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    const ctx = this.getContext('2d');
    if (ctx) {
        const imageData = ctx.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < imageData.data.length; i += 100) {
            imageData.data[i] += Math.floor(Math.random() * 2);
        }
        ctx.putImageData(imageData, 0, 0);
    }
    return origToDataURL.call(this, type);
};

// WebGL vendor/renderer spoofing
const getParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {
    if (p === 37445) return 'Intel Inc.';
    if (p === 37446) return 'Intel Iris OpenGL Engine';
    return getParam.call(this, p);
};
"""
