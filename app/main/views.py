from datetime import date
from flask import render_template, request, redirect, url_for, abort
from . import main
from ..feeds import (outlets, feed, top_stories, topics, sections, countries,
                     get_articles, search, outlet_feeds, source_list, credit, find_page_image)


# Order of the links in the section bar, after Top Stories
nav_order=['general', 'africa', 'ai', 'startups', 'funding', 'technology', 'research',
           'science', 'health', 'business', 'entertainment', 'sports']


@main.app_context_processor
def navigation():
    nav_links=[]
    for page_id in nav_order:
        if page_id in topics:
            nav_links.append((url_for('main.news_category', id=page_id), topics[page_id][0]))
        else:
            nav_links.append((url_for('main.news_section', id=page_id), sections[page_id][0]))

    return dict(
        nav_links=nav_links,
        nav_countries=[(code, name) for code, (name, feeds) in countries.items()],
        sources=source_list(),
        today=date.today()
    )


@main.route('/')
@main.route('/home')
def index():
    topic_name = request.args.get('topic_query')

    if topic_name:
        return redirect(url_for('.news_topic', query=topic_name))

    return render_template('index.html', title="NewsNow", breaking_news=get_articles(top_stories))


@main.route('/source/<id>')
def news_source(id):
    if id not in outlets:
        abort(404)

    title=outlets[id]['name']
    topic_name = request.args.get('from_source')

    if topic_name:
        return redirect(url_for('.news_in_source', source_nm=title, this_source=id, query=topic_name))

    return render_template('news_list.html', kicker="Source", title=title, news_list=get_articles([feed(id)]), source_title=title)


@main.route('/breaking')
def breaking_news():
    return render_template('news_list.html', kicker="Top stories", title="Breaking News", subtitle=credit(top_stories), news_list=get_articles(top_stories))


@main.route('/categories/<id>')
def news_category(id):
    if id not in topics:
        abort(404)

    title, feeds=topics[id]
    return render_template('news_list.html', kicker="Topic", title=title, subtitle=credit(feeds), news_list=get_articles(feeds))


@main.route('/countries/<id>')
def news_country(id):
    if id not in countries:
        abort(404)

    title, feeds=countries[id]
    return render_template('news_list.html', kicker="Country", title=title, subtitle=credit(feeds), news_list=get_articles(feeds))


@main.route('/sections/<id>')
def news_section(id):
    if id not in sections:
        abort(404)

    title, feeds=sections[id]
    return render_template('news_list.html', kicker="Section", title=title, subtitle=credit(feeds), news_list=get_articles(feeds))


@main.route('/article-image')
def article_image():
    image=find_page_image(request.args.get('url', ''))
    if not image:
        return '', 404

    response=redirect(image)
    response.headers['Cache-Control']='public, max-age=86400'
    return response


@main.route('/topic/<query>')
def news_topic(query):
    return render_template('news_list.html', kicker="Search results", title=query, subtitle="Matching headlines from the latest stories on every page of NewsNow", news_list=search(query))


@main.route('/fromSource/<source_nm>/<this_source>/<query>')
def news_in_source(source_nm, this_source, query):
    if this_source not in outlets:
        abort(404)

    topic_name = request.args.get('from_source')

    if topic_name:
        return redirect(url_for('.news_in_source', source_nm=source_nm, this_source=this_source, query=topic_name))

    return render_template('news_list.html', kicker="Search results in "+source_nm, title=query, news_list=search(query, outlet_feeds(this_source)), source_title=source_nm)
