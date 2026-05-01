#CS121_Assignment2

import re
from urllib.parse import urlparse, urljoin, urldefrag, parse_qs
from bs4 import BeautifulSoup
import json
import os

unique_urls = set()
word_frequencies = {}
subdomain_counts = {}
longest_page_info = ("", 0)
pages_processed = 0

STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be because been
before being below between both but by can can't cannot could couldn't did didn't do
does doesn't doing don't down during each few for from further had hadn't has hasn't
have haven't having he he'd he'll he's her here here's hers herself him himself his
how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more
most mustn't my myself no nor not of off on once only or other ought our ours
ourselves out over own same shan't she she'd she'll she's should shouldn't so some
such than that that's the their theirs them themselves then there there's these they
they'd they'll they're they've this those through to too under until up very was
wasn't we we'd we'll we're we've were weren't what what's when when's where where's
which while who who's whom why why's with won't would wouldn't you you'd you'll
you're you've your yours yourself yourselves
""".split())

ALLOWED_DOMAINS = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"}

WORD_RE = re.compile(r"[a-zA-Z]+")

INVALID_PARAMETERS = {
    "do", "tab_files", "tab_details", "image", "ns",
    "media", "ical", "idx", "sid", "rev", "rev2",
    "action", "version", "a", "h", "hb", "sf", "support",
    "share", "ical"
}

BAD_HTML_FILENAMES = {
    "projects.html", "homework.html", "outline.html", "lecture-notes.html",
    "grades.html", "handouts.html", 
    "teach.html", "students.html", "academics.html", "bio.html", 
    "apply.html", "faculty-staff.html"
}

TERMINAL_STATS_CODES = {604, 605, 607, 608}


def save_stats():
    stats = {
        "unique_pages_count": len(unique_urls),
        "subdomains": dict(sorted(subdomain_counts.items())),
        "longest_page": longest_page_info,
        "top_50_words": sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)[:50]
    }
    temp_path = "stats_backup.json.tmp"
    with open(temp_path, "w") as f:
        json.dump(stats, f, indent=4)
    os.replace(temp_path, "stats_backup.json")

def get_visible_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    
    for tag in soup.find_all(style=True):
        style_content = tag["style"].replace(" ", " ").lower()
        if "display:none" in style_content or "visibility:hidden" in style_content:
            tag.decompose()
    return soup.get_text(separator=' ', strip=True)

def normalize(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return f"{parsed.scheme}://{host}{parsed.path.rstrip('/')}"

def tokenize_string(text: str) -> list[str]:
    return re.findall(r'[a-zA-Z]+', text.lower())

def scraper(url, resp):
    global pages_processed, longest_page_info

    if resp.status in TERMINAL_STATS_CODES:
        print(f"[SKIP] Cache server rejected {url} with status {resp.status}")
        return []
    final_url = resp.url if resp.url else url
    clean_url = normalize(final_url)

    if resp.status == 200 and resp.raw_response and clean_url not in unique_urls:
        raw_content = resp.raw_response.content
        visible_text = get_visible_text(raw_content)
        tokens = tokenize_string(visible_text)

        if len(raw_content) > 1000000 and len(tokens) < 300:
            return []

        if len(tokens) < 50:
            print(f"[SKIP] Low-content page ({len(tokens)} tokens): {clean_url}")
            return []
        
        unique_urls.add(clean_url)
        pages_processed += 1

        meaningful_tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
        for word in meaningful_tokens:
            word_frequencies[word] = word_frequencies.get(word, 0) + 1

        if len(tokens) > longest_page_info[1]:
            longest_page_info = (clean_url, len(tokens))
        
        parsed = urlparse(clean_url)
        domain = (parsed.hostname or "").lower()
        if any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS):
            subdomain_counts[domain] = subdomain_counts.get(domain, 0) + 1
        
        if pages_processed % 25 == 0:
            save_stats()
            print(f"Progress Saved: {pages_processed} pages processed.")

    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    links = []
    if resp.status != 200 or resp.raw_response is None:
        return links

    # handle the  redirection
    final_url = resp.url
    if final_url != url and not is_valid(final_url):
        return links

    try:
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")

        for tag in soup.find_all("a", href=True):
            href = tag.get("href")

            absolute_url = urljoin(final_url, href)

            # remove fragments (defragment)
            defragmented, _ = urldefrag(absolute_url)
            links.append(normalize(defragmented))

    except Exception:
        return list()

    return links


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        if parsed.scheme not in set(["http", "https"]):
            return False

        domain = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        query_params = parse_qs(parsed.query.lower())

        # checking allowed domains
        if not any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS):
            return False
        
        # checking invalid parameters
        if any(param in INVALID_PARAMETERS for param in query_params):
            return False
        
        if len(query_params) > 3:
            return False
        
        # checking bad html filenames
        path_parts = path.split("/")
        filename = path_parts[-1] if path_parts else ""
        if filename in BAD_HTML_FILENAMES:
            return False

        #make sure  no falling into traps

        # handling calendar
        if "calendar" in path or "event" in path or domain == "gitlab.ics.uci.edu":
            return False
            
        if domain == "archive.ics.uci.edu" and "datasets" in path:
            return False

        # handling loop and length
        path_sections = [p for p in path.split("/") if p]
        if len(url) > 250 or len(path_sections) > 10:
            return False
        
        # Repeating directory detection
        if len(path_sections) > 6 and len(path_sections) != len(set(path_sections)):
            return False

        #pages with dates regenerating
        if re.search(r"/\d{4}/\d{2}/\d{2}", path):
            return False

        #pagination
        if "/page/" in path:
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def make_report(filename="report.txt"):
    f = open(filename, "w")

    f.write("Unique Pages: " + str(len(unique_urls)) + "\n")
    f.write("Longest Page: " + longest_page_info[0] + "\n")
    f.write("Word Count: " + str(longest_page_info[1]) + "\n")

    top_words = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)[:50]
    f.write("Top 50 Words: " + str(top_words) + "\n")

    f.write("Subdomains: " + str(sorted(subdomain_counts.items())) + "\n")

    f.close()


if __name__ == "__main__":
    make_report()
