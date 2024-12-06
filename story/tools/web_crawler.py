import json
import asyncio
from pathlib import Path
from typing import Dict, Optional, Set
from urllib.parse import urljoin
from crawl4ai import AsyncWebCrawler
from openai import AsyncOpenAI

class WebCrawler:
    def __init__(self, base_url: str, storage_dir: Path):
        self.base_url = base_url
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.answers_file = storage_dir / "answers.json"
        self.explored_urls_file = storage_dir / "explored_urls.txt"
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

    async def crawl(self, question: str, question_id: str, max_depth: int = 3) -> Optional[str]:
        return await self._explore_page(self.base_url, question, question_id, depth=0, max_depth=max_depth)
        
    async def _explore_page(self, url: str, question: str, question_id: str, 
                           depth: int = 0, max_depth: int = 3) -> Optional[str]:
        if depth >= max_depth or url in self.explored_urls:
            return None
            
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                
                if result.success and result.cleaned_html:
                    answer = await self._analyze_content(url, result.cleaned_html, question)
                    if answer:
                        self._save_answer(question_id, answer)
                        return answer
                        
                    # Process internal links
                    if result.links and result.links.get('internal'):
                        promising_urls = await self._evaluate_urls(result.links['internal'], question)
                        for link_url in promising_urls:
                            full_url = urljoin(self.base_url, link_url)
                            found_answer = await self._explore_page(
                                full_url, question, question_id, depth + 1, max_depth
                            )
                            if found_answer:
                                return found_answer
                            
                self._mark_as_explored(url)
                return None
                
        except Exception as e:
            self._mark_as_explored(url)
            return None
            
    async def _analyze_content(self, url: str, content: str, question: str) -> Optional[str]:
        client = AsyncOpenAI()
        prompt = self._build_analysis_prompt(url, content, question)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=750,
            temperature=0.1
        )
        
        return self._parse_llm_response(response.choices[0].message.content)
        
    def _save_answer(self, question_id: str, answer: str):
        self.answers[question_id] = answer.strip()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.answers_file, 'w', encoding='utf-8') as f:
            json.dump(self.answers, f, ensure_ascii=False, indent=4)
            
    def _mark_as_explored(self, url: str):
        self.explored_urls.add(url)
        with open(self.explored_urls_file, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")

    def _build_analysis_prompt(self, url: str, content: str, question: str) -> str:
        return f"""Analyze the following webpage content and answer the question.
        If the content contains a clear answer, provide it. If not, respond with 'None'.
        
        URL: {url}
        Question: {question}
        
        Content:
        {content}
        """

    def _parse_llm_response(self, response: str) -> Optional[str]:
        if not response or response.lower().strip() == 'none':
            return None
        return response.strip()