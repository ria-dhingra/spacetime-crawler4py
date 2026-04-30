#CS121_Assignment2

import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import json

unique_urls = set()
word_frequencies = {}
subdomain_counts = {}
longest_page_info = ("", 0)
pages_processed = 0

try:
    with open("stopwords.txt", "r") as f:
        STOP_WORDS = set(line.strip().lower() for line in f)
except FileNotFoundError:
    STOP_WORDS = set()
    Print("Warning: stopwords.txt not found. Word frequencies will include stop words.")

def tokenize_string(text: str) -> list[str]:
    tokens = []
    current_token_chars = []

    for char in text:
        if char.isascii() and char.isalnum():
            # normalize to lowercase and build the token
            current_token_chars.append(char.lower())
        else:
            # found a delimiter
            if current_token_chars:
                tokens.append(''.join(current_token_chars))
                current_token_chars = []
    if current_token_chars:
        tokens.append(''.join(current_token_chars))
    return tokens

def get_visible_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)


def scraper(url, resp):
    global pages_processed, longest_page_info

    clean_url = url.split('#')[0]
    if resp.status == 200 and resp.raw_response and clean_url not in unique_urls:
        unique_urls.add(clean_url)
        pages_processed += 1

        text = get_visible_text(resp.raw_response.content)
        tokens = tokenize_string(text)

        meaningful_tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
        for word in meaningful_tokens:
            word_frequencies[word] = word_frequencies.get(word, 0) + 1
        
        global longest_page_info
        if len(tokens) > longest_page_info[1]:
            longest_page_info = (clean_url, len(tokens))
        
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.endswith(".uci.edu"):
            subdomain_counts[domain] = subdomain_counts.get(domain, 0) + 1
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
            clean_url = urldefrag(absolute_url)[0]

            links.append(clean_url)

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

        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        full_url = url.lower()

        # allow only the required UCI domains
        valid_domains = [
        "ics.uci.edu",
        "cs.uci.edu",
        "informatics.uci.edu",
        "stat.uci.edu"
        ]

        if not any(domain == d or domain.endswith("." + d) for d in valid_domains):
            return False

        #make sure  no falling into traps

        # very long URLs
        if len(url) > 300:
            return False

        # long query strings
        if len(parsed.query) > 100:
            return False

        # too many path segments
        path_sections = [p for p in path.split("/") if p]
        if len(path_sections) > 12:
            return False

        # repeating directories(endless loops)
        if len(path_sections) != len(set(path_sections)) and len(path_sections) > 7:
            return False

        # common trap keywords
        trap_keys = [
            "calendar", "date=", "month=", "year=",
            "login", "logout", "session",
            "sort=", "filter=",
            "rss", "feed"
        ]

        if any(word in full_url for word in trap_keys):
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
    f = open("report.txt", "w")

    f.write("Unique Pages:" + str(len(unique_urls)) + "\n")
    f.write("Longest Page:" + longest_page_info[0] + "\n")
    f.write("Word Count: " + str(longest_page_info[1]) + "\n")
    top_words = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)[:50]
    f.write("Top 50 Words: " + str(top_words) + "\n")
    f.write("Subdomains: " + str(sorted(subdomain_counts.items())) + "\n")

    f.close()

if __name__ == "__main__":
    make_report()
