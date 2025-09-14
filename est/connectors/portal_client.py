from playwright.sync_api import sync_playwright
import time
import re
from typing import List
import os
import hashlib
import pickle

class PortalClient:
    def __init__(self, base_url: str, user: str, password: str, headless: bool = True, cache_dir: str = ".cache_portal"):
        self.base_url = base_url.rstrip('/')
        self.user = user
        self.password = password
        self.headless = headless
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        h = hashlib.sha256(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, h + ".pkl")

    def _load_cache(self, key: str):
        path = self._get_cache_path(key)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return pickle.load(f)
        return None

    def _save_cache(self, key: str, value):
        path = self._get_cache_path(key)
        with open(path, "wb") as f:
            pickle.dump(value, f)

    def fetch_schedule_html(self) -> List[str]:
        cache_key = f"schedule:{self.base_url}:{self.user}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"{self.base_url}/Login")
            # Ajustar seletores conforme o HTML real:
            page.fill('input[name="Matricula"], input#username, input[name="login"]', self.user)
            page.fill('input[name="Password"], input#password, input[type="password"]', self.password)
            page.click('button[type="submit"], input[type="submit"], button:has-text("Entrar")')
            page.wait_for_load_state("networkidle")
            time.sleep(1.0)
            for path in ["/Aluno/QuadroDeHorarios/"]:
                try:
                    page.goto(f"{self.base_url}{path}")
                    page.wait_for_load_state("networkidle")
                    time.sleep(0.6)
                    html = page.content()
                    if "Disciplina" in html or "Horário" in html or "Sala" in html:
                        break
                except Exception:
                    pass
            else:
                html = page.content()
            context.close()
            browser.close()
        self._save_cache(cache_key, html)
        return html

    def fetch_blog_posts_html(self) -> List[str]:
        cache_key = f"blog_posts:{self.base_url}:{self.user}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"{self.base_url}/Login")
            # Ajustar seletores conforme o HTML real:
            page.fill('input[name="Matricula"], input#username, input[name="login"]', self.user)
            page.fill('input[name="Password"], input#password, input[type="password"]', self.password)
            page.click('button[type="submit"], input[type="submit"], button:has-text("Entrar")')
            page.wait_for_load_state("networkidle")
            time.sleep(1.0)
            for path in ["/Aluno/MinhasTurmas/"]:
                try:
                    page.goto(f"{self.base_url}{path}")
                    page.wait_for_load_state("networkidle")
                    time.sleep(0.6)
                    html = page.content()
                    if "Minhas Disciplinas" in html:
                        break
                except Exception:
                    pass
            else:
                html = page.content()

            posts_html = []

            # Encontrar todos os links do tipo "/Aluno/Blog/<id>" na página atual
            blog_links = set(re.findall(r'href="(/Aluno/Blog/\d+)"', html))
            for link in blog_links:
                try:
                    page.goto(f"{self.base_url}{link}")
                    page.wait_for_load_state("networkidle")
                    time.sleep(0.5)
                    post_html = page.content()
                    posts_html.append(post_html)
                except Exception:
                    pass

            context.close()
            browser.close()
        self._save_cache(cache_key, posts_html)
        return posts_html
