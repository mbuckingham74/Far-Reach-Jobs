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
  const { url, waitFor, timeout } = req.body;

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

    // Navigate to page
    await page.goto(url, {
      waitUntil: 'networkidle',
      timeout: pageTimeout
    });

    // Optional: wait for a specific selector
    if (waitFor) {
      try {
        await page.waitForSelector(waitFor, { timeout: 10000 });
      } catch (e) {
        console.log(`Selector '${waitFor}' not found, continuing anyway`);
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
