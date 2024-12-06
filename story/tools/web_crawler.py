import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Set
from urllib.parse import urljoin
from crawl4ai import AsyncWebCrawler, CacheMode
from openai import OpenAI
from story.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

class SmartWebCrawler:
    def __init__(self, base_url: str, storage_dir: Path):
        print(f"🚀 Initializing SmartWebCrawler for {base_url}")
        self.base_url = base_url.rstrip('/')
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.answers_file = storage_dir / "smart_crawler_answers.json"
        self.explored_urls_file = storage_dir / "smart_crawler_explored_urls.txt"
        self.answers = self._load_json(self.answers_file)
        self.explored_urls = self._load_explored_urls()

    def _load_json(self, file_path: Path) -> Dict:
        print(f"📚 Loading JSON from {file_path}")
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_explored_urls(self) -> Set[str]:
        print("🔍 Loading previously explored URLs")
        if self.explored_urls_file.exists():
            with open(self.explored_urls_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f)
        return set()

    def clear_explored_urls(self):
        """Clear the list of explored URLs"""
        print("🧹 Clearing explored URLs list")
        self.explored_urls = set()
        if self.explored_urls_file.exists():
            self.explored_urls_file.unlink()

    async def crawl(self, question: str, question_id: str, max_depth: int = 10, force_refresh: bool = True) -> Optional[str]:
        """Crawl starting from the base_url up to max_depth and attempt to answer the question."""
        if force_refresh:
            self.clear_explored_urls()
            
        print(f"🎯 Starting crawl for question: {question}")
        async with AsyncWebCrawler(verbose=True) as crawler:
            return await self._explore_page(
                crawler=crawler, 
                url=self.base_url, 
                question=question, 
                question_id=question_id, 
                depth=0, 
                max_depth=max_depth
            )

    async def _explore_page(
        self,
        crawler: AsyncWebCrawler,
        url: str,
        question: str,
        question_id: str,
        depth: int,
        max_depth: int
    ) -> Optional[str]:
        if depth >= max_depth or url in self.explored_urls:
            print(f"⚠️  Skipping {url} (depth: {depth}, max_depth: {max_depth})")
            return None

        print(f"🌐 Exploring page (depth {depth}): {url}")

        try:
            print(f"📥 Fetching content from {url}")
            result = await self._fetch_with_retry(crawler, url)

            print(f"✅ Marking {url} as explored")
            self._mark_as_explored(url)

            if result.success and result.markdown:
                print("🤔 Analyzing page content")
                answer = self._analyze_content(url, result.markdown, question)
                if answer and answer.lower() != 'none':
                    print(f"💡 Found answer: {answer[:100]}...")
                    self._save_answer(question_id, answer)
                    return answer

                print("🔗 Extracting links from page")
                all_links = set()
                if result.links:
                    # Handle the case where links might be a dictionary of lists or just a list
                    if isinstance(result.links, dict):
                        for link_list in result.links.values():
                            if isinstance(link_list, list):
                                # Extract only the URL strings from the link objects if they're dictionaries
                                for link in link_list:
                                    if isinstance(link, dict) and 'url' in link:
                                        all_links.add(link['url'])
                                    elif isinstance(link, str):
                                        all_links.add(link)
                    elif isinstance(result.links, list):
                        for link in result.links:
                            if isinstance(link, dict) and 'url' in link:
                                all_links.add(link['url'])
                            elif isinstance(link, str):
                                all_links.add(link)

                for link_url in all_links:
                    full_url = urljoin(self.base_url, link_url)
                    if full_url.startswith(self.base_url) and full_url not in self.explored_urls:
                        print(f"➡️  Following link (depth {depth+1}): {full_url}")
                        found_answer = await self._explore_page(
                            crawler, full_url, question, question_id, depth + 1, max_depth
                        )
                        if found_answer:
                            return found_answer

            print("❌ No answer found on this page")
            return None

        except Exception as e:
            print(f"💥 Error exploring {url}: {str(e)}")
            return None

    def _analyze_content(self, url: str, content: str, question: str) -> Optional[str]:
        print(f"🧠 Analyzing content from {url}")
        prompt = f"""
        You are a precise web content analyzer. Your task is to find a specific answer to the given question.
        Rules:
        - Answer ONLY based on the provided content
        - If you can't find a clear answer, respond with 'None'
        - Be concise but complete
        - Include relevant context
        - Don't make assumptions

        Question: {question}

        Content:
        {content}

        Answer format:
        - If found: Provide the answer with necessary context
        - If not found: None
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a more capable model
            messages=[
                {"role": "system", "content": "You are a precise web content analyzer focused on extracting specific information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=750
        )

        answer = response.choices[0].message.content.strip()
        return None if answer.lower() == 'none' else answer

    def _save_answer(self, question_id: str, answer: str):
        print(f"💾 Saving answer for question {question_id}")
        self.answers[question_id] = answer
        with open(self.answers_file, 'w', encoding='utf-8') as f:
            json.dump(self.answers, f, ensure_ascii=False, indent=4)

    def _mark_as_explored(self, url: str):
        print(f"📝 Marking URL as explored: {url}")
        self.explored_urls.add(url)
        with open(self.explored_urls_file, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")

    async def _explore_links(self, crawler, links, question, question_id, depth, max_depth):
        tasks = []
        for link_url in links:
            full_url = urljoin(self.base_url, link_url)
            if full_url.startswith(self.base_url) and full_url not in self.explored_urls:
                print(f"➡️  Queueing link (depth {depth+1}): {full_url}")
                tasks.append(self._explore_page(
                    crawler, full_url, question, question_id, depth + 1, max_depth
                ))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return next((r for r in results if r is not None and not isinstance(r, Exception)), None)
        return None

    async def _fetch_with_retry(self, crawler, url, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await crawler.arun(
                    url=url,
                    cache_mode=CacheMode.BYPASS,
                    word_count_threshold=0,
                    verbose=True,
                    remove_overlay_elements=True,
                    js_only=False
                )
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"🔄 Retry {attempt + 1}/{max_retries} for {url}: {str(e)}")
                await asyncio.sleep(1)
