/**
 * Universal React-Aware Form Filler
 *
 * This script fills entire forms in one execution, handling:
 * - React/Vue/Angular synthetic events
 * - Various input types (text, select, radio, checkbox)
 * - Human-like micro-delays between fields
 *
 * Usage: Execute via page.evaluate() with fieldMapping parameter
 */

async function injectFormData(fieldMapping, options = {}) {
    const {
        delayMin = 30,
        delayMax = 100,
        dispatchEvents = true
    } = options;

    /**
     * React-aware value setter that bypasses synthetic event system
     */
    const setNativeValue = (element, value) => {
        // Get value property descriptor from element and its prototype
        const elementDescriptor = Object.getOwnPropertyDescriptor(element, 'value');
        const prototypeDescriptor = Object.getOwnPropertyDescriptor(
            Object.getPrototypeOf(element), 'value'
        );

        // Use prototype setter to properly trigger React state updates
        if (elementDescriptor?.set && prototypeDescriptor?.set &&
            elementDescriptor.set !== prototypeDescriptor.set) {
            prototypeDescriptor.set.call(element, value);
        } else if (prototypeDescriptor?.set) {
            prototypeDescriptor.set.call(element, value);
        } else {
            element.value = value;
        }

        // Dispatch events that React/Vue listen for
        if (dispatchEvents) {
            element.dispatchEvent(new Event('focus', { bubbles: true }));
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            element.dispatchEvent(new Event('blur', { bubbles: true }));
        }
    };

    /**
     * Handle different input types appropriately
     */
    const fillField = async (selector, value) => {
        // Support multiple selector formats — use CSS.escape() for IDs with special chars (React :r0: etc.)
        let el = null;
        if (selector.startsWith('#')) {
            // Escape the ID portion to handle colons, brackets, etc.
            const rawId = selector.slice(1);
            el = document.getElementById(rawId) || document.querySelector('#' + CSS.escape(rawId));
        } else if (selector.startsWith('.') || selector.startsWith('[')) {
            el = document.querySelector(selector);
        } else {
            // Try by name, then by attribute ID (safe for special chars), then fuzzy
            el = document.querySelector(`[name="${selector}"]`) ||
                 document.getElementById(selector) ||
                 document.querySelector(`[aria-label*="${selector}" i]`) ||
                 document.querySelector(`[placeholder*="${selector}" i]`);
        }

        if (!el) {
            return { selector, status: 'not_found' };
        }

        const tagName = el.tagName.toLowerCase();
        const inputType = (el.type || '').toLowerCase();

        try {
            // File inputs - cannot set via JS, flag for Browser-Use
            if (inputType === 'file') {
                return { selector, status: 'file_upload_needed', element: el };
            }

            // Checkboxes
            if (inputType === 'checkbox') {
                const shouldBeChecked = value === true || value === 'true' || value === 'yes' || value === 'Yes';
                if (el.checked !== shouldBeChecked) {
                    el.click();
                }
                return { selector, status: 'filled', type: 'checkbox' };
            }

            // Radio buttons - find the one with matching value
            if (inputType === 'radio') {
                // If value matches this radio's value, click it
                if (el.value === value || value === true) {
                    if (!el.checked) el.click();
                } else {
                    // Find radio with matching value in same group
                    const name = el.name;
                    const matchingRadio = document.querySelector(`input[name="${name}"][value="${value}"]`);
                    if (matchingRadio && !matchingRadio.checked) {
                        matchingRadio.click();
                    }
                }
                return { selector, status: 'filled', type: 'radio' };
            }

            // Select dropdowns
            if (tagName === 'select') {
                // Try exact match first
                let option = Array.from(el.options).find(o =>
                    o.value === value || o.text === value
                );
                // Try partial match
                if (!option) {
                    option = Array.from(el.options).find(o =>
                        o.text.toLowerCase().includes(value.toLowerCase()) ||
                        o.value.toLowerCase().includes(value.toLowerCase())
                    );
                }
                if (option) {
                    el.value = option.value;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
                return { selector, status: option ? 'filled' : 'option_not_found', type: 'select' };
            }

            // Text inputs, textareas, email, tel, etc.
            setNativeValue(el, value);
            return { selector, status: 'filled', type: inputType || 'text' };

        } catch (err) {
            return { selector, status: 'error', error: err.message };
        }
    };

    // Process all fields
    const results = {
        filled: [],
        failed: [],
        files: [],
        timestamp: new Date().toISOString()
    };

    for (const [selector, value] of Object.entries(fieldMapping)) {
        if (value === null || value === undefined || value === '__SKIP__') {
            continue;
        }

        const result = await fillField(selector, value);

        if (result.status === 'filled') {
            results.filled.push(selector);
        } else if (result.status === 'file_upload_needed') {
            results.files.push({ selector, value });
        } else {
            results.failed.push(result);
        }

        // Human-like micro-delay between fields
        await new Promise(r => setTimeout(r, delayMin + Math.random() * (delayMax - delayMin)));
    }

    return results;
}

// Export for use
if (typeof module !== 'undefined') {
    module.exports = { injectFormData };
}
