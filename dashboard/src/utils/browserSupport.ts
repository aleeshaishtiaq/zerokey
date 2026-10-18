const chromiumBrowserPattern = /^(Google Chrome|Chrome|Chromium|Microsoft Edge|Edge|Brave|Opera|Vivaldi|Arc)(?:\s|$)/i;

export function isSupportedChromiumBrowser(browser: string) {
  return chromiumBrowserPattern.test(browser.trim());
}