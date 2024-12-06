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

            print(f"📋 Result status: {result.success}")
            
            # Try different content sources in order of preference
            content = None
            if result.cleaned_html:
                content = result.cleaned_html
                print("📄 Using cleaned HTML content")
            elif result.html:
                content = result.html
                print("📄 Using raw HTML content")
            
            if content:
                print(f"📝 Content length: {len(content)}")
                print(f"📄 First 500 chars of content:\n{content[:500]}...")
            else:
                print("⚠️ No content available")
                return None

            print(f"✅ Marking {url} as explored")
            self._mark_as_explored(url)

            if result.success and content:
                print("🤔 Analyzing page content")
                answer = self._analyze_content(url, content, question)
                if answer and answer.lower() != 'none':
                    print(f"💡 Found answer: {answer[:100]}...")
                    self._save_answer(question_id, answer)
                    return answer

                print("🔗 Analyzing links for relevance")
                prioritized_links = self._analyze_links_relevance(result.links, question)
                
                if prioritized_links:
                    print("🎯 Exploring prioritized links")
                    for link_url in prioritized_links:
                        full_url = urljoin(self.base_url, link_url)
                        if full_url.startswith(self.base_url) and full_url not in self.explored_urls:
                            print(f"➡️  Following promising link: {full_url}")
                            found_answer = await self._explore_page(
                                crawler, full_url, question, question_id, depth + 1, max_depth
                            )
                            if found_answer:
                                return found_answer
                else:
                    print("⚠️  No promising links found")

            print("❌ No answer found on this page")
            return None

        except Exception as e:
            print(f"💥 Error exploring {url}: {str(e)}")
            print(f"🔍 Error details: {type(e).__name__}")
            import traceback
            print(f"📚 Traceback: {traceback.format_exc()}")
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

    def _extract_links(self, links) -> set:
        """Extract and normalize links from the crawler result."""
        print("🔍 Processing extracted links")
        all_links = set()
        
        if not links:
            print("⚠️  No links found on page")
            return all_links

        try:
            # Handle the specific format we're receiving
            if isinstance(links, dict) and 'internal' in links:
                for link_data in links['internal']:
                    if isinstance(link_data, dict) and 'href' in link_data:
                        print(f"🔗 Found internal link: {link_data['href']} ({link_data.get('text', 'No text')})")
                        all_links.add(link_data['href'])
                
                # Also process external links if they exist
                if 'external' in links and links['external']:
                    for link_data in links['external']:
                        if isinstance(link_data, dict) and 'href' in link_data:
                            print(f"🌍 Found external link: {link_data['href']} ({link_data.get('text', 'No text')})")
                            all_links.add(link_data['href'])

        except Exception as e:
            print(f"⚠️  Error processing links: {str(e)}")
            import traceback
            print(f"📚 Traceback: {traceback.format_exc()}")
        
        print(f"📊 Total links found: {len(all_links)}")
        if all_links:
            print("📋 Links to explore:")
            for link in sorted(all_links):
                print(f"  ➡️  {link}")
        
        return all_links

    def _analyze_links_relevance(self, links: dict, question: str) -> list:
        """Use LLM to analyze and prioritize links based on their relevance to the question."""
        print(f"🤖 Analyzing link relevance for question: {question}")
        
        # Prepare links data for analysis
        links_data = []
        if isinstance(links, dict) and 'internal' in links:
            for link in links['internal']:
                if isinstance(link, dict) and 'href' in link:
                    links_data.append({
                        'url': link['href'],
                        'text': link.get('text', ''),
                        'title': link.get('title', '')
                    })

        if not links_data:
            print("⚠️  No links to analyze")
            return []

        prompt = f"""
        You are an intelligent web crawler assistant. Analyze these links and determine which are most likely to contain information about the question.
        
        Question: {question}

        Available links:
        {json.dumps(links_data, indent=2, ensure_ascii=False)}

        Task:
        1. Analyze each link's URL, text, and title
        2. Determine relevance to the question
        3. Return a valid JSON array containing only the URLs of relevant links in order of likely relevance
        4. If no links seem relevant, return empty array

        IMPORTANT: Your response must be a valid JSON array of strings, nothing else.
        Example valid responses:
        ["/kontakt", "/about-us"]
        []

        Remember: Return ONLY the JSON array, no other text.
        """

        try:
            print("🔄 Requesting LLM analysis of links")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a precise link analyzer that returns only URLs in a JSON array format. Always return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=750
            )

            content = response.choices[0].message.content.strip()
            print(f"🔍 Raw LLM response: {content}")

            try:
                result = json.loads(content)
                if not isinstance(result, list):
                    print("⚠️  LLM returned non-list response, falling back to default")
                    return [link['url'] for link in links_data]
            except json.JSONDecodeError:
                print("⚠️  Failed to parse LLM response as JSON, attempting to extract URLs")
                # Fallback: try to extract URLs from the response using regex
                import re
                urls = re.findall(r'["\']([^"\']+)["\']', content)
                result = [url for url in urls if url.startswith('/') or url.startswith('http')]
                if not result:
                    print("⚠️  Fallback parsing failed, using all links")
                    return [link['url'] for link in links_data]
            
            if result:
                print("📊 Prioritized links:")
                for url in result:
                    print(f"  🎯 {url}")
            else:
                print("⚠️  No relevant links found")
            
            return result

        except Exception as e:
            print(f"💥 Error analyzing links: {str(e)}")
            import traceback
            print(f"📚 Traceback: {traceback.format_exc()}")
            # Fall back to all links if LLM analysis fails
            return [link['url'] for link in links_data]

# TODO: remove, only for testing
# async def main():
#     # Initialize the crawler
#     base_url = "https://softo.ag3nts.org"
#     storage_dir = Path("crawler_storage")
#     crawler = SmartWebCrawler(base_url, storage_dir)

#     # Define test questions
#     questions = [
#         ("Jak nazywa się firma zbrojeniowa produkująca roboty przemysłowe i militarne?", "q1"),
#         # ("Jak nazywa się firma tworząca oprogramowanie do zarządzania robotami?", "q2"),
#         # ("Na jakiej ulicy znajduje się siedziba firmy Softo?", "q3"),
#     ]

#     # Process each question
#     for question, question_id in questions:
#         print("\n" + "="*50)
#         print(f"📝 Processing question: {question}")
#         answer = await crawler.crawl(question, question_id)
#         print(f"🎯 Final answer: {answer if answer else 'Not found'}")
#         print("="*50 + "\n")

# if __name__ == "__main__":
#     # Run the async main function
#     asyncio.run(main())
