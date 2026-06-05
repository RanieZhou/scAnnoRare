# -*- coding: utf-8 -*-
"""用 Playwright 三引擎实测 HTTPS 页面访问 localhost Agent 的浏览器行为。"""
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://10.112.89.52:8443/index.html"

ENGINES = [
    ("Chromium（对应 Chrome / Edge）", "chromium"),
    ("Firefox（火狐）", "firefox"),
    ("WebKit（对应 Safari）", "webkit"),
]


def run_engine(p, label, engine):
    browser = getattr(p, engine).launch()
    # ignore_https_errors: 仅为绕过自签名证书；真实部署用正规证书无此问题
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    console_errors = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.goto(URL, wait_until="load")
    page.wait_for_function("window.__DONE__ === true", timeout=15000)
    results = page.evaluate("window.__RESULTS__")
    origin = page.evaluate("location.origin")
    page.screenshot(path=f"compat_{engine}.png", full_page=True)
    browser.close()
    return origin, results, console_errors


def main():
    print(f"测试 URL: {URL}\n")
    summary = []
    with sync_playwright() as p:
        for label, engine in ENGINES:
            print("=" * 64)
            print(f"【{label}】")
            try:
                origin, results, cerr = run_engine(p, label, engine)
                print(f"  页面 Origin: {origin}")
                passed = 0
                for r in results:
                    mark = "✅ 通过" if r["ok"] else "❌ 被拦截"
                    print(f"  {mark}  {r['name']}")
                    print(f"          → {r['detail']}")
                    if r["ok"]:
                        passed += 1
                summary.append((label, passed, len(results)))
                if cerr:
                    print("  浏览器控制台错误:")
                    for e in cerr[:4]:
                        print(f"          ! {e[:120]}")
            except Exception as e:
                print(f"  运行失败: {e}")
                summary.append((label, -1, 0))
            print()

    print("=" * 64)
    print("汇总:")
    for label, passed, total in summary:
        if passed < 0:
            print(f"  {label}: 运行异常")
        else:
            print(f"  {label}: {passed}/{total} 项请求成功到达 Agent")


if __name__ == "__main__":
    main()
