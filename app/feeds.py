"""News for every page of the site, read from publishers' own RSS/Atom feeds.

Feeds need no API key and have no daily request limit. Each feed is cached for 30 minutes.
"""
import html, http.client, re, threading, time, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import feedparser
from .models import NewsArticle, Sources

USER_AGENT='Mozilla/5.0 (compatible; NewsNow)'

CACHE_SECONDS=30*60
MAX_ARTICLES=30
MAX_SUMMARY=400

# Share photos looked up from article pages change rarely, so they are kept for a day
PAGE_IMAGE_SECONDS=24*60*60
PAGE_IMAGE_PATH='/article-image'

# TechCrunch feeds include adverts for its own events under this author name
SKIP_AUTHORS={'TechCrunch Events'}


# Every outlet the site reads. 'url' is the outlet's main feed, used on its source page.
outlets={
    'bbc-news': {'name': 'BBC News', 'url': 'https://feeds.bbci.co.uk/news/rss.xml'},
    'npr': {'name': 'NPR', 'url': 'https://feeds.npr.org/1001/rss.xml'},
    'nyt': {'name': 'The New York Times', 'url': 'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml'},
    'al-jazeera': {'name': 'Al Jazeera', 'url': 'https://www.aljazeera.com/xml/rss/all.xml'},
    'espn': {'name': 'ESPN', 'url': 'https://www.espn.com/espn/rss/news'},
    'the-verge': {'name': 'The Verge', 'url': 'https://www.theverge.com/rss/index.xml'},
    'techcrunch': {'name': 'TechCrunch', 'url': 'https://techcrunch.com/feed/'},
    'mit-technology-review': {'name': 'MIT Technology Review', 'url': 'https://www.technologyreview.com/feed/'},
    'crunchbase-news': {'name': 'Crunchbase News', 'url': 'https://news.crunchbase.com/feed/'},
    'tech-eu': {'name': 'Tech.eu', 'url': 'https://tech.eu/feed/'},
    'techcabal': {'name': 'TechCabal', 'url': 'https://techcabal.com/feed/'},
    'disrupt-africa': {'name': 'Disrupt Africa', 'url': 'https://disruptafrica.com/feed/'},
    # allAfrica republishes African outlets and names the original one in brackets.
    # It blocks repeated page requests, so its stories don't get photos looked up.
    'allafrica': {'name': 'allAfrica', 'url': 'https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf',
                  'outlet_in_summary': True, 'page_images': False},
    # The Africa edition mixes in French articles
    'the-conversation-africa': {'name': 'The Conversation Africa', 'url': 'https://theconversation.com/africa/articles.atom',
                                'english_only': True},
    'arxiv': {'name': 'arXiv', 'kind': 'paper',
              'url': 'https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=30'},
    # Nature's summaries start with a citation line, and its feed includes correction notices
    'nature': {'name': 'Nature', 'url': 'https://www.nature.com/nature.rss',
               'summary_prefix': r'^Nature, Published online: [^;]+; doi:\S+\s*',
               'skip_titles': ('Author Correction', 'Publisher Correction', 'Correction', 'Retraction Note')},
    'cbc': {'name': 'CBC News', 'url': 'https://www.cbc.ca/webfeed/rss/rss-topstories'},
    'abc-australia': {'name': 'ABC News Australia', 'url': 'https://www.abc.net.au/news/feed/51120/rss.xml'},
    'rnz': {'name': 'RNZ', 'url': 'https://www.rnz.co.nz/rss/national.xml'},
    'the-hindu': {'name': 'The Hindu', 'url': 'https://www.thehindu.com/news/national/feeder/default.rss'},
    'times-of-india': {'name': 'The Times of India', 'url': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms'},
    'sabc-news': {'name': 'SABC News', 'url': 'https://www.sabcnews.com/sabcnews/feed/'},
    'daily-maverick': {'name': 'Daily Maverick', 'url': 'https://www.dailymaverick.co.za/dmrss/'},
    'dw': {'name': 'DW', 'url': 'https://rss.dw.com/rdf/rss-en-ger'},
    'rfi': {'name': 'RFI', 'url': 'https://www.rfi.fr/en/france/rss'},
    'the-local-france': {'name': 'The Local France', 'url': 'https://www.thelocal.fr/feeds/rss.php'},
    'ansa': {'name': 'ANSA', 'url': 'https://www.ansa.it/english/news/english_nr_rss.xml'},
    'moscow-times': {'name': 'The Moscow Times', 'url': 'https://www.themoscowtimes.com/rss/news'},
    'times-of-israel': {'name': 'The Times of Israel', 'url': 'https://www.timesofisrael.com/feed/'},
    'japan-times': {'name': 'The Japan Times', 'url': 'https://www.japantimes.co.jp/feed/'},
    'scmp': {'name': 'South China Morning Post', 'url': 'https://www.scmp.com/rss/4/feed'},
    'mexico-news-daily': {'name': 'Mexico News Daily', 'url': 'https://mexiconewsdaily.com/feed/'},
    'dutchnews': {'name': 'DutchNews', 'url': 'https://www.dutchnews.nl/feed/'},
    'nl-times': {'name': 'NL Times', 'url': 'https://nltimes.nl/rss'},
    'nation-africa': {'name': 'Nation', 'url': 'https://nation.africa/kenya/rss.xml'},
    'the-standard': {'name': 'The Standard', 'url': 'https://www.standardmedia.co.ke/rss/headlines.php'},
    'premium-times': {'name': 'Premium Times', 'url': 'https://www.premiumtimesng.com/feed'},
    'punch': {'name': 'Punch', 'url': 'https://punchng.com/feed/'},
    'myjoyonline': {'name': 'MyJoyOnline', 'url': 'https://www.myjoyonline.com/feed/'},
}


def feed(outlet_id, url=None):
    """A feed from one of the outlets above; url defaults to the outlet's main feed."""
    outlet=outlets[outlet_id]
    return dict(outlet, outlet=outlet_id, url=url or outlet['url'])


top_stories=[feed('bbc-news'), feed('npr'), feed('nyt'), feed('al-jazeera')]

# Topic id: (title, feeds)
topics={
    'general': ('General', [
        feed('bbc-news', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
        feed('al-jazeera'),
        feed('nyt'),
    ]),
    'business': ('Business', [
        feed('bbc-news', 'https://feeds.bbci.co.uk/news/business/rss.xml'),
        feed('npr', 'https://feeds.npr.org/1006/rss.xml'),
        feed('nyt', 'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml'),
    ]),
    'entertainment': ('Entertainment', [
        feed('bbc-news', 'https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml'),
        feed('npr', 'https://feeds.npr.org/1008/rss.xml'),
    ]),
    'health': ('Health', [
        feed('bbc-news', 'https://feeds.bbci.co.uk/news/health/rss.xml'),
        feed('npr', 'https://feeds.npr.org/1128/rss.xml'),
    ]),
    'science': ('Science', [
        feed('bbc-news', 'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml'),
        feed('npr', 'https://feeds.npr.org/1007/rss.xml'),
    ]),
    'technology': ('Technology', [
        feed('bbc-news', 'https://feeds.bbci.co.uk/news/technology/rss.xml'),
        feed('npr', 'https://feeds.npr.org/1019/rss.xml'),
        feed('the-verge'),
    ]),
    'sports': ('Sports', [
        feed('bbc-news', 'https://feeds.bbci.co.uk/sport/rss.xml'),
        feed('espn'),
    ]),
}

sections={
    'africa': ('Africa', [feed('allafrica'), feed('the-conversation-africa')]),
    'ai': ('AI', [
        feed('techcrunch', 'https://techcrunch.com/category/artificial-intelligence/feed/'),
        feed('mit-technology-review', 'https://www.technologyreview.com/topic/artificial-intelligence/feed'),
        feed('the-verge', 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml'),
    ]),
    'research': ('Research', [feed('arxiv'), feed('nature')]),
    'startups': ('Startups', [
        feed('techcrunch', 'https://techcrunch.com/category/startups/feed/'),
        feed('techcabal'),
        feed('disrupt-africa'),
        feed('tech-eu'),
    ]),
    'funding': ('Funding', [
        feed('crunchbase-news'),
        feed('techcrunch', 'https://techcrunch.com/category/venture/feed/'),
    ]),
}

# Country code: (name, feeds)
countries={
    'au': ('Australia', [feed('abc-australia')]),
    'ca': ('Canada', [feed('cbc')]),
    'cn': ('China', [feed('scmp')]),
    'fr': ('France', [feed('rfi'), feed('the-local-france')]),
    'de': ('Germany', [feed('dw')]),
    'gh': ('Ghana', [feed('myjoyonline')]),
    'in': ('India', [feed('the-hindu'), feed('times-of-india')]),
    'il': ('Israel', [feed('times-of-israel')]),
    'it': ('Italy', [feed('ansa')]),
    'jp': ('Japan', [feed('japan-times')]),
    'ke': ('Kenya', [feed('nation-africa'), feed('the-standard')]),
    'mx': ('Mexico', [feed('mexico-news-daily')]),
    'nl': ('Netherlands', [feed('dutchnews'), feed('nl-times')]),
    'nz': ('New Zealand', [feed('rnz')]),
    'ng': ('Nigeria', [feed('premium-times'), feed('punch')]),
    'ru': ('Russia', [feed('moscow-times')]),
    'za': ('South Africa', [feed('sabc-news'), feed('daily-maverick')]),
    'gb': ('United Kingdom', [feed('bbc-news', 'https://feeds.bbci.co.uk/news/uk/rss.xml')]),
    'us': ('United States', [feed('npr', 'https://feeds.npr.org/1003/rss.xml'), feed('nyt')]),
}

# Every distinct feed on the site, which is what the search box looks through
all_feeds=list({f['url']: f for feeds in [top_stories]+[page[1] for page in list(topics.values())+list(sections.values())+list(countries.values())] for f in feeds}.values())


def outlet_feeds(outlet_id):
    """All of an outlet's feeds used on the site, for searching within that outlet."""
    return [f for f in all_feeds if f['outlet']==outlet_id] or [feed(outlet_id)]

FRENCH_WORDS={'les', 'des', 'pour', 'une', 'dans', 'du', 'comment', 'pourquoi', 'est', 'sur', 'aux', 'et', 'ou', 'qui', 'que'}

_cache={}
_page_images={}

# Article pages the app may look up photos for: only links that came from these feeds
_known_articles=set()

# Look up at most two photos at a time per website, so pages loading don't flood a publisher
_host_limits=defaultdict(lambda: threading.BoundedSemaphore(2))
_host_limits_lock=threading.Lock()


def load_entries(url):
    """Download and parse a feed, returning its entries, or [] if it can't be fetched."""
    cached=_cache.get(url)
    if cached and time.time()-cached[0]<CACHE_SECONDS:
        return cached[1]

    try:
        request=urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(request, timeout=10) as response:
            entries=feedparser.parse(response.read()).entries
    except (OSError, http.client.HTTPException, ValueError):
        return []

    _cache[url]=(time.time(), entries)
    return entries


def clean_text(value):
    text=re.sub(r'<[^>]+>', ' ', value or '')
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def looks_french(title):
    words=re.findall(r"[a-zà-ÿ]+", title.lower())
    return sum(word in FRENCH_WORDS for word in words)>=2


def date_pipe(date):
    """Format an ISO timestamp as e.g. '2 Nov 2026, 14:52'."""
    try:
        parsed=datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')
    except (TypeError, ValueError):
        return ''
    return '{} {}'.format(parsed.day, parsed.strftime('%b %Y, %H:%M'))


def find_image(entry):
    for media in entry.get('media_content', []) + entry.get('media_thumbnail', []):
        if media.get('url') and media.get('medium', 'image')=='image':
            return media['url']

    for link in entry.get('enclosures', []):
        if link.get('type', '').startswith('image/'):
            return link.get('href')

    markup=entry.get('summary', '')+' '.join(part.get('value', '') for part in entry.get('content', []))
    for tag in re.findall(r'<img[^>]+>', markup):
        # Skip 1x1 tracking pixels, such as The Conversation's view counter
        if re.search(r'''(width|height)=["']?1["'\s/>]''', tag):
            continue
        src=re.search(r'src="([^"]+)"', tag)
        if src:
            return src.group(1)
    return None


def page_image_url(article_url):
    """App URL that redirects to an article's share photo, for feeds that don't include photos."""
    _known_articles.add(article_url)
    return PAGE_IMAGE_PATH+'?'+urllib.parse.urlencode({'url': article_url})


def find_page_image(article_url):
    """Read the og:image share photo from an article page, or None."""
    if article_url not in _known_articles:
        return None

    cached=_page_images.get(article_url)
    if cached and time.time()-cached[0]<PAGE_IMAGE_SECONDS:
        return cached[1]

    with _host_limits_lock:
        host_limit=_host_limits[urllib.parse.urlparse(article_url).hostname]

    try:
        with host_limit:
            request=urllib.request.Request(article_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(request, timeout=10) as response:
                page=response.read(300000).decode('utf-8', 'ignore')
    except (OSError, http.client.HTTPException, ValueError):
        return None

    image=None
    for tag in re.findall(r'<meta[^>]+>', page):
        if re.search(r'''(property|name)=["']og:image["']''', tag):
            content=re.search(r'''content=["']([^"']+)["']''', tag)
            if content:
                image=html.unescape(content.group(1))
            break

    # Sites fall back to their logo when a story has no photo; text-only looks better
    if image and 'logo' in image.lower():
        image=None

    _page_images[article_url]=(time.time(), image)
    return image


def to_article(entry, feed):
    title=clean_text(entry.get('title'))
    url=entry.get('link')
    if not title or not url:
        return None
    if entry.get('author') in SKIP_AUTHORS:
        return None
    if feed.get('english_only') and looks_french(title):
        return None
    if title.startswith(feed.get('skip_titles', ())):
        return None

    summary=clean_text(entry.get('summary'))
    if feed.get('summary_prefix'):
        summary=re.sub(feed['summary_prefix'], '', summary)
    source_name=feed['name']

    if feed.get('outlet_in_summary'):
        match=re.match(r'\[([^\]]+)\]\s*', summary)
        if match:
            if match.group(1)!=feed['name']:
                source_name=match.group(1)+' via '+feed['name']
            summary=summary[match.end():]

    if len(summary)>MAX_SUMMARY:
        summary=summary[:MAX_SUMMARY].rsplit(' ', 1)[0]+'…'

    kind=feed.get('kind', 'article')
    if kind=='paper':
        names=[author.get('name') for author in entry.get('authors', []) if author.get('name')]
        author=', '.join(names[:3])+(' et al.' if len(names)>3 else '')
    else:
        author=entry.get('author')

    published=entry.get('published_parsed') or entry.get('updated_parsed')
    published_iso=time.strftime('%Y-%m-%dT%H:%M:%SZ', published) if published else None

    image=find_image(entry)
    if not image and kind!='paper' and feed.get('page_images', True):
        image=page_image_url(url)

    article=NewsArticle(source_name, author, title, url, image, date_pipe(published_iso), summary or None, None, feed['outlet'], published_iso)
    article.kind=kind
    return article


def load_articles(feed):
    articles=[to_article(entry, feed) for entry in load_entries(feed['url'])]
    articles=[article for article in articles if article]
    return sorted(articles, key=lambda article: article.published_iso or '', reverse=True)


def load_all(feeds):
    with ThreadPoolExecutor(max_workers=min(len(feeds), 12)) as pool:
        return list(pool.map(load_articles, feeds))


def get_articles(feeds):
    """Latest articles from several feeds, alternating between them so no single outlet dominates."""
    per_feed=load_all(feeds)

    results=[]
    seen=set()
    for position in range(max((len(articles) for articles in per_feed), default=0)):
        for articles in per_feed:
            if position<len(articles) and articles[position].url not in seen:
                seen.add(articles[position].url)
                results.append(articles[position])

    return results[:MAX_ARTICLES] or None


def search(query, feeds=None):
    """Newest articles whose headline or summary contains every word of the query."""
    words=query.lower().split()
    if not words:
        return None

    matches={}
    for articles in load_all(feeds or all_feeds):
        for article in articles:
            text=(article.title+' '+(article.description or '')).lower()
            if all(word in text for word in words):
                matches.setdefault(article.url, article)

    results=sorted(matches.values(), key=lambda article: article.published_iso or '', reverse=True)
    return results[:MAX_ARTICLES] or None


def source_list():
    """Every outlet, alphabetically, for the Sources menu and directory."""
    ordered=sorted(outlets.items(), key=lambda item: item[1]['name'].lower().replace('the ', '', 1))
    return [Sources(outlet_id, outlet['name']) for outlet_id, outlet in ordered]


def credit(feeds):
    """'From BBC News, NPR and Al Jazeera' for the outlets behind a page."""
    names=[]
    for f in feeds:
        if f['name'] not in names:
            names.append(f['name'])
    if len(names)==1:
        return 'From '+names[0]
    return 'From '+', '.join(names[:-1])+' and '+names[-1]
