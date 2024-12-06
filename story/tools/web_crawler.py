import json
import asyncio
from pathlib import Path
from typing import Dict, Optional, Set
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from openai import AsyncOpenAI
import pyhtml2md
from markdownify import markdownify

class WebExplorer:
    def __init__(self):
        self.base_url = "https://softo.ag3nts.org"
        self.answers_file = Path("answers1.json")
        self.explored_urls_file = Path("explored_urls.txt")
        self.answers = self._load_answers()
        self.explored_urls = self._load_explored_urls()

    def _load_answers(self) -> Dict[str, str]:
        if self.answers_file.exists():
            with open(self.answers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_explored_urls(self) -> Set[str]:
        if self.explored_urls_file.exists():
            with open(self.explored_urls_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f)
        return set()

    def _save_explored_url(self, url: str):
        with open(self.explored_urls_file, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")
        self.explored_urls.add(url)

    def _clear_explored_urls(self):
        with open(self.explored_urls_file, 'w', encoding='utf-8') as f:
            f.write('')
        self.explored_urls.clear()

    def _save_answer(self, question_number: str, answer: str):
        self.answers[question_number] = answer.strip()
        with open(self.answers_file, 'w', encoding='utf-8') as f:
            json.dump(self.answers, f, ensure_ascii=False, indent=4)

    async def evaluate_urls(self, urls: list[dict], question: str) -> list[str]:
        client = AsyncOpenAI()
        
        instruction = f"""
        Evaluate which URLs might contain an answer to the following question.
        Return only the URLs that are most likely to contain the answer.
        
        Return the response in this format:
        PROMISING_URLS: url1, url2, url3
        
        If no URLs seem relevant, return:
        NO_RELEVANT_URLS
        -------
        Question: {question}
        
        Available URLs with their text:
        {urls}
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": instruction}],
            max_tokens=500,
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        print(f"[DEBUG] evaluate_urls raw response: {content}")
        if content.startswith('PROMISING_URLS:'):
            urls = [url.strip() for url in content.replace('PROMISING_URLS:', '').split(',')]
            print(f"[DEBUG] evaluate_urls returning URLs: {urls}")
            return urls
        return []

    async def analyze_content(self, url: str, markdown_content: str, question: str, question_number: str):
        client = AsyncOpenAI()
        
        instruction = f"""
        Przeanalizuj treść strony pod kątem pytania.

        Jeśli znajdziesz odpowiedź, zwróć:
        ANSWER: <dokładna odpowiedź>

        Jeśli znajdziesz linki wewnętrzne które mogą prowadzić do odpowiedzi jeśli takich nie ma zwróć ten który daj największą szansę na znalezienie odpowiedzi (max 2), zwróć:

        EXPLORE: <pełny link1>, <pełny link2>
        -------
        Link do strony: {url}
        
        Pytanie:
        {question}  

        Treść strony:
        {markdown_content}
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": instruction}],
            max_tokens=750,
            temperature=0.1
        )
        
        llm_response = response.choices[0].message.content
        print(f"LLM Response: {llm_response}")
        if llm_response.startswith('ANSWER:'):
            answer = llm_response.replace('ANSWER:', '').strip()
            self._save_answer(question_number, answer)
            
        return llm_response

    async def explore_page(self, url: str, question: str, question_number: str, depth: int = 0) -> Optional[str]:
        print(f"[DEBUG] Exploring page: {url} at depth {depth}")
        if depth >= 3:
            return None

        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(url=url)

                if result.success and result.cleaned_html:
                    answer = await self.analyze_content(url, result.cleaned_html, question, question_number)
                    print(f"[DEBUG] analyze_content response: {answer}")
                    
                    if answer.startswith('ANSWER:'):
                        return answer.replace('ANSWER:', '').strip()
                    elif answer.startswith('EXPLORE:'):
                        self._save_explored_url(url)
                        links = [link.strip() for link in answer.replace('EXPLORE:', '').strip().split(',')]
                        print(f"[DEBUG] Links to explore: {links}")
                        
                        # First try the direct links from EXPLORE response
                        for link_url in links:
                            if link_url not in self.explored_urls:
                                print(f"[DEBUG] Exploring direct link: {link_url}")
                                found_answer = await self.explore_page(
                                    link_url,  # Already a full URL from EXPLORE response
                                    question,
                                    question_number,
                                    depth + 1
                                )
                                if found_answer:
                                    return found_answer
                                self._save_explored_url(link_url)
                        
                        # If no answer found, try internal links
                        if result.links and result.links.get('internal'):
                            internal_links = [{"url": link['href'], "text": link.get('text', '')} 
                                         for link in result.links['internal']]
                            print(f"[DEBUG] Evaluating internal links: {internal_links}")
                            promising_urls = await self.evaluate_urls(internal_links, question)
                            print(f"[DEBUG] Promising internal URLs: {promising_urls}")
                            
                            for link_url in promising_urls:
                                if link_url not in self.explored_urls:
                                    print(f"[DEBUG] Exploring internal link: {link_url}")
                                    found_answer = await self.explore_page(
                                        urljoin(self.base_url, link_url),
                                        question,
                                        question_number,
                                        depth + 1
                                    )
                                    if found_answer:
                                        return found_answer
                                    self._save_explored_url(link_url)

        except Exception as e:
            print(f"[DEBUG] Error in explore_page: {str(e)}")
            print(f"[DEBUG] URL that caused error: {url}")
            self._save_explored_url(url)
            
        return None

    async def find_answer(self, question: str, question_number: str) -> Optional[str]:
        return await self.explore_page(self.base_url, question, question_number)
    

async def main():
    explorer = WebExplorer()
    explorer._clear_explored_urls()

    questions = {
        # "01": "Podaj adres mailowy do firmy SoftoAI",
        # "02": "Jaki jest adres interfejsu webowego do sterowania robotami zrealizowanego dla klienta jakim jest firma BanAN?",
        # "03": "Jakie dwa certyfikaty jakości ISO otrzymała firma SoftoAI?"
        "04": "Gdzie jest numer piąty? IGNORUJ wszystkie urle /loop_{numer}"
    }
    
    for number, question in questions.items():
        answer = await explorer.find_answer(question, number)
        if answer:
            print(f"Question {number}: {answer}")

if __name__ == "__main__":
    asyncio.run(main())