"""Static interface and disclosure checks; not native assistive-technology acceptance."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).parent/'web'

class WebContractTests(unittest.TestCase):
    def test_all_doms_ids_are_unique_and_link_targets_exist(self):
        html=(ROOT/'index.html').read_text()
        ids=re.findall(r'\bid="([^"]+)"',html)
        self.assertEqual(len(ids),len(set(ids)))
        for a in re.findall(r'href="#([^"]+)"',html):self.assertIn(a,ids)

    def test_every_script_dom_lookup_exists(self):
        html=(ROOT/'index.html').read_text();js=(ROOT/'app.js').read_text()
        ids=set(re.findall(r'\bid="([^"]+)"',html))
        for ident in set(re.findall(r"\$\('([\w-]+)'\)",js)):
            self.assertIn(ident,ids)

    def test_external_scripts_and_inline_onclick_absent(self):
        html=(ROOT/'index.html').read_text()
        self.assertNotRegex(html,r'<script[^>]*src="https?://')
        self.assertNotRegex(html,r'\bon(?:click|error|load|submit)=')
        self.assertNotIn('innerHTML',(ROOT/'app.js').read_text())
        self.assertNotIn('document.write',(ROOT/'app.js').read_text())

    def test_mobile_reduced_motion_keyboard_and_tap_targets(self):
        css=(ROOT/'style.css').read_text();html=(ROOT/'index.html').read_text()
        for rule in ('max-width:820px','max-width:380px','prefers-reduced-motion','focus-visible','min-height:44px'):
            self.assertIn(rule,css)
        self.assertIn('href="#main"',html)
        self.assertIn('role="status"',html)

    def test_honest_local_only_and_no_secrets(self):
        html=(ROOT/'index.html').read_text();js=(ROOT/'app.js').read_text();css=(ROOT/'style.css').read_text()
        self.assertIn('127.0.0.1',html)
        self.assertIn('not human',html.lower())
        for source in (html,js,css):
            self.assertNotRegex(source,r'(?i)(?:api[_-]?key|private[_-]?key)\s*[:=]\s*["\'][a-z0-9]{16,}')
            self.assertNotIn('nonpublic-company-identifier',source.lower())
            self.assertNotIn('internal-product-source',source.lower())

if __name__=='__main__':unittest.main()
