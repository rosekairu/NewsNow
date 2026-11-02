## NewsNow

#### A newspaper-style news site that gathers the latest headlines from publishers around the world.

### Description
NewsNow reads publishers' own RSS and Atom news feeds and lays the stories out like a newspaper front page. Every story links to the original article.

- **Top Stories** from BBC News, NPR, The New York Times and Al Jazeera.
- **Topics:** general, business, entertainment, health, science, technology and sports.
- **Sections:** Africa, AI, Research (new arXiv papers and Nature), Startups and Funding.
- **Countries:** 19 countries, including Kenya, Nigeria, Ghana and South Africa, each from local outlets.
- **Sources:** a page for each of the 39 outlets.
- **Search** across every page, or within a single outlet.

Feeds need no API key and have no request limits. Each feed is cached for 30 minutes. When a feed has no photo for a story, the article's share photo is looked up from its page, at most two at a time per publisher, and remembered for a day.

### Technologies Used
1. Python 3 and Flask 3
2. feedparser, for reading news feeds
3. HTML and CSS, with Newsreader and IBM Plex Sans from Google Fonts
4. Gunicorn, for serving the site in production

### Running Locally

1. Create a virtual environment and install the dependencies:
   ```bash
   python3 -m venv .venv
   ./.venv/bin/pip install -r requirements.txt
   ```
2. Start the server and open http://127.0.0.1:5000:
   ```bash
   ./.venv/bin/python manage.py
   ```
3. Run the tests:
   ```bash
   ./.venv/bin/python -m unittest discover tests
   ```

### Adding a news source
All outlets and pages are defined at the top of [app/feeds.py](app/feeds.py). Add the outlet to `outlets`, then add `feed('outlet-id')` to any topic, section or country.

### Deploying to Render
The repository includes a [render.yaml](render.yaml) Blueprint for Render's free plan.

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint** and select the repository. Render reads `render.yaml`, installs the requirements and starts the site with Gunicorn.
3. The site appears at an address like `https://newsnow.onrender.com`.

On the free plan the site sleeps after 15 minutes without visitors, and the next visit takes about a minute to wake it.
