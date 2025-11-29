const express = require('express');
const { chromium } = require('playwright');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'playwright-service' });
});

// Fetch a page and return HTML
app.post('/fetch', async (req, res) => {
  const { url, waitFor, selectActions, clickSelector, clickWaitFor, timeout } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  let browser = null;
  try {
    console.log(`Fetching: ${url}`);

    browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
      ]
    });

    const context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      viewport: { width: 1920, height: 1080 },
      locale: 'en-US',
    });

    const page = await context.newPage();

    // Set reasonable timeout (default 30s)
    const pageTimeout = timeout || 30000;
    page.setDefaultTimeout(pageTimeout);

    // Navigate to page - use 'domcontentloaded' instead of 'networkidle'
    // because many sites have continuous background activity that prevents
    // networkidle from ever completing (analytics, websockets, polling, etc.)
    await page.goto(url, {
      waitUntil: 'domcontentloaded',
      timeout: pageTimeout
    });

    // Give JavaScript a moment to render dynamic content
    await page.waitForTimeout(2000);

    // Optional: wait for a specific selector
    if (waitFor) {
      try {
        await page.waitForSelector(waitFor, { timeout: 10000 });
      } catch (e) {
        console.log(`Selector '${waitFor}' not found, continuing anyway`);
      }
    }

    // Optional: select dropdown values before clicking
    // selectActions is an array of {selector, value} objects
    if (selectActions && Array.isArray(selectActions)) {
      for (const action of selectActions) {
        try {
          console.log(`Selecting value '${action.value}' for '${action.selector}'`);
          await page.selectOption(action.selector, action.value);
          await page.waitForTimeout(500);
        } catch (e) {
          console.log(`Select failed for '${action.selector}': ${e.message}`);
        }
      }
    }

    // Optional: click a button/link and wait for results
    if (clickSelector) {
      try {
        console.log(`Clicking: ${clickSelector}`);
        await page.click(clickSelector);

        // Wait for results to load
        await page.waitForTimeout(3000);

        // If a specific selector to wait for after click is provided, wait for it
        if (clickWaitFor) {
          try {
            await page.waitForSelector(clickWaitFor, { timeout: 15000 });
          } catch (e) {
            console.log(`Post-click selector '${clickWaitFor}' not found, continuing anyway`);
          }
        }
      } catch (e) {
        console.log(`Click failed for '${clickSelector}': ${e.message}`);
      }
    }

    // Get the rendered HTML
    const html = await page.content();
    const finalUrl = page.url(); // In case of redirects

    await browser.close();
    browser = null;

    console.log(`Success: ${url} (${html.length} bytes)`);

    res.json({
      success: true,
      url: finalUrl,
      html: html
    });

  } catch (error) {
    console.error(`Error fetching ${url}:`, error.message);

    if (browser) {
      await browser.close();
    }

    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Playwright service listening on port ${PORT}`);
});
