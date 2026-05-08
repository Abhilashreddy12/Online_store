/**
 * Sidebar Filters JavaScript
 * Handles filter interaction, mobile drawer toggle, and price range
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize filter drawer toggle on mobile
    initializeFilterDrawer();
    
    // Initialize price range slider
    initializePriceSlider();
    
    // Initialize filter change handlers
    initializeFilterHandlers();
    
    // Initialize clear filters button
    initializeClearFilters();
});

/**
 * Initialize filter drawer toggle for mobile
 */
function initializeFilterDrawer() {
    const filterToggle = document.querySelector('.filter-toggle-mobile');
    const filterDrawer = document.querySelector('.filters-drawer');
    const filterDrawerClose = document.querySelector('.filters-drawer-close');
    const filterOverlay = filterDrawer;
    
    if (!filterToggle) return;
    
    // Open drawer
    filterToggle.addEventListener('click', function() {
        filterDrawer.classList.add('open');
        document.body.style.overflow = 'hidden';
    });
    
    // Close drawer
    if (filterDrawerClose) {
        filterDrawerClose.addEventListener('click', function() {
            filterDrawer.classList.remove('open');
            document.body.style.overflow = '';
        });
    }
    
    // Close on overlay click
    filterDrawer.addEventListener('click', function(e) {
        if (e.target === filterDrawer) {
            filterDrawer.classList.remove('open');
            document.body.style.overflow = '';
        }
    });
    
    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && filterDrawer.classList.contains('open')) {
            filterDrawer.classList.remove('open');
            document.body.style.overflow = '';
        }
    });
}

/**
 * Initialize price range slider
 */
function initializePriceSlider() {
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    const priceSlider = document.getElementById('price-range-slider');
    
    if (!minPriceInput || !maxPriceInput) return;
    
    // Update price inputs on slider change
    if (priceSlider) {
        priceSlider.addEventListener('input', function() {
            minPriceInput.value = this.value;
        });
    }
    
    // Validate price inputs
    minPriceInput.addEventListener('change', function() {
        const minValue = parseFloat(this.value) || 0;
        const maxValue = parseFloat(maxPriceInput.value) || Infinity;
        
        if (minValue > maxValue) {
            this.value = maxValue;
        }
    });
    
    maxPriceInput.addEventListener('change', function() {
        const maxValue = parseFloat(this.value) || Infinity;
        const minValue = parseFloat(minPriceInput.value) || 0;
        
        if (maxValue < minValue) {
            this.value = minValue;
        }
    });
}

/**
 * Initialize filter change handlers
 */
function initializeFilterHandlers() {
    const filterCheckboxes = document.querySelectorAll('.filter-option input[type="checkbox"]');
    const filterRadios = document.querySelectorAll('.filter-option input[type="radio"]');
    
    // Handle checkbox changes
    filterCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            applyFilters();
        });
    });
    
    // Handle radio button changes
    filterRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            applyFilters();
        });
    });
}

/**
 * Apply filters and update URL
 */
function applyFilters() {
    const url = new URL(window.location);
    const searchParams = url.searchParams;
    
    // Get all filter values
    const selectedCategories = Array.from(
        document.querySelectorAll('input[name="category"]:checked')
    ).map(el => el.value);
    
    const selectedBrands = Array.from(
        document.querySelectorAll('input[name="brand"]:checked')
    ).map(el => el.value);
    
    const selectedSizes = Array.from(
        document.querySelectorAll('input[name="size"]:checked')
    ).map(el => el.value);
    
    const selectedColors = Array.from(
        document.querySelectorAll('input[name="color"]:checked')
    ).map(el => el.value);
    
    const selectedAvailability = Array.from(
        document.querySelectorAll('input[name="availability"]:checked')
    ).map(el => el.value);
    
    // Update URL parameters
    if (selectedCategories.length > 0) {
        searchParams.set('category', selectedCategories.join(','));
    } else {
        searchParams.delete('category');
    }
    
    if (selectedBrands.length > 0) {
        searchParams.set('brand', selectedBrands.join(','));
    } else {
        searchParams.delete('brand');
    }
    
    if (selectedSizes.length > 0) {
        searchParams.set('size', selectedSizes.join(','));
    } else {
        searchParams.delete('size');
    }
    
    if (selectedColors.length > 0) {
        searchParams.set('color', selectedColors.join(','));
    } else {
        searchParams.delete('color');
    }
    
    if (selectedAvailability.length > 0) {
        searchParams.set('availability', selectedAvailability.join(','));
    } else {
        searchParams.delete('availability');
    }
    
    // Update URL without page reload
    window.history.pushState({}, '', url.toString());
    
    // Reload products with AJAX (optional - implement based on your needs)
    // For now, perform actual page navigation
    window.location.href = url.toString();
}

/**
 * Clear all filters
 */
function clearAllFilters() {
    // Clear all checkboxes and radios
    document.querySelectorAll('.filter-option input[type="checkbox"]').forEach(el => {
        el.checked = false;
    });
    document.querySelectorAll('.filter-option input[type="radio"]').forEach(el => {
        el.checked = false;
    });
    
    // Reset price inputs
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    if (minPriceInput) minPriceInput.value = '';
    if (maxPriceInput) maxPriceInput.value = '';
    
    // Remove all filter parameters from URL
    const url = new URL(window.location);
    url.searchParams.delete('category');
    url.searchParams.delete('brand');
    url.searchParams.delete('size');
    url.searchParams.delete('color');
    url.searchParams.delete('availability');
    url.searchParams.delete('min_price');
    url.searchParams.delete('max_price');
    
    // Navigate to clean URL
    window.location.href = url.toString();
}

/**
 * Toggle filter group visibility
 */
function toggleFilterGroup(element) {
    const group = element.closest('.filter-group');
    const options = group.querySelector('.filter-options');
    
    if (options) {
        options.style.display = options.style.display === 'none' ? 'flex' : 'none';
        element.textContent = options.style.display === 'none' ? '▼' : '▲';
    }
}

/**
 * Update wishlist button appearance
 */
function updateWishlistButton(productId, isInWishlist) {
    const wishlistBtn = document.querySelector(`[data-wishlist-btn="${productId}"]`);
    
    if (wishlistBtn) {
        if (isInWishlist) {
            wishlistBtn.classList.add('active');
            wishlistBtn.innerHTML = '❤️ Remove from Wishlist';
        } else {
            wishlistBtn.classList.remove('active');
            wishlistBtn.innerHTML = '🤍 Add to Wishlist';
        }
    }
}
