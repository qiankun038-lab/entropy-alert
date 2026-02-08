// ============================================
// ENTROPY SURVIVOR - Alpha Intelligence System
// Frontend Application
// ============================================

// State
let currentTab = 'alpha';
let worldviewData = null;
let alphaData = [];
let tradesData = [];
let sourceWeights = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initForms();
    loadData();
    startPolling();
});

// Navigation
function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });
}

function switchTab(tab) {
    currentTab = tab;
    
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tab}`);
    });
}

// Data Loading
async function loadData() {
    try {
        // Load worldview
        const wvResponse = await fetch('/data/worldview.json');
        if (wvResponse.ok) {
            worldviewData = await wvResponse.json();
            renderWorldview();
        }
        
        // Load source weights
        const swResponse = await fetch('/data/source_weights.json');
        if (swResponse.ok) {
            sourceWeights = await swResponse.json();
            renderSourceTrust();
        }
        
        // Load alpha feed
        await loadAlphaFeed();
        
        // Load trades
        await loadTrades();
        
        updateLastUpdate();
    } catch (error) {
        console.log('Data loading - some files may not exist yet:', error);
    }
}

async function loadAlphaFeed() {
    try {
        const response = await fetch('/data/alpha.jsonl');
        if (response.ok) {
            const text = await response.text();
            alphaData = text.trim().split('\n')
                .filter(line => line)
                .map(line => JSON.parse(line))
                .reverse(); // Newest first
            renderAlphaFeed();
        }
    } catch (error) {
        console.log('No alpha data yet');
    }
}

async function loadTrades() {
    try {
        const response = await fetch('/data/trades.jsonl');
        if (response.ok) {
            const text = await response.text();
            tradesData = text.trim().split('\n')
                .filter(line => line)
                .map(line => JSON.parse(line))
                .reverse();
            renderTrades();
        }
    } catch (error) {
        console.log('No trades data yet');
    }
}

// Rendering
function renderAlphaFeed() {
    const container = document.getElementById('alpha-feed');
    
    if (alphaData.length === 0) {
        container.innerHTML = `
            <div class="alpha-card">
                <div class="alpha-meta">
                    <span class="alpha-source twitter">System</span>
                    <span class="alpha-time">Awaiting first ingestion...</span>
                </div>
                <div class="alpha-content">
                    <p>Alpha signals will appear here once ingestion begins.</p>
                </div>
                <div class="alpha-signal">
                    <span class="signal-badge neutral">INITIALIZING</span>
                </div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = alphaData.map(alpha => `
        <div class="alpha-card">
            <div class="alpha-meta">
                <span class="alpha-source ${alpha.source_type}">${alpha.source}</span>
                <span class="alpha-time">${formatTime(alpha.timestamp)}</span>
            </div>
            <div class="alpha-content">
                <p>${escapeHtml(alpha.raw_content?.substring(0, 500) || alpha.content || 'No content')}</p>
            </div>
            ${alpha.extracted_signal ? `
                <div class="alpha-signal">
                    <span class="signal-badge ${getSignalClass(alpha.extracted_signal.direction)}">${alpha.extracted_signal.direction?.toUpperCase() || 'NEUTRAL'}</span>
                    <span class="signal-confidence">Asset: ${alpha.extracted_signal.asset || 'N/A'} | Confidence: ${Math.round((alpha.extracted_signal.confidence || 0.5) * 100)}%</span>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function renderWorldview() {
    if (!worldviewData) return;
    
    // State ID
    const stateEl = document.getElementById('worldview-state');
    if (stateEl) {
        stateEl.textContent = `State: ${worldviewData.state_id || 'unknown'}`;
    }
    
    // Macro regime
    const regimeEl = document.getElementById('macro-regime');
    if (regimeEl && worldviewData.macro_thesis) {
        regimeEl.innerHTML = `
            <span class="regime-label">Current Regime:</span>
            <span class="regime-value">${worldviewData.macro_thesis.current_regime || 'Unknown'}</span>
        `;
    }
    
    // Beliefs
    const beliefsEl = document.getElementById('beliefs-list');
    if (beliefsEl && worldviewData.macro_thesis?.key_beliefs) {
        if (worldviewData.macro_thesis.key_beliefs.length === 0) {
            beliefsEl.innerHTML = '<p class="empty-state">No beliefs formed yet.</p>';
        } else {
            beliefsEl.innerHTML = worldviewData.macro_thesis.key_beliefs.map(belief => `
                <div class="belief-item">
                    <span class="belief-text">${escapeHtml(belief.belief)}</span>
                    <span class="belief-confidence">${Math.round(belief.confidence * 100)}%</span>
                </div>
            `).join('');
        }
    }
    
    // Sector views
    const sectorsEl = document.getElementById('sector-bars');
    if (sectorsEl && worldviewData.sector_views) {
        sectorsEl.innerHTML = Object.entries(worldviewData.sector_views).map(([sector, data]) => {
            const confidence = data.confidence || 0.5;
            const barWidth = confidence * 100;
            const barClass = data.stance === 'bullish' ? 'bullish' : 
                           data.stance === 'bearish' ? 'bearish' : 'neutral';
            
            return `
                <div class="sector-bar">
                    <span class="sector-name">${formatSectorName(sector)}</span>
                    <div class="bar-container">
                        <div class="bar ${barClass}" style="width: ${barWidth}%"></div>
                    </div>
                    <span class="sector-stance">${capitalize(data.stance || 'neutral')}</span>
                </div>
            `;
        }).join('');
    }
    
    // Active theses
    const thesesEl = document.getElementById('theses-list');
    if (thesesEl && worldviewData.active_theses) {
        if (worldviewData.active_theses.length === 0) {
            thesesEl.innerHTML = '<p class="empty-state">No active theses. Awaiting alpha signals.</p>';
        } else {
            thesesEl.innerHTML = worldviewData.active_theses.map(thesis => `
                <div class="thesis-item">
                    <div class="thesis-header">
                        <span class="thesis-asset">${thesis.asset}</span>
                        <span class="thesis-status ${thesis.status}">${thesis.status}</span>
                    </div>
                    <p class="thesis-text">${escapeHtml(thesis.thesis)}</p>
                    <div class="thesis-meta">
                        <span>Confidence: ${Math.round(thesis.confidence * 100)}%</span>
                        <span>Sources: ${thesis.sources?.join(', ') || 'N/A'}</span>
                    </div>
                </div>
            `).join('');
        }
    }
}

function renderSourceTrust() {
    const container = document.getElementById('trust-scores');
    if (!container || !sourceWeights) return;
    
    const allSources = [
        ...sourceWeights.sources.twitter,
        ...sourceWeights.sources.substack,
        ...sourceWeights.sources.telegram,
        ...sourceWeights.sources.websites
    ].sort((a, b) => b.trust - a.trust);
    
    container.innerHTML = allSources.map(source => `
        <div class="trust-item">
            <span class="trust-name">${source.handle || source.name}</span>
            <span class="trust-value">${Math.round(source.trust * 100)}%</span>
        </div>
    `).join('');
}

function renderTrades() {
    const tradesListEl = document.getElementById('trades-list');
    if (!tradesListEl) return;
    
    if (tradesData.length === 0) {
        tradesListEl.innerHTML = '<p class="empty-state">No trades executed yet.</p>';
        return;
    }
    
    tradesListEl.innerHTML = tradesData.map(trade => `
        <div class="trade-item">
            <div class="trade-header">
                <span class="trade-action ${trade.action?.toLowerCase()}">${trade.action}</span>
                <span class="trade-asset">${trade.asset}</span>
                <span class="trade-time">${formatTime(trade.executed_at)}</span>
            </div>
            <div class="trade-details">
                <span>Entry: $${trade.entry_price}</span>
                <span>Size: ${trade.size}</span>
                <span class="trade-pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}">
                    P&L: ${trade.pnl >= 0 ? '+' : ''}${trade.pnl}%
                </span>
            </div>
        </div>
    `).join('');
}

// Forms
function initForms() {
    // Confidence slider
    const confidenceSlider = document.getElementById('override-confidence');
    const confidenceDisplay = document.getElementById('confidence-display');
    if (confidenceSlider && confidenceDisplay) {
        confidenceSlider.addEventListener('input', (e) => {
            confidenceDisplay.textContent = `${e.target.value}%`;
        });
    }
    
    // Override form
    const overrideForm = document.getElementById('override-form');
    if (overrideForm) {
        overrideForm.addEventListener('submit', handleOverrideSubmit);
    }
}

async function handleOverrideSubmit(e) {
    e.preventDefault();
    
    const type = document.getElementById('override-type').value;
    const content = document.getElementById('override-content').value;
    const confidence = document.getElementById('override-confidence').value / 100;
    
    const override = {
        id: `override_${Date.now()}`,
        type,
        content,
        confidence,
        timestamp: new Date().toISOString(),
        added_by: 'human'
    };
    
    // For now, log to console - will be saved by backend
    console.log('Human override submitted:', override);
    alert('Override submitted! The system will process this on next update.');
    
    // Clear form
    document.getElementById('override-content').value = '';
}

// Polling
function startPolling() {
    // Refresh data every 60 seconds
    setInterval(loadData, 60000);
}

// Utilities
function formatTime(timestamp) {
    if (!timestamp) return '--';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function formatSectorName(sector) {
    return sector.split('_').map(capitalize).join(' ');
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getSignalClass(direction) {
    if (!direction) return 'neutral';
    const d = direction.toLowerCase();
    if (d === 'long' || d === 'bullish' || d === 'buy') return 'bullish';
    if (d === 'short' || d === 'bearish' || d === 'sell') return 'bearish';
    return 'neutral';
}

function updateLastUpdate() {
    const el = document.getElementById('last-update');
    if (el) {
        el.textContent = new Date().toLocaleTimeString();
    }
}

// Export for debugging
window.EntropySurvivor = {
    worldviewData,
    alphaData,
    tradesData,
    sourceWeights,
    loadData,
    switchTab
};
