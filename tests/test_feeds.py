import time
import unittest
from app.feeds import clean_text, date_pipe, find_image, looks_french, to_article, feed, credit


class FeedHelpersTest(unittest.TestCase):
    '''
    Test Class for the helpers that turn feed entries into articles
    '''

    def test_clean_text_strips_tags_and_entities(self):
        self.assertEqual(clean_text('<p>Fish &amp; chips</p>\n<br> today'), 'Fish & chips today')

    def test_date_pipe(self):
        self.assertEqual(date_pipe('2026-11-02T14:52:00Z'), '2 Nov 2026, 14:52')
        self.assertEqual(date_pipe(None), '')

    def test_looks_french(self):
        self.assertTrue(looks_french("Comment les séries coréennes utilisent l'Afrique pour redorer leur image"))
        self.assertFalse(looks_french('Why the WHO must declare climate change a public health emergency'))

    def test_find_image_skips_tracking_pixels(self):
        entry={'summary': '<img src="https://example.com/count.gif" width="1" height="1" /><img src="https://example.com/photo.jpg">'}
        self.assertEqual(find_image(entry), 'https://example.com/photo.jpg')

    def test_allafrica_credits_original_outlet(self):
        entry={'title': 'Kenya: Ebola Update', 'link': 'https://allafrica.com/stories/1.html',
               'summary': '[Capital FM] Nairobi -- The government is expected to release contacts.',
               'published_parsed': time.gmtime(0)}
        article=to_article(entry, feed('allafrica'))
        self.assertEqual(article.source_name, 'Capital FM via allAfrica')
        self.assertEqual(article.description, 'Nairobi -- The government is expected to release contacts.')
        self.assertIsNone(article.url_to_image)

    def test_techcrunch_event_adverts_are_skipped(self):
        entry={'title': '4 days left to register', 'link': 'https://techcrunch.com/x', 'author': 'TechCrunch Events'}
        self.assertIsNone(to_article(entry, feed('techcrunch')))

    def test_credit(self):
        self.assertEqual(credit([feed('bbc-news'), feed('npr'), feed('bbc-news')]), 'From BBC News and NPR')
