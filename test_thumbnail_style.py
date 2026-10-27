import unittest
from PIL import Image, ImageChops
from thumbnail_style import add_caption
from human_history import visual_prompt


class ThumbnailStyleTests(unittest.TestCase):
    def test_caption_stays_inside_reserved_left_area(self):
        original = Image.new('RGB', (1280, 720), '#123456')
        image = original.copy()
        add_caption(image, 'LAST EMBER', placement='upper-left')
        bounds = ImageChops.difference(original, image).getbbox()
        self.assertIsNotNone(bounds)
        self.assertLess(bounds[2], 600)
        self.assertLess(bounds[3], 330)

    def test_thumbnail_uses_dedicated_close_composition(self):
        action = 'A worried adult cups a glowing coal near their face'
        prompt = visual_prompt(action, thumbnail=True)
        self.assertIn(action, prompt)
        self.assertIn('Tight framing, dominant subject on right', prompt)
        self.assertIn('uncluttered left third', prompt)
        self.assertNotIn('Clear environmental composition', prompt)


if __name__ == '__main__':
    unittest.main()
