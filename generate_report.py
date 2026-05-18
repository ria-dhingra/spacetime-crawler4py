import json

with open("stats_backup.json") as f:
    stats = json.load(f)

with open("report.txt", "w") as f:
    f.write(f"1. Unique pages: {stats['unique_pages_count']}\n\n")
    
    f.write(f"2. Longest page: {stats['longest_page'][0]} ({stats['longest_page'][1]} words)\n\n")
    
    f.write("3. 50 most common words:\n")
    for word, count in stats['top_50_words']:
        f.write(f"   {word} - {count}\n")
    f.write("\n")
    
    f.write(f"4. Subdomains found: {len(stats['subdomains'])}\n")
    for subdomain, count in sorted(stats['subdomains'].items()):
        f.write(f"   {subdomain}, {count}\n")