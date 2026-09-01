import { chromium } from "playwright";

async function main() {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const contexts = browser.contexts();
  const pages = contexts[0].pages();
  console.log(`Open Pages: ${pages.length}`);

  for (const p of pages) {
    const title = await p.title();
    const url = p.url();
    console.log(`- ${title} | ${url}`);
  }

  const signinPage = pages.find((p) => p.url().includes("accounts.google.com") || p.url().includes("labs.google"));
  if (signinPage) {
    await signinPage.screenshot({ path: "storage/signin_page.png" });
    console.log("Saved screenshot to storage/signin_page.png");

    const texts = await signinPage.evaluate(() => {
      return Array.from(document.querySelectorAll("button, div[role='button'], li, a")).map((el) => el.innerText.trim()).filter(Boolean);
    });
    console.log("Page Interactive Elements:", texts.slice(0, 20));
  }
  process.exit(0);
}

main().catch(console.error);
